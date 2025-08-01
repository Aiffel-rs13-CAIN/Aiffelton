import os
import json
from pathlib import Path
from typing import Any


def load_a2a_config(path: str | Path) -> dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)



def load_a2a_server_addresses_from_config_dir(config_dir: str, except_file: str = None) -> list[dict[str, str]]:
    """
    지정한 디렉터리에서 A2A 설정 파일을 읽고, 각 파일의 host/port를 기반으로
    A2A 서버 URL을 구성해 리스트로 반환합니다.

    Args:
        config_dir (str): JSON 설정 파일들이 들어있는 디렉터리 경로
        except_file (str): 제외할 JSON 설정 파일 (my own)

    Returns:
        list[dict[str, str]]: [{'name': agent name, 'url': 'http://host:port/'}]
    """
    server_entries = []

    for filename in os.listdir(config_dir):
        if filename.endswith(".json"):
            if except_file and filename == except_file : 
                continue
            
            config_path = os.path.join(config_dir, filename)
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                host = config.get("host")
                port = config.get("port")
                name = config.get("name")
                if not host or not port:
                    print(f"[경고] {filename}에 host 또는 port 정보가 없습니다. 건너뜁니다.")
                    continue

                url = f"http://{host}:{port}/"
                server_entries.append({"name": name, "url": url})

            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"[에러] {filename} 파일 처리 중 오류 발생: {e}")

    return server_entries
