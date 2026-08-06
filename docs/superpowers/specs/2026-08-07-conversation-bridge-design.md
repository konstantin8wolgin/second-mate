# CONV-BRIDGE-01 Conversation Bridge Design

Status: frozen under the 2026-08-07 standing product authority; provider-free
implementation is authorized, while any real provider or agent dispatch remains
a separate meaningful gate

## Goal

Make Second Mate ordinary infrastructure behind a First Mate conversation:

1. discuss and research a task normally;
2. say “run this”;
3. review one concise, editable task proposal;
4. approve the exact task meaning and its one repository-ledger write in one
   visible action;
5. reach `ready-for-preflight` without dispatching anything.

The bridge must support varied repository work without asking the user to author
a rigid task document or manage digests, executable permissions, activation
markers, session state, or recovery records.

## Scope

CONV-BRIDGE-01 implements only conversation-summary intake through an approved,
preflight-ready handoff. It is entirely local and provider-free.

It does not:

- call a provider, model, agent, network service, or credential store;
- select or dispatch an executor;
- implement a generic target preflight or Execution Consent;
- mutate target content beyond the existing Direction ledger;
- commit, merge, push, or open a pull request;
- weaken one-owner, no-duplicate, `unknown-running`, independent-evidence, or
  recovery behavior; or
- generalize the proven FS-01 packet, preflight, or execution schemas.

RUN-FACADE-01 is a separate follow-on contract described below. Its future live
dispatch portion always requires a meaningful final `Run now` confirmation.

## Verified compatibility boundary

The current `Draft`, `Packet`, and `preflight` types intentionally encode the
deterministic FS-01 fixture: fixed proof paths, fixed effects, and one direct
fixture route. Treating a varied conversation task as that packet would produce
false readiness. Generalizing those types in this packet would also bundle the
future run facade and risk established FS-01 behavior.

The bridge therefore adds a parallel pre-execution handoff type while reusing
the existing mechanisms that already fit:

- `prepare_direction` for a read-only, repository-bound candidate;
- `promote_direction` for separate exact approval and ledger-write authority;
- the repository-wide mutation lock;
- immutable linear Direction history;
- drift, open-run, race, replacement, and interrupted-write refusal/recovery;
- deterministic JSON and digest helpers; and
- the thin CLI’s strict error and serialization behavior.

## Considered approaches

### Selected: focused conversation bridge

Add a focused `second_mate.conversation` module with its own proposal, approval
action, handoff draft, Run Intent, and status types. Reuse Direction promotion
unchanged for the only write. This preserves proven boundaries and gives the
later facade one exact input.

### Rejected: translate every conversation into FS-01

The fixture packet requires `artifact.txt`, `sentinel.txt`, and fixture-specific
effects. Mapping arbitrary work into it would be misleading and unsafe.

### Rejected: generalize Draft, preflight, and execution now

That would combine conversation intake, route choice, generic baseline
inspection, provider activation, and execution lifecycle in one packet. It is
larger than the selected evidence question and belongs to RUN-FACADE-01.

## User-facing flow

The ordinary interface shows only these meaningful states:

1. **Discussing** — First Mate gathers enough context to summarize the task.
2. **Review task** — the user sees outcome, assumptions, proposed effects,
   prohibited effects, and acceptance signals in ordinary language.
3. **Approve** — one action explicitly means both “approve this exact task
   meaning” and “store it once in this project’s Direction ledger.”
4. **Ready to prepare run** — the task is durable and `ready-for-preflight`, but
   no target mutation, provider call, or execution is authorized.

The user does not see or manage internal hashes, record identifiers, promotion
bases, lock files, executable qualification, consumed markers, private session
paths, or cleanup mechanics. A concise refusal may name a user-relevant cause
such as “the repository changed; review the refreshed proposal.”

## Conversation task input

First Mate, not the user, creates the strict transport document:

```json
{
  "schema_version": 1,
  "handoff_id": "conversation-task-17",
  "source_conversation_id": "conversation-42",
  "repository_id": "second-mate",
  "task": "Add a normal conversation-to-run handoff.",
  "assumptions": ["The selected checkout is the intended project."],
  "allowed_effects": ["Read and modify files required by the approved task."],
  "prohibited_effects": ["Do not publish or deploy."],
  "acceptance": ["The handoff is verified provider-free end to end."]
}
```

All keys are exact. Unknown keys such as `transcript`, `messages`,
`private_reasoning`, credentials, provider sessions, or activation data are
rejected. Text is normalized to UTF-8/LF with surrounding whitespace removed;
empty values and duplicate list items are rejected. `task`, `allowed_effects`,
and `acceptance` must be non-empty. `assumptions` and `prohibited_effects` may be
empty and are then displayed as “None stated.”

The structured transport is an integration boundary, not a user-authored task
template. First Mate derives it from the visible conversation summary.

## Read-only proposal preparation

`prepare_conversation_handoff(repository, task_data)`:

1. strictly validates and normalizes the task input;
2. derives a stable Direction identifier from the canonical
   `handoff_id`/`repository_id` binding without persisting the raw source
   conversation identifier;
3. renders all material task meaning into canonical Direction text;
4. calls `prepare_direction` against the current repository and Direction
   history;
5. returns a `ConversationProposal` with the candidate, proposal digest, human
   review, and `awaiting-approval` status; and
6. performs no write.

The Direction text contains:

- outcome;
- assumptions;
- proposed later effects, labelled as requested scope rather than authority;
- prohibited effects;
- acceptance signals; and
- the statement that neither route approval nor Execution Consent follows.

The proposal digest covers the normalized task, non-persisted source binding,
and exact Direction candidate envelope. Changing any displayed task meaning or
source handoff identity changes the proposal digest.

The proposal is mutable only by preparing a new proposal before approval. Once
approved, changed meaning requires a new handoff identifier and a new Direction
version under the existing linear-history rules.

## One visible Approve action, two durable records

The user-facing Approve action creates one `ConversationApprovalAction` bound
to both the proposal digest and Direction candidate digest. Its two explicit
scopes are fixed and visible:

- `direction_meaning`
- `direction_ledger_write`

The action also records a caller-supplied stable action identifier, actor, and
time. It contains no route, provider, or execution scope.

```json
{
  "schema_version": 1,
  "id": "approve-conversation-task-17",
  "decision": "approved",
  "proposal_digest": "<proposal digest>",
  "candidate_digest": "<Direction candidate digest>",
  "approved_by": "project-owner",
  "approved_at": "2026-08-07T10:00:00Z",
  "approved_scopes": ["direction_meaning", "direction_ledger_write"]
}
```

The scope list must be exactly the two values above in that order. A missing,
additional, duplicated, or reordered scope is not the same action and is
rejected.

`approve_conversation_handoff(repository, proposal_data, approval_action_data)`
deterministically derives:

1. a `DirectionApproval` for the exact candidate; and
2. a distinct `PromotionGrant` for only
   `.second-mate/directions.json` / `direction_ledger_write`, bound to the
   prepared target head, target fingerprint, run-state digest, and existing
   stop conditions.

The existing `promote_direction` mutation installs both records atomically as
one immutable approved Direction version. The returned handoff draft displays
the two records separately with ordinary summaries while keeping their
low-level binding fields available only in the machine document.

Neither record grants route approval, provider access, Execution Consent,
target-file mutation, commit, merge, push, or deployment.

## Handoff draft and Run Intent

Successful approval returns a deterministic `ConversationHandoffDraft`:

- exact approved Direction and digests;
- normalized task, assumptions, effects, prohibitions, and acceptance;
- separate Direction-approval and ledger-grant receipts;
- `status: ready-for-preflight`;
- `execution_authorized: false`;
- a human summary: “Task approved and stored. No run has started.”; and
- a `RunIntent` containing only the material task contract the later facade
  needs.

`RunIntent` contains the repository identifier, Direction identifier/digest,
proposal digest, task, assumptions, requested/prohibited effects, and
acceptance signals. It contains no target revision, preflight, route decision,
provider boundary, executable identity, activation, owner, or Execution
Consent. Those facts do not exist yet and must never be implied.

## Idempotence, conflicts, and ownership

An exact repeated Approve call:

- validates the same proposal and approval action;
- finds the current approved Direction version;
- verifies that the stored candidate meaning, Direction approval, and
  promotion grant exactly match the deterministic records; and
- returns the byte-identical handoff draft without another write.

It rejects, without mutation:

- the same handoff/Direction identifier with different content;
- a mismatched proposal or candidate digest;
- a missing or non-exact approval scope;
- a changed actor, time, or action identifier after successful import;
- stale target or Direction history before first promotion;
- a superseded matching Direction version;
- an open or pending run;
- a busy repository mutation lock;
- malformed, aliased, ignored, missing-recorded, or non-linear Direction
  history; and
- interrupted state that does not match the exact intended promotion.

The bridge adds no retry loop. Existing promotion recovery may finish only the
same durably recorded atomic write. It never starts an execution.

## Status and readiness

`conversation_handoff_status(repository, proposal_data)` is read-only and
returns one of:

- `awaiting-approval` — the exact proposal is not stored;
- `ready-for-preflight` — the exact matching version is current;
- `conflict` — the identifier exists with different authority or meaning; or
- `superseded` — the exact version exists but is no longer current.

Every status includes a concise human summary, the visible task/effect review,
and the next meaningful action. `ready-for-preflight` explicitly means ready to
enter RUN-FACADE preparation, not that preflight passed or execution is
authorized.

## Library and internal CLI surface

The public package exports the conversation proposal, approval action, handoff
draft, Run Intent, status, and the three functions above.

The internal transport CLI adds:

- `second-mate handoff prepare --target ... --input ...`
- `second-mate handoff approve --target ... --proposal ... --approval ...`
- `second-mate handoff status --target ... --proposal ...`

It emits deterministic JSON containing human-readable summaries. These commands
exist for First Mate integration, operator diagnosis, and end-to-end tests; they
are not the desired ordinary-user ceremony and expose no dispatch command.

## RUN-FACADE-01 follow-on contract

RUN-FACADE-01 consumes an exact `RunIntent` and owns the path from approved task
to one supervised execution. Its provider-free preparation portion may later:

1. resolve the user-selected real repository/worktree and verify repository
   identity;
2. bind the current revision and visible worktree state;
3. derive the fitting direct/Foundation route and exact packet;
4. run read-only preflight;
5. resolve executable/capability/private-state details internally; and
6. show one concise final Run Preview.

The Run Preview must show, in ordinary language:

- target project, branch/worktree, and whether it has uncommitted work;
- intended outcome and assumptions;
- final allowed paths/effects and prohibited effects;
- provider/network use and trusted-local residual risk;
- stop conditions and verification plan; and
- the statement that one execution will start and ambiguous completion will not
  be retried automatically.

Only the user’s explicit final `Run now` action may create one-shot Execution
Consent bound internally to the exact Run Intent, target revision/fingerprint,
route/packet, preflight, provider boundary, and effect boundary. Drift refreshes
the preview and requires a new confirmation.

After consent, the future facade may launch exactly one agent run, retain
ownership, classify failure or `unknown-running`, and require independent
target/test/build evidence. It must never treat provider output as proof or
silently start a duplicate. It then presents a review and offers later commit or
merge choices. Commit, merge, push, publication, and deployment are not
automatic and require fitting authority.

Ordinary users see `preparing`, `ready to run`, `running`, `completed`,
`failed`, or `status uncertain—no duplicate run started`. Low-level hashes,
marker files, executable modes, private session paths, signal handling, and
cleanup records stay internal unless needed in an operator diagnostic.

CONV-BRIDGE-01 does not implement RUN-FACADE-01 or any live behavior.

## Test strategy

All tests use fresh temporary Git repositories and local Python processes only.
No installed Codex executable, provider, authentication state, network, or real
target is used.

Test-first coverage must prove:

- read-only preparation and deterministic normalization/rendering/digests;
- rejection of unknown/raw-transcript fields;
- one visible approval action produces two distinct exact stored records;
- ready draft and Run Intent contain all and only the approved task contract;
- exact reapproval is byte-identical and does not write again;
- same identifier/different content, authority mismatch, stale basis, open run,
  lock contention, concurrency, malformed history, and supersession fail closed;
- interrupted Direction-write recovery remains exact;
- status transitions and ordinary summaries are truthful;
- CLI prepare/approve/status is provider-free end to end;
- existing DIR-INTAKE, FS-01, trusted-local, and package behavior remains green;
  and
- the package contains the new operator documentation but no dispatch surface.

## Documentation and evidence

The implementation close updates the canonical Program, workflow specification,
implementation checklist, package README/index, Direction operator guide, and a
new conversation-bridge operator guide. Claims distinguish executable provider-
free evidence from the approved product decision. No live or usability claim is
created by this packet.

## Acceptance criteria

CONV-BRIDGE-01 is complete when:

- a fresh First Mate-style summary can be prepared without mutation;
- the returned review is concise and editable before approval;
- one approval action atomically stores two separate exact authority records;
- exact repetition is idempotent and conflicting repetition fails closed;
- the result is a truthful, human-readable `ready-for-preflight` Run Intent;
- no provider, agent, network, credential, live target, preflight, execution,
  commit, merge, push, or destructive action occurs;
- all focused and repository quality/package gates pass; and
- independent review finds no unresolved Critical or Important issue.
