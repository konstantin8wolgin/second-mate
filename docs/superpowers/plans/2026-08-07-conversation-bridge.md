# CONV-BRIDGE-01 Conversation Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a concise First Mate conversation summary and one explicit approval action into an idempotent, human-readable, provider-free `ready-for-preflight` Run Intent.

**Architecture:** Add a focused `second_mate.conversation` boundary beside the fixture-only Draft/preflight path. It strictly normalizes conversation-derived task data, renders all material meaning into the existing immutable Direction candidate, derives the two existing authority records from one explicit approval action, and returns a non-executable handoff draft. Reuse Direction promotion, repository mutation locking, history validation, and recovery unchanged; add only a safe read seam for status/idempotence.

**Tech Stack:** Python 3.12, frozen dataclasses, strict deterministic JSON, existing Git/Direction repository primitives, argparse CLI, pytest, Ruff, mypy, Hatch/uv.

## Global Constraints

- Provider-free only: no provider, agent, network, auth, credential, installed Codex execution, or live target.
- The only target mutation is the existing `.second-mate/directions.json` write.
- Preserve existing Direction, FS-01, trusted-local, one-owner, no-duplicate, ambiguity, evidence, and cleanup behavior.
- One visible approval action must create two distinct stored records; neither grants route approval or Execution Consent.
- Persist canonical task meaning only; reject raw transcript/reasoning/provider/activation fields.
- Do not generalize the existing fixture Draft, preflight, service, or executor path.
- No dispatch, commit/merge facade, push, PR, or system configuration belongs to this implementation.
- Derive expected values in tests from literals; every production behavior begins with a watched failing test.

---

### Task 1: Safe Direction lookup and read-only conversation proposal

**Files:**
- Modify: `src/second_mate/direction.py`
- Create: `src/second_mate/conversation.py`
- Modify: `src/second_mate/__init__.py`
- Create: `tests/test_conversation.py`

**Interfaces:**
- Produces: `DirectionVersionLookup`, `find_direction_version(repository, direction_id=None)`.
- Produces: `ConversationTask`, `ConversationReview`, `ConversationProposal`.
- Produces: `prepare_conversation_handoff(repository, task_data)`.
- Consumes: existing `prepare_direction`, `DirectionCandidateEnvelope`, `digest_json`.

- [ ] **Step 1: Write the safe lookup failing tests**

Add tests that require missing history to return `None`, current history to
return `is_current=True`, an older immutable version to return
`is_current=False`, and malformed/missing-recorded history to keep existing
fail-closed behavior.

```python
def test_find_direction_version_distinguishes_missing_current_and_superseded(
    tmp_path: Path,
) -> None:
    repository = make_repository(tmp_path)
    assert find_direction_version(repository) is None
    d01 = promote_exact(repository, "D-01", "Initial task.")
    current = find_direction_version(repository, "D-01")
    assert current is not None
    assert current.version == d01
    assert current.is_current is True
    d02 = promote_exact(repository, "D-02", "Changed task.", change_note="Change task.")
    old = find_direction_version(repository, "D-01")
    assert old is not None and old.is_current is False
    assert find_direction_version(repository).version == d02
```

- [ ] **Step 2: Run the lookup test and verify RED**

Run: `uv run pytest -W error tests/test_conversation.py::test_find_direction_version_distinguishes_missing_current_and_superseded -q`

Expected: import/attribute failure because `find_direction_version` does not exist.

- [ ] **Step 3: Implement the minimal read seam**

Add:

```python
@dataclass(frozen=True, slots=True)
class DirectionVersionLookup:
    version: ApprovedDirectionVersion
    is_current: bool


def find_direction_version(
    repository: Path,
    direction_id: str | None = None,
) -> DirectionVersionLookup | None:
    root = repository.resolve()
    store = _DirectionLedgerStore(root)
    store.reject_missing_recorded_history()
    if not store.exists():
        return None
    ledger = store.load()
    if direction_id is None:
        return DirectionVersionLookup(version=ledger.current, is_current=True)
    wanted = _direction_id(direction_id)
    for version in ledger.versions:
        if version.direction.id == wanted:
            return DirectionVersionLookup(
                version=version,
                is_current=version is ledger.current,
            )
    return None
```

- [ ] **Step 4: Run the lookup tests and verify GREEN**

Run: `uv run pytest -W error tests/test_direction.py tests/test_conversation.py -q`

Expected: lookup tests pass and all existing Direction tests remain green.

- [ ] **Step 5: Write the preparation failing tests**

Use a literal task document with all exact fields. Assert that preparation:

- leaves the full target snapshot unchanged;
- normalizes CRLF/surrounding whitespace;
- emits `awaiting-approval` and ordinary review fields;
- derives `D-CB-` plus 20 lowercase hex characters;
- labels effects as requested rather than authorized;
- includes no execution authority; and
- rejects a document containing `transcript` or `private_reasoning`.

```python
def test_prepare_conversation_handoff_is_read_only_and_reviewable(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    before = target_snapshot(repository)
    proposal = prepare_conversation_handoff(repository, conversation_task())
    assert target_snapshot(repository) == before
    assert proposal.status == "awaiting-approval"
    assert proposal.review.task == "Implement the approved bridge."
    assert proposal.review.execution_authorized is False
    assert proposal.direction_candidate.candidate.id.startswith("D-CB-")
    assert "Proposed effects (not execution authority)" in (
        proposal.direction_candidate.candidate.text
    )
```

- [ ] **Step 6: Run preparation tests and verify RED**

Run: `uv run pytest -W error tests/test_conversation.py -k 'prepare or transcript' -q`

Expected: import/attribute failure because the conversation module is absent.

- [ ] **Step 7: Implement strict task parsing, rendering, review, and proposal**

Create these frozen types and public function:

```python
@dataclass(frozen=True, slots=True)
class ConversationTask:
    handoff_id: str
    source_conversation_id: str
    repository_id: str
    task: str
    assumptions: tuple[str, ...]
    allowed_effects: tuple[str, ...]
    prohibited_effects: tuple[str, ...]
    acceptance: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConversationReview:
    task: str
    assumptions: tuple[str, ...]
    proposed_effects: tuple[str, ...]
    prohibited_effects: tuple[str, ...]
    acceptance: tuple[str, ...]
    execution_authorized: bool = False


@dataclass(frozen=True, slots=True)
class ConversationProposal:
    task: ConversationTask
    direction_candidate: DirectionCandidateEnvelope
    review: ConversationReview
    proposal_digest: str
    status: str = "awaiting-approval"
    summary: str = "Review this task. No run has started."
    next_action: str = "Approve the task meaning and one Direction-ledger write."


def prepare_conversation_handoff(
    repository: Path,
    task_data: object,
) -> ConversationProposal: ...
```

Use exact-key parsing. Normalize `\r\n`/`\r` to `\n`, strip surrounding
whitespace, reject NUL/empty/duplicate values, require non-empty task/effects/
acceptance, and permit empty assumption/prohibition lists. Derive the Direction
ID from `digest_json({"handoff_id": ..., "repository_id": ...})[:20]`.

Render deterministic Direction text with fixed headings for Outcome,
Assumptions, Proposed effects (not execution authority), Prohibited effects,
Acceptance, and Authority boundary. Use the current Direction lookup to select
`change_note=None` for initial history or the fixed change note
`"Adopt the newly approved conversation-derived task."` for a new version.

Compute the proposal digest over the exact task, candidate, and review body.
The proposal parser must rederive the review and digest, so a tampered display
cannot approve different hidden content.

- [ ] **Step 8: Run focused preparation tests and verify GREEN**

Run: `uv run pytest -W error tests/test_conversation.py -k 'prepare or transcript or normalize' -q`

Expected: all focused tests pass with no warnings.

- [ ] **Step 9: Commit Task 1**

```bash
git add src/second_mate/direction.py src/second_mate/conversation.py \
  src/second_mate/__init__.py tests/test_conversation.py
git commit -m "feat(second-mate): prepare conversation handoffs"
```

### Task 2: One-click approval, two durable records, idempotence, and status

**Files:**
- Modify: `src/second_mate/conversation.py`
- Modify: `src/second_mate/__init__.py`
- Modify: `tests/test_conversation.py`

**Interfaces:**
- Consumes: Task 1 proposal parser and `find_direction_version`.
- Produces: `ConversationApprovalAction`, `AuthorityReceipt`, `RunIntent`,
  `ConversationHandoffDraft`, `ConversationHandoffStatus`.
- Produces: `approve_conversation_handoff(...)` and
  `conversation_handoff_status(...)`.

- [ ] **Step 1: Write the approval and ready-draft failing test**

Assert that one exact action writes only `.second-mate/directions.json`, returns
two separately named receipts, stores those two exact records in the immutable
version, emits a non-executable Run Intent, and reports ready-for-preflight.

```python
def test_one_approval_stores_two_records_and_returns_non_executable_run_intent(
    tmp_path: Path,
) -> None:
    repository = make_repository(tmp_path)
    proposal = prepare_conversation_handoff(repository, conversation_task())
    before = target_snapshot(repository)
    draft = approve_conversation_handoff(
        repository,
        proposal.to_json(),
        approval_action(proposal),
    )
    assert draft.status == "ready-for-preflight"
    assert draft.execution_authorized is False
    assert draft.run_intent.task == "Implement the approved bridge."
    assert draft.authority.direction_approval.status == "recorded"
    assert draft.authority.ledger_write_grant.status == "recorded"
    assert draft.authority.route_approval.status == "not-granted"
    assert draft.authority.execution_consent.status == "not-granted"
    assert changed_paths(before, target_snapshot(repository)) == {".second-mate/directions.json"}
```

- [ ] **Step 2: Run the approval test and verify RED**

Run: `uv run pytest -W error tests/test_conversation.py::test_one_approval_stores_two_records_and_returns_non_executable_run_intent -q`

Expected: missing approval/draft interfaces.

- [ ] **Step 3: Implement the approval action and deterministic records**

Parse the exact action schema from the design. Require literal schema integer 1,
decision `approved`, exact proposal/candidate digests, and exactly:

```python
_APPROVED_SCOPES = ("direction_meaning", "direction_ledger_write")
```

Derive Direction approval ID `<action-id>.direction` and promotion-grant ID
`<action-id>.ledger`. Copy actor/time into both. Build the fixed promotion
boundary from the candidate basis and call `promote_direction`.

Return the deterministic draft with authority receipts and Run Intent. Do not
include source conversation ID in the Run Intent or durable Direction ledger.

- [ ] **Step 4: Run the approval test and verify GREEN**

Run: `uv run pytest -W error tests/test_conversation.py::test_one_approval_stores_two_records_and_returns_non_executable_run_intent -q`

Expected: pass.

- [ ] **Step 5: Write idempotence and conflict failing tests**

Add separate tests for:

- exact repeated approval returns identical deterministic JSON and unchanged
  ledger bytes/metadata;
- same Direction ID/different proposal refuses without mutation;
- changed action ID/actor/time after success refuses;
- missing/additional/reordered approval scope refuses;
- proposal/candidate digest mismatch refuses;
- stale prepared basis refuses;
- current matching version later superseded returns `superseded` and cannot be
  reapproved;
- lock contention/open run/concurrent different imports leave one winner; and
- exact interrupted Direction promotion recovery still completes only the
  intended record.

Before each test body, name the production mutation it catches. Use real temp
repositories and existing atomic-writer hooks; do not mock Direction behavior.

- [ ] **Step 6: Run the new cases and verify RED**

Run: `uv run pytest -W error tests/test_conversation.py -k 'idempotent or conflict or stale or scope or superseded or lock or concurrent or interrupted' -q`

Expected: at least the exact retry fails because existing promotion rejects ID
reuse, and status interfaces are missing.

- [ ] **Step 7: Implement exact-match reuse and read-only status**

Before first promotion, lookup the candidate Direction ID. If absent, use
`promote_direction`. If present, require it to be current and compare its
Direction text, predecessor, change note, Direction approval, and promotion
grant to the deterministically derived records. Return the same draft only for
an exact match; otherwise raise `ConversationConflictError`.

Implement:

```python
def conversation_handoff_status(
    repository: Path,
    proposal_data: object,
) -> ConversationHandoffStatus: ...
```

Return `awaiting-approval`, `ready-for-preflight`, `conflict`, or `superseded`
with fixed ordinary summaries and `execution_authorized=False`. Status performs
no write and never creates authority.

- [ ] **Step 8: Run all conversation and Direction tests and verify GREEN**

Run: `uv run pytest -W error tests/test_conversation.py tests/test_direction.py tests/test_e2e_direction.py -q`

Expected: pass with existing Direction behavior unchanged.

- [ ] **Step 9: Commit Task 2**

```bash
git add src/second_mate/conversation.py src/second_mate/__init__.py \
  tests/test_conversation.py
git commit -m "feat(second-mate): approve conversation handoffs idempotently"
```

### Task 3: Stable internal CLI and end-to-end First Mate transport

**Files:**
- Modify: `src/second_mate/cli.py`
- Create: `tests/test_e2e_conversation.py`
- Create: `tests/fixtures/conversation_operator/task.json`
- Modify: `tests/test_package.py`

**Interfaces:**
- Consumes: Task 1/2 library functions.
- Produces: `handoff prepare|approve|status` deterministic JSON commands.

- [ ] **Step 1: Write the literal CLI journey failing test**

Run the real module CLI in subprocesses:

1. prepare the literal task fixture and prove target snapshot unchanged;
2. write an approval action derived from returned digests;
3. approve and prove only Direction history changed;
4. approve again and require byte-identical stdout/ledger bytes;
5. status and require ready-for-preflight ordinary summary;
6. inspect `--help` and require no handoff dispatch/run command.

```python
def test_first_mate_handoff_cli_is_readable_idempotent_and_stops_before_run(
    tmp_path: Path,
) -> None:
    target = make_repository(tmp_path)
    proposal = run_cli("handoff", "prepare", "--target", target, "--input", TASK)
    approval = exact_action(proposal)
    first = run_cli(
        "handoff",
        "approve",
        "--target",
        target,
        "--proposal",
        write(proposal),
        "--approval",
        write(approval),
    )
    second = run_cli(
        "handoff",
        "approve",
        "--target",
        target,
        "--proposal",
        write(proposal),
        "--approval",
        write(approval),
    )
    assert first == second
    assert first["status"] == "ready-for-preflight"
    assert first["execution_authorized"] is False
```

- [ ] **Step 2: Run the CLI journey and verify RED**

Run: `uv run pytest -W error tests/test_e2e_conversation.py -q`

Expected: argparse rejects the unknown `handoff` command.

- [ ] **Step 3: Implement the thin CLI routes**

Add one `handoff` parser with required subcommands and file inputs from the
design. Dispatch directly to library functions through `_read_json`; reuse
`_emit`. Catch `ConversationConflictError`. Do not add a run/provider/executor
choice or render low-level activation state.

- [ ] **Step 4: Run CLI and package tests and verify GREEN**

Run: `uv run pytest -W error tests/test_e2e_conversation.py tests/test_package.py -q`

Expected: pass.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/second_mate/cli.py tests/test_e2e_conversation.py \
  tests/fixtures/conversation_operator/task.json tests/test_package.py
git commit -m "feat(second-mate): expose conversation handoff transport"
```

### Task 4: Operator documentation and canonical Program close

**Files:**
- Create: `docs/second-mate/CONVERSATION-HANDOFF.md`
- Modify: `README.md`
- Modify: `docs/second-mate/README.md`
- Modify: `docs/second-mate/DIRECTION-OPERATOR.md`
- Modify: `docs/second-mate/PROGRAM.md`
- Modify: `docs/second-mate/workflow-spec.md`
- Modify: `docs/second-mate/implementation-checklist.md`
- Modify: `pyproject.toml`
- Modify: `tests/test_package.py`

**Interfaces:**
- Documents: First Mate’s prepare/review/approve/status integration.
- Freezes: provider-free RUN-FACADE-01 follow-on plan and meaningful `Run now`
  gate without implementing it.

- [ ] **Step 1: Write the packaging failing test**

Extend the source-distribution test to require
`docs/second-mate/CONVERSATION-HANDOFF.md`. Run it against a freshly built
archive and watch it fail before changing `pyproject.toml`.

Run: `uv build && uv run pytest -W error tests/test_package.py -q`

Expected: the new guide is absent from the sdist.

- [ ] **Step 2: Write the operator guide and package it**

Document the ordinary flow first. Include literal transport examples for the
implementing First Mate, but label files/digests as internal. Explain mutable
proposal versus immutable approved Direction, one approval/two records,
idempotence, status meanings, no transcript retention, and no execution.

Add the guide to the Hatch sdist include list.

- [ ] **Step 3: Reconcile canonical claims**

Update Program authority/history, Delivery Map, selected frontier, continuation
prompt, checklist, workflow, and package indexes to mark CONV-BRIDGE-01 complete
only within provider-free evidence. Record RUN-FACADE-01’s exact provider-free
plan:

- consume Run Intent;
- resolve real target/current revision;
- derive route/packet and read-only preflight;
- show concise final effects/risk/verification preview;
- require one separate `Run now` Execution Consent;
- one launch, no duplicate on ambiguity, independent evidence;
- review then optional separately authorized commit/merge.

Do not claim live usability, a provider result, generic preflight, Execution
Consent, or RUN-FACADE implementation.

- [ ] **Step 4: Run documentation/package checks and verify GREEN**

Run:

```bash
uv build
uv run pytest -W error tests/test_package.py tests/test_e2e_conversation.py -q
git diff --check
```

Expected: the guide is packaged, CLI journey remains green, and no broken patch
format exists.

- [ ] **Step 5: Commit Task 4**

```bash
git add README.md pyproject.toml docs/second-mate tests/test_package.py
git commit -m "docs(second-mate): close provider-free conversation bridge"
```

### Task 5: Independent review and full close verification

**Files:**
- Modify only files required by a proven Critical/Important review finding.
- Create a test first for every behavioral correction.

**Interfaces:**
- Validates: frozen design and this implementation plan.
- Produces: a clean local implementation commit range with no provider effect.

- [ ] **Step 1: Request independent code review**

Use `superpowers:requesting-code-review` with base `6b907b3` and current HEAD.
Require read-only review of authority separation, proposal/display binding,
idempotence, privacy, concurrency, status truthfulness, CLI stability, and
preservation of FS-01.

- [ ] **Step 2: Fix review findings test-first**

Fix every Critical or Important finding. For behavior, write a failing test and
watch the expected failure before changing production code. Re-run the focused
suite and request re-review until no Critical/Important issue remains.

- [ ] **Step 3: Run full repository verification**

Run fresh:

```bash
uv run pytest -W error
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv sync --offline --locked
uv build
git diff --check 6b907b3..HEAD
```

Inspect sdist/wheel contents, install the wheel into a fresh `/tmp` environment,
and smoke import, `py.typed`, `second-mate --help`, and all handoff help paths.
Confirm no trusted-local run directory/marker was created or changed, no provider
process was started, `firstmate/` remains untracked/untouched, and the worktree
contains only intended changes.

- [ ] **Step 4: Commit any reviewed close correction**

If review required changes:

```bash
git add <exact reviewed paths>
git commit -m "fix(second-mate): harden conversation handoff boundary"
```

- [ ] **Step 5: Record final status**

Report the ordinary First Mate integration flow, exact changed paths/commits,
red-green and full verification evidence, residual friction, and the frozen
provider-free RUN-FACADE-01 next plan. State explicitly that no provider, real
target, dispatch, commit/merge facade, push, or external effect occurred.
