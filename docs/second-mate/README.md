# Second Mate design

Status: canonical design; POL-01 narrowly selected, the verified FS-01
Foundation baseline canonically adopted, CAP-01 and MS-01 complete, and
DIR-INTAKE-01 and CAP-02A implemented and locally verified; PRV-01 and CAP-02B
are complete for one consumed trusted-local proof run, while MS-02 still needs
the human product check

Second Mate is a lean coordinator for AI coding work. It preserves human-owned product Direction, gives capable models room to solve technical problems, and requires evidence that fits each completion claim. It is a clean project, not a retrofit of FirstMate, Knowless, or their backlog and worker structures.

The repository contains a Python 3.12 coordinator for approved Direction
intake, the fixture-only FS-01 lifecycle, the CAP-02A offline adapter proof, and
the durable evidence record for one manually enveloped CAP-02B run. It is
operated manually and does not self-orchestrate. The
[Direction operator guide](DIRECTION-OPERATOR.md),
[FS-01 operator guide](FS-01-OPERATOR.md), and
[trusted-local operator contract](TRUSTED-LOCAL-OPERATOR.md) describe those
boundaries. CAP-02A remains a library path over an injected mock control plane,
not a live command or provider integration. CAP-02B called one exact local
Codex CLI host through a private manual envelope; it did not add a production
adapter. Executable evidence is recorded in [PROGRAM.md](PROGRAM.md); that
evidence does not prove automated Rumble, reusable live dispatch, the broader
workflow, or product readiness.

## Authority and sources

The authority order is:

1. the user's latest explicit Direction and decisions;
2. this purpose-built package, until an approved revision replaces it;
3. later accepted project evidence and decision records within their stated scope.

[workflow-spec.md](workflow-spec.md) is the canonical workflow design. [implementation-checklist.md](implementation-checklist.md) is a readiness check, not a plan or task graph.

[The imported Foundation-First material](../placeholder/README.md) is a temporary, noncanonical reference. It preserves useful source ideas and unresolved tensions but does not import Knowless or FirstMate authority into Second Mate. Historical Milestone Spine artifacts are neither source nor authority.

## Non-goals

Second Mate is not:

- a dashboard, orchestration platform, agent mesh, or general control plane;
- a numerical scoring system or confidence-based gatekeeper;
- a RAG system, code graph, universal dependency graph, or renamed Milestone Spine;
- a mandatory schema, template, test portfolio, or multi-agent ritual for every change;
- an excuse to replace model judgment with coordinator policy; or
- authorization to copy, modify, or depend on FirstMate or Knowless implementation internals.

Mechanisms outside the canonical workflow enter scope only after pilots show a repeated need that cannot be met more simply.

## Recorded narrow pre-Program envelope — 2026-08-03

The human has approved exact Direction D-01, the documented evidence-based
Foundation route, and Python 3.12 and ENV-01. The human selected **POL-01:
narrow pre-Program consent**, canonically adopted the already verified FS-01
baseline, and approved CAP-01 as complete. The narrow decision answers only the
dangerous question of whether fixture-only FS-01 is sufficient as Second Mate's
permanent authority, evidence, and recovery foundation.

Its boundary is this clean checkout, the existing Python FS-01 implementation
and tests, and the checked-in fixture. Its resources are local Python 3.12,
Git, filesystem, CPU, and disk. It permits no network, credentials, provider,
external target, or external commitment; disposable run state is discarded and
at most the existing FS-01 Foundation Slice is retained. The recorded
2026-08-03 docs-only packet had separately scoped Execution Consent on its
recorded current read-only preflight. It authorized neither a later packet nor
any Validation or Foundation mutation or expansion.

The record does not backdate or prove the missing historical bootstrap grant.
No broad or future Second Mate Execution Consent was recorded by this envelope. Direction
approval, route approval, toolchain/environment acceptance, current preflight,
and this packet's scoped Execution Consent remain distinct records. Any later
bounded mutating packet needs its own current read-only preflight and exactly
fitting Execution Consent. Provider or host selection, credentials, external
execution, pushing, publishing, deployment, Rumble integration, and pilots were
not authorized by this envelope.

At the time of the 2026-08-03 packet record, MS-01 remained blocked on a
personal operator/product check. Binding Direction coverage remained
`still_remaining`; neither CAP-01 completion nor canonical FS-01 adoption
proved broader Direction coverage or product completion.

## Recorded status reconciliation — 2026-08-04

Read-only preflight established repository basis
`e46c6dc82df54e16ecd39d6ab826c6146d401739`. The latest request supplies
scoped Execution Consent only for local status-document edits to this README,
`workflow-spec.md`, `PROGRAM.md`, and `implementation-checklist.md`; it
authorizes no runtime mutation, later packet, or external effect.

On this basis, the human accepted plan-conformant FS-01 completion without
personally observing the fixture CLI/output journey and declined further FS-01
decision requests. For MS-01 only, that one-time scoped acceptance replaces the
former personal-observation gate and completes MS-01. It is not a human review,
observation, CLI/output-clarity judgment, or proof of D-01 fit; those unobserved
qualities remain accepted residual uncertainty.

The fixed FS-01 first workflow is therefore terminal, with no further user
decision. This narrow close does not amend the general milestone human-product
review rule, turn technical evidence into broader product evidence, or change
binding Direction coverage from `still_remaining`. Provider or host selection,
credentials, CAP-02 onward, pilot work, Rumble, push, publication, deployment,
and all external work were not authorized by that reconciliation.

## Recorded approved-Direction intake — 2026-08-04

After a fresh preflight, the human approved the exact test-first
DIR-INTAKE-01 plan and granted separately scoped Execution Consent for its
local shared-lock, immutable Direction-history, CLI, documentation, and proof
mutations. The implemented [operator flow](DIRECTION-OPERATOR.md) preserves
external/manual Rumble, separate exact Direction approval and ledger-write
authority, portable D-01/D-02 history, and safe handoff into `draft`.

This packet supplies no provider or host decision, model call, credential or
network access, live target, route/Map automation, push, commit, publication,
deployment, or pilot authority. Its completion unlocks only the separate
PRV-01 human decision/evidence packet described in [PROGRAM.md](PROGRAM.md).

## Recorded trusted-local execution decision — 2026-08-04

The human selected TLX-01: Second Mate's first planned live execution mode is
explicitly trusted-local and does not require a sandbox. It assumes a
human-selected machine, unprivileged operating-system account, repository, and
worktree are trusted enough for a coding agent and repository-controlled code
to use the account's broader permissions. That may include unrelated files,
credentials, local services, and arbitrary network destinations.

This choice narrows the near-term product claim instead of silently weakening
it. Second Mate still requires exact Direction, a frozen packet, read-only
preflight, separate Execution Consent, one durable owner, private exact-session
binding, `unknown-running` recovery, independent target evidence, and
recoverable clean close. It does not claim that the unsandboxed executor is
contained, that hostile repository content is safe, or that target evidence
proves the absence of effects elsewhere on the machine or network. Full DIR-02
coverage against executor overreach remains unproved.

Sandboxed execution is preserved as SBOX-01, a separate deferred hardening or
deployment path. It is not a prerequisite for the first trusted-local adapter
or supervised run, and a future sandbox failure must not silently downgrade to
trusted-local mode.

TLX-01 is a design decision, not run consent. No provider authentication or
call, credential use, target selection or mutation, system configuration,
CAP-02 implementation, dispatch, push, or commit is authorized by this packet.
Each later real run needs the exact unsandboxed activation acknowledgment and
fields in [TRUSTED-LOCAL-OPERATOR.md](TRUSTED-LOCAL-OPERATOR.md).

The later CAP-02A request separately authorized only a test-first offline/mock
adapter packet. That packet is now locally complete: exact activation/basis
binding, offline-only launch, private identity-recorded artifacts, strict
bounded JSONL lifecycle, cancellation and `unknown-running`, restart recovery,
independent-evidence posture, and narrow explicit cleanup are executable. It
selects `provider-billing-controls-only` with no Second Mate token-spend cap.
It did not select a billing project or authorize credentials, authentication,
provider calls, a real process/agent, system configuration, a live target,
CAP-02B, push, or commit; none occurred within CAP-02A.

## Recorded one-run trusted-local proof — 2026-08-04

The human later selected one exact local Codex CLI `0.146.0`/existing-ChatGPT
boundary and authorized one real CAP-02B run against frozen public Second Mate
HEAD `94c21707ab13294b8e756049691e89cba1c91725`. Activation
`cap02b-20260804t224244z-94c21707-audit01` was consumed once. Independent
inspection—not provider claims—proved the lifecycle, two allowed paths, one
recovery defect, every repository gate, clean close, and exact private cleanup.
The signal-exit regression and minimal positive-exit fix are locally committed
as `3ecf0fe`; [PROGRAM.md](PROGRAM.md) is the canonical evidence record.

CAP-02B therefore closes only this one manual proof boundary. The package still
has no production live-process adapter or trusted-local CLI route. MS-02 cannot
be completed from technical evidence alone: the next gate is the human product
check on whether the observed manual activation, evidence, recovery, cleanup,
and residual-risk experience is usable and still fits D-01.
