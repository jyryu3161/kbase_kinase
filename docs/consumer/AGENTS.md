# AGENTS.md — for agents consuming this knowledge base

This file is written in English because every record in this knowledge base is
written in English. Project documentation is in Korean; the data is not.

If you are an LLM agent that has been handed this repository in order to reason
about a protein-ligand complex, read this file first.

---

## 1. What this knowledge base gives you

One thing: **precedent**.

You are looking at a kinase-ligand complex. You want to propose the next
chemical modification. This knowledge base answers:

> At this position in this pocket, has anyone tried a modification like this
> before? What happened, and what did it cost them?

The atomic record is a **Design Move**: one compound-to-compound modification,
with the structural observation that motivated it, the measured effect with its
assay context, the trade-offs, and pointers back to the exact table row or
figure panel in the source paper.

## 2. What this knowledge base does NOT give you

Read this section before you trust anything here.

**It does not interpret structures.** Computing contacts, classifying pockets,
deciding which subpocket a substituent occupies: that is your job. This
knowledge base takes a descriptor you produce and returns precedent.

**It does not contain human-validated knowledge.** No person has reviewed any
record. Every record carries `review_status: unreviewed`, and that is the only
value that field ever takes. There is no confidence score, because there is
nobody to assign one honestly.

**It does not contain design rules.** You will not find prose that says "use
this tactic when X and avoid it when Y." Ungoverned generalization propagates
error further than individual records do. What you get instead is counts: how
many precedents exist for a given site-goal-tactic combination, how many
improved, how many got worse.

**It does not certify causal reasoning.** The machine checks verify that a
number appears in the source and that referenced identifiers exist. They do not
verify that the structural observation actually explains the measured effect.
That inference is the authors', and now yours.

## 3. How to query

### Input: a structure descriptor

Field names deliberately mirror KLIFS so that translation from KLIFS output (or
from your own analysis) is minimal.

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
  "ligand_features": {
    "exposed_vectors": ["solvent"],
    "has_covalent_warhead": false
  },
  "goal": ["potency", "selectivity"]
}
```

Subpocket names are KLIFS names and their semantics are **ligand contact**, not
pocket existence and not pocket openness. A subpocket in `occupied_subpockets`
means a ligand atom contacts it.

Omit what you do not know. Do not guess. `unknown` and `null` are distinct from
`false`, and matching two unknowns against each other earns no similarity
credit.

### Reader API

```python
kb.get("MOVE-0001")                   # one record by id
kb.find(descriptor)                   # precedent search; also tags=, target=
kb.cite("MOVE-0001")                  # PMID, page, table row, quote, kb_version
kb.tactics(site=..., goal=...)        # aggregate counts, not prose
kb.reference("P00533")                # kinase anatomy: anchors, domain, pocket seq
kb.structure("6LUD", chain="A")       # per-structure conformational state
kb.mutation("EGFR", "T790M")          # resistance mutation record
```

### Output: why it matched

`find` tells you *why* each result matched, in three distinct categories:

| Category | Meaning | How much to trust it |
|---|---|---|
| Same target | Precedent on the same kinase | Directly relevant |
| Same KLIFS position, different target | Structurally analogous position | **Transfer hypothesis.** Not demonstrated applicability |
| Same tag combination | Same site, goal, and tactic | Weakest. Check the structural context yourself |

Do not collapse these. A precedent from ABL1 at the same KLIFS position as your
EGFR site is a lead for a hypothesis, not evidence that it will work.

## 4. Record types

| File | Record | Unit |
|---|---|---|
| `moves.jsonl` | Design Move | One compound-to-compound modification |
| `moves_flagged.jsonl` | Design Move that failed a check | Same, but read the `checks` object first |
| `structures.jsonl` | Structure | `pdb_id` + `chain` + `ligand` |
| `references.jsonl` | Reference | One kinase (whole kinome coverage) |
| `mutations.jsonl` | Mutation | One resistance mutation |
| `figures.jsonl` | Figure | One figure or table, with panels |
| `tactics.jsonl` | Aggregate | One site-goal-tactic combination |
| `manifest.json` | Build metadata | File hashes, snapshot ids, kb_version |
| `CONTRACT.md` | Full schema | Generated at build time. Authoritative |

`CONTRACT.md` in `dist/` is generated by the build and is authoritative on field
names and value domains. This file explains intent; that file explains structure.

## 5. Reading numbers correctly

This is where you are most likely to go wrong. Every `effects` entry looks like
this:

```yaml
metric: IC50
assay: biochemical
assay_context: {atp_conc: "1 mM", construct: "...", cell_line: null}
before: {value: 10000, unit: nM, qualifier: ">"}
after:  {value: 11,    unit: nM, qualifier: "="}
direction: improved
magnitude_bucket: large
comparable: false
comparability_reason: "before is a lower bound"
fold_change: null
```

Rules the build enforces, which you can rely on:

1. If `qualifier` is not `=`, `fold_change` is `null`.
2. If `comparable` is `false`, `fold_change` is `null`.
3. `direction` and `magnitude_bucket` are always populated, even with no numbers.

So: **use `direction` and `magnitude_bucket` for ranking.** Use `fold_change`
only when it is non-null, and when it is null do not compute your own from
`before` and `after`. The `comparability_reason` field tells you why it was
withheld.

## 6. Reading conflicts correctly

Source databases disagree. When they do, this knowledge base does not pick a
winner.

```yaml
conformation:
  dfg:
    klifs: {value: in, source: SNAP-klifs-2026-09-15}
    kincore: {spatial: DFGin, dihedral: BLAminus, source: SNAP-kincore-2026-09-15}
    agreement: agree      # agree | conflict | one_source | unknown
```

On `agreement: conflict`, both raw values are preserved. Decide in your own
context, or report the disagreement to the user. Do not silently pick one.

Kincore emits `None` when atoms or residues are missing. That is a real value
meaning "not assignable," not a null.

## 7. Reading absence correctly

Three different kinds of nothing, and they are not interchangeable:

| Value | Meaning |
|---|---|
| `unmapped` | Position mapping was ambiguous or out of supported range |
| `not_observed` | The structure does not resolve this region |
| `not_applicable` | This kinase genuinely has no such feature |
| `lookup_failed` | An external service was down when we checked |
| `not_found` | We checked successfully and it is absent |

In particular, `mutations.jsonl` records with an empty `overcome_by` list mean
"no precedent in this knowledge base," **not** "no known solution exists."
`kb.mutation()` distinguishes these two cases in its response. A mutation absent
from the file entirely means we have no record of it at all.

## 8. Citing

When you use a Move to justify a proposal, cite it with `kb.cite()`. You get
back the PMID, the page and table row or figure panel, the quoted span (25 words
or fewer), and the `kb_version`. Pass all of it through to the user.

State that the record is unreviewed and machine-extracted. If the number you are
relying on has `cross_parser_numbers: fail` or lives in `moves_flagged.jsonl`,
say so explicitly. The user needs to know when to open the PDF.

## 9. Coverage model

Two layers with very different coverage and very different provenance.

**Reference layer: whole kinome.** Generated mechanically from external
snapshots (KLIFS, Kincore, UniProt, SIFTS, InterPro, KinHub). No LLM touched it.
Available for kinases nobody has written a Move about. Use it to establish
coordinates.

**Knowledge layer: wherever literature exists.** Moves, mutations, and figures
are LLM-extracted from papers that were manually obtained. Sparse and uneven by
design. A kinase with no Moves is not a kinase where nothing works; it is a
kinase whose papers are not in here yet.

Never report reference-layer coverage as knowledge-layer coverage.

## 10. If you need something that is not here

The knowledge layer grows by adding PDFs to `inbox/` and running `kb ingest`.
If your task keeps hitting empty results for a target or tactic that matters,
say so to the user with specifics: which target, which site, which tactic. That
is directly actionable as a literature request.

Do not fill gaps by inventing precedent. An honest "no precedent in this KB" is
useful. A fabricated one is worse than silence.
