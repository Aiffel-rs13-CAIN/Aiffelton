#!/usr/bin/env bash
set -euo pipefail

# -----------------------
# defaults
# -----------------------
INPUT=""
SPLITS=2
RESULTS_ROOT="Results"
MERGE_NAME=""
MODE="block"      # block | rr
JOBS=""           # default = SPLITS
DRYRUN=0
USE_LINK=0

# -----------------------
# args
# -----------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)       INPUT="$2"; shift 2;;
    --splits)      SPLITS="${2}"; shift 2;;
    --results-root)RESULTS_ROOT="$2"; shift 2;;
    --merge-name)  MERGE_NAME="$2"; shift 2;;
    --mode)        MODE="$2"; shift 2;;
    --jobs)        JOBS="$2"; shift 2;;
    --dry-run)     DRYRUN=1; shift 1;;
    --link)        USE_LINK=1; shift 1;;
    -h|--help)
      cat <<EOF
Usage: $0 --input <tasks.jsonl> [--splits N] [--results-root results] [--merge-name NAME]
          [--mode block|rr] [--jobs K] [--dry-run] [--link]

- --input         : 원본 JSONL (필수)
- --splits        : 분할 개수(=병렬 수), 기본 2
- --results-root  : 결과 루트 폴더 이름 (기본 results)
- --merge-name    : 최종 병합 폴더 이름 (기본: 원본 파일명)
- --mode          : block(앞뒤로 균등 분할) | rr(라운드로빈), 기본 block
- --jobs          : 동시에 돌릴 run 수 (기본 = splits)
- --dry-run       : 실행만 출력, 실제 수행 안 함
- --link          : 병합 시 mv 대신 심볼릭 링크 사용(공간 절약)
EOF
      exit 0;;
    *)
      echo "[ERR] unknown arg: $1" >&2; exit 1;;
  esac
done

[[ -z "$INPUT" ]] && { echo "[ERR] --input is required"; exit 1; }
[[ -f "$INPUT" ]] || { echo "[ERR] not found: $INPUT"; exit 1; }
[[ "$SPLITS" -ge 1 ]] || { echo "[ERR] --splits must be >=1"; exit 1; }
[[ -z "$JOBS" ]] && JOBS="$SPLITS"

# 도구 확인
command -v autogenbench >/dev/null || { echo "[ERR] autogenbench not in PATH"; exit 1; }

# 경로/이름
INPUT_ABS="$(readlink -f "$INPUT")"
INPUT_DIR="$(dirname "$INPUT_ABS")"
BASENAME="$(basename "$INPUT_ABS" .jsonl)"
SPLIT_DIR="splits_${BASENAME}"
LOG_DIR="$SPLIT_DIR/_logs"
mkdir -p "$SPLIT_DIR" "$LOG_DIR"

[[ -z "$MERGE_NAME" ]] && MERGE_NAME="$BASENAME"

echo "[INFO] input       : $INPUT_ABS"
echo "[INFO] splits      : $SPLITS (mode=$MODE)"
echo "[INFO] resultsRoot : $RESULTS_ROOT"
echo "[INFO] mergeName   : $MERGE_NAME"
echo "[INFO] jobs(par)   : $JOBS"
[[ $DRYRUN -eq 1 ]] && echo "[INFO] DRY RUN mode"
[[ $USE_LINK -eq 1 ]] && echo "[INFO] Merge by symbolic links"

# -----------------------
# 1) 분할
# -----------------------
TOTAL=$(wc -l < "$INPUT_ABS")
if [[ "$MODE" == "block" ]]; then
  LINES_PER=$(( (TOTAL + SPLITS - 1) / SPLITS ))
  echo "[INFO] total lines: $TOTAL -> block splits, ~$LINES_PER per file"
  if [[ $DRYRUN -eq 0 ]]; then
    split -d -l "$LINES_PER" "$INPUT_ABS" "$SPLIT_DIR/${BASENAME}."
    idx=0
    for f in "$SPLIT_DIR/${BASENAME}."*; do
      mv "$f" "$SPLIT_DIR/${BASENAME}.part${idx}.jsonl"
      idx=$((idx+1))
    done
  else
    echo split -d -l "$LINES_PER" "$INPUT_ABS" "$SPLIT_DIR/${BASENAME}."
  fi
else
  echo "[INFO] total lines: $TOTAL -> round-robin splits"
  if [[ $DRYRUN -eq 0 ]]; then
    for i in $(seq 0 $((SPLITS-1))); do
      : > "$SPLIT_DIR/${BASENAME}.part${i}.jsonl"
    done
    awk -v N="$SPLITS" -v prefix="$SPLIT_DIR/${BASENAME}.part" '{
      i = (NR-1)%N;
      fn = prefix""i".jsonl";
      print $0 >> fn
    }' "$INPUT_ABS"
  else
    echo "[DRY] round-robin write -> $SPLIT_DIR/${BASENAME}.part*.jsonl"
  fi
fi

# 생성된 분할 파일 리스트
PARTS=()
for i in $(seq 0 $((SPLITS-1))); do
  PARTS+=("$SPLIT_DIR/${BASENAME}.part${i}.jsonl")
done

# -----------------------
# 2) 병렬 실행
# -----------------------
pids=()
running=0

run_one() {
  local part="$1"
  local name="$(basename "$part" .jsonl)"   # 시나리오명으로 사용됨
  local log="$LOG_DIR/${name}.log"
  echo "[RUN] autogenbench run $part  (log: $log)"
  if [[ $DRYRUN -eq 0 ]]; then
    autogenbench run "$part" >"$log" 2>&1
  else
    echo "[DRY] autogenbench run $part > $log 2>&1"
  fi
}

for part in "${PARTS[@]}"; do
  # 동시 JOBS 개수 제한
  while [[ $running -ge $JOBS ]]; do
    wait -n || true
    running=$((running-1))
  done
  run_one "$part" &
  pids+=($!)
  running=$((running+1))
done

# 남은 것 대기
for pid in "${pids[@]}"; do
  wait "$pid" || true
done
echo "[INFO] all runs finished."

# -----------------------
# 3) 병합 (id 기반)
#    results/<partName>/<task_id>/<instance_id>  ->  results/<MERGE_NAME>/<task_id>/<instance_id>
# -----------------------
MERGE_DST="$RESULTS_ROOT/$MERGE_NAME"
[[ $DRYRUN -eq 0 ]] && mkdir -p "$MERGE_DST"

move_or_link_dir() {
  local src="$1"
  local dst="$2"
  if [[ $USE_LINK -eq 1 ]]; then
    # 심볼릭 링크
    ln -s "$src" "$dst"
  else
    mv "$src" "$dst"
  fi
}

echo "[INFO] merging into: $MERGE_DST"

dups=0
for part in "${PARTS[@]}"; do
  partName="$(basename "$part" .jsonl)"           # 예: medqa_tasks.part0
  srcScenario="$RESULTS_ROOT/$partName"
  if [[ ! -d "$srcScenario" ]]; then
    echo "[WARN] results not found for $partName -> skip"
    continue
  fi

  # 구조 검증: id 기반이라고 가정. (id 디렉터리가 있고 그 아래 instance 디렉터리)
  # id 목록 순회
  shopt -s nullglob
  for idDir in "$srcScenario"/*; do
    [[ -d "$idDir" ]] || continue
    idBase="$(basename "$idDir")"
    dstId="$MERGE_DST/$idBase"

    if [[ -e "$dstId" ]]; then
      # 이미 동일 id가 있으면: 각 instance 하위만 병합 시도
      echo "[WARN] duplicate task_id: $idBase -> merging instance subdirs"
      for inst in "$idDir"/*; do
        [[ -d "$inst" ]] || continue
        instBase="$(basename "$inst")"
        srcInst="$idDir/$instBase"
        dstInst="$dstId/$instBase"
        if [[ -e "$dstInst" ]]; then
          echo "[WARN]   instance exists: $idBase/$instBase (skip)"
          dups=$((dups+1))
          continue
        fi
        echo "[MERGE] $partName:$idBase/$instBase -> $MERGE_NAME/$idBase/$instBase"
        if [[ $DRYRUN -eq 0 ]]; then
          mkdir -p "$dstId"
          move_or_link_dir "$srcInst" "$dstInst"
        fi
      done
      # 빈 idDir 정리
      rmdir "$idDir" >/dev/null 2>&1 || true
    else
      echo "[MERGE] $partName:$idBase -> $MERGE_NAME/$idBase"
      if [[ $DRYRUN -eq 0 ]]; then
        move_or_link_dir "$idDir" "$dstId"
      fi
    fi
  done
  shopt -u nullglob

  # 빈 시나리오 폴더 정리(선택)
  if [[ $DRYRUN -eq 0 ]]; then
    rmdir "$srcScenario" >/dev/null 2>&1 || true
  fi
done

if [[ $dups -gt 0 ]]; then
  echo "[WARN] duplicates encountered during instance merge: $dups"
fi

echo "[OK] done. merged results -> $MERGE_DST"

