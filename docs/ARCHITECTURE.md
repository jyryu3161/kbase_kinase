# 아키텍처

## 디렉터리 구조

```
kbase_kinase/
├── intend.md                  # 왜 만드는가
├── AGENTS.md                  # 개발 규칙 정본 (Codex 자동 로드)
├── CLAUDE.md                  # @AGENTS.md import
├── pyproject.toml
├── .env.example
├── .codex/hooks.json          # Codex hook: 위험 명령 차단, 종료 시 ruff + pytest
│
├── docs/{PRD,ARCHITECTURE,ADR}.md
├── docs/consumer/AGENTS.md    # 소비자 agent용 안내 (영어). 빌드가 dist/로 복사
│
├── src/
│   ├── kbase/                 # 엔진. 도메인 단어를 모른다
│   │   ├── records.py         # JSONL IO, ID 발급, content_hash
│   │   ├── schema.py          # pydantic 기반 검증 엔진
│   │   ├── snapshot.py        # 스냅샷 수집, 해시, manifest
│   │   ├── parse/
│   │   │   ├── mineru.py      # MinerU 래퍼
│   │   │   ├── docling.py     # Docling 래퍼
│   │   │   └── crosscheck.py  # 두 파서의 수치 대조
│   │   ├── llm.py             # OpenRouter 클라이언트, structured outputs
│   │   ├── checks.py          # 검사 실행기 (검사는 도메인이 등록)
│   │   ├── build.py           # dist 빌드, 원자적 교체
│   │   ├── reader.py          # get / find / cite
│   │   ├── cache.py           # 캐시 키 생성과 조회
│   │   └── wiki.py            # 템플릿 렌더러
│   │
│   └── domains/kinase/        # kinase를 아는 유일한 곳
│       ├── schema.py          # Move/Reference/Structure/Mutation/Figure 정의
│       ├── vocab/
│       │   ├── site.yaml      # SITE 폐쇄 어휘
│       │   ├── goal.yaml      # GOAL 폐쇄 어휘
│       │   └── tactic.yaml    # TACTIC 폐쇄 어휘
│       ├── prompts/
│       │   ├── move_extract.md        # 버전 태그 포함
│       │   ├── figure_read.md
│       │   └── mutation_extract.md
│       ├── sources/
│       │   ├── pubmed.py      # Biopython Entrez
│       │   ├── klifs.py       # 중심 소스
│       │   ├── kincore.py
│       │   ├── uniprot.py
│       │   ├── sifts.py       # PDBe 잔기 매핑
│       │   ├── interpro.py    # 도메인 경계
│       │   ├── kinhub.py      # Manning 분류
│       │   ├── pdb.py
│       │   └── chembl.py      # 3차 수치 검증
│       ├── queries.yaml       # 검색식
│       ├── descriptor.py      # 구조 descriptor → 필터 변환
│       ├── checks.py          # 도메인 검사 등록
│       └── wiki_templates/
│
├── ref/                       # 외부 스냅샷 (커밋, 해시 고정)
│   ├── manifest.json
│   ├── klifs/2026-09-15/
│   ├── kincore/2026-09-15/
│   └── ...
│
├── kb/                        # 추출 레코드 JSONL (전부 미검수)
│   ├── moves.jsonl
│   ├── figures.jsonl
│   └── mutations.jsonl
│
├── dist/                      # 빌드 산출물 (커밋)
│   ├── CONTRACT.md            # 빌드가 생성. 소비 계약의 정본
│   ├── AGENTS.md              # docs/consumer/AGENTS.md 복사본
│   ├── manifest.json
│   ├── moves.jsonl
│   ├── moves_flagged.jsonl
│   ├── structures.jsonl
│   ├── references.jsonl
│   ├── mutations.jsonl
│   ├── figures.jsonl
│   └── tactics.jsonl
│
├── wiki/                      # 생성된 마크다운 (커밋)
│   ├── index.md
│   ├── kinases/
│   ├── tactics/
│   └── papers/
│
├── inbox/                     # PDF 투입 (gitignore)
│   └── unmatched/
├── work/                      # 파싱 중간물, 캐시 (gitignore)
│
├── examples/queries/          # 예제 descriptor JSON
├── phases/                    # harness
├── scripts/execute.py
└── tests/
    └── test_engine_isolation.py
```

## 엔진과 도메인의 경계

이 경계가 템플릿 재사용의 전부다. 말로 지키지 않고 테스트로 지킨다.

| | 엔진 `src/kbase/` | 도메인 `src/domains/kinase/` |
|---|---|---|
| 아는 것 | 레코드, 스키마, 검사, 캐시, 빌드, 파일 | kinase, gatekeeper, DFG, KLIFS, PubMed |
| 레코드 IO | JSONL 읽기/쓰기, ID 발급, 해시 | 어떤 필드가 있는지 정의 |
| 검증 | 검사를 등록받아 실행하는 틀 | 어떤 검사를 등록할지 |
| 파싱 | MinerU/Docling 호출과 교차검증 | 없음 |
| LLM | 클라이언트, 스키마 강제, 재시도 | 프롬프트 내용 |
| 외부 소스 | 없음 | 모든 어댑터 |
| wiki | 템플릿 렌더링 엔진 | 템플릿 내용과 페이지 축 |

`tests/test_engine_isolation.py`가 두 가지를 검사한다. `src/kbase/` 모듈의 AST import 그래프에 `domains`가 나타나지 않는 것, 그리고 도메인 금지 어휘가 엔진 소스에 나타나지 않는 것. 후자는 보조 검사이고 전자가 본질이다.

두 번째 도메인을 만들 때는 `src/kbase/`를 그대로 복사하고 `src/domains/<new>/`를 채운다. 실제 두 번째 도메인이 생기기 전에 별도 pip 패키지로 쪼개지 않는다.

## 데이터 흐름

```
KLIFS · Kincore · PDB · UniProt        사용자가 넣은 PDF
SIFTS · ChEMBL · KinHub · InterPro            │
        │                              inbox/PMID_xxx.pdf
   sync-ref (네트워크)                         │
   스냅샷 고정 + 해시 기록              MinerU ─┬─ Docling
        │                                      │
        ▼                                work/parsed/
      ref/                                     │
        │                             LLM 추출 (스키마 강제)
   build-reference (오프라인)                  │
        │                                      ▼
   ┌────┴────┬──────────┐              기계 검사 9종
   ▼         ▼          ▼           (ChEMBL 3차 검증 포함)
reference  structures  mutations              │
(kinome)   (PDB단위)   (변이단위)             ▼
   │         │          │              kb/moves.jsonl
   └────┬────┴──────────┘                     │
        │                                      │
        └──────────────┬──────────────────────┘
                       ▼
                 build (오프라인)
                       │
        dist/ (moves, moves_flagged, structures,
               mutations, references, figures,
               tactics, manifest, CONTRACT, AGENTS)
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
       wiki/ (3축)          소비자 agent
```

네트워크를 쓰는 단계는 `sync-ref`, `literature`, `ingest`의 식별 단계뿐이다. `build-reference`와 `build`는 오프라인이다. CI가 외부 서비스 가용성에 좌우되지 않는다.

## 패턴

**파일 계약.** 소비 인터페이스는 JSONL 파일과 `CONTRACT.md`다. 서버도 데몬도 없다. 언어 중립이고, git diff로 지식 변화가 보이며, 커밋 해시로 특정 시점의 KB를 인용할 수 있다.

**정본과 파생물 분리.** `kb/`가 추출 결과, `dist/`가 빌드 산출물, `wiki/`가 사람이 보는 파생물이다. wiki를 source of truth로 만들지 않는다. `ref/`는 외부 것이므로 아무도 편집하지 않는다.

**기계 검사 등록 패턴.** 엔진의 `checks.py`가 실행기이고, 도메인이 검사 함수를 등록한다. 검사는 `(record, context) -> CheckResult`이며 `pass` / `fail` / `not_applicable` / `lookup_failed`를 돌려준다.

**단일 writer + 잠금.** 동시 실행을 허용하지 않는다. 잠금 파일로 막는다.

**원자적 교체.** 빌드는 `work/dist-tmp/`에서 만들고 검사를 통과한 뒤 `dist/`와 교체한다. 실패하면 기존 `dist/`가 그대로 남는다.

**출처를 필드 단위로.** reference와 structure의 각 필드에 어느 스냅샷에서 왔는지를 붙인다. 소스가 엇갈리면 고르지 않고 `conflicts` 또는 `agreement: conflict`로 남긴다.

## 레코드 스키마

전체 필드 정의는 빌드가 생성하는 `dist/CONTRACT.md`가 정본이다. 여기서는 설계 의도가 드러나는 부분만 적는다.

### Move

```yaml
move_id: MOVE-0001          # 최초 생성 시 고정. content_hash와 분리
schema_version: 1
review_status: unreviewed   # 항상 이 값

source:
  pmid: "12345678"
  parser: {name: mineru, version: "3.4.5", backend: hybrid-engine}
  locations:
    - {kind: table, page: 5, table_index: 2, row: 5, bbox: [...]}

target: {gene: EGFR, uniprot: P00533, variant: "L858R/T790M"}
structure_ref: STRUCT-6LUD-A-XYZ

observation:
  text: "..."               # 영어
  quote: "..."              # 25단어 이하
  evidence: [location 참조]

change:
  from_compound: "cpd 12"
  to_compound: "cpd 23"
  description: "..."
  smiles_from: null         # 논문에 있으면 기록만
  smiles_to: null

effects:
  - metric: IC50
    assay: biochemical
    assay_context: {atp_conc: "1 mM", construct: "...", cell_line: null}
    target_ref: "EGFR L858R/T790M"
    before: {value: 10000, unit: nM, qualifier: ">"}
    after:  {value: 11,    unit: nM, qualifier: "="}
    direction: improved         # 항상 채운다
    magnitude_bucket: large     # 항상 채운다
    comparable: false
    comparability_reason: "before is a lower bound"
    fold_change: null
    chembl_crosscheck: {status: not_found, activity_id: null}
    evidence: [location 참조]

tradeoffs: [...]
mutations: [MUT-EGFR-T790M]
tags: {site: [front_pocket], goal: [potency], tactic: [covalent_warhead]}
proposed_tags: []
figures: [FIG-0012]

checks: {...}
extraction:
  model: "deepseek/deepseek-v4.1-flash"
  provider: "deepinfra"
  prompt_version: "move-extract@3"
  run_at: "2026-09-15T14:02:11+09:00"
content_hash: "..."
```

수치 규칙 세 가지를 스키마 validator가 강제한다.

1. `qualifier`가 `=`가 아니면 `fold_change`는 `null`
2. `comparable`이 `false`면 `fold_change`는 `null`
3. `direction`과 `magnitude_bucket`은 수치가 없어도 채운다

3번이 있어야 조건을 명시하지 않은 논문의 사례도 전례로 살아남는다.

`move_id`와 `content_hash`를 분리하는 이유는, 문구를 고치면 해시가 바뀌어 연결된 mutation·figure·인용이 전부 끊기기 때문이다. ID는 최초 생성 시 발급하고 이후 유지한다. 인용에는 `move_id` + `kb_version`을 쓴다.

### Reference (전체 kinome)

```yaml
ref_id: KIN-P00533
gene: EGFR
uniprot: P00533
group: TK                        # KinHub / Manning
family: EGFR                     # KLIFS
domain: {start: 712, end: 979, source: SNAP-interpro-2026-09-15}
klifs_pocket_seq: "KVLGSGAFGTVYKVAIKELEILDEAYVMASVDPHVCRLLGIQLITQLMPFGCLLDYVREYLEDRRLVHRDLAARNVLVITDFGLA"
anchors:
  gatekeeper:
    - {uniprot_resnum: 790, aa: T, source: SNAP-klifs-2026-09-15, method: klifs_position}
  hinge: [...]
  dfg: [...]
  catalytic_lys: [...]
  alphaC_glu: [...]
  solvent_front: [...]
  p_loop: [...]
conflicts:
  - {field: gatekeeper, values: [...], resolved: false}
coverage: full | partial | unmapped
source_snapshots: [SNAP-klifs-2026-09-15, SNAP-kinhub-2026-09-15, ...]
```

`unmapped`를 정상 값으로 취급한다. 정렬이 모호하거나 지원 범위 밖이면 추측하지 않는다. 갭은 `not_observed`, `not_applicable`, `unmapped`로 원인을 구분한다.

범용 85-residue 매퍼를 직접 만들지 않는다. KLIFS 스냅샷에 있는 pocket 서열과 위치를 쓰고, 없으면 `unmapped`다.

잔기 번호는 번호 체계를 필드명에 담는다(`uniprot_resnum`, `pdb_resnum`). ABL1 gatekeeper는 PDB에 따라 315(ABL1a)와 334(ABL1b)로 갈리므로, 체계 없는 번호 하나로는 위치가 특정되지 않는다.

### Structure

```yaml
structure_id: STRUCT-6LUD-A-XYZ
pdb_id: 6LUD
chain: A
alt: A
ligand: XYZ
allosteric_ligand: null
uniprot: P00533
resolution: 1.7
quality: {score: ..., missing_residues: 0, missing_atoms: 0, curation_flag: false}

conformation:
  dfg:
    klifs: {value: in, source: SNAP-klifs-2026-09-15}       # in | out | out-like
    kincore: {spatial: DFGin, dihedral: BLAminus, source: SNAP-kincore-2026-09-15}
    agreement: agree            # agree | conflict | one_source | unknown
  alphaC:
    klifs: {value: out, source: ...}                        # in | out
    kincore: {value: out, source: ...}
    agreement: agree
  kincore_activity: Active      # None도 정상 값 (원자 결측)

subpockets:
  occupied: [bp_I_A, bp_I_B, front, gate]
  not_occupied: [bp_II_B, bp_III, bp_IV, bp_V, fp_I]
  semantics: klifs_ligand_contact

interaction_fingerprint: {source: SNAP-klifs-2026-09-15, residues: [...]}
sifts_mapping: [{chain: A, pdb_resnum: 790, uniprot_resnum: 790, insertion_code: null}]
```

KLIFS 서브포켓 필드는 boolean이며 의미는 리간드 접촉이다. 포켓의 존재나 열림이 아니다. 이 사실을 `semantics` 필드에 박아 소비자가 오해하지 않게 한다.

Kincore의 `None`은 결측을 뜻하는 정상 값이다. null로 뭉개지 않는다.

구조 상태는 이 계층에서만 온다. LLM이 그림 캡션에서 DFG/αC 상태나 결합 모드를 읽어 채우지 않는다.

Kincore의 αC 분류가 KLIFS `aC_helix`와 같은 의미인지 아직 확인하지 않았다. 확인 전까지 αC의 `conflict`는 판정 기준 차이일 수 있다.

### Mutation

```yaml
mutation_id: MUT-EGFR-T790M
target: {gene: EGFR, uniprot: P00533}
mutation: {wt: T, uniprot_resnum: 790, mut: M}
position_annotation: {klifs_position: ..., role: gatekeeper, source: ...}
affected_drugs: [{name: gefitinib, effect: resistance, evidence: [...]}]
overcome_by: [MOVE-0001]
analogous_positions:
  - {target: ABL1, mutation: T315I, relation: same_klifs_position, status: hypothesis}
checks: {...}
review_status: unreviewed
```

WT 확인 검사와 변이 확인 검사를 구분한다. T790M 구조에 WT의 T만 요구하면 정상적인 변이 구조를 거부하게 된다.

`analogous_positions`는 유사 전례 후보이며 항상 `status: hypothesis`다. 자동 신뢰도를 부여하지 않는다.

### Figure

```yaml
figure_id: FIG-0012
pmid: "12345678"
kind: figure | table
page: 4
bbox: [...]
caption: "..."
footnotes: [...]
panels:
  - {label: "3a", bbox: [...], structure_refs: [STRUCT-6LUD-A-XYZ]}
local_path: "<git 밖 경로>"
sha256: "..."
parser_warnings: [orphan_subpanel]
```

구조 참조는 패널에만 붙인다. 그림 하나의 모든 패널에 같은 PDB 상태를 상속시키지 않는다. MinerU 이슈 #5031이 서브패널을 부모 연결 없이 내보내므로, 그런 경우 `parser_warnings`에 `orphan_subpanel`을 남긴다.

## 기계 검사 9종

사람 검수가 없으므로 이것이 유일한 안전망이다.

| 검사 | 내용 | 실패 시 |
|---|---|---|
| `schema` | pydantic 검증 | 격리 |
| `quote_in_source` | quote가 파싱 원문에 정규화 후 존재 | 플래그 |
| `cross_parser_numbers` | 인용 수치가 MinerU와 Docling 양쪽에 존재 | 플래그 |
| `chembl_crosscheck` | 같은 문서의 ChEMBL activity와 값·단위 대조 | 플래그. `not_found`는 실패가 아니다 |
| `pmid_exists` | 스냅샷 대조. `not_found`와 `lookup_failed` 구분 | 플래그 |
| `structure_ref_exists` | `structures.jsonl`에 실재하고 chain·ligand까지 일치 | 플래그 |
| `tag_vocab` | 폐쇄 어휘 준수 | 위반 태그를 `proposed_tags`로 이동 |
| `qualifier_consistency` | 수치 규칙 세 가지 위반 탐지 | 격리 |
| `duplicate` | (pmid, 위치, 화합물 쌍) 키 중복 | 병합 후보 표시 |

격리된 레코드는 `kb/`에 들어가지 않고 `work/quarantine/`에 남는다. 플래그된 레코드는 `dist/moves_flagged.jsonl`로 배포되며 reader 기본값에서 제외된다.

### 검증 3층이 못 잡는 것

`CONTRACT.md`에 명시한다.

- 파서 교차: 두 파서가 같은 표를 같이 잘못 읽으면 통과한다
- ChEMBL 대조: 커버리지가 부분적이라 `not_found`가 흔하다. 없다고 틀린 것이 아니다
- 전체: 숫자가 맞아도 다른 화합물이나 다른 assay의 값일 수 있다. 관찰에서 효과로 이어지는 인과 해석은 어느 검사도 보증하지 않는다

## 외부 소스

2026-09-15 직접 호출로 확인한 상태다.

### 쓰는 것

**KLIFS** (`klifs.net/api_v2`) — 중심 소스. `kinase_ID`가 85-residue pocket 서열과 UniProt, family, group을 준다. `structures_list`가 구조별로 다음을 준다.

| 필드군 | 값 |
|---|---|
| `DFG` | `in` / `out` / `out-like` |
| `aC_helix` | `in` / `out` |
| 서브포켓 15종 (boolean) | `bp_I_A`, `bp_I_B`, `bp_II_in`, `bp_II_A_in`, `bp_II_B`, `bp_II_out`, `bp_III`, `bp_IV`, `bp_V`, `fp_I`, `fp_II`, `front`, `back`, `gate` |
| 구조 식별 | `pdb`, `chain`, `alt`, `ligand`, `allosteric_ligand` |
| 품질 | `quality_score`, `resolution`, `missing_residues`, `missing_atoms`, `curation_flag` |

`interactions_get_IFP`, `interactions_get_types`, `interactions_match_residues` 엔드포인트가 있어 kinase에 한해서는 별도 상호작용 지문 도구가 필요 없다. EGFR 하나가 구조 565건이므로 kinase 단위로 페이지를 나눠 받고 실패 ID를 기록한다.

신선도가 낮다. 4개 kinase 표본(EGFR·ABL1·CDK2·BTK)에서 2025년 이후 구조 167건 중 0건을 담고 있었다. 2023–2024년은 잘 덮여 있다. 최신 구조의 상태는 Kincore만 주므로 `agreement: one_source`가 된다.

**Kincore** (`dunbrack.fccc.edu/kincore`) — 2026-05-25 갱신. Spatial label(`DFGin`/`DFGinter`/`DFGout`), Dihedral label(`BLAminus`, `BLAplus`, `ABAminus`, `BLBminus`, `BLBplus`, `BLBtrans`, `BABtrans`, `BBAminus`), Chelix-Saltbridge, HRD, ActLoopCT, 종합 Activity label. 원자나 잔기 결측 시 `None`. standalone 구현은 `DunbrackLab/Kincore-standalone2`.

**UniProt REST**, **PDBe SIFTS**(`ebi.ac.uk/pdbe/api/mappings/uniprot/<id>`), **InterPro/Pfam PF00069**, **KinHub**, **ChEMBL API** 모두 응답한다.

ChEMBL은 문서 단위 조회로 3차 수치 검증에 쓴다. 라이선스는 CC BY-SA 3.0.

### 피하는 것

| 소스 | 상태 |
|---|---|
| PKIDB | 양쪽 URL 무응답 |
| CIViC 구 REST | 410 Gone. GraphQL로 이전 |
| Drug Target Commons | TCP 무응답. 검색엔진에는 살아 있게 나온다. CC BY-NC-SA |
| LINCS Data Portal | TCP 무응답 |
| MoleculeNet | 404 |
| HMS LINCS `/db/` 앱 | HTTP 500. 파일은 `/_static/db/prod-20200624/`에 2020년 동결 스냅샷으로 생존 |
| OncoKB API | 응답하지만 재배포 불가 라이선스 |

내용 함정 둘을 기록해 둔다. Metz 2011의 `MOESM138_ESM.csv`는 pKi 데이터가 아니라 kinase×kinase 유사도 행렬이고, 실제 데이터는 `MOESM137_ESM.xls`다. HMS LINCS 마스터 시트의 `dataset_url` 열은 전부 죽은 링크이므로 `dataset_id`로 조인해야 한다.

### 라이선스 등급

| 등급 | 소스 |
|---|---|
| 퍼블릭 도메인 | PDB (CC0) |
| 명확히 개방 | PKIS2 S4 Table (CC BY 4.0) |
| 개방, 동일조건변경허락 | ChEMBL (CC BY-SA 3.0) |
| 비상업 제한 | DTC, Harmonizome |
| 라이선스 없음 / 유보 | KLIFS, Kincore, ProfKin, Davis/Metz/PKIS1 SI |

저장소 비공개가 이 문제를 대부분 덮는다. `ref/manifest.json`에 스냅샷마다 출처와 라이선스를 기록해, 나중에 공개용 export를 만들 때 무엇을 빼야 하는지 알 수 있게 한다.

## 문헌 수집 3경로

```
경로 A: 전략축 리뷰 논문 시드 → 참고문헌 전개 → primary 후보
경로 B: medchem 저널 + 전략축 쿼리 직접 검색
경로 C: KLIFS 리간드 결합 구조 → 해당 구조 보고 논문 역추적
        ↓
   PMID 후보 통합, 중복 제거
        ↓
   교집합 점수로 우선순위 (3경로 모두 = 최상위)
        ↓
   PDF 요청 목록 CSV
```

Biopython `Entrez`는 검색, 레코드 조회, PMID에서 PMC 연결 확인에만 쓴다. 인용망 전개는 별도 소스를 붙인다. 검색식은 `domains/kinase/queries.yaml`에 둔다.

경로 C가 KLIFS 덕에 강하다. 리간드 결합 구조와 서브포켓 점유 패턴을 미리 알 수 있으므로, "back pocket을 채운 전례"를 구조 쪽에서 먼저 골라 해당 논문을 요청할 수 있다.

## PDF 투입 흐름

```
1. inbox/PMID_12345678.pdf 를 넣는다
2. kb ingest 실행
3. 파일명 규칙 위반 시 첫 페이지에서 DOI/제목을 읽어 PubMed 조회로 매칭
4. 매칭 실패분은 inbox/unmatched/ 로 옮기고 목록 보고
5. MinerU 파싱 → Docling 파싱 → 추출 → 검사 → kb/ 반영
6. kb build 로 dist/ 와 wiki/ 갱신
```

같은 PDF를 다시 넣으면 sha256이 같으므로 캐시를 쓰고 중복 레코드를 만들지 않는다. PDF 한 편을 추가해도 전체 재처리가 일어나지 않는다.

캐시 키 구성: PDF sha256, 파서 이름·버전·백엔드·옵션, 프롬프트 버전, 모델·공급자, 스키마 버전, 어휘 버전, ref 스냅샷 ID. MinerU는 출력에 `_version_name`만 남기고 설정 지문이 없으므로 이 키를 직접 만든다.

성공 산출물이 온전할 때만 캐시를 쓴다. 실패나 중단된 실행을 완료로 기록하지 않는다.

## 소비 계약

### 입력: 구조 descriptor

KLIFS 필드와 같은 모양으로 맞춰 소비자의 변환 부담을 없앤다.

```json
{
  "target": {"gene": "EGFR", "uniprot": "P00533", "variant": "C797S"},
  "site_features": {
    "occupied_subpockets": ["bp_I_A", "front", "gate"],
    "accessible_subpockets": ["bp_II_in"],
    "dfg_state": "in",
    "alphaC_state": "out",
    "contacts": [{"uniprot_resnum": 793, "aa": "M", "type": "hbond"}]
  },
  "ligand_features": {"exposed_vectors": ["solvent"], "has_covalent_warhead": false},
  "goal": ["potency", "selectivity"]
}
```

`unknown`과 `null`을 구분한다. 모르는 값끼리 일치해도 유사도 가점을 주지 않는다.

`occupied_subpockets`는 KLIFS 의미(리간드 접촉)를 따른다. `accessible_subpockets`는 KLIFS에 없는 소비자 판단으로, 아직 접촉하지 않았지만 현재 리간드가 성장해 들어갈 수 있다고 본 서브포켓이다. KB는 이 값을 만들지 않고 structure의 `not_occupied`를 accessible로 해석하지 않는다. 성장 방향 힌트로만 쓴다.

`contacts`의 잔기 번호는 `uniprot_resnum`이다. PDB 번호로 분석한 소비자는 `kb.structure()`의 `sifts_mapping`으로 변환한다.

### 출력: 매칭 이유 3범주

| 범주 | 의미 | 표시 |
|---|---|---|
| 같은 target | 같은 kinase의 전례 | 직접 관련 |
| 같은 KLIFS 위치, 다른 target | 구조적으로 유사한 위치 | 전이 가설 |
| 같은 태그 조합 | 같은 부위·목표·전술 | 가장 약함 |

세 범주를 합치지 않는다. 다른 target의 전례는 가설의 단서이지 적용 가능성의 증거가 아니다.

### reader API

```python
kb.get("MOVE-0001")
kb.find(descriptor)                  # 또는 tags=, target=
kb.cite("MOVE-0001")                 # PMID, 위치, quote, kb_version
kb.tactics(site=..., goal=...)       # 집계
kb.reference("P00533")
kb.structure("6LUD", chain="A")
kb.mutation("EGFR", "T790M")         # overcome_by 유무를 구분해 응답
```

기본값은 `moves.jsonl`(검사 전부 통과)만 본다. 플래그된 레코드는 명시적으로 켜야 나온다.

과도하게 넓은 질의는 `total`과 `truncated`, 추가 필터 안내를 돌려준다. 정상 검색을 시스템 오류로 취급하지 않는다.

## wiki 3축

| 축 | 경로 | 내용 |
|---|---|---|
| kinase별 | `wiki/kinases/EGFR.md` | 구조 좌표와 그 타겟에서 나온 Move 목록 |
| 태그 조합별 | `wiki/tactics/front_pocket__potency__covalent_warhead.md` | 어느 부위에서 어떤 전술이 몇 번 통했는지 |
| 논문별 | `wiki/papers/PMID-12345678.md` | 그 논문에서 나온 Move와 그림 포인터 |

모든 페이지의 front matter에 생성 시각, 빌드 해시, 소스 레코드 ID, 미검수 경고를 박는다. wiki는 파생물이며 정본이 아니다. `wiki/index.md`도 생성물이다.

## 실패 처리

| 상황 | 처리 | 재개 |
|---|---|---|
| 타임아웃, 429, 일시적 5xx | 최대 3회 재시도, 서버 대기 지시 반영 | 실패 ID만 기록해 재실행 |
| 인증·설정 오류 | 해당 단계 중단, 비밀값 없는 오류 메시지 | 설정 수정 후 같은 입력으로 재개 |
| 원문 없음 | `not_accessible` 기록 | 메타데이터 유지, 전문 추출 보류 |
| MinerU 실패, PDF 손상 | 해당 문헌 격리, 원본과 오류 보존 | 다른 문헌은 진행. 무한 OCR 재시도 금지 |
| 두 파서 결과 불일치 | `cross_parser_numbers: fail` | 격리하지 않고 flagged로 배포 |
| KLIFS/Kincore 상태 충돌 | 양쪽 원값 보존, `agreement: conflict` | 확정 주장으로 배포하지 않음 |
| 외부 API 장애 중 검증 | `lookup_failed`와 `not_found` 구분 | 장애 때문에 기존 링크를 지우지 않는다 |
| LLM 스키마 이탈 | 로컬 검증 후 보정 요청 1회 | 계속 실패하면 후보 격리 |
| dist 빌드 실패 | 임시 디렉터리에서 실패 종료 | 마지막 정상 dist 유지 |
| 과도하게 넓은 질의 | `total`, `truncated`, 필터 안내 반환 | 오류로 취급하지 않음 |
| 알 수 없는 ID, 스키마 비호환 | 명시적 오류 | 0건 검색 결과와 구분 |

## 상태 관리

이 프로젝트에 런타임 상태는 없다. 모든 상태가 파일이다.

| 상태 | 위치 | 누가 쓰는가 |
|---|---|---|
| 외부 스냅샷 | `ref/` | `sync-ref`만 |
| 추출 레코드 | `kb/` | `ingest`만 |
| 빌드 산출물 | `dist/`, `wiki/` | `build`만 |
| 캐시, 파싱 중간물 | `work/` | 여러 명령. gitignore |
| 격리된 레코드 | `work/quarantine/` | `ingest` |
| 잠금 | `work/.lock` | 모든 쓰기 명령 |

입력이 같으면 `kb/`와 `dist/`가 바이트 단위로 동일해야 한다. `dist/manifest.json`에 파일별 해시를 둔다. 레코드 개수만 같아도 내용 변경이나 중복 치환이 발생할 수 있기 때문이다.

빌드가 계산하는 `analogous_positions`나 집계는 `dist/`에만 쓴다. `kb/`를 빌드가 수정하지 않는다.
