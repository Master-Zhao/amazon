# Repository Agent Rules

This repository is a synthetic-data proof of concept (PoC). It has no production adapter and must never call the real Amazon Ads API.

## Document precedence

1. `docs/implementation/poc-01-keyword-bid-agent.md`
2. `docs/spec/amazon-ads-agent-loop-engineering-spec-v0.2.1.md` (current PoC patch baseline)
3. `docs/spec/amazon-ads-agent-loop-engineering-spec-v0.2.md` (immutable original baseline)
4. JSON Schema files under `schemas/`
5. Versioned YAML configuration under `config/`
6. Automated tests
7. Code implementation

The current implementation task may narrow scope but must not violate the main specification. If a Schema conflicts with the main specification, record the issue in `docs/implementation/poc-01-issues.md`; do not guess silently. Tests must not weaken the main safety constraints.

## Required reading before development

Read both files before any coding task:

- `docs/spec/amazon-ads-agent-loop-engineering-spec-v0.2.md`
- `docs/spec/amazon-ads-agent-loop-engineering-spec-v0.2.1.md`
- `docs/implementation/poc-01-keyword-bid-agent.md`

## Mandatory engineering constraints

1. Use `decimal.Decimal` for money, bids, and ratios.
2. Serialize those JSON values as Decimal strings.
3. Never use `float` in business calculations.
4. Validate every input and output with JSON Schema.
5. Reject unknown fields by default.
6. A final suggested value must come from the Candidate Engine candidate set.
7. A Reasoner may only rank or select candidates.
8. A Reasoner must not change the rule version.
9. A Reasoner must not create objects outside task scope.
10. Automatic revisions occur only before human approval.
11. Allow at most three automatic revisions.
12. Stop after the same error occurs twice consecutively.
13. Stop automatic changes immediately after validation succeeds.
14. A valid change ends in `waiting_for_approval`.
15. No-change and insufficient-evidence paths may end in `completed`.
16. Never perform a production write without human approval.
17. `production_write_called` must always be `false` in this PoC.
18. Never call the real Amazon Ads API.
19. Never read or commit real secrets.
20. Never log access tokens, authorization headers, or credentials.
21. Never delete or weaken tests to make a build pass.
22. Never modify the main specification without an explicit task.
23. Record specification issues in `poc-01-issues.md`.
24. Run focused tests after completing each module.
25. Run the complete test suite before completion.
26. `manual_intervention_required` must not enter approval or preflight.
27. Every manual-intervention terminal must create a Schema-valid ManualInterventionPackage.
28. The original run is terminal after entering manual intervention.
29. Future recovery must explicitly create a new run.
30. Never reuse a failed plan or an old approval during recovery.
31. A plan digest mismatch must fail closed before preflight.
32. V0.2.1 is the current PoC patch baseline; the original V0.2 file must remain byte-for-byte unchanged.

## Modification limits

- Do not modify `docs/spec/` unless a task explicitly requires it.
- Do not hard-code production configuration.
- Load every PoC threshold from `config/poc-rules-v0.1.yaml`.
- Clearly mark test-only fault injection.
- A Stub must not present itself as a real model or API.
- Do not add a production adapter to this PoC.

## Completion report

Report created and modified files, commands run, test results, unfinished items, specification conflicts, whether production-write capability exists, and Git status.
