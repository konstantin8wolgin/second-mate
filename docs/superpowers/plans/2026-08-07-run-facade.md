# RUN-FACADE-01 Provider-Free Execution Facade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn one validated CONV-BRIDGE Run Intent into a concise final run
preview, one separately confirmed and durable execution authority, exactly one
injected provider-free launch, independent result evidence, and a review-ready
close without exposing activation or recovery machinery to the ordinary user.

**Architecture:** Add a generic `second_mate.run_facade` boundary beside, not
inside, the fixture-only FS-01 Draft/service path. It validates the current
approved Direction, resolves the selected target and Git basis read-only,
derives a direct execution packet and user preview, then records one visible
**Run now** action as distinct route-approval and Execution-Consent receipts.
A private durable facade store owns one launch identity and delegates lifecycle
mechanics through an injected execution-boundary protocol. The first
implementation uses only a deterministic fake boundary over disposable Git
targets; a future live adapter is a separate activation packet.

**Tech Stack:** Python 3.12, frozen dataclasses, strict deterministic JSON,
existing Direction/revision/digest primitives, existing trusted-local lifecycle
types where their contracts fit, argparse, pytest, Ruff, mypy, Hatch/uv.

## Frozen provider-free boundary

- Do not invoke the installed Codex CLI, authenticate, inspect credentials,
  use network, call a provider, or consume/reuse either historical activation.
- Use fresh disposable Git targets and an injected fake execution boundary.
- Preserve `RunIntent`, Direction/FS-01 schemas, `.second-mate/state.json`, and
  the existing trusted-local cleanup rules; do not generalize fixture types.
- Preparation and preflight are read-only. The only pre-launch mutation is
  private coordinator state owned by this facade, outside the target worktree.
- The ordinary flow has one final **Run now** confirmation. Internally it keeps
  route approval and Execution Consent as separate digest-bound receipts.
- Consent is one-shot. Once launch may have been attempted, no retry or
  redispatch is automatic, including after an exception or malformed stream.
- Every facade authority/state transition uses the existing repository-wide
  mutation lock. Durable active or ambiguous facade ownership is visible to
  Direction promotion and FS-01 start; only exact terminal close releases it.
- Any observed preview, Direction, target, route, or execution-boundary drift
  durably invalidates that consent as `stale`. Restoring old bytes never makes
  it executable again; a new preview and **Run now** action are required.
- Trusted-local mode is not containment. The preview must say that the agent
  may access the local machine and that repository evidence cannot prove the
  absence of outside effects.
- Independent evidence comes from coordinator-side Git/revision inspection,
  never provider claims alone.
- RUN-FACADE-01 ends at `review-ready`, `failed`, or `unknown-running`. It may
  offer later commit/merge choices but must not stage, commit, merge, push, or
  deploy.
- Every production behavior starts with a watched failing test. Preserve the
  complete existing suite.

---

### Task 1: Strict Run Intent validation and read-only final preview

**Files:**
- Create: `src/second_mate/run_facade.py`
- Modify: `src/second_mate/__init__.py`
- Create: `tests/test_run_facade.py`

**Public interfaces:**
- `run_intent_from_json(value) -> RunIntent`
- `RunRouteProposal`, `ExecutionBoundary`, `ExecutionBoundarySummary`
- `RunRoute`, `RunPreflight`, `RunPreview`
- `prepare_run_preview(repository, run_intent_data, route_data, boundary) -> RunPreview`

- [ ] **Step 1: Write strict parsing and current-Direction failing tests**

Use the literal `RunIntent.to_json()` returned by a real approved conversation
handoff. Require exact keys/schema, non-empty normalized text, unique lists,
lowercase SHA-256 digests, and a current approved Direction whose ID/digest and
stored proposal digest exactly match the intent. Reject a hand-built intent,
wrong repository label, missing/malformed history, superseded Direction, open
FS-01 state, and unknown transcript/provider/activation fields.

- [ ] **Step 2: Run and observe RED**

Run: `uv run pytest -W error tests/test_run_facade.py -k 'intent or direction' -q`

Expected: import failure because `second_mate.run_facade` does not exist.

- [ ] **Step 3: Implement the minimal strict parser and provenance check**

Parse without changing `conversation.py`. Reuse `find_direction_version`,
`require_direction_promotion_idle`, and deterministic digest helpers. Treat the
repository ID as a human label and the selected worktree plus current Direction
record as the actual target identity; never claim that the label alone proves
physical identity.

- [ ] **Step 4: Write read-only preview failing tests**

Require preparation to:

- leave every target and private-state byte unchanged;
- resolve the unaliased Git worktree root, HEAD, and visible fingerprint with
  `inspect_revision`;
- validate one First Mate-supplied direct-route proposal with a short reason and
  no score;
- bind the exact Run Intent, Direction, target root, HEAD, fingerprint, route,
  qualified execution-boundary name/digest, requested/prohibited effects,
  acceptance, and trusted-local risk into a deterministic `preview_digest`;
- display ordinary task/effect/verification language and `awaiting-run-confirmation`;
- state that execution is not authorized and no preflight claim survives target
  drift; and
- omit executable path/hash, credential/session data, activation ID, marker
  path, private root, owner token, and raw conversation content.

- [ ] **Step 5: Implement `RunRoute`, `RunPreflight`, and `RunPreview`**

Accept only a strict route proposal whose repository and Direction bindings
match the Run Intent and whose decision is literal `direct`; refuse a task that
cannot honestly use that route rather than inventing Foundation/Map readiness.
Call the injected boundary's read-only `qualify` operation before returning the
preview. The first concrete boundary is fake and provider-free. Record the
worktree scope as the selected repository, while stating that trusted-local
execution is not technically contained to it. Include verification requirements
for current Git basis, changed paths, acceptance checks, and residual uncertainty.

- [ ] **Step 6: Replay Task 1 GREEN and regression slices**

Run:

```bash
uv run pytest -W error tests/test_run_facade.py tests/test_conversation.py \
  tests/test_direction.py tests/test_repository.py -q
uv run ruff check src/second_mate/run_facade.py tests/test_run_facade.py
uv run ruff format --check src/second_mate/run_facade.py tests/test_run_facade.py
uv run mypy src
```

- [ ] **Step 7: Commit Task 1**

```bash
git add src/second_mate/run_facade.py src/second_mate/__init__.py \
  tests/test_run_facade.py
git commit -m "feat(second-mate): prepare generic run previews"
```

### Task 2: One final confirmation, two authorities, and private durable ownership

**Files:**
- Modify: `src/second_mate/run_facade.py`
- Modify: `src/second_mate/__init__.py`
- Modify: `src/second_mate/repository.py`
- Modify: `src/second_mate/direction.py`
- Modify: `src/second_mate/service.py`
- Modify: `tests/test_run_facade.py`

**Public interfaces:**
- `RunConfirmationAction`, `RunAuthority`, `RunAuthorityReceipt`
- `FacadeRunState`, `FacadeStateStore`
- `authorize_run(repository, preview, action) -> FacadeRunState`
- `facade_run_status(repository, run_id) -> FacadeRunStatus`

- [ ] **Step 1: Write authority separation failing tests**

One exact action has schema 1, a stable ID/actor/time, decision `run`, exact
preview digest, and fixed ordered scopes `direct_route` and
`one_shot_execution`. Assert one user action returns two distinct receipts:

1. route approval bound to the exact direct-route record; and
2. Execution Consent bound to the exact preview, Direction, target basis,
   requested/prohibited effects, and trusted-local risk acknowledgment.

Neither receipt authorizes commit, merge, push, deploy, retry, or a different
target/provider boundary.

- [ ] **Step 2: Write durable ownership and crash-window failing tests**

Derive the state root internally with
`git_private_path(repository, "second-mate-run-facade")`; the caller and user do
not supply it. Require a mode-`0700`, schema-validated, identity-bound private
state file to be durably installed before any launch. Assert exact authorization
retry returns byte-identical status without rewriting; changed
action/preview/basis refuses; duplicate/concurrent authority has one winner;
symlink, replacement, permissive root, malformed state, partial write, and
unknown file fail closed. Holding `mutation_lock` must block authorization even
though its durable bytes live outside the worktree.

- [ ] **Step 3: Implement the smallest private store**

Store only task/authority/basis digests, state identity, phase, one launch
attempt flag, execution-boundary name/digest, lifecycle classification, and
evidence references. Do not store prompt, transcript, credentials, raw
conversation, or private reasoning. Create the fixed Git-private directory with
mode `0700`, use atomic exclusive file creation plus parent-directory durability,
and revalidate identity on every update. Phases are:

`authorized`, `stale`, `launching`, `running`, `completed`, `failed`,
`unknown-running`, `review-ready`, and `closed`.

Any state at or after `launching` has consumed the one-shot attempt.
`stale` is terminal for the consent and cannot transition back to `authorized`.

- [ ] **Step 4: Implement common repository ownership visibility**

Add one shared, strict repository-activity inspection seam. Under
`mutation_lock`, it must validate both existing FS-01 state and the fixed
Git-private facade state. Direction promotion, FS-01 start/restart, facade
authorization, facade launch, and every facade transition call it with the
identity they are allowed to own. Active, failed-unclosed, `unknown-running`,
or review-pending facade state blocks Direction/FS-01 mutation; an open FS-01
run blocks facade launch. Malformed/replaced activity state fails closed.

- [ ] **Step 5: Replay Task 2 GREEN**

Run: `uv run pytest -W error tests/test_run_facade.py -k 'authority or state or concurrent or partial or ownership' -q`

- [ ] **Step 6: Commit Task 2**

```bash
git add src/second_mate/run_facade.py src/second_mate/__init__.py \
  src/second_mate/repository.py src/second_mate/direction.py \
  src/second_mate/service.py tests/test_run_facade.py
git commit -m "feat(second-mate): bind one-shot run authority"
```

### Task 3: Injected launch, ambiguity, cancellation, and independent evidence

**Files:**
- Modify: `src/second_mate/run_facade.py`
- Modify: `src/second_mate/__init__.py`
- Create: `tests/fakes/run_boundary.py`
- Modify: `tests/test_run_facade.py`
- Create: `tests/test_e2e_run_facade.py`

**Interfaces:**
- Extend `ExecutionBoundary` with `launch`, `finish`, `load`, `cancel`, and
  `cleanup` operations
- `execute_authorized_run(repository, run_id, boundary) -> FacadeRunState`
- `cancel_facade_run(...)`, `recover_facade_run(...)`, `review_facade_run(...)`

- [ ] **Step 1: Write exactly-once dispatch failing tests**

Use a fake boundary that records calls and mutates one named file in a fresh
disposable Git repository. Require its name/digest to match the boundary already
qualified and bound into the preview, recompute target HEAD/fingerprint
immediately before consuming the attempt, set `launching` durably before calling
`launch`, and call `launch` exactly once. Reject qualification/boundary drift,
target drift, missing consent, reused state, or a second caller without invoking
the boundary.

Any observed preview, Direction, target, route, or boundary drift must first
persist `stale` under the shared lock and then refuse. Tests restore the old
bytes/fingerprint and prove the old consent still cannot launch.

- [ ] **Step 2: Write ambiguity and recovery failing tests**

Inject failure before launch, during launch return, malformed lifecycle, stream
interruption, cancellation failure, process disappearance, and state-update
failure. Before launch may remain `authorized`; after the durable `launching`
transition every ambiguous case becomes `unknown-running` and never redispatches.
Recovery may load/cancel the exact owned run, but may not infer completion or
reuse consent. Cleanup is delegated only after a terminal or explicitly
abandoned exact run and remains limited to run-owned private artifacts.

Add cross-lifecycle races proving: open FS-01 blocks facade launch; active or
`unknown-running` facade state blocks Direction promotion and FS-01 start;
competing facade/Direction/FS-01 starts have exactly one winner; and only exact
terminal facade close restores repository mutation eligibility.

- [ ] **Step 3: Implement the injected boundary orchestration**

Adapt the existing `OfflineTrustedLocalAdapter` lifecycle behind the protocol
where it fits; do not weaken or duplicate its identity-bound cleanup. The fake
boundary is the only concrete boundary instantiated by tests. Do not construct
`CodexCliTrustedLocalAdapter` and do not resolve the installed `codex` binary.

- [ ] **Step 4: Write independent evidence and review failing tests**

After fake completion, recompute Git revision and diff from the frozen basis.
Record changed paths, current revision, acceptance observations supplied by
deterministic local probes, and explicit limitations. Contradictory provider
output cannot override target facts. Unexpected target changes, missing
acceptance evidence, or unverifiable outside-effects claims produce `failed` or
`unknown-running`, never `review-ready`.

`review-ready` returns task, requested/prohibited effects, actual changed paths,
acceptance results, residual uncertainty, and separate not-yet-authorized
`commit` and `merge` offers. It performs no Git mutation.

- [ ] **Step 5: Run the complete provider-free facade journey**

Run:

```bash
uv run pytest -W error tests/test_run_facade.py tests/test_e2e_run_facade.py -q
uv run pytest -W error tests/test_trusted_local.py tests/test_trusted_local_codex.py -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
```

- [ ] **Step 6: Commit Task 3**

```bash
git add src/second_mate/run_facade.py src/second_mate/__init__.py \
  tests/fakes/run_boundary.py tests/test_run_facade.py \
  tests/test_e2e_run_facade.py
git commit -m "feat(second-mate): execute one injected run safely"
```

### Task 4: Ordinary library/CLI surface and operator contract

**Files:**
- Modify: `src/second_mate/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_e2e_run_facade.py`
- Create: `docs/second-mate/RUN-FACADE-OPERATOR.md`
- Modify: `docs/second-mate/CONVERSATION-HANDOFF.md`
- Modify: `README.md`
- Modify: `docs/second-mate/README.md`
- Modify: `pyproject.toml`
- Modify: `tests/test_package.py`

- [ ] **Step 1: Write CLI RED tests**

Add provider-free commands. All private-state and execution-boundary resolution
is supplied by the embedding First Mate host, not command-line flags:

```console
second-mate run prepare --target TARGET --intent INTENT \
  --route ROUTE
second-mate run authorize --target TARGET --preview PREVIEW \
  --confirmation CONFIRMATION
second-mate run execute --target TARGET --run-id RUN_ID
second-mate run status --target TARGET --run-id RUN_ID
second-mate run review --target TARGET --run-id RUN_ID
second-mate run cancel --target TARGET --run-id RUN_ID
```

The public production CLI must not accept an executable path, provider token,
activation marker, session ID, arbitrary cleanup path, `--retry`, `--commit`,
`--merge`, `--push`, `--state-root`, or `--boundary`. Refactor `main` to accept
an optional embedding host that supplies qualification and lifecycle boundaries.
Provider-free CLI tests inject the fake host; ordinary production invocation
without a configured host refuses prepare/execute/cancel as unavailable and
never falls back to installed Codex. This prevents the provider-free packet from
quietly creating a live dispatch route.

- [ ] **Step 2: Implement stable transport adapters**

Keep ordinary output limited to task/effects, target/revision summary, named
execution mode, risk, verification, state, and next meaningful action. The
route document and low-level receipts remain First Mate machine transport, not
user steps. Private paths and boundary internals never appear in CLI arguments
or ordinary output. Errors are concise and non-retrying.

- [ ] **Step 3: Add the operator contract and package test**

Document discuss → Approve → preview → **Run now** → execute → verify → review.
State exactly which steps are automatic, why trusted-local is not containment,
how `unknown-running` stops duplicate dispatch, and why commit/merge remain
separate choices. Require the guide in the source-distribution manifest and
prove its presence after `uv build`.

- [ ] **Step 4: Replay literal CLI/provider-free E2E GREEN**

Run:

```bash
uv run pytest -W error tests/test_cli.py tests/test_e2e_run_facade.py \
  tests/test_package.py -q
uv build
```

- [ ] **Step 5: Commit Task 4**

```bash
git add src/second_mate/cli.py tests/test_cli.py \
  tests/test_e2e_run_facade.py docs/second-mate/RUN-FACADE-OPERATOR.md \
  docs/second-mate/CONVERSATION-HANDOFF.md README.md \
  docs/second-mate/README.md pyproject.toml tests/test_package.py
git commit -m "feat(second-mate): expose the provider-free run facade"
```

### Task 5: Canonical reconciliation, independent review, and close

**Files:**
- Modify: `docs/second-mate/PROGRAM.md`
- Modify: `docs/second-mate/implementation-checklist.md`
- Modify: `docs/second-mate/workflow-spec.md` only if implementation evidence
  contradicts or sharpens its current contract

- [ ] **Step 1: Reconcile claims from executable evidence only**

Mark RUN-FACADE-01 provider-free complete only if the literal fake journey,
negative dispatch tests, durable ownership/recovery tests, package gates, and
independent review pass. Keep terminal live adapter behavior, provider security,
outside-machine effects, human usability, commit/merge execution, pilot value,
and MS-02 open.

- [ ] **Step 2: Request independent specification and safety review**

Review the complete diff from the pre-facade base for authority collapse,
duplicate dispatch, stale basis, fake-to-live leakage, private-state
replacement, false evidence, broad cleanup, privacy retention, misleading CLI,
FS-01 regression, and documentation overclaim. Fix every Critical/Important
finding test-first and request focused re-review.

- [ ] **Step 3: Run fresh completion gates**

```bash
uv sync --offline --locked
uv run pytest -W error
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv build
git diff --check PRE_FACADE_BASE..HEAD
```

Inspect both archives, install the wheel in a fresh temporary environment, and
smoke import, `py.typed`, CLI help, prepare/status, and one disposable fake
journey. Independently confirm no provider process, credential access, consumed
marker change, installed Codex invocation, `firstmate/` change, push, or PR.

- [ ] **Step 4: Commit the truthful close**

```bash
git add docs/second-mate/PROGRAM.md \
  docs/second-mate/implementation-checklist.md \
  docs/second-mate/workflow-spec.md
git commit -m "docs(second-mate): close provider-free run facade"
```

## Stop and next meaningful gate

After this plan is implemented and independently verified, stop before any real
boundary is selected or invoked. The next user-facing meaningful gate is one
fresh final **Run now** confirmation bound to a current target, provider/account
boundary, executable qualification, risk preview, and one-shot activation. A
real run must never reuse CAP-02B/C, infer credentials, or convert the fake
journey into live authority. MS-02 remains a human product judgment after the
facade is observable.
