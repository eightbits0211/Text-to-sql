# Agent Rules for the NLP Project

These rules apply to every coding agent, delegated agent, automation, and
assistant session working in this repository.

## 1. Branch and pull-request safety

1. Never commit directly to `main`, `master`, or the repository's default branch.
2. Always create or use a dedicated specification/feature branch before making
   tracked repository changes. Use a descriptive name such as:
   `spec/part2-baseline-plan` or `feature/part2-data-pipeline`.
3. Never force-push, rewrite shared history, amend someone else's commit, or
   reset/discard unrelated work.
4. Every completed change must be submitted through a pull request targeting the
   default branch.
5. The agent must not merge its own pull request unless the user explicitly
   requests that action and repository policy permits it.
6. Before opening a PR, inspect the diff, run the smallest relevant validation,
   and summarize known limitations.
7. Keep commits focused and descriptive. Include the required Copilot
   co-author trailer when creating commits, unless the user explicitly opts out.
8. If the workspace is not a Git repository or remote/branch creation is
   unavailable, do not pretend that a branch or PR exists. Report the blocker
   and preserve changes without committing.
9. Intended repository remote: `https://github.com/eightbits0211/Text-to-sql.git`.
   Verify the configured remote before using it; do not assume authentication or
   push permission.

## 2. Scope and authority

1. Treat the two attached course PDFs and the approved PRD as the authoritative
   project requirements.
2. Do not silently expand the Part 2 scope into Part 3 novelty work.
3. Treat BIRD, production deployment, conversational memory, and arbitrary
   database engines as optional or out of scope unless the user explicitly
   re-scopes the project.
4. Preserve the internal Part 2 implementation freeze of September 30, 2026
   and the official submission deadline of October 15, 2026.
5. If two requirements conflict, stop and ask the user rather than choosing a
   high-impact interpretation silently.
6. When requirements, scope, behavior, implementation approach, or repository
   state is ambiguous, ask the user before acting. Do not fill in a
   high-impact assumption silently.

## 3. Engineering standards

1. Inspect existing code and documentation before editing.
2. Prefer existing helpers, types, conventions, and dependency manifests.
3. Make precise, minimal, complete changes; if only one line or a few lines
   need changing, edit only those lines and do not rewrite the entire file.
4. Preserve type safety and validate external data at boundaries.
5. Do not use broad exception handling or silent fallbacks.
6. Dataset, model, and execution errors must be surfaced explicitly and logged
   with enough context to reproduce the failure.
7. Never report an empty result as a successful SQL execution.
8. Keep model interfaces stable so classical, modern, and improved systems can
   use the same evaluator and demo.
9. Use deterministic seeds and record configuration for experiments.
10. Do not commit datasets, credentials, API keys, private user data, large
    checkpoints, generated caches, or machine-specific secrets.
11. Do not hardcode credentials, machine-specific paths, dataset locations,
    model identifiers, ports, dates, or environment-specific settings when the
    value should be configurable. Use configuration, environment variables, or
    documented command-line arguments with validated defaults.
12. Update the persistent project state file at the end of every work session
    with what was completed, current roadblocks, and next immediate steps.
    Update the project progress log only for major checkpoints, milestone
    completion, blockers, scope changes, or important handoffs; do not add a
    row for every small edit or test.
13. Keep autonomous fix/debug loops bounded: after 3 consecutive failed attempts
    at the same issue, stop, preserve the failure trace, and ask the user for
    direction instead of trying a fourth autonomous fix.
14. Before every session ends, provide a context-history summary covering
    completed work, decisions, current blockers, active branch/PR, validation
    performed, and next immediate steps. Update `state.md` first so the summary
    remains recoverable.

## 4. NLP/Text-to-SQL rules

1. Every retained example must have a non-empty question, schema, and gold SQL.
2. Schema serialization must include tables, columns, types, primary keys, and
   foreign-key relationships.
3. Evaluation must use fixed, documented splits and identical procedures across
   models.
4. Exact-match, execution accuracy, and invalid-SQL rate must remain separate
   metrics with documented limitations.
5. One malformed prediction must not terminate an evaluation run.
6. Empty or unsupported predictions count as invalid and must be visible in
   artifacts.
7. Predicted SQL must be validated before execution.
8. Never execute generated SQL against an unintended database.
9. Do not claim generalization from a smoke slice as full Spider performance.
10. Preserve gold SQL and raw input examples for qualitative error analysis.

## 5. Testing and validation

1. After editing, run targeted tests for the changed behavior.
2. Before opening a PR, run the relevant smoke command from a clean or
   documented environment.
3. For data changes, test valid records, missing fields, missing databases, and
   deterministic split/statistics behavior.
4. For evaluator changes, test exact matches, semantically equivalent queries
   where supported, invalid SQL, empty SQL, and execution errors.
5. For demo changes, test a successful query, an unsupported question, an
   invalid query, and a missing database path.
6. Do not weaken or delete tests merely to make a build pass.
7. Record commands and results in the PR description when the validation is not
   obvious from CI.

## 6. Agent workflow

1. Read the relevant PRD/plan section before starting.
2. Break work into a bounded task with a clear acceptance check.
3. Check repository status before editing and preserve unrelated changes.
4. Implement one coherent slice.
5. Validate it immediately.
6. Update documentation when behavior, commands, metrics, or scope changes.
7. Review the diff for accidental files, secrets, generated data, and unrelated
   edits.
8. Commit only on the dedicated branch.
9. Open/update the PR with summary, tests, artifacts, and known limitations.
10. Stop and ask the user when a design choice materially changes scope,
    evaluation validity, deadlines, or external resource usage.
11. At the autonomous-loop limit, report the attempted approaches, commands or
    tests, relevant error output, and the exact decision needed from the user.

## 7. Delegation rules

1. Delegated agents must receive a bounded objective and explicit acceptance
   criteria.
2. Delegated agents must follow these same branch, secret, testing, and PR rules.
3. Do not duplicate work across agents without a stated reason.
4. Review delegated changes before integration.
5. Agents must not launch unrelated background work or modify files outside
   their assigned scope.

## 8. Data, credentials, and external services

1. Never expose credentials, tokens, private datasets, or sensitive logs.
2. Do not send repository contents to third-party services unless the user
   explicitly authorizes the specific service and data.
3. Prefer local or approved public sources for dataset acquisition.
4. Document licenses and citations for downloaded datasets and models.
5. Do not add a dependency or call an external API without documenting why it is
   needed and how it affects reproducibility.

## 9. Communication rules

1. Report what changed, what was tested, and what remains unresolved.
2. Use absolute Markdown links to repository files when referring to them.
3. Distinguish facts, measurements, assumptions, and recommendations.
4. Never claim that tests, commits, branches, or pull requests exist unless
   they were actually verified.
5. Raise deadline or scope risks early, especially risks to the Sep 30 freeze.
