# Second Mate implementation and pilot readiness

Status: canonical readiness checklist; POL-01 is narrowly selected, the
verified FS-01 baseline is canonically adopted, CAP-01 and MS-01 are complete,
DIR-INTAKE-01, CONV-BRIDGE-01, and CAP-02A are implemented and locally verified,
PRV-01 plus CAP-02B are historically closed for one consumed run with only
partial independent evidence retained, and CAP-02C plus
EVA-01/EVA-02/EVA-03/EVA-04 are reproducible provider-free. One CAP-02C
disposable live exercise is consumed and conservatively closed as
`unknown-running`; MS-02 remains blocked on RUN-FACADE-01 and the human product
check

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
| All future Execution Consent | **CAP-02C exercise H consumed; blocked afterward** | The latest live grant authorized exactly activation `cap02c-live-20260806-02-4ybb2d`; it is consumed and not reusable. No second dispatch, pilot, or target effect is authorized. Every future run needs a new current preflight and fitting consent. |
| FS-01 deterministic local lifecycle and its stated invariants | **R** | The implementation, fixture journey, refusal/recovery tests, and repository gates are executable; their claim remains fixture-only. |
| MS-01: Foundation Slice close | **H: completed under one-time scoped acceptance** | The human accepted plan-conformant FS-01 completion without personally observing the fixture CLI/output journey and declined further FS-01 decision requests. This is not a human review, observation, clarity judgment, or D-01-fit proof; those remain accepted residual uncertainty. |
| Approved-Direction intake | **R for the local manual boundary** | Current implementation and tests prove no-write preparation, separate exact approval/promotion authority, immutable D-01/D-02 history, shared mutation locking, drift/open-state/race refusal, marked-write recovery, clone-readable persistence, CLI inspection, and `draft` consumption. The [operator guidance](DIRECTION-OPERATOR.md) describes this evidence; it is not itself proof. Automated Rumble and provider work remain unproved. |
| Trusted-local initial execution boundary | **CAP-02A/C + EVA-03/EVA-04 R; two consumed live records I/N** | CAP-02A/C behavior and exact-cleanup recovery are reproducible locally. CAP-02B's marker/fix and CAP-02C's retained consumed marker independently prove exhausted authority. CAP-02C's contemporaneous close records exact target output, conservative ambiguity, stopped-process recovery, and exact cleanup; deletion of its raw stream, result bytes, and private state makes those observations non-replayable. None proves containment against agent mistakes, hostile repository content, credential access, network egress, or unrelated-machine effects. |
| Provider/host boundary and trusted-local adapters | **PRV-01 H + I; CAP-02A/C R; CAP-02C live I/N** | The Codex/auth/data/network/retention/no-retry/cleanup selections are human records. Both live markers retain consumed bindings, not the deleted streams. CAP-02A/C supply reproducible coordinator/subprocess behavior but no CLI route. Every future real run needs a fresh boundary and activation. |
| Codex CLI adapter preparation | **R plus one consumed live ambiguity** | CAP-02C binds the resolved target, executable/probes/model/prompt/environment/argv, streams private output, cancels exact owned groups, preserves no-retry recovery, and phase-gates cleanup. Fake-process tests remain reproducible. The live exercise exposed a deprecated `web_search_request` flag; a red-green provider-free regression now omits it while retaining explicit `standalone_web_search` denial. The corrected argv has no second live proof. |
| One real trusted-local provider-owned run and medium pilot | **CAP-02B closed; CAP-02C consumed unknown-running; MS-02 open** | CAP-02B is historically closed with partial retained evidence. CAP-02C's marker independently proves activation `cap02c-live-20260806-02-4ybb2d` and its frozen bindings are consumed; its contemporaneous close records the exact target result, `unknown-running`, no retry, stopped-process decision, and abandoned cleanup, but the raw evidence is deleted. Product usability, a successful terminal corrected-adapter close, a pilot, CAP-03, milestone proof, and the human product check remain unproved. |

## Remaining unchecked dependency audit (EVA-02, revalidated after EVA-04)

This table covers every item intentionally left unchecked below. “Contingent”
means its trigger has not occurred; implementing it now would add unevidenced
machinery rather than proof. “External” means provider-free repository work
cannot supply the missing observation or decision.

| Unchecked claim | Current provider-free evidence | Exact remaining dependency |
|---|---|---|
| Scaled Sol High Rumble | Manual Direction intake accepts a what/why summary and persists no raw provider material. | **External model run:** a separately authorized scaled Rumble and its output-quality evidence. |
| Ultra synthesis with separate private reasoning | Direction/route authority sources are structurally separate; no synthesis run is retained. | **External model runs:** separately launched synthesis and challenge with controlled inputs. |
| Compact interaction view | No current shared-relationship ambiguity requires one. | **Contingent:** create only when an observed coordination hazard selects it. |
| Validation Slice contract | VAL-01 explicitly selected no Validation Slice for the current route. | **Contingent:** one decision-changing feasibility question and discard authority. |
| Disposable-code exclusion | No Validation Slice or disposable implementation exists in the permanent path. | **Contingent policy:** a selected future slice must prove discard/promotion handling; a universal framework now would violate DIR-06. |
| Independent Map Challenger | The current Map is structurally inspectable but has no retained independent model challenge. | **External model review:** fresh authority-equivalent challenge without shared private reasoning. |
| User-facing bug reproduction | Current recovery defects were reproduced through real fake-process boundaries, not a user-facing product journey. | **Contingent:** an actual user-facing bug and its end-to-end operator reproduction. |
| Working-model freedom inside a contract | CAP-02B and CAP-02C each have one consumed non-replayable record; CAP-02C's contemporaneous close records exact target output but not a terminal adapter close. | **Human product evidence**, plus a future fresh live proof only if the corrected adapter result remains decision-changing. |
| Failed-packet frontier lock | FS-01 records failure/recovery truthfully; no executable Map/frontier runtime exists. | **Pilot-selected Map behavior:** adding generic enforcement now would create the forbidden control plane. |
| High-cost mutation review | EVA-01 through EVA-04 and the implemented slices are local and reversible; no high-cost mutation is selected. | **Contingent human/recovery gate:** an actual irreversible or migration-bearing packet. |
| Milestone human product checks | MS-01 has its narrow recorded exception; MS-02 is explicitly open. | **Human:** the MS-02 product judgment, then future milestone checks when reached. |
| Proportional evidence across every lifecycle kind | Current implemented slices use claim-matched tests, structure, build/package, retained history, and explicit limits. | **Future lifecycle evidence:** unselected Validation, pilot milestone, and stabilization claims cannot be pre-proved. |
| Combining evidence classes only when needed | EVA-01 through EVA-04 classify current evidence without treating prose or provider output as proof. | **Future claim-specific judgment:** this is not a universally enforceable runtime property. |
| Recovery pressure across Packet/Map/Foundation/Direction | FS-01 and Direction recovery examples are executable; Map/Foundation pressure is not. | **Pilot evidence:** a real invalid premise at those broader layers. |
| Model-tier routing | No model router exists, consistent with manual invocation and DIR-06. | **External operating choice:** use the documented roles when an authorized model run is selected. |
| Normal First Mate conversation handoff | CONV-BRIDGE-01 reproducibly prepares a readable task, records one approval as distinct Direction/write authority, and stops at a non-executable `ready-for-preflight` Run Intent. | **Provider-free RUN-FACADE-01:** resolve target/route/preflight and expose one separate final Run confirmation; no live dispatch is required to build or test the facade. |
| MS-02 usability | Both live activations are consumed, CAP-02C closed conservatively, and the conversation-to-ready bridge is reproducible. | **RUN-FACADE-01 plus human product judgment**; a later terminal live proof remains a separate decision. |
| SBOX-01 | Only the non-downgrading sandbox contract exists. | **External environment and authority:** select and qualify a real sandbox mechanism. |
| Pilot target selection | No external target, Direction, data envelope, or pilot grant is selected. | **Human/external target:** MS-02 plus PILOT-SELECT-01 decisions and consent. |
| Pilot observations | No pilot has run. | **External pilot execution and observation.** |
| Pilot-scoped conclusions | No pilot observations exist to scope. | **External pilot evidence**, then a bounded conclusion. |

The two formerly broad provider-free items below are narrowed and checked:
the fixed FS-01 journey proves one small direct packet without Map/Foundation
runtime, and structural/runtime inspection proves the persistence set of the
implemented scope. After EVA-04, no other unchecked item is currently eligible
for a provider-free implementation without first receiving its named trigger.

## Authority and scope

- [x] **H** — The user chose narrow pre-Program consent with the recorded FS-01-only envelope.
- [x] **R** — Direction approval, route approval, and execution authority are represented as distinct states in the schemas and operator flow.
- [x] **H + R** — The human canonically adopted the reproducible FS-01 baseline and approved CAP-01 complete; no broader claim follows.
- [x] **H** — The 2026-08-03 docs-only packet and 2026-08-04 status reconciliation have separately scoped recorded consent; no broad or future consent is inferred.
- [x] **I + H** — Git retains basis `e46c6dc82df54e16ecd39d6ab826c6146d401739`; its recorded consent is limited to the four status documents.
- [x] **H** — The selected narrow envelope permits no new Validation or Foundation expansion; each later packet remains separately gated.
- [x] **R within the coordinator boundary** — FS-01 and trusted-local guards refuse mismatched authority. Unsandboxed executors are not technically contained after dispatch.
- [x] **R** — The current handwritten implementation-Python inventory is 7,885 lines excluding tests, within the 4,000–9,000 scope-pressure range. This rough count proves no broader readiness.
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
- [x] **H + I + N** — The separate CAP-02C live grant is exhausted. Its marker independently proves activation `cap02c-live-20260806-02-4ybb2d` and its frozen bindings remain consumed. The sanitized record preserves hashes and contemporaneous classifications for exact target output, stopped-process ambiguity, no retry, and exact abandoned cleanup, but deletion of the underlying raw lifecycle, result bytes, and private state makes those observations non-replayable rather than independently proved.
- [x] **H** — EVA-01 is authorized from clean `34dc2ae` for this evidence audit, bounded local repairs, documentation, verification, and local commits only; all live/provider/system/push boundaries remain closed.
- [x] **H + R** — EVA-02 is authorized from clean `196dbbc`; its target/recovery repairs and remaining-plan audit are reproducible provider-free, with all live/provider/system/push boundaries still closed.
- [x] **H + R** — EVA-03 was authorized from clean `ee32d05`; durable exact-cleanup recovery, adversarial refusals, and cancellation-drain descriptor ownership are reproducible provider-free, with all live/provider/system/push and broader-deletion boundaries still closed.
- [x] **H + R** — EVA-04 was authorized from clean `52db12f`; same-inode crash-safe cleanup records, bounded linear parsing, strict corruption refusal, and ambiguous-durability retry are reproducible provider-free, with all live/provider/system/push and broader-deletion boundaries still closed.
- [x] **H + R** — CONV-BRIDGE-01's standing local authority and exact design are recorded; its prepare/approve/status behavior, two durable non-execution records, exact retry, and provider-free refusals are reproducible. No run authority follows.

## Direction and routing

- [ ] Scaled Sol High Rumble produces a what/why-only candidate Direction Summary.
- [x] **R** — The exact approved Direction text is immutable and versioned on material change.
- [x] **R** — Direction intake persists neither raw Rumble material nor provider transcripts.
- [ ] Sol Ultra synthesis and a fresh independent challenge use the same authority sources without shared private reasoning.
- [x] **R** — The current route record stores a short reason without a score.
- [x] **R, fixed FS-01 scope** — One small isolated fixture packet executes directly without Map or Foundation runtime; arbitrary-work route classification remains unproved.
- [x] **R** — DIR-INTAKE-01 preserves separate approval/write authority, portable durable history, and the schema consumed by `draft`.
- [x] **R** — CONV-BRIDGE-01 turns a concise First Mate-derived task into a readable proposal and immutable approved Direction without persisting raw conversation or granting route/execution authority.

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
- [x] **S** — No execution packet is currently `ready`; CONV-BRIDGE-01 is complete and RUN-FACADE-01 is the detailed provider-free next boundary before the MS-02 human gate.
- [x] **R + S** — Runtime state and the Map keep route status distinct from binding Direction coverage.
- [x] **S** — The Map contains no full backlog, dependency graph, universal task schema, or Milestone Spine.

## Packet execution and close

- [x] **S** — No execution packet is currently `ready`; completed CONV-BRIDGE-01 has one bounded provider-free outcome, named red-green proof, adversarial refusal coverage, and explicit stop conditions.
- [x] **R + S, packet-scoped** — Executable preflight resolves the repository/instruction/basis fields it owns; EVA-02 inspected every remaining Program dependency, EVA-03 pressure-tested interrupted cleanup, and EVA-04 independently pressure-tested its persistence crash windows. This is not a universal automated preflight claim.
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
- [x] **R + S** — Current warnings-as-errors tests, lint, format, type, build, package, and smoke gates remain floors; dependency and test inspection finds no unrelated universal framework.
- [ ] Recovery chooses Packet, Map, Foundation, or Direction pressure at the smallest invalid premise; current records demonstrate examples but do not prove this generic process behavior.
- [ ] Major architecture and recovery work routes to Sol Ultra; ready implementation routes to Sol xhigh; trivial low-risk work may use Sol High.

## Runtime and pilot readiness

- [x] **R + S, implemented scope** — Current repository persistence is limited to approved Direction history and direct route/state/evidence/handoff/close records; trusted-local persistence is limited to its consumed marker and exact private artifacts outside repository authority. No Foundation review or Map runtime exists yet.
- [x] **R, implemented scope** — Direction/runtime code keeps raw provider material outside repository state and trusted-local artifacts in owner-private files. No claim is made that an unsandboxed executor cannot reach other private data.
- [x] **S** — Tracked files, imports, dependencies, and CLI inspection find no dashboard, mesh, score, generalized workflow control plane, RAG/code graph, or universal schema/test framework.
- [x] **R + S** — The implemented workflow is manually invoked and does not self-orchestrate.
- [x] **H + S** — TLX-01 records trusted-local unsandboxed assumptions and preserves SBOX-01 as a non-downgrading later path.
- [x] **H** — The selected POC policy is `provider-billing-controls-only`; CAP-02B's recorded boundary used the existing ChatGPT account without selecting an API billing project.
- [x] **H + I** — PRV-01 selected one exact proof-run boundary; the marker retains its provider digest and target bindings. The selection is exhausted and not reusable.
- [x] **R** — LIVE-BOUNDARY-01 reproducibly proves the offline activation/session/parser/ambiguity/evidence/cleanup contract; it proves no provider or real process.
- [x] **R** — CAP-02A reproducibly proves the injected offline adapter and failure paths while preserving FS-01; it makes no live claim.
- [x] **R** — Cleanup refuses active runs; `unknown-running` cleanup needs explicit `abandoned` recovery disposition and refuses while this adapter still owns the process. It validates the private directory, session, exact names, identities, and retained marker, then appends bounded digest-checked `cleanup-pending` and run-directory/private-root-bound authorization records to the same identity-recorded files before deleting only the three run files and empty directory. Fresh recovery accepts only the last complete valid record and an exact viable incomplete final frame, re-syncs visible cleanup authority before unlink, and then accepts only the identity-recorded remainder or same empty directory. Complete corruption, impossible/oversized lengths, missing authorization/intent/session, inode-reuse replacement, artifact replacement, and unexpected entries fail closed. Parsing is linearly bounded; cleanup never recurses or touches repository/system/provider data.
- [x] **I + N** — CAP-02B's marker and two-path fix are independently retained. Its real JSONL lifecycle, historical gate output, close document, and cleanup identities were deleted and are now non-replayable close records, not current proof. No outside-effects claim follows.
- [x] **R + I/N** — CAP-02C plus EVA-04 reproducibly prove resolved-root/current-revision qualification, memory-only inputs, capability-minimized argv, descriptor-bound fake dispatch, private streams, cancellation, no-retry recovery, and crash-safe exact cleanup. The consumed marker independently proves the live activation and frozen bindings are exhausted; the contemporaneous close records real transport, exact target output, conservative diagnostic handling, no retry, and cleanup, but the deleted raw artifacts make those observations non-replayable and do not establish a terminal close. The deprecated default-disabled flag is removed with a red-green fake-process regression; no CLI route or second live claim follows.
- [x] **R** — A normal First Mate conversation can submit an explicit proposed task, capture exact human Direction approval and distinct basis-bound ledger-promotion authority separately from route approval and Execution Consent, and receive a readable `ready-for-preflight` Run Intent without low-level activation or executable mechanics.
- [ ] RUN-FACADE-01 resolves the real target/current revision, shows the final effects/risk/verification preview, consumes separate one-shot Execution Consent, launches exactly once, independently verifies, handles ambiguity without duplicate dispatch, and offers review/optional separately authorized commit or merge without exposing low-level mechanics.
- [ ] MS-02 receives the human product check after that normal-use bridge is observable. Technical completion cannot manufacture this judgment or reuse either consumed activation.
- [ ] SBOX-01, when a trust/data/deployment need pulls it forward, proves filesystem, environment, credential, network, optional-capability, cancellation, and cleanup containment in the actual environment and fails closed without automatic trusted-local downgrade.
- [ ] The pilot target is medium-sized, baseline-known, and rich enough to exercise Foundation choice, several packets, one meaningful milestone, and honest recovery if evidence demands it.
- [ ] Pilot observations cover Direction fidelity, decisive evidence, integration, closure, handoff, product progress, rework, missed outcomes, artifact burden, and human intervention.
- [ ] Pilot conclusions are scoped to observed evidence and do not claim universal superiority.
