# kbase_kinase

kinase 구조 기반 lead optimization 지식베이스.

최종 소비자는 protein-ligand 복합체를 보고 다음 화학구조 변형을 제안하는 multi-modal LLM agent다. 이 저장소는 그 제안의 근거가 될 **전례**를 공급한다.

> 지금 보고 있는 이 포켓의 이 위치에서, 이런 변형을 시도한 전례가 있는가.
> 있었다면 무슨 일이 일어났고, 대가는 무엇이었는가.

---

## 무엇이 들어 있나

원자 단위는 **Design Move**다. 화합물 A→B 변형 한 건에, 그 변형을 유발한 구조 관찰, 측정된 효과와 assay 조건, trade-off, 그리고 원문의 표 행이나 그림 패널을 가리키는 포인터가 붙는다.

계층은 두 겹이다.

| 계층 | 커버리지 | 출처 |
|---|---|---|
| reference | 전체 kinome | 외부 DB 스냅샷에서 기계 생성 |
| knowledge | 문헌이 있는 곳만 | 논문 PDF에서 LLM 추출 |

reference는 처음 보는 kinase에도 구조 좌표를 준다. knowledge는 희소하고 고르지 않으며, 그게 설계 의도다.

## 중요: 이 지식은 미검수다

사람이 어떤 레코드도 검수하지 않았다. 모든 레코드의 `review_status`는 `unreviewed`이고, 그것이 이 필드가 갖는 유일한 값이다. 신뢰도 점수는 없다. 정직하게 부여할 사람이 없기 때문이다.

레코드가 주장하는 것은 어떤 기계 검사를 통과했는지뿐이다.

- MinerU와 Docling 두 파서가 같은 수치를 뽑았는가
- 그 수치가 ChEMBL의 같은 문서 activity와 맞는가
- 인용 구간이 파싱 원문에 실제로 존재하는가
- PMID, 구조 참조, 태그가 실재하고 어휘를 지키는가

이 검사들이 못 잡는 것은 `dist/CONTRACT.md`에 적혀 있다. 요약하면, 두 파서가 같은 실수를 하면 통과하고, 숫자가 맞아도 다른 화합물의 값일 수 있으며, 관찰에서 효과로 이어지는 인과 해석은 어느 검사도 보증하지 않는다.

## 빠른 시작

### 소비자 agent라면

`docs/consumer/AGENTS.md`(빌드 후에는 `dist/AGENTS.md`)를 읽어라. 질의 방법, 레코드 종류, 수치와 충돌과 부재를 읽는 방법, 그리고 신뢰 한계가 거기 있다.

```python
kb.find({
  "target": {"gene": "EGFR", "uniprot": "P00533", "variant": "C797S"},
  "site_features": {"occupied_subpockets": ["bp_I_A", "front"], "dfg_state": "in"},
  "goal": ["potency", "selectivity"]
})
```

필드명은 KLIFS와 같은 모양이다. 구조 해석은 소비자가 하고, 전례는 이 저장소가 돌려준다.

### 논문을 추가하려면

```bash
cp paper.pdf inbox/PMID_12345678.pdf
kb ingest
kb build
```

파일명이 규칙을 벗어나도 첫 페이지에서 DOI나 제목을 읽어 스스로 맞춘다. 실패분은 `inbox/unmatched/`에 모여 보고된다.

어떤 논문을 구해야 할지는 다음으로 확인한다.

```bash
kb literature --plan    # 우선순위가 붙은 PMID 요청 목록 CSV
```

### 개발하려면

`AGENTS.md`의 CRITICAL 규칙을 먼저 읽어라. 특히 엔진이 도메인을 모른다는 규칙과 수치 처리 규칙은 위반하면 이 저장소의 존재 이유가 무너진다.

```bash
ruff check . && pytest
pytest tests/test_engine_isolation.py   # 엔진/도메인 경계 검사
```

## 명령어

```bash
kb sync-ref                    # 외부 스냅샷 갱신 (유일하게 네트워크를 쓰는 단계)
kb build-reference             # 전체 kinome reference + structures 생성
kb literature --plan           # PMID 후보 수집, PDF 요청 목록
kb ingest                      # inbox/ PDF 처리
kb build --check               # dist/ 빌드 + 검사 (오프라인)
kb ask examples/queries/*.json # 예제 질의
```

빌드는 네트워크를 쓰지 않는다. 외부 서비스가 죽어도 빌드가 되고, 과거 산출물을 재현할 수 있다.

## 디렉터리

```
src/kbase/          엔진. 도메인 단어를 모른다
src/domains/kinase/ kinase를 아는 유일한 곳
ref/                외부 스냅샷 (커밋, 해시 고정)
kb/                 추출 레코드 JSONL (전부 미검수)
dist/               빌드 산출물 + CONTRACT.md (커밋)
wiki/               생성된 마크다운 3축 (커밋)
inbox/ work/        PDF와 파싱 중간물 (gitignore)
```

## 다른 도메인에 복제하려면

`src/kbase/`는 지식의 내용을 모르는 기계류다. 복사해서 그대로 쓴다. `src/domains/` 아래 폴더 하나를 새로 채우면 같은 구조의 지식베이스가 된다.

이 경계는 `tests/test_engine_isolation.py`가 import 그래프로 감시한다.

## 문서

| 문서 | 내용 |
|---|---|
| `intend.md` | 왜 만드는가, 무엇이 아닌가, 성공 판정 기준 |
| `AGENTS.md` | 이 저장소에서 작업할 때의 규칙 (Codex 자동 로드, `CLAUDE.md`가 import) |
| `docs/consumer/AGENTS.md` | 소비자 agent용 안내 (영어) |
| `docs/PRD.md` | 사용자, 기능 범위, 하지 않을 일 |
| `docs/ARCHITECTURE.md` | 구조, 데이터 흐름, 스키마, 외부 소스 |
| `docs/ADR.md` | 설계 결정 27건과 트레이드오프 |
| `dist/CONTRACT.md` | 빌드가 생성. 소비 계약의 정본 (영어) |

## 기술 스택

Python, pydantic v2, typer, Biopython, MinerU 3.4.5 + Docling, OpenRouter `deepseek/deepseek-v4.1-flash`, pytest + tdd-guard, ruff.

외부 소스는 KLIFS, Kincore, UniProt, PDBe SIFTS, InterPro, KinHub, ChEMBL을 쓴다. 2026-09-15 기준 생존과 라이선스는 `docs/ARCHITECTURE.md`에 정리돼 있다.

## 상태

기획 완료. 구현은 `phases/` harness로 step 0부터 진행한다.
