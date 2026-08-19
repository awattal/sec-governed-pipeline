# Column Inventory

Counts across the raw and modelled layers, and what happens between
them. Source of truth is `information_schema`; this document is the
readable summary.

## Totals

| Layer | Columns |
|---|---|
| Raw tables (4) | 69 |
| — of which SEC-native | 65 |
| — of which added by `ingest.py` | 4 |
| Model columns (4 models) | 57 |

`ingest.py` adds `quarter` to every raw table as provenance. It is
not present in the SEC source files.

## Raw layer by table

| Table | SEC columns | Consumed by a model | Unused |
|---|---|---|---|
| `sub` | 36 | 14 | 22 |
| `num` | 10 | 10 | 0 |
| `tag` | 9 | 9 | 0 |
| `pre` | 10 | 0 | 10 |
| **Total** | **65** | **33** | **32** |

Roughly half of all SEC columns are unused. Almost all of that sits
in `sub` and `pre`.

## Model layer by model

| Model | Columns |
|---|---|
| `stg_submissions` | 15 |
| `stg_num` | 16 |
| `stg_tag` | 10 |
| `int_num_in_scope` | 16 |
| **Total** | **57** |

`int_num_in_scope` is `select *` from `stg_num` with a row filter. It
duplicates all 16 columns and creates none.

## Elements created in the model layer

Six elements exist in no source table.

| Element | Model | Built from |
|---|---|---|
| `taxonomy` | `stg_num` | `version` |
| `period_end_date` | `stg_num` | `ddate` |
| `is_us_gaap` | `stg_num` | `version` |
| `is_consolidated` | `stg_num` | `segments` |
| `is_parent_only` | `stg_num` | `coreg` |
| `taxonomy` | `stg_tag` | `version` |

Plus `quarter`, carried from `ingest.py` into three models.

## Dropped from `sub` (22 columns)

Filer contact and administrative metadata, consumed by no model:

`stprba`, `cityba`, `zipba`, `bas1`, `bas2`, `baph` (business address
and phone); `countryma`, `stprma`, `cityma`, `zipma`, `mas1`, `mas2`
(mailing address); `countryinc`, `stprinc` (state of incorporation);
`ein`, `former`, `afs`, `fye`, `accepted`, `instance`, `nciks`,
`aciks`.

No use case requires them. Revisit if one does.

## `pre` — ingested, not modelled

All 10 SEC columns are unused. The table holds statement structure —
which line each tag occupies in which statement — and was ingested
for future work on statement-level checks. It is out of scope for
lineage and CDE designation until a model reads it.

## Scoping note for CDE designation

Criticality is scored on 41 elements, not 57. `int_num_in_scope`
duplicates `stg_num` exactly, so scoring both would double-count
every fact-level element. `int_num_in_scope` is scored as the end of
the chain; `stg_num` inherits.

41 = 16 (`int_num_in_scope`) + 15 (`stg_submissions`) + 10 (`stg_tag`).
