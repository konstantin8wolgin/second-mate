# Second Mate implementation and pilot readiness

Status: canonical readiness checklist; POL-01 is narrowly selected, the
verified FS-01 baseline is canonically adopted, CAP-01 and MS-01 are complete,
DIR-INTAKE-01 and CAP-02A are implemented and locally verified, PRV-01 plus
CAP-02B are historically closed for one consumed run with only partial
independent evidence retained, and CAP-02C plus EVA-01 are reproducible without
a provider; MS-02 remains blocked on the human product check

This checklist records gates and observable readiness. It does not assign tasks, define a backlog, impose ordering beyond the workflow's authority gates, or recreate a Milestone Spine.

An unchecked item means the broader workflow or Program gate has not been
proved and accepted; it does not mean no supporting code exists. A checked item
is now prefixed with the evidence class from the Program: **R** reproducible,
**I** independently retained, **H** human decision/authority, or **S** current
structural inspection. A documentation assertion by itself earns no class. The local
FS-01 slice now supplies executable evidence for a narrow subset of the
Foundation, packet, safeguard, and persistence items. [PROGRAM.md](PROGRAM.md)
records that evidence and its limits. The human did not personally observe the
fixture CLI/output journey or supply a clarity or D-01-fit judgment; those
accepted residual uncertainties, the provider path, and pilot evidence must not
be inferred from a green fixture suite.

## Current evidence classification

The evidence classifications below apply to the current branch and exact
recorded decisions. They distinguish reproducible evidence, retained artifacts,
human authority, and non-replayable historical close records; they do not
backdate the historical bootstrap.

| First-workflow requirement area | Classification | Current evidence or exact gap |
|---|---|---|
| D-01, route, and T-01/ENV-01 | **H; current technical subset R** | Separate human decisions are recorded. Current Python/Linux/Git behavior is reproducible; the decisions themselves are authority, not executable proof. |
| POL-01 selection, canonical FS-01 adoption, CAP-01, and recorded documentation consents | **H; FS-01 technical subset R** | The human decisions remain accepted within their exact scope. Current fixture behavior is independently reproducible; prose does not prove consent or broader readiness. |
| All future Execution Consent | **EVA-01 completed locally; blocked afterward** | The latest delegation authorized only the bounded provider-free EVA-01 audit, repairs, documentation, and local commits. Every later mutation, real activation, target, provider call, pilot, or external effect needs a new current preflight and fitting consent. |
| FS-01 deterministic local lifecycle and its stated invariants | **R** | The implementation, fixture journey, refusal/recovery tests, and repository gates are executable; their claim remains fixture-only. |
| MS-01: Foundation Slice close | **H: completed under one-time scoped acceptance** | The human accepted plan-conformant FS-01 completion without personally observing the fixture CLI/output journey and declined further FS-01 decision requests. This is not a human review, observation, clarity judgment, or D-01-fit proof; those remain accepted residual uncertainty. |
| Approved-Direction intake | **R for the local manual boundary** | Current implementation and tests prove no-write preparation, separate exact approval/promotion authority, immutable D-01/D-02 history, shared mutation locking, drift/open-state/race refusal, marked-write recovery, clone-readable persistence, CLI inspection, and `draft` consumption. The [operator guidance](DIRECTION-OPERATOR.md) describes this evidence; it is not itself proof. Automated Rumble and provider work remain unproved. |
| Trusted-local initial execution boundary | **CAP-02A/C R; real exercise I + non-replayable close record** | CAP-02A/C behavior is reproducible locally. CAP-02B's marker and fix remain independently inspectable, but its deleted stream and close artifacts are not replayable. None proves containment against agent mistakes, hostile repository content, credential access, network egress, or unrelated-machine effects. |
| Provider/host boundary and trusted-local adapters | **PRV-01 H + I; CAP-02A/C R** | The one-run Codex/auth/data/network/retention/no-retry/cleanup selection is a human record; the marker retains its provider digest and target bindings, not the deleted live stream. CAP-02A/C supply reproducible coordinator and subprocess behavior but no CLI route. Every future real run needs a fresh boundary and activation. |
| Dormant Codex CLI adapter preparation | **R without a provider** | CAP-02C binds executable/probes/model/prompt/environment/argv, reuses exact activation, streams stdout and private stderr, owns process-group cancellation, preserves transcript-tail/unknown-running/no-retry behavior, disables the inventoried `skill_search` surface, phase-gates cleanup, and exposes no CLI route. All process proof used temporary fake executables; no `codex exec`, auth inspection, provider call, or live target was used. |
| One real trusted-local provider-owned run and medium pilot | **CAP-02B historically closed once; retained evidence partial; MS-02 open** | The retained marker proves activation `cap02b-20260804t224244z-94c21707-audit01` and its frozen bindings are consumed; Git and current tests prove the two-path recovery fix. The deleted JSONL/session/control/close artifacts make the original event lifecycle and cleanup non-replayable historical records. No retry is permitted. Product usability, live CAP-02C operation, a pilot, CAP-03, milestone proof, and the human product check remain unproved. |

## Authority and scope

- [x] **H** — The user chose narrow pre-Program consent with the recorded FS-01-only envelope.
- [x] **R** — Direction approval, route approval, and execution authority are represented as distinct states in the schemas and operator flow.
- [x] **H + R** — The human canonically adopted the reproducible FS-01 baseline and approved CAP-01 complete; no broader claim follows.
- [x] **H** — The 2026-08-03 docs-only packet and 2026-08-04 status reconciliation have separately scoped recorded consent; no broad or future consent is inferred.
- [x] **I + H** — Git retains basis `e46c6dc82df54e16ecd39d6ab826c6146d401739`; its recorded consent is limited to the four status documents.
- [x] **H** — The selected narrow envelope permits no new Validation or Foundation expansion; each later packet remains separately gated.
- [x] **R within the coordinator boundary** — FS-01 and trusted-local guards refuse mismatched authority. Unsandboxed executors are not technically contained after dispatch.
- [x] **R** — The current handwritten implementation-Python inventory is 6,381 lines excluding tests, within the 4,000–9,000 scope-pressure range. This rough count proves no broader readiness.
- [x] **S** — Dependency/import and tracked-file inspection finds no FirstMate or Knowless workflow dependency.
- [x] **I** — The nested `firstmate/` checkout is currently excluded only by local `.git/info/exclude`; it is untracked, untouched, and non-portable.
- [x] **H** — The roadmap-reconciliation grant covered only that local boundary correction and its two canonical documents.
- [x] **H + R** — DIR-INTAKE-01's exact test-first grant is recorded and its bounded behavior is reproducible; no provider or external authority follows.
- [x] **H** — TLX-01 selects unsandboxed trusted-local mode with its broad limitations and defers SBOX-01; it is not run consent.
- [x] **H** — TLX-01's documentation consent authorized no provider, credential, target, system, dispatch, push, or commit effect.
- [x] **H + R** — CAP-02A's exact offline grant is recorded and its offline behavior is reproducible; it supplied no live authority.
- [x] **H + I** — CAP-02B's exact one-run grant is recorded; the retained marker independently binds and exhausts that activation.
- [x] **I** — The CAP-02B marker proves the activation is exhausted, and Git proves the two-path fix. The deleted event/close artifacts are not replayable; no retry/resume/redispatch follows.
- [x] **H + R** — CAP-02C's provider-free grant is recorded and its fake-executable behavior is reproducible without `codex exec` or a live target.
- [x] **H** — EVA-01 is authorized from clean `34dc2ae` for this evidence audit, bounded local repairs, documentation, verification, and local commits only; all live/provider/system/push boundaries remain closed.

## Direction and routing

- [ ] Scaled Sol High Rumble produces a what/why-only candidate Direction Summary.
- [x] **R** — The exact approved Direction text is immutable and versioned on material change.
- [x] **R** — Direction intake persists neither raw Rumble material nor provider transcripts.
- [ ] Sol Ultra synthesis and a fresh independent challenge use the same authority sources without shared private reasoning.
- [x] **R** — The current route record stores a short reason without a score.
- [ ] Small isolated work can stay direct without Map or Foundation ceremony.
- [x] **R** — DIR-INTAKE-01 preserves separate approval/write authority, portable durable history, and the schema consumed by `draft`.

## Foundation readiness

- [ ] A compact interaction view is created only when shared relationships or dangerous unknowns warrant it.
- [ ] A Validation Slice, when selected, names one decision-changing question, realistic envelope, evidence, limits, and discard boundary.
- [ ] Disposable code cannot enter the permanent path merely because it works.
- [x] **S** — The current Backbone document is limited to concepts, ownership/lifecycle, invariants, compatibility, boundaries, and proof seams; this is structural inspection, not runtime proof.
- [x] **H + R** — The adopted FS-01 slice reproducibly exercises its fixture journey and current quality bar; it proves no live-provider or broader-workflow claim.
- [x] **S** — The Foundation review structurally separates reproduced evidence, uncertainty, boundaries, and route consequences.

## Delivery Map readiness

- [x] **S** — The Map structurally links Direction, capabilities, milestones, evidence, and the next frontier without granting execution authority.
- [ ] An independent Sol Ultra Challenger checks coverage, product meaning, Foundation fit, order, assumptions, proof, and packet breadth.
- [x] **H** — The human approved the initial Foundation route only, not the later staircase or mutation.
- [x] **H** — The human approved the exact test-first DIR-INTAKE-01 plan before its bounded mutation.
- [x] **S** — No packet is currently `ready`; the completed packet histories remain detailed and the next product step is the undetailed MS-02 human gate.
- [x] **R + S** — Runtime state and the Map keep route status distinct from binding Direction coverage.
- [x] **S** — The Map contains no full backlog, dependency graph, universal task schema, or Milestone Spine.

## Packet execution and close

- [x] **S** — No packet is currently `ready`; completed EVA-01 has one outcome, a bounded repair set, named red-green proof, and explicit stop conditions.
- [x] **R + S, packet-scoped** — Executable preflight resolves the repository/instruction/basis fields it owns; EVA-01 separately inspected dependencies, baseline failures, authority, and irreversible-change risk. This is not a universal automated preflight claim.
- [ ] User-facing bugs are reproduced end to end before the fix and replayed after it.
- [ ] The working model may plan, diagnose, implement, test, and iterate freely inside the contract.
- [x] **R, FS-01 scope** — FS-01 clean close replays its affected fixture interaction at the final revision.
- [x] **R, FS-01 scope** — FS-01 writes evidence, route/coverage status, residual uncertainty, pressure, and handoff in one recoverable transition.
- [ ] A failed packet cannot unlock or detail new frontier work; this remains a workflow rule without an executable general enforcement proof.

## Safeguards and evidence

- [ ] High-cost-to-reverse mutations trigger independent review, rollback/migration proof where applicable, and any required human authority.
- [ ] Each meaningful product milestone has one human product check, without packet-by-packet approval.
- [ ] Validation, Foundation, packets, milestones, and stabilization use evidence proportional to their claims.
- [ ] Executable, structural, end-to-end, manual, and human evidence are combined only when the claim needs them.
- [x] **R + S** — Current lint, format, type, test, build, package, and smoke gates remain floors; dependency and test inspection finds no unrelated universal framework.
- [ ] Recovery chooses Packet, Map, Foundation, or Direction pressure at the smallest invalid premise; current records demonstrate examples but do not prove this generic process behavior.
- [ ] Major architecture and recovery work routes to Sol Ultra; ready implementation routes to Sol xhigh; trivial low-risk work may use Sol High.

## Runtime and pilot readiness

- [ ] Persistence is limited to Direction, the route reason, applicable Foundation Backbone/review, Map, evidence/status, handoff, and the clean-close transaction.
- [x] **R, implemented scope** — Direction/runtime code keeps raw provider material outside repository state and trusted-local artifacts in owner-private files. No claim is made that an unsandboxed executor cannot reach other private data.
- [x] **S** — Tracked files, imports, dependencies, and CLI inspection find no dashboard, mesh, score, generalized workflow control plane, RAG/code graph, or universal schema/test framework.
- [x] **R + S** — The implemented workflow is manually invoked and does not self-orchestrate.
- [x] **H + S** — TLX-01 records trusted-local unsandboxed assumptions and preserves SBOX-01 as a non-downgrading later path.
- [x] **H** — The selected POC policy is `provider-billing-controls-only`; CAP-02B's recorded boundary used the existing ChatGPT account without selecting an API billing project.
- [x] **H + I** — PRV-01 selected one exact proof-run boundary; the marker retains its provider digest and target bindings. The selection is exhausted and not reusable.
- [x] **R** — LIVE-BOUNDARY-01 reproducibly proves the offline activation/session/parser/ambiguity/evidence/cleanup contract; it proves no provider or real process.
- [x] **R** — CAP-02A reproducibly proves the injected offline adapter and failure paths while preserving FS-01; it makes no live claim.
- [x] **R** — Cleanup refuses active runs; `unknown-running` cleanup needs explicit `abandoned` recovery disposition and refuses while this adapter still owns the process. It then validates the private directory, session, exact names, identities, and retained marker before deleting only the three run files and empty directory. It never recurses or touches repository/system/provider data.
- [x] **I + N** — CAP-02B's marker and two-path fix are independently retained. Its real JSONL lifecycle, historical gate output, close document, and cleanup identities were deleted and are now non-replayable close records, not current proof. No outside-effects claim follows.
- [x] **R** — CAP-02C reproducibly proves fake-executable boundary qualification, memory-only adapter inputs, fixed capability-minimized argv including `skill_search`, descriptor-bound dispatch, private streams, process-group cancellation, transcript-tail/unknown-running/no-retry recovery, and phase-gated exact cleanup. It adds no CLI route or live claim.
- [ ] MS-02 receives the human product check on whether the historically closed one-run record plus the unactivated CAP-02C adapter, retained evidence, recovery, cleanup, and residual-risk experience are usable and still fit D-01. Technical completion cannot manufacture this judgment or decide whether a newly authorized adapter exercise is required first.
- [ ] SBOX-01, when a trust/data/deployment need pulls it forward, proves filesystem, environment, credential, network, optional-capability, cancellation, and cleanup containment in the actual environment and fails closed without automatic trusted-local downgrade.
- [ ] The pilot target is medium-sized, baseline-known, and rich enough to exercise Foundation choice, several packets, one meaningful milestone, and honest recovery if evidence demands it.
- [ ] Pilot observations cover Direction fidelity, decisive evidence, integration, closure, handoff, product progress, rework, missed outcomes, artifact burden, and human intervention.
- [ ] Pilot conclusions are scoped to observed evidence and do not claim universal superiority.
