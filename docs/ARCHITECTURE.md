# 아키텍처

## 디렉토리 구조

```
kbase_kinase/
├── INTENT.md  CLAUDE.md  AGENTS.md  README.md
├── config.yaml  .env.example  pyproject.toml
├── docs/                    # PRD, ARCHITECTURE, ADR, ONTOLOGY, CURATION, SOURCES, NEW_DOMAIN
│
├── engine/kbase/            # 일반 IO·검증·빌드. kinase 코드에 의존하지 않는다
│   ├── records.py           #   레코드 읽기/쓰기, 스키마 검증
│   ├── build.py             #   kb/ + ref/ → dist/
│   ├── validate.py          #   무결성 게이트
│   ├── reader.py            #   소비자용 읽기 라이브러리
│   └── cli.py
│
├── domain/kinase/           # 이것만 갈아끼우면 다른 도메인
│   ├── ontology.yaml        #   SITE/GOAL/TACTIC + synonyms + aliases
│   ├── positions.py         #   지원 target 한정 위치 매핑
│   ├── schemas/             #   move / mutation / figure JSON Schema
│   ├── prompts/  queries.yaml  sources.yaml
│
├── sources/
│   ├── pdf/                 # 사용자가 PMID_<pmid>.pdf 를 드롭 (gitignore)
│   ├── fulltext/            # MinerU 출력 (gitignore)
│   └── literature.jsonl     # PMID 인덱스 (커밋)
├── assets/figures/          # 원본 해상도 그림 (git-lfs)
├── .cache/                  # 외부 API 원응답 (gitignore)
│
├── staging/                 # LLM 추출 후보. Step D부터 존재
├── rejected.jsonl           # 거부 원장
├── kb/     moves/ mutations/ figures/   # 사람이 승인한 지식
├── ref/    고정 snapshot                 # 외부 DB 파생. 사람이 수정하지 않는다
├── dist/                                # 생성물. 소비자 진입점
├── reports/                             # ontology_gaps, review_queue
└── scripts/  tests/
```

## 세 디렉터리의 소유권

이 구분이 아키텍처의 중심이다. **디렉터리마다 주인이 하나고 규칙이 하나다.**

| 디렉터리 | 주인 | 규칙 | 재생성 |
|---|---|---|---|
| `kb/` | 사람 | 승인된 것만 들어온다. **빌드가 수정하지 않는다** | 불가. 전문가 판단이 박혀 있다 |
| `ref/` | 기계 | 외부 DB 고정 snapshot. **사람이 수정하지 않는다** | 가능. 지워도 된다 |
| `dist/` | 빌드 | `kb/` + `ref/`의 비정규화 산출물 | 가능. 항상 덮어쓴다 |

섞으면 두 가지를 잃는다. 하나는 `rm -rf && rebuild`를 영영 못 하게 된다는 것이고, 다른 하나는 `git log kb/`가 기계 소음에 잠겨 **"무엇을 언제 누가 승인했는가"**를 답할 수 없게 된다는 것이다. 사람 게이트를 두는 이유 자체가 사라진다.

## 패턴

### 1. 통제 어휘가 지각과 지식을 잇는다

```
[복합체]  --분석/인식-->  descriptor  ┐
                                       ├→ 같은 어휘로 색인된 Move / Figure / Mutation
[kb/*.yaml] --큐레이션-->  tags        ┘
```

태그는 **SITE / GOAL / TACTIC 세 축만** 쓴다. `gk_class`, `mechanism_class` 같은 값은 태그가 아니라 typed field다. 상태(back pocket이 열렸는지 채워졌는지)도 태그가 아니라 구조 descriptor의 필드다.

TACTIC 축이 없으면 site가 없는 변형("logD를 낮춰 hERG 해결", "매크로사이클화")을 담을 수 없다. 그리고 **에이전트의 출력이 사는 축이 TACTIC이다** — 에이전트는 부위가 아니라 화학적 조작을 제안한다.

### 2. 구조적 사실과 설계 논리를 다른 경로로 받는다

> **구조적 사실은 DB에서. 설계 논리는 논문에서.**
> **LLM은 구조적으로 검증 가능한 주장을 담당하지 않는다.**

residue 번호, 도메인 경계, DFG/αC 상태는 외부 DB에서 온다. LLM이 채우는 것은 반증 불가능한 잔여뿐이고, 거기서도 원문의 글자 그대로의 부분문자열(`span`)을 근거로 달아야 한다.

### 3. 신뢰도 세 필드는 서로를 결정하지 않는다

```yaml
review_status: pending | validated | rejected    # 사람만 바꾼다
checks_passed: true | false                      # 기계만 쓴다
confidence:    high | medium | low               # 사람만 부여한다
```

PMID·PDB가 실재하고 숫자가 원문에 등장한다는 사실은 **"관찰 → 변형 → 효과"의 연결이 옳다는 증거가 아니다.** 기계 검사 통과는 승격 사유가 아니라 리뷰 큐의 정렬 신호다.

### 4. 모든 값은 출처와 방법을 들고 다닌다

```yaml
dfg:
  value: out
  source: kincore
  source_record: "3OXZ_A"
  source_version: "PK_labels_PDB 2026-05-25"
  method: dihedral_classification
```

출처(provenance)와 검수 상태(review_status)는 **별개 사실이다.** 출처가 무엇이든 사람이 검수했는지는 따로 간다. 소스가 충돌하면 양쪽 원값과 기준을 보존하고 `conflict`로 표시하며, **사람이 수정한 값을 CI가 기계값으로 덮지 않는다.**

## 데이터 흐름

```
PubMed / KLIFS / Kincore / UniProt / SIFTS / CIViC / RCSB
        │
        │  sync-ref  (네트워크 사용. 고정 snapshot으로 동결)
        ▼
    ref/  ────────────────────────┐
                                   │
사용자가 PDF를 sources/pdf/ 에 드롭  │
        │                          │
        │  ingest  (MinerU)        │
        ▼                          │
  sources/fulltext/                │
        │                          │
        │  extract  (LLM, 스키마 강제)│
        ▼                          │
    staging/  ──── 자동 검사 ────→ 리뷰 큐 정렬 (승격 아님)
        │                          │
        │  사람 승인                 │
        ▼                          │
     kb/  ────────────────────────┤
                                   │
                                   ▼
                          build  (로컬 자료만)
                                   │
                                   ▼
                                dist/
                                   │
                                   ▼
                        소비자 에이전트가 조회·인용
```

네 계층이다. **acquire → extract → curate → build.**

두 가지를 분리해 둔 것이 중요하다.

- **`sync-ref`는 네트워크를 쓰고 `build --check`는 로컬 자료만 쓴다.** CI가 외부 서비스 가용성과 최신값에 좌우되지 않는다.
- **`staging/`에서 `kb/`로 가는 유일한 경로는 사람이다.** 자동 검사는 그 줄을 건너지 못한다.

## 멱등성과 재현성

- 캐시 키에 입력 해시뿐 아니라 **parser 버전·옵션, ontology/schema 버전, ref snapshot 식별자, 코드 버전**을 포함한다. 모델·프롬프트만으로는 파이프라인 변경을 감지하지 못한다.
- 성공 산출물이 온전할 때만 캐시를 쓴다. 실패·중단을 완료로 기록하지 않는다.
- 단일 writer로 시작하고 동시 실행은 잠금 파일로 막는다.
- **PDF 한 편을 추가했을 때 전체 재처리가 일어나서는 안 된다.**
- 입력이 바뀌지 않은 재실행은 `kb/`와 `dist/`가 동일해야 한다.
- manifest에 **파일별 해시**를 둔다. 레코드 개수만으로는 내용 변경이나 중복 치환을 못 잡는다.
- 사용한 ref snapshot의 식별자·해시·보관 경로를 manifest에 고정한다. 그러지 않으면 과거 `dist/`를 재현할 수 없다.

## 오류 처리

| 상황 | 처리 | 재개 |
|---|---|---|
| timeout · 429 · 일시적 5xx | 제한시간, 최대 3회, 서버 대기 지시 반영 | 실패 ID만 기록해 재실행 |
| 인증·설정 오류 | 단계 중단, **비밀값 없는** 오류 메시지 | 설정 수정 후 같은 입력으로 재개 |
| 원문 없음 | `not_accessible` | 메타데이터 유지, 전문 추출 보류 |
| PDF 손상·MinerU 실패 | 해당 문헌 격리, 원본과 오류 보존 | 다른 문헌 진행. **무한 OCR 재시도 금지** |
| 수치·화합물·표 연결 불명확 | `needs_review` | 자동 승인하지 않음 |
| 위치 매핑 모호 · 소스 충돌 | 필드에 `unknown` / `conflict` + 사유 | 후보 보존, 확정 주장으로 배포 안 함 |
| 외부 API 장애 중 PDB 검증 | `lookup_failed`와 `not_found` 구분 | **장애 때문에 기존 링크를 삭제하지 않음** |
| LLM 형식 불일치 | 로컬 검증 후 보정 요청 1회 | 계속 실패하면 후보 격리 |
| dist 생성·검증 실패 | 임시 디렉터리에서 실패 종료 | **마지막 정상 dist 유지** |
| 과도하게 넓은 질의 | `total` · `truncated` · 필터 안내 반환 | 정상 검색을 시스템 오류로 취급 안 함 |
| 알 수 없는 ID · 스키마 비호환 | 명시적 오류 | **0건 검색 결과와 구분** |

## 소비 계약

`dist/`는 비정규화 생성물이며 git에 커밋한다. grep만 쓰는 에이전트, JS 런타임, `raw.githubusercontent` fetch가 빌드 단계 없이 동작해야 하기 때문이다. 대신 **CI가 `build --check`로 diff가 비었는지 검사한다.** 이 검사가 없으면 `dist/`는 조용히 썩는다.

v1의 `dist/`:

```
dist/
  manifest.json        # 소비자가 반드시 먼저 읽는다
  CONTRACT.md          # 규범 명세
  moves.jsonl  figures.jsonl  mutations.jsonl
  targets.jsonl  structures.jsonl  papers.jsonl
  images/              # 썸네일
```

읽기 라이브러리는 stdlib만 쓰고 v1에는 세 메서드다. `get` / `find` / `cite`. **`include_unreviewed=False`가 기본이고, `cite`와 `check-refs`는 같은 정책을 쓴다.**

비정규화 규칙: **작고, 느리게 변하고, 관련성 판단이나 인용에 필요한 것만 복제한다.** 595비트 IFP, 전체 캡션, 전체 앵커맵은 복제하지 않는다.

자동 계산값(유사 전례 후보 등)은 **`dist/`에만 쓴다. 빌드가 `kb/`를 수정하지 않는다.**

## 상태 관리

이 프로젝트에 런타임 상태는 없다. 상태는 전부 파일과 git이다.

| 상태 | 저장 위치 | 변경 주체 |
|---|---|---|
| 지식의 검수 상태 | 레코드의 `review_status` | 사람 |
| 기계 검사 결과 | 레코드의 `checks_passed` | 빌드 |
| 문헌 확보 상태 | `sources/literature.jsonl`의 `pdf_status` | ingest |
| 외부 DB 시점 | `dist/manifest.json`의 snapshot 식별자·해시 | `sync-ref` |
| 처리 이력 | 단계별 매니페스트의 캐시 키 | 각 단계 |
| 거부 이력 | `rejected.jsonl` | 사람 |
| 승인 이력 | git 커밋 | 사람 |

**`kb/`의 git 이력이 감사 기록이다.** 그래서 기계가 만든 것을 거기 섞지 않는다.
