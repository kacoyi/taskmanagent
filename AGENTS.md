# Taskmanagent architecture entry point

Follow `/home/loong/ai-workspace/AGENTS.md` for shared capability policy.

This repository is in architecture design. Product implementation has not
started. The current task authorizes design and contract maintenance, not
automatic execution against managed repositories or paid AI services.

## Read only the context needed for the change

1. Read `contracts/engineering.v0.json` for product intent, scope and open inputs.
2. Select the affected entries in `contracts/architecture.v1.json` for module
   ownership and dependencies; load storage/AI/transport sections only if relevant.
3. Select the relevant route in `contracts/evolution.v1.json`; read the affected
   module contracts, immediate consumers and acceptance fixtures when they exist.
4. Consult relevant entries in `contracts/decisions.v1.json` before reversing a
   structural decision. Record the reason and migration path when changing it.

The JSON contracts are normative design specifications, not evidence that the
code, tests, schemas or enforcement tools already exist. Planned source paths
are navigation targets; do not create empty scaffolding to fill the map.
Routine changes do not require loading every contract in full. Use structured
JSON selection to read the relevant route, owner, decision and scenarios.

## Maintain boundaries

- Domain modules own their data and expose small typed contracts. No imports
  of another module's internals, direct writes to its tables, or domain imports
  of UI/provider/storage frameworks.
- The desktop is a replaceable client of application use cases. AI is a
  replaceable inference dependency. Neither owns product truth.
- Preserve user intent, decisions and verification evidence independently of
  rebuildable indexes and projections. Do not silently rewrite history.
- Keep changes local to the declared route. A justified boundary change is
  allowed: update the decision, ownership and compatibility rules together.
- Optimize frequent changes and bounded experiments as specified in
  `contracts/architecture.v1.json#/change_cost_policy`; add flexibility only
  when its expected savings justify its maintenance cost.
- Never equate graph grouping with a source-code refactor, AI consensus with
  evidence, a test pass with deployment, or deployment with runtime health.

## Verify and report honestly

For contract or design-tooling changes, run `python3 tools/check_contracts.py`
and `python3 -m unittest discover -s tests -v` (Python 3.9+; standard library).
These check design consistency and fixture integrity, not product behavior.
Bootstrap executable source dependency and boundary-schema checks before the
first product slice. Use behavior fixtures, migration/restore scenarios and
affected contract tests; do not invent coverage or performance claims.

Record architectural changes in these contracts in the same change as code;
private implementation changes need not rewrite unchanged contracts.
Do not duplicate architecture prose in large READMEs or create a generic
framework, event bus, plugin platform or shared utility bucket speculatively.
Explicit later user instructions take precedence over these design choices.
