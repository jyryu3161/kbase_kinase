# kb_kinase

## 1. 목적

`kb_kinase`는 kinase 구조 기반 신약설계 및 lead optimization을 위한 독립 지식베이스 구축 저장소이다.

최종 목표는 다음 질문에 답할 수 있는 지식 계층을 만드는 것이다.

> 주어진 kinase–ligand 결합 구조에서 어떤 residue, pocket, conformational state, interaction을 활용하여 potency, selectivity, resistance profile, physicochemical property를 개선할 수 있는가?

본 repository의 역할은 다음 네 단계로 구분한다.

1. **Literature acquisition**
   - PubMed PMID 및 논문 metadata 수집
   - review → primary paper citation expansion
   - PDB/KLIFS 등 구조 ID 연결

2. **Knowledge extraction**
   - kinase 구조 특징
   - ligand interaction
   - lead optimization 사례
   - selectivity/resistance 전략
   - 실패/trade-off 사례

3. **Curated KB**
   - concept
   - engineering rule
   - successful case
   - limitation/failure pattern

4. **LLM Wiki**
   - 사람이 읽을 수 있으면서
   - LLM agent가 검색하고 reasoning할 수 있는 Markdown/YAML 지식체계


---

# 2. Repository 기본 구조

```text
kb_kinase/
│
├── README.md
├── LICENSE
├── CITATION.cff
├── pyproject.toml
├── pixi.toml
├── .gitignore
├── .env.example
│
├── config/
│   ├── settings.yaml
│   ├── journal_whitelist.yaml
│   ├── search_queries.yaml
│   ├── target_kinases.yaml
│   ├── evidence_scoring.yaml
│   ├── wiki_taxonomy.yaml
│   └── schemas/
│       ├── paper.schema.json
│       ├── structure.schema.json
│       ├── case.schema.json
│       ├── rule.schema.json
│       └── concept.schema.json
│
├── data/
│   ├── raw/
│   │   ├── pubmed/
│   │   ├── pmc/
│   │   ├── crossref/
│   │   ├── pdb/
│   │   ├── uniprot/
│   │   ├── klifs/
│   │   └── references/
│   │
│   ├── interim/
│   │   ├── papers/
│   │   ├── structures/
│   │   ├── citations/
│   │   └── fulltext/
│   │
│   ├── processed/
│   │   ├── papers.parquet
│   │   ├── papers.csv
│   │   ├── structures.parquet
│   │   ├── cases.parquet
│   │   ├── evidence.parquet
│   │   └── relations.parquet
│   │
│   ├── curated/
│   │   ├── concepts/
│   │   ├── rules/
│   │   ├── cases/
│   │   ├── limitations/
│   │   └── references/
│   │
│   └── external/
│       └── README.md
│
├── llm_wiki/
│   ├── README.md
│   ├── index.md
│   │
│   ├── concepts/
│   │   ├── kinase_fold/
│   │   ├── binding_site/
│   │   ├── conformational_states/
│   │   └── ligand_interactions/
│   │
│   ├── binding_modes/
│   │   ├── type_I/
│   │   ├── type_I_half/
│   │   ├── type_II/
│   │   ├── type_III/
│   │   ├── type_IV/
│   │   ├── allosteric/
│   │   └── covalent/
│   │
│   ├── design_rules/
│   │   ├── potency/
│   │   ├── selectivity/
│   │   ├── resistance/
│   │   └── properties/
│   │
│   ├── cases/
│   │   ├── approved_drugs/
│   │   ├── clinical_candidates/
│   │   └── experimental/
│   │
│   ├── failure_patterns/
│   ├── target_families/
│   ├── methods/
│   └── references/
│
├── scripts/
│   ├── acquisition/
│   ├── literature/
│   ├── structure/
│   ├── curation/
│   ├── wiki/
│   ├── validation/
│   └── utils/
│
├── src/
│   └── kb_kinase/
│       ├── __init__.py
│       ├── literature/
│       ├── structures/
│       ├── schemas/
│       ├── scoring/
│       ├── curation/
│       ├── wiki/
│       └── utils/
│
├── prompts/
│   ├── paper_screening.md
│   ├── review_case_extraction.md
│   ├── primary_paper_extraction.md
│   ├── structural_rationale.md
│   ├── engineering_rule_extraction.md
│   ├── failure_case_extraction.md
│   └── wiki_page_generation.md
│
├── notebooks/
│   ├── 01_pubmed_search.ipynb
│   ├── 02_review_screening.ipynb
│   ├── 03_case_mining.ipynb
│   ├── 04_structure_mapping.ipynb
│   └── 05_wiki_qc.ipynb
│
├── tests/
│   ├── test_pubmed.py
│   ├── test_schemas.py
│   ├── test_structure_mapping.py
│   ├── test_scoring.py
│   └── test_wiki_links.py
│
└── docs/
    ├── architecture.md
    ├── literature_strategy.md
    ├── curation_guideline.md
    ├── evidence_policy.md
    ├── wiki_style_guide.md
    └── roadmap.md
```

---

# 3. 가장 중요한 데이터 계층

## 3.1 `data/raw/`

외부 source에서 받은 것을 **가급적 수정하지 않고 그대로 보존**한다.

예:

```text
data/raw/pubmed/
    pubmed_review_search_2026-09-15.xml
    pubmed_primary_search_2026-09-15.xml

data/raw/pdb/
    3CS9.cif
    4WA9.cif
```

원칙:

- raw 파일 overwrite 금지
- 수집일 포함
- source 기록
- 가능한 경우 API request/query도 같이 기록

### PDF

copyright 문제가 있기 때문에 GitHub repo에는 일반적으로 넣지 않는 것을 권장한다.

```text
data/external/
    README.md
```

에 다음만 관리한다.

```text
PMID
local_filename
local_path
access_type
OA_status
```

PMC Open Access 논문은 라이선스가 허용하는 범위에서 XML/text를 관리할 수 있다.

---

# 4. `data/interim/`

raw 데이터를 정규화한 중간 결과.

예:

```text
PMID
Title
Abstract
Journal
Year
Authors
DOI
PMC_ID
PDB_ID
Target
Drug
```

LLM 처리 이전 데이터도 이 단계에 둔다.

---

# 5. `data/processed/`

프로그램이 직접 사용할 canonical tables.

가장 중요한 것은 `papers.parquet`.

## Paper schema

```yaml
paper_id: PMID_12345678

pmid: "12345678"
pmcid:
doi:

title:
journal:
year:

paper_type:
  - review
  - primary
  - structural
  - medicinal_chemistry
  - clinical

target:
kinase_family:

drug:
compound_series:

design_topics:
  - potency
  - selectivity
  - resistance
  - physicochemical_property

inhibitor_type:
  - type_I
  - type_II
  - allosteric
  - covalent

pdb_ids: []

fulltext_status:
  - fulltext
  - abstract_only
  - unavailable

selected: true

selection_score: 15

case_ids:
  - CASE_KIN_001
```

---

# 6. Curated Knowledge Layer

`data/curated/`는 **LLM이 자동으로 생성한 결과를 사람이 검수한 지식**만 들어간다.

Raw LLM output을 여기에 넣으면 안 된다.

## Concept

예:

```text
CONCEPT_KIN_001_GATEKEEPER
```

```yaml
id: CONCEPT_KIN_001

name: Gatekeeper residue

category:
  kinase_binding_site

definition:

structural_role:

drug_design_relevance:

examples:

evidence:
  - PMID:
  - PDB:

confidence:
  high
```

---

# 7. Engineering Rule

가장 중요한 KB 단위.

예:

```text
RULE_KIN_SELECTIVITY_004
```

```yaml
id: RULE_KIN_SELECTIVITY_004

name:
  Exploiting gatekeeper-dependent back-pocket accessibility

design_goal:
  selectivity

structural_feature:
  gatekeeper

observation:

design_hypothesis:

recommended_strategy:

applicable_when:

avoid_when:

risks:

validation:
  - target/off-target structural alignment
  - pocket comparison
  - docking
  - biochemical profiling

supporting_cases:
  - CASE_KIN_002
  - CASE_KIN_014

evidence:
  - PMID:
    evidence_type: experimental

confidence:
  high
```

---

# 8. Case가 핵심 단위

논문이 아니라 **design case**가 KB의 중심이다.

예:

```text
CASE_KIN_001/
    case.yaml
    summary.md
    structures.yaml
    compounds.yaml
    evidence.yaml
```

## `case.yaml`

```yaml
id: CASE_KIN_001

target:
  gene:
  uniprot:
  kinase_group:

drug:

development_stage:

design_problem:
  - potency
  - selectivity

starting_point:

structural_observation:

key_residues:

design_change:

result:

tradeoffs:

lessons:

pdb_ids:

papers:
  - PMID:
    role: lead_optimization
  - PMID:
    role: structural_validation
```

---

# 9. `llm_wiki/`는 curated KB와 분리

중요하다.

```text
data/curated/
```

는 canonical structured knowledge.

```text
llm_wiki/
```

는 이를 기반으로 생성된 **human/LLM-readable knowledge representation**이다.

즉:

```text
Raw literature
      ↓
Processed data
      ↓
Curated KB
      ↓
LLM Wiki
```

이다.

LLM Wiki를 직접 source of truth로 만들지 않는 것이 좋다.

---

# 10. LLM Wiki 기본 구조

## Structural concepts

```text
llm_wiki/concepts/
```

대표 페이지:

```text
hinge.md
gatekeeper.md
dfg_motif.md
alphaC_helix.md
activation_loop.md
glycine_rich_loop.md
catalytic_lysine.md
solvent_front.md
front_pocket.md
back_pocket.md
```

---

# 11. Binding mode

```text
type_I.md
type_I_half.md
type_II.md
type_III.md
type_IV.md
covalent.md
reversible_covalent.md
```

---

# 12. Lead optimization rules

```text
design_rules/

potency/
    hinge_optimization.md
    back_pocket_filling.md
    water_displacement.md

selectivity/
    gatekeeper_exploitation.md
    unique_residue_targeting.md
    conformational_selectivity.md
    allosteric_selectivity.md

resistance/
    gatekeeper_mutation.md
    solvent_front_mutation.md
    p_loop_mutation.md

properties/
    solvent_exposed_substituent.md
    lipophilicity_management.md
```

---

# 13. `scripts/` 세부 구조

```text
scripts/
│
├── acquisition/
│   ├── search_pubmed.py
│   ├── fetch_pubmed_records.py
│   ├── fetch_pmc_fulltext.py
│   ├── fetch_crossref.py
│   └── fetch_pdb.py
│
├── literature/
│   ├── identify_reviews.py
│   ├── extract_review_references.py
│   ├── resolve_pmids.py
│   ├── deduplicate_papers.py
│   ├── detect_fulltext.py
│   └── score_papers.py
│
├── structure/
│   ├── map_pdb_to_pmid.py
│   ├── parse_mmcif.py
│   ├── identify_kinase_chain.py
│   ├── map_uniprot.py
│   ├── extract_ligands.py
│   ├── analyze_binding_site.py
│   └── calculate_contacts.py
│
├── curation/
│   ├── create_case_candidates.py
│   ├── merge_case_evidence.py
│   ├── validate_case_schema.py
│   └── promote_to_curated.py
│
├── wiki/
│   ├── build_concept_pages.py
│   ├── build_rule_pages.py
│   ├── build_case_pages.py
│   ├── build_indexes.py
│   └── validate_links.py
│
└── validation/
    ├── check_pmids.py
    ├── check_pdb_ids.py
    ├── check_dois.py
    ├── check_evidence.py
    └── check_duplicate_cases.py
```

---

# 14. Biopython의 역할

Biopython을 모든 데이터 수집에 사용하려고 하면 안 된다.

Biopython은 크게 다음 역할에 사용하는 것이 적절하다.

## B1. PubMed search

```python
from Bio import Entrez

Entrez.email = "..."
handle = Entrez.esearch(
    db="pubmed",
    term=query,
    retmax=100
)
```

사용 목적:

- PMID search
- query 자동화
- review PMID 확보
- target/drug-specific literature search

---

# 15. PubMed record retrieval

```python
Entrez.efetch(
    db="pubmed",
    id=pmids,
    rettype="medline",
    retmode="text"
)
```

또는 XML.

추출 대상:

```text
PMID
Title
Abstract
Journal
Publication date
Authors
DOI
Publication type
MeSH
```

가능하면 MEDLINE text보다 **XML을 canonical raw format으로 저장**한다.

---

# 16. PMC 확인

Biopython `Entrez`로 PMID → PMC 연결 정보를 확인한다.

목적:

```text
PMID
→ PMCID
→ full text availability
```

PMC OA 여부는 별도 검증한다.

---

# 17. Citation expansion

NCBI 관련 데이터나 Crossref/OpenAlex 같은 외부 source를 조합하는 것이 좋다.

Biopython만으로 citation network 전체를 해결하려고 하지 않는다.

초기 workflow:

```text
Review PMID
→ references
→ DOI/PMID resolution
→ candidate primary papers
```

---

# 18. Biopython PDB/MMCIF

추천:

```python
from Bio.PDB import MMCIFParser
```

PDB legacy format보다는 **mmCIF 우선**.

해야 할 일:

```text
structure parse
chain extraction
residue coordinates
ligand detection
distance calculation
neighbor search
```

---

# 19. Residue neighborhood

예:

```python
from Bio.PDB import NeighborSearch
```

향후 다음과 같은 데이터 생성에 사용한다.

```yaml
ligand:
  name: ABC

contacts:
  - residue: MET318
    distance: 3.1
    interaction_candidate: hydrophobic

  - residue: GLU316
    distance: 2.8
    interaction_candidate: hydrogen_bond
```

주의:

**거리만으로 H-bond를 확정하지 않는다.**

geometry/atom type 기반 별도 rule이 필요하다.

---

# 20. Sequence alignment

Biopython은 kinase sequence 비교에도 유용하다.

용도:

```text
target vs off-target sequence
kinase domain alignment
residue conservation
gatekeeper position mapping
```

사용:

```python
Bio.Align
```

다만 kinase pocket 비교에는 향후 KLIFS의 표준화된 85-residue numbering을 사용하는 것이 더 좋다.

---

# 21. UniProt ↔ PDB mapping

Biopython 단독이 아니라 UniProt API/SIFTS를 이용하는 것이 좋다.

목적:

```text
PDB residue number
↔
UniProt residue number
```

이 mapping을 반드시 저장해야 한다.

```yaml
pdb:
  chain: A
  residue: 318

uniprot:
  accession: P00533
  residue: 790
```

---

# 22. ligand extraction

Biopython으로 structure에서 hetero residue를 식별할 수 있다.

단:

```text
HOH
ions
buffers
cryoprotectants
```

등을 제거하기 위한 blacklist/annotation이 필요하다.

파일:

```text
config/non_drug_ligands.yaml
```

을 별도로 두는 것이 좋다.

---

# 23. Biopython이 하지 않아도 되는 것

다음은 억지로 Biopython으로 구현하지 않는다.

```text
KLIFS query
ChEMBL query
Crossref
complex cheminformatics
molecule standardization
substructure search
```

이런 부분은 각각:

```text
requests/httpx
RDKit
pandas/polars
```

가 더 적합하다.

---

# 24. 검색 query 관리

검색식은 코드에 hard-code하지 않는다.

```text
config/search_queries.yaml
```

예:

```yaml
seed_reviews:

  structural:
    - >
      kinase inhibitor AND
      ("structure-based" OR "structure-guided")
      AND Review[Publication Type]

  selectivity:
    - >
      kinase inhibitor AND
      selectivity AND
      structure AND
      Review[Publication Type]

  resistance:
    - >
      kinase inhibitor AND
      resistance AND
      structure AND
      Review[Publication Type]

  covalent:
    - >
      kinase AND
      covalent inhibitor AND
      Review[Publication Type]
```

---

# 25. Journal whitelist

```text
config/journal_whitelist.yaml
```

Tier A:

```text
Nature
Nature Chemical Biology
Nature Cancer
Cancer Discovery
Science
Cell
JACS
Angewandte Chemie
Nature Communications
```

Tier B:

```text
Journal of Medicinal Chemistry
ACS Medicinal Chemistry Letters
Journal of Chemical Information and Modeling
Chemical Science
Structure
Biochemistry
```

단 journal은 **hard exclusion criterion이 아니라 scoring factor**로 사용하는 것을 권장한다.

---

# 26. Evidence scoring

```text
config/evidence_scoring.yaml
```

예:

```yaml
ligand_bound_structure: 3
prospective_structure_guided_design: 3
clear_lead_optimization: 3
residue_level_rationale: 3

potency_improvement: 2
selectivity_improvement: 2
resistance_overcome: 2
clinical_candidate: 2

major_journal: 1
fulltext_available: 1
```

---

# 27. 자동 screening 결과

각 논문에:

```yaml
selection_score: 16

classification:
  core: true

reason:
  - ligand-bound structure
  - prospective design
  - clear medicinal chemistry optimization
```

를 저장한다.

최종 selection은 사람이 확인한다.

---

# 28. LLM 사용 단계

LLM이 직접 raw PubMed search를 담당하게 하지 않는다.

파이프라인:

```text
Python deterministic retrieval
        ↓
Metadata normalization
        ↓
Candidate filtering
        ↓
Full text
        ↓
LLM extraction
        ↓
Schema validation
        ↓
Human review
        ↓
Curated KB
        ↓
LLM Wiki
```

---

# 29. LLM output도 schema 강제

예를 들어 `primary_paper_extraction.md`에서는 반드시 JSON/YAML 형태로 추출.

```yaml
design_problem:

starting_compound:

structural_observation:

key_residues:

chemical_modification:

experimental_effect:

structural_interpretation:

tradeoffs:

evidence_sentences:

confidence:
```

없는 정보는 추측하지 않고:

```yaml
not_reported
```

로 기록한다.

---

# 30. PMID와 evidence 연결

모든 지식에는 반드시 source가 있어야 한다.

나쁜 형태:

```text
Gatekeeper mutation causes resistance.
```

좋은 형태:

```yaml
claim:
  Gatekeeper mutation can reduce inhibitor binding
  through steric obstruction.

evidence:
  - PMID: XXXXXXXX
    evidence_type: experimental_structure

  - PMID: XXXXXXXX
    evidence_type: biochemical
```

---

# 31. Wiki page마다 provenance

예:

```yaml
---
id: RULE_KIN_004
title: Gatekeeper exploitation
version: 0.2
last_updated: 2026-09-15

source_cases:
  - CASE_KIN_003
  - CASE_KIN_011

source_pmids:
  - "12345678"
  - "23456789"

confidence: high
---
```

이 front matter를 모든 Wiki 페이지에 넣는 것을 권장한다.

---

# 32. Wiki index

자동 생성한다.

```text
llm_wiki/index.md
```

예:

```text
## Structural features

- Hinge
- Gatekeeper
- DFG motif
- αC helix
- Solvent front

## Design strategies

- Hinge optimization
- Back-pocket exploitation
- Allosteric targeting
- Covalent targeting

## Cases

- ...
```

---

# 33. ID convention

처음부터 고정한다.

```text
CONCEPT-KIN-0001
RULE-KIN-POT-0001
RULE-KIN-SEL-0001
RULE-KIN-RES-0001

CASE-KIN-0001

PAPER-PMID-12345678
STRUCT-PDB-4XYZ
```

---

# 34. Versioning

KB는 성장하므로 기존 지식을 덮어쓰는 방식만 사용하면 안 된다.

Git 자체 versioning + metadata version을 같이 사용하는 것을 권장한다.

```yaml
version: 1.2
created:
updated:
status:
  draft
  reviewed
  validated
  deprecated
```

---

# 35. Pipeline CLI

최종적으로는:

```bash
kb-kinase search-reviews

kb-kinase fetch-pubmed

kb-kinase expand-references

kb-kinase score-papers

kb-kinase fetch-structures

kb-kinase create-cases

kb-kinase validate

kb-kinase build-wiki
```

처럼 CLI로 실행되는 형태가 가장 좋다.

---

# 36. 초기 MVP

V0.1에서는 모든 기능을 구현하지 않는다.

### MVP 1 — Literature

구현:

```text
PubMed query
PMID collection
metadata retrieval
deduplication
journal filtering
fulltext status
CSV/Parquet output
```

목표:

**seed review 10–15편 확보**

---

### MVP 2 — Case discovery

Review full text에서:

```text
target
drug
compound
PDB
primary paper
design strategy
```

추출.

목표:

**30–40개 kinase design case 후보**

---

### MVP 3 — Primary paper

Case별 primary paper:

```text
lead optimization
structural paper
selectivity
resistance
```

수집.

목표:

**20–25개 최종 case / 40–60 primary papers**

---

### MVP 4 — Structure

PDB/mmCIF를 받아:

```text
protein chain
ligand
residue neighborhood
UniProt mapping
```

생성.

---

### MVP 5 — Curated KB

최종:

```text
20–25 cases
20–30 rules
20–30 concepts
10–15 failure patterns
```

---

### MVP 6 — LLM Wiki

Curated KB를 Markdown Wiki로 변환.

---

# 37. Phase 2 이후 구조 분석 확장

향후 별도 structure-agent와 연결할 때 추가한다.

```text
pocket detection
target/off-target comparison
hinge interaction analysis
DFG state classification
αC state
gatekeeper identification
water network
interaction fingerprint
mutation mapping
resistance hotspot
```

이것들은 현재 KB 구축 repository와 분리하거나:

```text
src/kb_kinase/structures/
```

에서 최소 기능만 제공하는 것이 좋다.

실제 heavy structural analysis는 추후 별도:

```text
kinase_structure_agent
```

repository로 분리해도 된다.

---

# 38. Git에 넣지 않을 것

`.gitignore`:

```text
data/raw/pmc/pdf/
data/external/fulltext/
*.pdf

.env
API keys

large structure archives
vector databases
LLM caches
```

단 PMID, DOI, metadata, extraction 결과는 Git에 넣는다.

---

# 39. 권장 Python stack

최소:

```text
Python 3.12
Biopython
pandas 또는 polars
pyarrow
pydantic
PyYAML
httpx
tenacity
lxml
beautifulsoup4
rich
typer
pytest
```

구조 분석 확장:

```text
MDAnalysis
gemmi
ProDy
```

화학구조:

```text
RDKit
```

LLM integration은 특정 vendor에 묶지 말고 adapter 형태를 권장한다.

---

# 40. 최종 데이터 흐름

```text
PubMed / PMC / PDB / KLIFS
            │
            ▼
        RAW DATA
            │
            ▼
      normalized records
            │
            ▼
      literature scoring
            │
            ▼
      selected papers
            │
            ▼
       case extraction
            │
            ▼
   structure verification
            │
            ▼
        Curated KB
        /        \
       /          \
 Concepts        Cases
 Rules           Failures
       \          /
        \        /
         LLM Wiki
            │
            ▼
      Kinase Design Agent
```

---

# 41. 가장 중요한 설계 원칙

### 1.
**논문 DB를 만드는 것이 아니다.**

→ kinase lead optimization 지식을 만든다.

### 2.
**PMID가 기본 provenance key다.**

### 3.
**논문보다 Case가 중심 object다.**

### 4.
**Case보다 Rule이 향후 agent에는 더 중요하다.**

### 5.
`raw`, `processed`, `curated`, `llm_wiki`를 반드시 분리한다.

### 6.
LLM 생성 결과는 바로 canonical KB로 승격하지 않는다.

### 7.
모든 설계 rule은 실제 case와 PMID까지 역추적 가능해야 한다.

### 8.
구조 ID는 PDB, sequence identity는 UniProt을 canonical identifier로 사용한다.

### 9.
Kinase-specific 구조 위치는 장기적으로 KLIFS numbering과 연결한다.

### 10.
최종 목표는:

```text
Structure observation
        ↓
Engineering Rule
        ↓
Similar successful Cases
        ↓
Lead optimization hypothesis
        ↓
Evidence
```

가 자동으로 연결되는 KB를 만드는 것이다.