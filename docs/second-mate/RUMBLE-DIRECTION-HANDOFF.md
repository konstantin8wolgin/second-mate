# Rumble to Direction operator handoff

This is the smallest usable local bridge between the existing Rumble behavior
contract and Second Mate. Rumble still happens in an external voice or chat
session. Second Mate neither connects to that session nor calls a model; it
only prepares the exact resulting Direction Summary for review and promotes a
separately approved version into the target repository.

The behavior contract remains the model-facing prompt in
[`docs/placeholder/foundation-first/rumble-direction-skill.md`](../placeholder/foundation-first/rumble-direction-skill.md).
Use that prompt as written. It accepts nonlinear conversation and produces a
proportional what/why-only Direction Summary; this handoff does not replace it
with a form or questionnaire.

## Private external session

Run the Rumble in the voice or chat surface of your choice, using Sol High when
available. Keep the conversation, raw transcript, provisional material, and
private reasoning in that surface or another private local location. When the
candidate Summary is ready, copy only its exact text into an editable UTF-8
document outside the target repository.

The Summary remains provisional. Editing it, preparing a candidate, ending the
session, or doing nothing does not approve it.

## Prepare the exact candidate

Use the repository-owned environment described in the FS-01 guide. The
`prepare` command reads the current approved Direction lineage, but does not
write the target, Git index, or external state:

```sh
uv run second-mate direction prepare \
  --target "$TARGET" \
  --summary "$PRIVATE_CONTROL/D-01.md" \
  --id D-01 \
  > "$PRIVATE_CONTROL/D-01.candidate.json"
```

Review the exact `candidate.text`, `candidate_digest`, and read-only
`promotion_basis` in that output. The basis identifies the target root, Git
head, and full visible-revision fingerprint. Any edit to the text or target
requires running `prepare` again.

## Record explicit human approval

The human creates a separate approval document after reviewing the exact
candidate. Second Mate deliberately has no command that manufactures approval:

```json
{
  "approved_at": "2026-08-02T12:00:00Z",
  "approved_by": "human-identifier",
  "candidate_digest": "the exact candidate_digest from prepare",
  "decision": "approved",
  "direction_id": "D-01",
  "id": "DA-01",
  "schema_version": 1
}
```

Direction approval confirms exact meaning; it does not authorize a project
write. The human separately creates a promotion grant bound to the prepared
candidate and repository basis. The two decisions may share one human
touchpoint, but remain distinct records:

```json
{
  "allowed_effects": ["direction_ledger_write"],
  "allowed_paths": [".second-mate/directions.json"],
  "candidate_digest": "the exact candidate_digest from prepare",
  "granted_at": "2026-08-02T12:01:00Z",
  "granted_by": "human-identifier",
  "id": "DPG-01",
  "schema_version": 1,
  "stop_conditions": ["revision_drift", "direction_history_drift"],
  "target_fingerprint": "the exact promotion_basis target_fingerprint",
  "target_head": "the exact promotion_basis target_head",
  "target_root": "the exact absolute promotion_basis target_root"
}
```

Keep both control documents private until the normal project authority permits
promotion. A missing approval or grant, any decision other than the literal
`approved`, an edited candidate, a mismatched digest or target, revision drift,
or an unknown or duplicate field is refused before a project write.

Promote the reviewed version:

```sh
uv run second-mate direction promote \
  --target "$TARGET" \
  --candidate "$PRIVATE_CONTROL/D-01.candidate.json" \
  --approval "$PRIVATE_CONTROL/D-01.approval.json" \
  --grant "$PRIVATE_CONTROL/D-01.promotion-grant.json"
```

Promotion appends deterministic project authority to
`.second-mate/directions.json`. The ledger contains only approved Direction
text, its approval record, scoped promotion grant, exact digests, and version
lineage. It never stores the source path, prompt, transcript, messages, model
metadata, credentials, or private reasoning.

Review and commit the ledger through the project's normal delivery authority;
it is accepted project state, not disposable local control data.

Show the current approved Direction in the existing schema consumed by
`second-mate draft`:

```sh
uv run second-mate direction show --target "$TARGET" \
  > "$PRIVATE_CONTROL/approved-direction.json"
```

Use `--id D-01` to recover a specific immutable version.

## Version a material Direction change

Edit a new Summary document, then prepare a new identifier with a concise
change note:

```sh
uv run second-mate direction prepare \
  --target "$TARGET" \
  --summary "$PRIVATE_CONTROL/D-02.md" \
  --id D-02 \
  --change-note "Explain the human-approved meaning change." \
  > "$PRIVATE_CONTROL/D-02.candidate.json"
```

Second Mate binds the candidate to the current approved identifier and digest.
After a new separate approval and promotion grant, `promote` appends D-02
without editing D-01. Reused identifiers, missing change notes, stale
predecessors, competing branches, and unchanged replacement text are refused.

## Authority and deliberate limits

Direction approval confirms exact what and why. It does not approve a route,
grant Execution Consent, permit provider calls, or authorize other mutations.
Promote Direction before packet preflight: a later Direction promotion changes
the target fingerprint and correctly invalidates stale preflight and consent.
Direction state must remain visible to Git; preparation refuses a target whose
ignore rules hide the ledger. Preflight still fingerprints an existing ledger
if a later ignore rule appears, so hidden authority drift cannot preserve stale
consent. Promotion also refuses while a packet run is open and shares its
repository-wide mutation lock with dispatch and restart. It rechecks target
revision, repository-root identity, and state-directory identity around ledger
installation, restoring the prior ledger if outside drift invalidates an
in-flight promotion. Changed
versions use Linux atomic name exchange inside the verified FS-01 filesystem
boundary; promotion fails closed when that primitive is unavailable.

If promotion reports that an entry was retained for recovery, stop instead of
retrying: inspect and reconcile the randomized `.second-mate/.directions.*`
entry and the durable ledger through the project's normal authority boundary.
Second Mate preserves an unowned or concurrently displaced entry rather than
guessing that it is safe to delete.

Schema validation prevents transcript or reasoning fields from entering the
ledger, but software cannot infer whether prose pasted into the Summary is
private reasoning. The operator and external Rumble session must preserve that
boundary. Native Codex voice integration, provider/model execution, and live
session continuation remain deliberately deferred.
