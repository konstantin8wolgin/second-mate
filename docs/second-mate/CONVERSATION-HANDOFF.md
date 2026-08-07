# Conversation handoff operator guide

CONV-BRIDGE-01 is the provider-free integration boundary between an ordinary
First Mate conversation and Second Mate. It supports this flow:

> discuss and research → review one concise task → Approve → ready for preflight

`ready-for-preflight` does **not** mean that preflight passed or that a run was
authorized. The bridge does not select a provider or route, inspect credentials,
resolve an executable, create Execution Consent, launch an agent, modify task
files, commit, merge, push, or deploy.

## What the implementing First Mate supplies

First Mate derives one strict transport document from the visible conversation
summary. The user should edit or approve the ordinary-language meaning, not this
JSON:

```json
{
  "schema_version": 1,
  "handoff_id": "conversation-task-17",
  "source_conversation_id": "conversation-42",
  "repository_id": "second-mate",
  "task": "Add the approved conversation-to-run handoff.",
  "assumptions": ["The selected checkout is the intended project."],
  "allowed_effects": ["Read and modify files required by the approved task."],
  "prohibited_effects": ["Do not publish or deploy."],
  "acceptance": ["The bridge is verified provider-free end to end."]
}
```

Use exactly these keys. Do not include raw messages, transcripts, hidden
reasoning, prompts, credentials, provider/session data, executable details, or
activation state. Second Mate rejects unknown keys. It normalizes line endings
and surrounding whitespace, rejects NULs, empty required meaning, and duplicate
list entries, and hashes the source conversation identifier instead of returning
or storing it in approved Direction history.

`task`, `allowed_effects`, and `acceptance` must be non-empty. `assumptions` and
`prohibited_effects` may be empty; the review then says `None stated.`

## Prepare and show the review

The transport-neutral library call is:

```python
proposal = prepare_conversation_handoff(target_repository, task_document)
```

The equivalent internal CLI adapter is:

```console
second-mate handoff prepare \
  --target /path/to/selected/repository \
  --input /private/control/task.json
```

Preparation is read-only. Show the user only the returned task, assumptions,
proposed effects, prohibitions, acceptance conditions, summary, and next action.
The machine document also carries digests and repository/Direction bindings;
those are First Mate control-plane details, not user tasks.

If the user edits any material meaning, discard the proposal and prepare a new
one. Do not treat discussion, a draft request, or a previous approval as approval
of changed bytes.

## One Approve action, two durable records

One ordinary user-facing **Approve** action creates one internal action document.
First Mate supplies the stable action identifier, actor, and time and copies the
proposal and candidate digests from the exact prepared proposal. Its two scopes
are fixed and ordered:

```json
{
  "schema_version": 1,
  "id": "approve-conversation-task-17",
  "decision": "approved",
  "proposal_digest": "<from the exact proposal>",
  "candidate_digest": "<from the exact Direction candidate>",
  "approved_by": "project-owner",
  "approved_at": "2026-08-07T10:00:00Z",
  "approved_scopes": ["direction_meaning", "direction_ledger_write"]
}
```

Do not ask the user for a second click. Internally, approval records two distinct
durable records in the existing immutable Direction ledger:

1. a proposal- and candidate-digest-bound Direction approval; and
2. a candidate- and repository-basis-bound grant for one
   `.second-mate/directions.json` write.

Neither record is route approval or Execution Consent. The library call is:

```python
draft = approve_conversation_handoff(target_repository, proposal, approval_action)
```

The internal CLI adapter is:

```console
second-mate handoff approve \
  --target /path/to/selected/repository \
  --proposal /private/control/proposal.json \
  --approval /private/control/approval.json
```

Success returns `ready-for-preflight`, the exact approved Direction, two named
receipts, and a non-executable Run Intent. Only the Direction ledger changes.
Raw conversation content and the raw source conversation identifier are not
written to the target.

## Retry and status behavior

An exact repeated approval is idempotent: it returns the same draft bytes and
does not write the ledger again. Do not generate a new action identifier, actor,
or timestamp for a transport retry. Do not automatically retry after an
ambiguous external action; CONV-BRIDGE itself has no external action or dispatch.

Read status without creating authority:

```console
second-mate handoff status \
  --target /path/to/selected/repository \
  --proposal /private/control/proposal.json
```

The statuses are:

- `awaiting-approval`: the exact proposal remains valid but is not stored;
- `ready-for-preflight`: the exact approved Direction is current;
- `conflict`: the repository, proposal binding, meaning, or authority differs;
- `superseded`: the exact approved Direction is historical rather than current.

On `conflict` or `superseded`, stop and prepare a fresh proposal for human
review. Never overwrite history, infer approval, broaden scopes, or start a run.
Malformed or missing recorded history, stale repository basis, an open run, a
busy mutation lock, or non-exact interrupted recovery fails closed.

## The current stop and the later Run facade

The Run Intent deliberately contains task meaning only: repository identifier,
approved Direction identity/digest, proposal digest, task, assumptions,
requested/prohibited effects, and acceptance conditions. It contains no target
revision, route, provider, executable, activation, owner, or Execution Consent.

RUN-FACADE-01 is the separate next boundary. It must resolve the real target and
current revision, derive a route/packet, run a read-only preflight, qualify the
trusted-local execution boundary internally, show one concise final effects and
risk preview, and consume a separate one-shot **Run now** Execution Consent
before exactly one launch. It must then independently verify the result, report
uncertainty without duplicate dispatch, and offer review followed by separately
authorized commit or merge. None of that is implemented by this guide or by
CONV-BRIDGE-01.
