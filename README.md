# Aiffelthon 프로젝트

이 저장소는 아이펠 리서치 13기 **CAIN팀**의 Aiffelthon 프로젝트 전체를 관리하는 메인 레포지토리입니다.  
Autogen을 이용한 멀티에이전트 충돌 실험의 코드가 포함되어 있습니다.

## 핵심 연구주제

연구 주제: 다중 에이전트 협업에서 지식 충돌(Knowledge Conflict)의 역할 분석 및 MAS의 협업적 의사결정과 견고성에 미치는 영향 연구

핵심 가설: 지식 충돌이 단순한 장애물이 아니라, LLM 기반 MAS에서 적응적 견고성(adaptive robustness)을 유도하는 핵심 메커니즘으로 작용한다는 관점에서 연구를 수행하였습니다.

기존 논문에서 다루지 않은 도메인(의료) 문제들을 대상으로 Closed Model을 활용한 추가 실험을 설계하고 진행하였으며, 해당 실험의 전체 코드를 본 레포지토리를 통해 공개합니다.

(베이스라인 참고 논문: https://arxiv.org/pdf/2502.15153)

## 👥 팀 및 역할

**팀명**: CAIN <br />
**팀장**: 강희봉 - 프로젝트 전체 진행 관리, 관련 논문/래퍼런스 서치, 실험 설계 조율<br />
**팀원**: 김청해 - 관련 논문/래퍼런스 서치, AutogenBench 세팅 및 실험, Langgraph기반 에이전트 설계 및 구현<br />
**팀원**: 김영숙 - 관련 논문/래퍼런스 서치, AutogenBench 실험 보조, A2A 프로토콜 모듈 설계 및 구현

## 📁 프로젝트 구조

```
Agent/
├── agent-ai                   # A2A, Langgraphs기반 멀티에이전트 구축 (mem0, MCP 연동)
├── MedQA_Autogen/             # AutogenBench 기반 MedQA 시나리오 탐색용 코드
└── autogenbench_medQA         # AutogenBench 기반 MedQA 최종 시나리오 및 매트릭 탐색, 테스트
```

## 🔧 추가 구현 코드

프로젝트의 주요 실험 외에도 다음과 같은 기술 스택을 활용한 추가 구현 코드가 포함되어 있습니다:

### **멀티에이전트 시스템**

- **에이전트간 통신(A2A Protocol)**
- **Langgraph를 통한 흐름제어**
- **MCP(Model Context Protocol) 통합**
- **mem0 장기 메모리 시스템**

_위 기능들은 `Agent/agent-ai/` 디렉토리에 구현되어 있으며, 본 연구의 핵심 실험과는 독립적인 추가 개발 코드입니다._
