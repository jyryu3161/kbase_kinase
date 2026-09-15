# 프로젝트: kbase_kinase

kinase 구조 기반 신약설계 지식 베이스. 최종 소비자는 사람이 아니라 설계 에이전트다.
설계 배경과 결정 근거는 `docs/ARCHITECTURE.md`와 `docs/ADR.md`에 있다.

## 기술 스택

- Python 3.12, `uv` 가상환경(`.venv`), pip 전용 의존성
- Biopython (PubMed), httpx, pydantic, PyYAML, jsonschema, typer, rich, tenacity
- MinerU 3.4.5 (PDF 본문 추출, `hybrid-engine` 백엔드) — 선택적 extra
- OpenRouter 경유 LLM (벤더 중립 어댑터)
- pytest + tdd-guard
- **conda 전용 패키지에 의존하지 않는다** (opencadd, KiSSim 등은 PyPI에 없다)

## 아키텍처 규칙

### 신뢰도

- CRITICAL: **기계 검사 통과를 사람 검수로 취급하지 마라.** `review_status`(사람만) · `checks_passed`(기계만) · `confidence`(사람만)는 서로를 결정하지 않는다. 한 필드가 다른 필드를 자동으로 바꾸는 코드를 쓰지 마라.
- CRITICAL: **`kb/`에는 `review_status: validated`만 들어간다.** 자동 승격 경로를 만들지 마라. 기계 검사는 리뷰 큐의 정렬 신호일 뿐이다.
- 기본 조회는 검수분만 본다(`include_unreviewed=False`). `cite`와 `check-refs`는 같은 정책을 쓴다.

### 데이터 무결성

- CRITICAL: **근거 없는 레코드를 만들지 마라.** observation · effect · tradeoff는 **각각** 자기 evidence를 갖는다. 그림 하나의 접촉 설명이 효능 수치와 임상 trade-off까지 뒷받침한다고 취급하지 마라.
- CRITICAL: **부등호가 있는 값으로 배수를 계산하지 마라.** `>10000`과 `=11`에서 `909배`를 만들면 하한이 정확값으로 바뀐다. `fold_change: null` + `fold_change_bound: ">909"`로 둔다.
- CRITICAL: **residue 번호를 LLM이 만들게 하지 마라.** 구조적 사실은 외부 DB에서 온다. 모든 residue 참조는 `numbering_scheme`을 필수로 갖는다(기본값 없음).
- 매핑 검증은 WT 구조에 WT residue를, mutant 구조에 mutant residue를 기대한다. 반대로 하면 정상 변이 구조를 거부한다.
- 지원 밖 target과 모호한 정렬은 **`unmapped`를 반환한다.** 조용히 그럴듯한 값을 내놓지 마라.
- 표 각주를 버리지 마라. assay 조건과 부등호 의미가 거기 있다.

### 소유권

- CRITICAL: **빌드가 `kb/`를 수정하지 마라.** 자동 계산값은 `dist/`에만 쓴다.
- `ref/`는 외부 DB 고정 snapshot이다. 사람이 손으로 수정하지 않는다.
- `dist/`는 항상 덮어쓴다. 실패 시 임시 디렉터리에서 종료하고 **마지막 정상 `dist/`를 유지한다.**

### LLM 사용

- CRITICAL: **LLM에 `conf:`(DFG/αC)와 `mode:`(type I/II)를 배정시키지 마라.** 캡션으로는 추론 불가능한데 LLM은 자신 있게 지어낸다. 연결된 구조에서 오거나 `unknown`이다.
- LLM이 채우는 값은 폐쇄 어휘의 용어만 쓰고, 원문의 **글자 그대로의 부분문자열**인 `span`을 달아야 한다. span이 없으면 버린다.
- `response_format`에 `json_schema`를 쓰되 `provider: {require_parameters: true}`를 함께 보낸다. 스키마가 강제됐다고 믿지 말고 pydantic으로 재검증한다.

### 보안

- CRITICAL: **비밀값을 오류 메시지·로그·assert 메시지에 넣지 마라.** 키 이름과 오류 종류만 출력한다.
- `.env`는 커밋하지 않는다. 새 설정은 `.env.example`에 키 이름만 추가한다.

### 일반

- 태그는 SITE / GOAL / TACTIC 3축만. `gk_class`, `mechanism_class` 등은 typed field다.
- 소스가 충돌하면 양쪽 원값과 기준을 보존하고 `conflict`로 표시한다. **사람이 수정한 값을 기계값으로 덮지 마라.**
- 알 수 없는 ID와 스키마 비호환은 **명시적 오류**다. 0건 검색 결과와 구분한다.
- 임베딩 인덱스, 질의 DSL, MCP 서버를 만들지 마라. 결정된 사항이다(ADR-012).
- 캐시 키에 입력 해시뿐 아니라 parser 버전·ontology/schema 버전·ref snapshot·코드 버전을 포함한다.

## 개발 프로세스

- CRITICAL: 새 기능 구현 시 반드시 테스트를 먼저 작성하고, 테스트가 통과하는 구현을 작성할 것 (TDD)
- 커밋 메시지는 conventional commits 형식을 따를 것 (feat:, fix:, docs:, refactor:)
- 실행 순서는 `수동 Move → 조회 가능한 dist → 재현성·오류 복구 → 추출 자동화`다. 범용 기반을 먼저 짓지 않는다.
- 미룬 것을 앞당기지 마라: 범용 위치 매퍼, 합성 랭킹, 자동 Figure 점수식, JS 참조 리더, provider별 adapter framework, 전체 source 동기화.
- 성공 기준에 pytest만 넣지 마라. **사람이 원문을 대조한 Move와 소비자 질문 결과**를 함께 본다.

## 명령어

```bash
python3 -m pytest -q                  # 전체 테스트
python3 -m pytest tests/test_x.py -q  # 단위 테스트
kb build                              # kb/ + ref/ → dist/
kb build --check                      # dist/ 가 최신인지 (CI 게이트, 네트워크 미사용)
kb validate                           # 스키마·어휘·링크·근거 검사
kb sync-ref                           # 외부 DB → ref/ (네트워크 사용)
kb status                             # PDF 확보율, 어휘 커버리지, 리뷰 부채
```
