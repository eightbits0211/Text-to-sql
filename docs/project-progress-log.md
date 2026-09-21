# Text-to-SQL Project Progress Log

This is the authoritative high-level progress table. Every agent session must
update it after completing a checkpoint, discovering a blocker, or changing
scope. Percentages are estimates of completed **project checkpoints**, not
claims about final model accuracy.

## Current status

| Field | Value |
|---|---|
| Last updated | 2026-09-21 |
| Overall completion | 76% |
| Current phase | Part 2 baseline quality and evidence |
| Part 2 internal freeze | 2026-09-30 |
| Official Part 2 deadline | 2026-10-15, 23:55 IST |
| Active branch | `feature/part2-classical-baseline` |
| Current blocker | HPC GPU job submission is paused during partitioning configuration; repository default-branch strategy and HPC remote project/scheduler details remain open |
| Next checkpoint | Run larger evaluation with manifest and add report-ready error analysis |

## Checkpoint log

| ID | Workstream | Checkpoint | Status | Completion | Owner | Evidence / notes | Next action |
|---|---|---|---|---:|---|---|---|
| P0.1 | Requirements | Course PDFs reviewed and scope extracted | Done | 100% | Lead agent | Text-to-SQL, Spider/WikiSQL, baseline/demo/report requirements recorded | Maintain traceability |
| P0.2 | Product | Main PRD created | Done | 100% | Lead agent | [`text-to-sql-prd.md`](./text-to-sql-prd.md) | Update only when scope changes |
| P0.3 | Part 2 | Part 2 plan and Sep 30 internal freeze created | Done | 100% | Lead agent | [`part-2-submission-plan.md`](./part-2-submission-plan.md) | Execute checkpoints |
| P0.4 | Governance | Agent rules created and updated | Done | 100% | Lead agent | [`agent-rules.md`](./agent-rules.md) | Apply to every agent |
| P0.5 | Git | Local Git initialized and origin configured | Done | 100% | Lead agent | Branch `spec/agent-governance-rules`; no commit/push yet | Create reviewed baseline commit |
| P1.1 | Repository | Review current files and choose tracked scope | In progress | 25% | Lead agent | PDFs and planning files currently present | Decide `.gitignore` and tracked docs |
| P1.2 | Architecture | System architecture documented | Done | 100% | Lead agent | [`system-architecture.md`](./system-architecture.md) | Validate against implementation |
| P1.3 | Planning | Granular checkpoint plan documented | Done | 100% | Lead agent | [`implementation-checkpoints.md`](./implementation-checkpoints.md) | Start P2 checkpoints |
| P1.4 | Coordination | Sub-agent operating model documented | Done | 100% | Lead agent | [`sub-agent-coordination-plan.md`](./sub-agent-coordination-plan.md) | Assign bounded tasks |
| P1.5 | State | Persistent session state file created | Done | 100% | Lead agent | [`../state.md`](../state.md) | Update at session end |
| P1.6 | Technology | Technology stack documented | Done | 100% | Lead agent | [`tech-stack.md`](./tech-stack.md) | Verify versions during setup |
| P1.7 | Authority | PRD audited against authoritative PDFs | Done | 100% | Lead agent | [`prd-authority-audit.md`](./prd-authority-audit.md) | Preserve traceability |
| P1.8 | Coordination | Environment and data-pipeline agents completed bounded reports | Done | 100% | Lead agent | Agent reports received; no files modified | Resolve setup decisions |
| P1.9 | Coordination | Evaluation-contract agent report | Done | 100% | Evaluation agent | Shared evaluator contracts and fixture acceptance checks received | Confirm policy decisions |
| P2.1 | Environment | Python 3.12 + uv environment and smoke test | Done | 100% | Lead agent | `uv sync --dev`, pytest, Ruff, and SQLite smoke test pass | Implement data contracts |
| P2.2 | Repository | Initial project baseline pushed | Done | 100% | Lead agent | Commits `72fbc48`, `cee1f4e`; branch pushed using `eightbits0211` CLI account | Establish PR base/default branch |
| P2.3 | HPC | HPC security/setup notes documented | Done | 100% | Lead agent | [`hpc-setup.md`](./hpc-setup.md); no key read or copied | Confirm host/user/scheduler |
| P2.4 | Governance | Session-end context-history rule documented | Done | 100% | Lead agent | [`agent-rules.md`](./agent-rules.md) and [`../state.md`](../state.md) updated | Apply at every session end |
| P2.5 | Data | Typed contracts and deterministic schema serializer | Done | 100% | Lead agent | `src/text_to_sql/data/`; 3 tests pass; Ruff passes; PR #2 merged | Add SQLite fixtures |
| P2.6 | HPC | Non-destructive SSH authentication test | Done | 100% | Lead agent | Host authentication succeeded; no key contents accessed | Confirm remote path/scheduler |
| P2.7 | Repository/HPC | PR #1 merged and GPU submission pause recorded | Done | 100% | Lead agent | PR #1 merged; HPC team pause is documented | Continue CPU-only work; resume GPU work when enabled |
| P2.8 | Data | SQLite schema extraction and synthetic fixture tests | Done | 100% | Lead agent | `sqlite_schema.py`; 6 tests pass; Ruff passes | Implement WikiSQL loader |
| P2.10 | Data | WikiSQL JSON loader and exclusion statistics | Done | 100% | Lead agent | `wikisql.py`; 9 tests pass; Ruff passes; no PR opened yet | Implement Spider loader |
| P2.11 | Data/Evaluation | Spider loader, fixtures, and CPU evaluation harness | Done | 100% | Lead agent | `spider.py`, `metrics.py`; 12 tests pass; Ruff passes; no PR opened | Review checkpoint and select baseline |
| P2.12 | Baseline | Deterministic template baseline and shared prediction adapter | Done | 100% | Lead agent | `baselines/template.py`; count/aggregate generation and evaluation adapter covered by tests | Evaluate against downloaded benchmark data |
| P2.13 | Artifacts | JSONL prediction artifact persistence | Done | 100% | Lead agent | `evaluation/artifacts.py`; one-record-per-example fixture test | Add persisted metric reports |
| P2.14 | Demo | CLI question → SQL → read-only result | Done | 100% | Lead agent | `text-to-sql-demo` entry point and `cli.py` | Add documented smoke command |
| P2.15 | Evaluation | Difficulty, query-structure, error breakdowns and report files | Done | 100% | Lead agent | `evaluation/reports.py`; JSON, CSV, and Markdown fixture outputs; 14 tests pass | Run on real benchmark predictions |
| P2.16 | Reproducibility | Typed dataset configuration and smoke runner | Done | 100% | Lead agent | `config.py`, `data/README.md`, `scripts/run_part2_smoke.py`; explicit missing-path failure and CLI help | Configure real dataset paths |
| P2.17 | Dataset/Evaluation | Official WikiSQL and Spider download and smoke run | Done | 100% | Lead agent | External archives verified; 5 retained/0 excluded per dataset; artifacts written outside Git; Spider execution accuracy 0.4000, WikiSQL 0.0000 | Improve WikiSQL parsing |
| P2.18 | Evaluation | Result-table comparison policy | Done | 100% | Lead agent | Execution comparison now ignores SQL result-column label case; row order remains sensitive; regression test added; 18 tests pass | Reassess ordering policy before full evaluation |
| P2.19 | Review | Part 2 merge and authority alignment review | Done | 100% | Lead agent | PR #5 merged as `048cae6`; current implementation aligned with Part 2 PDF requirements, with report/evidence gaps recorded | Improve baseline and prepare report |
| P2.20 | Baseline | Projection, condition, aggregation, and multi-condition parsing | Done | 100% | Classical baseline agent | 22 tests pass; official 25-example smoke results: WikiSQL 0.0800, Spider 0.0800 execution accuracy | Run larger evaluation and analyze errors |
| P2.21 | Baseline | Identifier-aware projection selection | Done | 100% | Lead agent | Regression test confirms “names of singers” selects `Name`, not `Singer_ID`; 23 tests pass; CLI verified | Run larger evaluation and analyze errors |
| P2.9 | Governance | PR creation made approval-gated | Done | 100% | Lead agent | [`agent-rules.md`](./agent-rules.md) updated; no automatic PR policy | Notify user at major checkpoints |
| P2.1 | Environment | Dependency manifest and smoke-test command | Not started | 0% | Unassigned | Required before data/model work | Inspect available Python environment |
| P2.2 | Data | Dataset configuration and acquisition instructions | Not started | 0% | Unassigned | WikiSQL first, Spider second | Define config and paths |
| P2.3 | Data | WikiSQL loader and validation | Not started | 0% | Unassigned | Part 2 gate | Implement fixtures/tests |
| P2.4 | Data | Schema serialization | Not started | 0% | Unassigned | Tables, columns, types, keys | Implement deterministic serializer |
| P2.5 | Data | Spider loader and smoke split | Not started | 0% | Unassigned | Preserve official split metadata | Implement after WikiSQL |
| P2.6 | Baseline | Classical parser/template baseline | Done | 100% | Lead agent | Deterministic schema-aware template baseline implemented | Evaluate against downloaded benchmark data |
| P2.7 | Evaluation | Exact match, execution accuracy, invalid rate | Not started | 0% | Unassigned | Per-example failures must continue | Build fixture-driven evaluator |
| P2.8 | Analysis | Error categories and breakdown reports | Not started | 0% | Unassigned | Difficulty and query structure required | Generate CSV/Markdown reports |
| P2.9 | Demo | CLI question → SQL → result/error | Done | 100% | Lead agent | CLI integrated with read-only SQLite execution | Add documented smoke command |
| P2.10 | Report | Part 2 report sections and citations | Not started | 0% | Unassigned | Introduction through baseline results | Draft from saved evidence |
| P2.11 | QA | Clean-environment reproduction and PR review | Not started | 0% | Unassigned | Required before Sep 30 freeze | Run final checklist |

## Update protocol

When changing this log:

1. Update `Last updated`, `Overall completion`, and `Next checkpoint`.
2. Change only affected rows; preserve historical notes. Do not update this
   file for every small edit, test, or intermediate command.
3. Set status to one of `Not started`, `In progress`, `Blocked`, `Done`, or
   `Deferred`.
4. Add evidence such as a file, test command, metric artifact, or PR link.
5. Record blockers explicitly instead of lowering the percentage silently.
