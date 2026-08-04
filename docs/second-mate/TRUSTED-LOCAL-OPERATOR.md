# Trusted-local execution operator contract

Status: canonical activation gate plus CAP-02A offline/mock reference and one
consumed CAP-02B manual proof; no production live adapter command is implemented

This document defines Second Mate's first planned live execution mode. It is a
manual, single-run mode for a human-selected local machine, operating-system
account, repository, and worktree that the human is willing to trust without a
sandbox. It does not describe a live command that can be run today.

## Implemented offline proof boundary

CAP-02A implements `OfflineTrustedLocalAdapter` as a library-only reference
over an injected `OfflineControlPlane`. The production package supplies no
subprocess or provider implementation and exposes no CLI route for this path.
Tests inject deterministic process doubles; they do not launch Codex or another
agent.

The reference validates the exact activation mode, all frozen basis bindings,
the three risk acknowledgments, `provider-billing-controls-only`, and
`exact-private-run-artifacts-only` before state or launch. A matching mock run
first claims one owner-private, one-shot activation-consumption marker outside
the run envelope. It then creates exactly `session.json`, `transcript.jsonl`,
and `control.tmp` in one owner-private directory outside the repository and
records each physical file identity. The marker survives cleanup and prevents
the same activation from becoming reusable; a later run needs a new activation
identifier. The adapter retains the raw transcript without a total token cap
while bounding only the parser's per-record working state.

The first canonical `thread.started` UUID binds the session. Strict JSON,
ordering, terminal event, and mock exit checks distinguish `completed`,
`failed`, and `unknown-running`; provider-reported changes never become target
evidence. Cancellation and ambiguous launch, read, wait, or restart state stay
`unknown-running` with no automatic retry or cleanup. Explicit cleanup first
attests the durable session, exact directory contents, and every recorded
identity, then unlinks only the three known files and the empty directory. It
validates but never deletes the consumption marker.

This is executable evidence for the coordinator-side contract only. It is not
provider readiness, containment, process-group cancellation proof,
exact-session resume, a target mutation, or authority to activate a real run.

## Consumed CAP-02B proof run

On 2026-08-04 the human separately authorized one real run under this contract.
The frozen boundary selected local Codex CLI `0.146.0`, the existing ChatGPT
login, normal provider and repository network access, the current public Second
Mate branch at `94c21707ab13294b8e756049691e89cba1c91725`, ephemeral CLI session
storage, private transcript retention through clean close, no automatic retry
or resume, and `provider-billing-controls-only`. No API billing project,
credential, account, or system configuration was created or changed.

The run consumed activation
`cap02b-20260804t224244z-94c21707-audit01` once. Its private manual envelope
bound the first session, retained the raw stream through evidence close, and
allowed only two repository paths. Independent JSONL, Git, regression,
repository-gate, and cleanup inspection proved the target result; provider
output was not accepted as proof. The audit's one recovery defect and minimal
signal-exit fix are committed in `3ecf0fe`. [PROGRAM.md](PROGRAM.md) owns the
canonical detailed evidence.

After clean-close evidence was recorded, cleanup removed only the exact private
`transcript.jsonl`, `control.tmp`, `session.json`, and empty run directory. The
consumed activation marker remains. The deletion is not provider-side erasure,
and the clean target evidence cannot prove that no unrelated machine or network
effect occurred.

This was a one-off manual operating envelope around the real CLI, not a new
production control-plane implementation or reusable Second Mate command. Its
authority is exhausted: do not resume, retry, or redispatch it. A future run
needs a new current preflight and activation; MS-02 additionally requires the
human product check described in the Program.

## What trusted-local means

`trusted-local` means the executor is intentionally **not contained**. The
coding agent and repository commands it launches may use every permission the
selected operating-system account already has. Depending on that account and
machine, this may include:

- reading, changing, or deleting unrelated files and repositories;
- reading local credentials, tokens, browser or tool state, and agent sockets;
- connecting to arbitrary internet or local-network destinations;
- invoking repository scripts, hooks, build tools, or dependencies with the
  same broad access; and
- leaving processes or effects that a target-repository diff cannot observe.

This mode assumes both the operator environment and repository content are
trusted enough for that exposure. It provides no defense against hostile
repository instructions or code, a mistaken destructive command, credential
access, data exfiltration, or effects outside the inspected target.

## What Second Mate still guarantees

The absence of containment does not remove the coordinator contract. A
conforming trusted-local implementation must still:

1. refuse dispatch without an exact approved Direction, frozen packet,
   current read-only preflight, and separate matching Execution Consent;
2. persist one owner before launch and bind the run to the first exact provider
   session identifier;
3. treat malformed events, lost output, uncertain process state, interruption,
   or ambiguous exit as `unknown-running`, never as permission to retry;
4. resume only the exact recorded session after a human recovery decision and
   never use a "last session" shortcut;
5. keep credentials, raw transcripts, session data, private reasoning, and
   disposable runtime state outside repository authority;
6. validate final target revision, changed paths, tests, and claim-fit evidence
   independently of provider output; and
7. record only what was actually observed and close in one atomic or
   recoverable transition.

These are authority, lifecycle, evidence, and recovery guarantees. They are
not machine-isolation guarantees. Even a clean target diff cannot prove that
no unrelated file, credential, network destination, or remote system was
touched.

## Non-negotiable activation preflight

Before a future adapter may launch one trusted-local run, all of the following
must be resolved and recorded:

- **Trusted environment:** the human names the machine and unprivileged
  operating-system account, confirms that the run will not execute as root or
  with an intentionally exposed escalation path, and accepts the account's
  broader reachable surface.
- **Trusted target:** the repository/worktree is baseline-known, its current
  revision and instructions are recorded, its content is considered suitable
  for unsandboxed execution, and the target has a tested restore source or
  backup. Unrelated work must not share the selected worktree.
- **Risk acknowledgment:** the human explicitly acknowledges possible access
  to unrelated local files, credentials, local services, and networks; possible
  execution of repository-controlled code; and the inability of Second Mate's
  close evidence to prove that no outside effect occurred.
- **Provider boundary:** one host and exact CLI version are selected; the
  authentication source is named without recording the secret; permitted and
  excluded repository data are explicit; intended provider/network effects,
  billing project, provider/billing controls, spend policy, and
  transcript/session retention are resolved. For the initial proof of concept,
  the selected spend policy is `provider-billing-controls-only`: Second Mate
  imposes no token-spend cap of its own and does not represent unavoidable
  provider or billing limits as coordinator guarantees.
- **Capability minimization:** hooks, MCP servers, plugins, apps,
  browser/computer control, subagents, and other optional effect surfaces are
  disabled unless the same grant names and justifies them. Model-generated
  commands do not deliberately receive provider or unrelated credentials.
  These measures reduce exposure but are not represented as containment.
- **Frozen run contract:** Direction identifier/digest, packet and preflight
  digests, target identity/revision, allowed target changes and intended
  effects, stop conditions, owner, cancellation sequence, exact-session
  continuation rule, and `unknown-running` recovery action all match.
- **Narrow cleanup:** cleanup authority is limited to the exact private
  session, transcript, and temporary control artifacts created and durably
  identified by that run inside its dedicated private run directory. Cleanup
  must refuse identity drift or unexpected entries and must never recursively
  delete, follow a path supplied by provider output, touch repository work or
  arbitrary system files, or claim to delete provider-side data.

Any missing or mismatched item blocks dispatch. The implementation must not
offer a flag that silently substitutes trusted-local execution when a requested
sandbox is unavailable.

## Required activation consent

The design decision recorded in the Program is not permission to execute. Each
real run needs its own human activation record bound to the current preflight.
The record must communicate this meaning, without relying on a magic phrase:

> I authorize one unsandboxed trusted-local execution for the named packet,
> target revision, provider boundary, and owner. I understand that the coding
> agent and repository code may use the broader permissions of the named local
> account, including access to unrelated files, credentials, services, and
> networks, and that Second Mate cannot prove the absence of effects outside
> the target. I accept that exposure for this run, subject to the recorded data,
> provider/billing spend policy, retention, target-change, stop, cancellation,
> recovery, and exact-private-artifact cleanup limits.

The stored grant must bind that acknowledgment to the exact Direction, packet,
preflight, repository, revision/fingerprint, provider boundary, allowed target
changes, intended effects, and stop conditions. Direction approval, Map
approval, provider selection, or a general willingness to accept machine risk
does not substitute for this per-run consent.

## Cancellation and `unknown-running`

Cancellation is a request, not proof that execution stopped. A future adapter
must signal the owned process group using bounded graceful and forced stages,
retain the exact session identifier and transcript tail, and inspect the target
before deciding what happened.

If completion cannot be established, the durable state is `unknown-running`.
While it remains unknown:

- do not start a second executor for the packet;
- do not infer that the target is safe from process exit alone;
- do not resume or redispatch automatically;
- inspect process identity and the target's exact revision and changed paths;
  and
- require a human decision to resume the exact session, abandon it, or perform
  separately authorized recovery.

Because the mode is unsandboxed, target inspection cannot establish the state
of unrelated files or external systems. Any suspected outside effect is
recorded as residual uncertainty and may require independent operator recovery.

Recovery cleanup is a separate explicit local action. It may remove only the
exact private files created and identity-recorded for the run plus the now-empty
dedicated run directory. It does not revert repository changes, delete other
local files, invoke provider session deletion, or erase provider-side data.
Repository or external recovery always requires its own evidence and authority.
The one-shot activation-consumption marker is authority history, not disposable
session/transcript/temp state, and remains so cleanup cannot make the grant
reusable.

## What survives from LIVE-BOUNDARY-01

The following LIVE-BOUNDARY-01 work remains required for the trusted-local
path:

- exact binary/version identity;
- explicit capability inventory and optional-surface minimization;
- private session binding and transcript handling;
- strict, bounded event parsing;
- cancellation and `unknown-running` recovery;
- one durable owner and no automatic retry;
- provider-independent changed-path, final-revision, and claim-fit proof; and
- separate provider data, billing/spend policy, retention, and real-target
  authority; and
- identity-bound cleanup of only exact private run artifacts.

The following moves to the later sandboxed hardening/deployment path:

- proving filesystem deny-read and deny-write boundaries outside the grant;
- proving command-network denial or an enforced network allowlist;
- proving that credentials and unrelated host files are technically
  unreachable to model-generated commands;
- failing closed on sandbox startup or isolation-probe failure; and
- qualifying each operating environment's sandbox mechanism.

Sandboxing later strengthens the execution claim; it does not replace the
authority, recovery, or independent-evidence controls above.
