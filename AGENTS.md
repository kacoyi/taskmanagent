# Taskmanagent architecture entry point

Follow applicable parent workspace instructions when present. A standalone
clone does not require the maintainer's private workspace or tooling.

This repository is in architecture design. Product implementation has not
started. Design/tooling maintenance and publication of this repository are
authorized; managed-repository execution and paid AI calls require their own
established scope.

## Development workflow

Read `CONTRIBUTING.md` for the human and AI development workflow. It defines
when to commit, branch, experiment, research, ask for inputs, merge and release.
Use short-lived task branches and PRs after bootstrap. Complete authorized
routine work autonomously when its checks and merge conditions pass; do not
invent extra approvals or treat a design-only request as product authorization.
Preserve unrelated work. Report actual evidence, remaining limits and the
resulting commit/PR. Never bypass repository protections to finish a task.

For this maintainer's workspace, GitHub uses the official `gh` CLI over HTTPS.
Before authenticated work, inspect the remote and local `github.account`;
select that account with `gh auth switch` and verify the active login. If no
account is pinned, obtain the owner's choice rather than guessing. Keep Git
identity local to this clone and use a matching verified or noreply email.
Never read credential files or print tokens. Contributors use their own forks
and identities; no account name or credentials belong in shared Git config.

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
