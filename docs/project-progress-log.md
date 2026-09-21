# Text-to-SQL Project Progress Log

This is the authoritative high-level progress table. Every agent session must
update it after completing a checkpoint, discovering a blocker, or changing
scope. Percentages are estimates of completed **project checkpoints**, not
claims about final model accuracy.

## Current status

| Field | Value |
|---|---|
| Last updated | 2026-09-21 |
| Overall completion | 22% |
| Current phase | Planning and repository setup |
| Part 2 internal freeze | 2026-09-30 |
| Official Part 2 deadline | 2026-10-15, 23:55 IST |
| Active branch | `spec/agent-governance-rules` |
| Current blocker | GitHub push rejected with HTTP 403 for authenticated account `jithu004` |
| Next checkpoint | Resolve remote permissions, then push and open PR |

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
| P2.2 | Repository | Initial project baseline committed locally | In progress | 90% | Lead agent | Commit `72fbc48`; push blocked by GitHub permission error; source attachments excluded | Fix authentication/permission and push |
| P2.1 | Environment | Dependency manifest and smoke-test command | Not started | 0% | Unassigned | Required before data/model work | Inspect available Python environment |
| P2.2 | Data | Dataset configuration and acquisition instructions | Not started | 0% | Unassigned | WikiSQL first, Spider second | Define config and paths |
| P2.3 | Data | WikiSQL loader and validation | Not started | 0% | Unassigned | Part 2 gate | Implement fixtures/tests |
| P2.4 | Data | Schema serialization | Not started | 0% | Unassigned | Tables, columns, types, keys | Implement deterministic serializer |
| P2.5 | Data | Spider loader and smoke split | Not started | 0% | Unassigned | Preserve official split metadata | Implement after WikiSQL |
| P2.6 | Baseline | Classical parser/template baseline | Not started | 0% | Unassigned | Must return one candidate per input | Select and implement baseline |
| P2.7 | Evaluation | Exact match, execution accuracy, invalid rate | Not started | 0% | Unassigned | Per-example failures must continue | Build fixture-driven evaluator |
| P2.8 | Analysis | Error categories and breakdown reports | Not started | 0% | Unassigned | Difficulty and query structure required | Generate CSV/Markdown reports |
| P2.9 | Demo | CLI question → SQL → result/error | Not started | 0% | Unassigned | Must run from one documented command | Integrate stable baseline |
| P2.10 | Report | Part 2 report sections and citations | Not started | 0% | Unassigned | Introduction through baseline results | Draft from saved evidence |
| P2.11 | QA | Clean-environment reproduction and PR review | Not started | 0% | Unassigned | Required before Sep 30 freeze | Run final checklist |

## Update protocol

When changing this log:

1. Update `Last updated`, `Overall completion`, and `Next checkpoint`.
2. Change only affected rows; preserve historical notes.
3. Set status to one of `Not started`, `In progress`, `Blocked`, `Done`, or
   `Deferred`.
4. Add evidence such as a file, test command, metric artifact, or PR link.
5. Record blockers explicitly instead of lowering the percentage silently.
