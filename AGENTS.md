# TraceAI - Agent Constitution

## Product
TraceAI is an inline ingestion gateway that fingerprints text and image
assets against a known-copyright index and issues signed Clearance
Certificates. It is evidence infrastructure, not a legal decision-maker.

## Law (read before any work)
1. agents/rules/01-code-style.md - formatting, naming, typing
2. agents/rules/02-testing.md - test-first, coverage gates
3. agents/rules/03-thresholds.md - 0.85 text / 0.90 image are config
4. agents/rules/04-safety.md - secrets, scope, data handling

## Task flow
- Work ONLY from agents/taskcards/*.json. One card per session.
- Implementer: branch per card (card/<id>-slug), commit "T<id>: <what>".
- Run: ruff check . && ruff format --check . && pytest -q
- Never merge without the Verifier approval recorded in the card JSON.

## Hard refusals
- Never invent, weaken, or bypass acceptance criteria.
- Never change scan thresholds, schemas, or crypto code without an
  explicit human-approved card that names the change.
- Never place credentials in code, logs, or chat. Reference env vars only.
- Never mark an asset PASSED on degraded infrastructure (Ch. 3 rules).

## Memory
Record durable engineering decisions in the Memory MCP under
decisions/<topic>. Read it before planning; write to it after merging.
