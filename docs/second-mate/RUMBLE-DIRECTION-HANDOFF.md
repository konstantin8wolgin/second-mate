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

Review the exact `candidate.text` and `candidate_digest` in that output. Any
edit to the text requires running `prepare` again.

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

Keep this control document private until the normal project authority permits
promotion. A missing approval, any decision other than the literal `approved`,
an edited candidate, a mismatched digest, or an unknown approval field is
refused before a project write.

Promote the reviewed version:

```sh
uv run second-mate direction promote \
  --target "$TARGET" \
  --candidate "$PRIVATE_CONTROL/D-01.candidate.json" \
  --approval "$PRIVATE_CONTROL/D-01.approval.json"
```

Promotion appends deterministic project authority to
`.second-mate/directions.json`. The ledger contains only approved Direction
text, its approval record, exact digests, and version lineage. It never stores
the source path, prompt, transcript, messages, model metadata, credentials, or
private reasoning.

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
After a new separate approval, `promote` appends D-02 without editing D-01.
Reused identifiers, missing change notes, stale predecessors, competing
branches, and unchanged replacement text are refused.

## Authority and deliberate limits

Direction approval confirms exact what and why. It does not approve a route,
grant Execution Consent, permit provider calls, or authorize other mutations.
Promote Direction before packet preflight: a later Direction promotion changes
the target fingerprint and correctly invalidates stale preflight and consent.

Schema validation prevents transcript or reasoning fields from entering the
ledger, but software cannot infer whether prose pasted into the Summary is
private reasoning. The operator and external Rumble session must preserve that
boundary. Native Codex voice integration, provider/model execution, and live
session continuation remain deliberately deferred.
