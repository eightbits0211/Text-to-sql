# Sub-Agent Coordination Plan

## 1. Objective

Use small, bounded agents to accelerate independent work without duplicating
effort or creating conflicting implementations. The lead agent owns scope,
integration, progress tracking, and final PR readiness.

## 2. Roles

### Lead/integration agent

- Owns the PRD, plans, architecture, and final scope.
- Maintains [project-progress-log.md](./project-progress-log.md).
- Assigns bounded tasks with acceptance criteria.
- Resolves interface conflicts and asks the user about ambiguity.
- Reviews all agent output before integration.
- Owns the final branch/PR workflow.

### Data pipeline agent

Owns dataset record contracts, loaders, validation, schema serialization, split
statistics, and data fixtures. Must not implement model training or rewrite the
evaluation harness.

### Classical baseline agent

Owns the selected template/grammar or LSTM baseline behind the shared model
interface. Must use the data contracts and must not change dataset formats.

### Evaluation agent

Owns SQL normalization, safe SQLite execution, exact-match, execution accuracy,
invalid-SQL rate, breakdowns, and evaluator tests. Must not change model logic.

### Demo/report agent

Owns CLI/demo integration, report evidence templates, reproducibility commands,
and presentation examples. Must not invent metrics or alter experiment outputs.

### Modern/novelty agent

Starts only after the Part 2 freeze. Owns transformer and novelty experiments
behind the existing model/generation interfaces.

## 3. Task handoff format

Every delegated task must include:

```text
Task:
Scope:
In scope:
Out of scope:
Inputs/dependencies:
Files allowed to change:
Acceptance checks:
Expected evidence:
Blocker/escalation rule:
```

An agent must return:

```text
Summary:
Files changed:
Tests/commands run:
Artifacts produced:
Known limitations:
Questions/blockers:
Suggested next checkpoint:
```

## 4. Dependency order

```text
Configuration and fixtures
          ↓
Data contracts and loaders
          ↓
Schema serialization
          ↓
Classical model ───────┐
                       ├──→ Evaluation harness ──→ Error analysis
                       └──→ CLI/demo
                                      ↓
                         Part 2 freeze and review
                                      ↓
                         Modern model → Novelty
```

Agents may work in parallel only when they do not edit the same interface or
files. For example, evaluation fixture design can proceed while data parsing is
being implemented if both agree on the record contract first.

## 5. Communication protocol

- Use one task/branch per bounded implementation unit.
- State the exact files changed in every handoff.
- Do not communicate progress only through chat; update the progress log when a
  checkpoint changes status.
- Use shared, versioned fixtures rather than undocumented local assumptions.
- If a dependency or interface is missing, mark the task blocked and notify the
  lead agent rather than creating a private incompatible workaround.
- Ask the user when ambiguity affects scope, correctness, evaluation validity,
  external services, or deadlines.

## 6. Branch and PR protocol

- Each agent works on a dedicated branch such as
  `feature/data-wikisql-loader` or `feature/evaluation-harness`.
- No agent commits directly to the default branch.
- No agent merges its own PR.
- The lead agent reviews diffs, tests, artifacts, and scope before integration.
- Agents must not force-push or discard unrelated changes.
- Large datasets, checkpoints, credentials, and generated caches stay out of
  commits.

## 7. Conflict prevention

Before editing a shared contract, an agent must:

1. Read the architecture document.
2. Check the current progress log.
3. Identify the owning agent.
4. Propose the contract change to the lead agent.
5. Wait for approval if the change affects another workstream.

The lead agent should resolve conflicts by preserving the smallest stable
interface rather than merging incompatible assumptions.

## 8. Parallelization matrix

| Work item | Can run in parallel with | Must wait for |
|---|---|---|
| Fixtures/config | Evaluation fixture design | None |
| WikiSQL loader | CLI skeleton | Record contract |
| Spider loader | Baseline parser design | Record contract |
| Evaluation tests | Loader implementation | Prediction/result contracts |
| Baseline implementation | Evaluation implementation | Model interface |
| CLI integration | Error analysis templates | Prediction interface |
| Modern model | Final Part 2 report polish | Part 2 freeze and stable evaluator |
| Novelty | Final report expansion | Modern baseline metrics |

## 9. Escalation rules

Escalate immediately when:

- A task requires changing an authoritative requirement.
- A task needs credentials or an unapproved external service.
- A task threatens the September 30 Part 2 freeze.
- A metric definition would change previously reported results.
- A data issue changes split membership or benchmark validity.
- Two agents produce incompatible interfaces.
- The agent cannot verify a claimed test, branch, commit, or PR.

