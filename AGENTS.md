# 프로젝트: kbase_kinase

kinase 구조 기반 lead optimization 지식베이스. 최종 소비자는 protein-ligand 복합체를 보고 다음 화학구조 변형을 제안하는 multi-modal LLM agent다. 이 저장소는 그 제안에 근거가 될 **전례(Design Move)** 를 공급한다.

이 파일은 이 저장소에서 **개발하는** agent용 규칙의 정본이다. Codex(구현)가 자동으로 읽고, Claude Code(하네스 설계·리뷰)는 `CLAUDE.md`의 `@AGENTS.md`로 같은 내용을 읽는다. 규칙은 이 파일만 고친다. KB를 **소비하는** agent용 안내는 `docs/consumer/AGENTS.md`다.

작업 전에 `intend.md`를 읽어라. 왜 이런 설계인지가 거기 있다.

## 기술 스택

- Python 3.12 (현재 로컬은 3.10.9, pyproject에서 최소 3.10 허용)
- pydantic v2 (스키마 검증), typer (CLI), polars 또는 pandas, pyarrow
- Biopython (PubMed Entrez, mmCIF 파싱), httpx + tenacity (외부 API)
- MinerU 3.4.5 (주 PDF 파서), Docling (교차검증 파서)
- OpenRouter `deepseek/deepseek-v4.1-flash` (추출 LLM, structured outputs 강제)
- pytest + tdd-guard, ruff
- conda 전용 패키지에 의존하지 않는다 (opencadd, KiSSim 등은 PyPI에 없다)

## 아키텍처 규칙

### CRITICAL 규칙

절대 위반하지 마라. 위반하면 이 저장소의 존재 이유가 무너진다.

- **CRITICAL: 엔진은 도메인을 모른다.** `src/kbase/` 안의 코드는 `domains`를 import하지 않고, kinase·gatekeeper·DFG 같은 도메인 용어를 쓰지 않는다. 이유: 두 번째 도메인 저장소를 만들 때 `src/kbase/`를 그대로 복사해 쓸 수 있어야 한다. `tests/test_engine_isolation.py`가 import 그래프를 검사한다.

- **CRITICAL: `review_status`는 `unreviewed` 외의 값을 갖지 않는다.** `validated`, `confidence`, `verified` 같은 필드를 새로 만들지 마라. 이유: 이 프로젝트는 사람이 검수하지 않는다. 신뢰도 필드가 존재하면 근거 없이 채워지고, 하류 agent가 그 값을 믿는다. 레코드가 주장할 수 있는 것은 `checks` 객체에 기록된 기계 검사 결과뿐이다.

- **CRITICAL: 부등호나 조건 불일치가 있으면 `fold_change`는 `null`이다.** `qualifier`가 `=`가 아니거나 `comparable`이 `false`면 배수를 계산하지 마라. 이유: `>10000 → 11`을 909배로 저장하면 원문에 없던 정밀도가 태어난다. 대신 `direction`과 `magnitude_bucket`은 수치가 없어도 항상 채운다.

- **CRITICAL: 소스가 엇갈리면 한쪽을 고르지 않는다.** KLIFS와 Kincore가 다른 값을 주면 양쪽 원값과 판정 기준을 모두 보존하고 `agreement: conflict`로 표시한다. 이유: 검수자가 없으므로 임의 선택을 검토할 사람이 없다. 고르는 순간 다른 쪽 정보가 영구히 사라진다.

- **CRITICAL: 구조 상태는 `pdb_id + chain + ligand` 단위에 붙인다.** PDB ID 하나만으로 상태를 상속시키지 마라. 이유: 한 구조에 여러 chain과 여러 리간드가 있고, 한 그림에 여러 구조의 패널이 있다. ID 하나로는 어느 복합체인지 특정되지 않는다.

- **CRITICAL: PDF와 그림 이미지를 git에 커밋하지 않는다.** `inbox/`와 `work/`는 gitignore다. 레코드에는 로컬 경로와 sha256 포인터만 넣는다. 원문 인용(`quote`)은 25단어를 넘기지 않는다. 이유: 저작권과 저장소 용량.

- **CRITICAL: `kb/`와 `dist/`는 빌드가 쓴다.** 손으로 고치지 마라. 고쳐야 할 것이 있으면 추출 프롬프트나 검사 로직을 고치고 다시 빌드한다. 이유: 재현성. 같은 입력으로 재실행하면 동일한 결과가 나와야 한다.

- **CRITICAL: `ref/` 스냅샷은 `sync-ref` 명령만 갱신한다.** 빌드는 네트워크를 쓰지 않는다. 이유: 외부 서비스가 죽어도 빌드가 가능해야 하고, 과거 dist를 재현할 수 있어야 한다.

### 일반 규칙

- 검색 쿼리, 태그 어휘, 프롬프트를 코드에 하드코딩하지 않는다. `src/domains/kinase/` 아래 YAML과 마크다운 파일에 둔다.
- 태그는 폐쇄 어휘다. 어휘에 없는 표현은 `proposed_tags`로 따로 모으고, 별도 명령으로만 승격한다.
- `unknown`, `null`, `not_applicable`, `unmapped`, `not_observed`를 구분해 쓴다. 뭉개면 나중에 왜 비었는지 알 수 없다.
- 외부 조회 실패는 `lookup_failed`로, 실제 부재는 `not_found`로 기록한다. 장애 때문에 기존 링크를 지우지 않는다.
- 레코드 ID(`MOVE-0001`)는 최초 생성 시 고정한다. `content_hash`는 변경 감지 전용이며 ID 역할을 하지 않는다.
- LLM 출력은 반드시 스키마 검증을 통과한 뒤 저장한다. 형식 이탈 시 보정 요청은 1회만.
- LLM에 DFG/αC 상태, 결합 모드(type I/II), 잔기 번호를 배정시키지 않는다. 연결된 structure 레코드에서 오거나 `unknown`이다. 캡션으로는 추론할 수 없는데 LLM은 자신 있게 지어낸다.
- 잔기 번호에는 번호 체계를 항상 붙인다(`uniprot_resnum`, `pdb_resnum`). ABL1 gatekeeper는 PDB에 따라 315(ABL1a)와 334(ABL1b)로 갈린다.
- observation, effect, tradeoff는 각각 자기 evidence를 갖는다. 그림 하나의 접촉 설명이 효능 수치까지 뒷받침한다고 취급하지 않는다.
- 표 각주를 버리지 않는다. assay 조건과 부등호 의미가 거기 있다.
- 비밀값을 오류 메시지, 로그, assert 메시지에 넣지 않는다. 키 이름과 오류 종류만 출력한다. `.env`는 커밋하지 않고, 새 설정은 `.env.example`에 키 이름만 추가한다.
- 캐시 키에 PDF sha256, 파서 이름·버전·백엔드·옵션, 프롬프트 버전, 모델·공급자, 스키마 버전, 어휘 버전, ref 스냅샷 ID를 모두 넣는다. MinerU는 설정 지문을 제공하지 않으므로 직접 만든다.

## 개발 프로세스

- **CRITICAL: 새 기능 구현 시 반드시 테스트를 먼저 작성하고, 테스트가 통과하는 구현을 작성할 것 (TDD).** 실패하는 테스트를 먼저 실행해 확인한 뒤 구현한다.
- Codex hook(`.codex/hooks.json`)이 `rm -rf`, `git push --force`, `git reset --hard`, `DROP TABLE`을 차단하고, 턴 종료 시 `ruff check .`와 `pytest`를 돌린다. 실패 보고를 받으면 고친 뒤 끝낸다. hook을 약화시키는 수정을 하지 않는다.
- 커밋 메시지는 conventional commits 형식을 따를 것 (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`)
- 구현은 `phases/` harness로 진행한다. `python3 scripts/execute.py <task-name>`이 step마다 `codex exec`를 실행한다.
- 하나의 step에서 하나의 레이어만 다룬다. 엔진과 도메인을 같은 step에서 수정하지 않는다.

## 명령어

```bash
ruff check .                   # 린트
pytest                         # 테스트
pytest tests/test_engine_isolation.py   # 엔진/도메인 경계 검사

kb sync-ref                    # 외부 스냅샷 갱신 (네트워크 사용)
kb build-reference             # 전체 kinome reference + structures 생성
kb literature --plan           # PMID 후보 수집, PDF 요청 목록 CSV 출력
kb ingest                      # inbox/ PDF 처리 (파싱 → 추출 → 검사)
kb build --check               # dist/ 빌드 + 검사 (오프라인)
kb ask examples/queries/*.json # 예제 질의 실행
```

## 디렉터리 요약

```
src/kbase/          엔진. 도메인을 모른다
src/domains/kinase/ kinase를 아는 유일한 곳
ref/                외부 스냅샷 (커밋, 해시 고정)
kb/                 추출 레코드 JSONL (전부 미검수)
dist/               빌드 산출물 + CONTRACT.md (커밋)
wiki/               생성된 마크다운 (커밋)
inbox/ work/        PDF와 파싱 중간물 (gitignore)
.codex/             Codex hook (위험 명령 차단, 종료 시 ruff + pytest)
```

상세는 `docs/ARCHITECTURE.md`를 보라.

## 참고 문서

- `intend.md` — 왜 만드는가, 성공 판정 기준
- `docs/PRD.md` — 사용자와 기능 범위
- `docs/ARCHITECTURE.md` — 구조, 데이터 흐름, 스키마 전문
- `docs/ADR.md` — 설계 결정 27건과 트레이드오프
- `docs/consumer/AGENTS.md` — 소비자 agent용 안내 (영어). 빌드가 `dist/AGENTS.md`로 복사한다
- `kb_kinase GitHub Repository Specification v0.1.md` — 초기 참고 스펙. 현재 설계와 다른 부분이 많다. 참고용으로만 보라
- `plan_comment.md` — 이전 계획안에 대한 리뷰. 여기의 지적 5건이 현재 설계에 반영돼 있다
