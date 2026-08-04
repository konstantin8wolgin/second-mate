# Second Mate implementation and pilot readiness

Status: canonical readiness checklist; POL-01 is narrowly selected, the
verified FS-01 baseline is canonically adopted, CAP-01 and MS-01 are complete,
DIR-INTAKE-01 and CAP-02A are implemented and locally verified, and TLX-01
selects a trusted-local unsandboxed initial live mode without authorizing a run

This checklist records gates and observable readiness. It does not assign tasks, define a backlog, impose ordering beyond the workflow's authority gates, or recreate a Milestone Spine.

An unchecked item means the broader workflow or Program gate has not been
proved and accepted; it does not mean no supporting code exists. The local
FS-01 slice now supplies executable evidence for a narrow subset of the
Foundation, packet, safeguard, and persistence items. [PROGRAM.md](PROGRAM.md)
records that evidence and its limits. The human did not personally observe the
fixture CLI/output journey or supply a clarity or D-01-fit judgment; those
accepted residual uncertainties, the provider path, and pilot evidence must not
be inferred from a green fixture suite.

## Current evidence classification

The evidence classifications below apply to the current branch, the
2026-08-03 authority record, and the narrow 2026-08-04 status reconciliation.
They distinguish code or document existence from claim-fit proof; they do not
backdate the historical bootstrap.

| First-workflow requirement area | Classification | Current evidence or exact gap |
|---|---|---|
| D-01, route, and T-01/ENV-01 | **proved** | Explicit, separate human decisions are recorded in [PROGRAM.md](PROGRAM.md). |
| POL-01 selection, canonical FS-01 adoption, CAP-01, and recorded documentation consents | **proved** | The human selected the recorded narrow pre-Program envelope, canonically adopted verified FS-01 as the Foundation baseline, and approved CAP-01 complete. Each documentation consent fits only its recorded read-only basis and named files; the latest TLX-01 revision carries no runtime or external authority. |
| All future Execution Consent | **blocked on explicit human authority/product decision** | No broad or future consent exists. Every later mutating packet needs its own current read-only preflight and exactly fitting Execution Consent. |
| FS-01 deterministic local lifecycle and its stated invariants | **proved** | The implementation, fixture journey, refusal/recovery tests, and repository gates are recorded in [PROGRAM.md](PROGRAM.md) and [FS-01-OPERATOR.md](FS-01-OPERATOR.md). |
| MS-01: Foundation Slice close | **completed under one-time scoped acceptance** | The human accepted plan-conformant FS-01 completion without personally observing the fixture CLI/output journey and declined further FS-01 decision requests. This is not a human review, observation, clarity judgment, or D-01-fit proof; those remain accepted residual uncertainty. |
| Approved-Direction intake | **proved for the local manual intake boundary** | Current-HEAD implementation and [operator guidance](DIRECTION-OPERATOR.md) prove no-write preparation, separate exact approval/promotion authority, immutable D-01/D-02 history, shared mutation locking, drift/open-state/race refusal, marked-write recovery, clone-readable persistence, CLI inspection, and `draft` consumption. This proves neither automated Rumble nor provider work. |
| Trusted-local initial execution boundary | **offline coordinator contract proved; live activation remains blocked** | TLX-01 explicitly removes sandbox qualification from the near-term path while narrowing the claim. CAP-02A proves exact coordinator activation, ownership, session, ambiguity, independent-evidence, and cleanup behavior entirely offline; it provides no containment against agent mistakes, hostile repository content, credential access, network egress, or unrelated-machine effects. |
| Provider/host boundary and offline trusted-local adapter | **CAP-02A proved offline; real provider boundary remains blocked** | The spend policy is selected as no Second Mate token cap beyond unavoidable provider/billing controls. PRV-01 still lacks an authentication source, billing project, permitted data, intended provider/network effect, cancellation, exact-session continuation, retention, exact version, and later trusted-target class. CAP-02A proves only the mock/local control plane; sandbox proof is not its prerequisite. |
| One real trusted-local provider-owned run and medium pilot | **blocked on explicit human authority/product decision** | CAP-02B lacks a baseline-known trusted target/change, resolved provider/data/cost/retention choices, a production adapter, and a per-run unsandboxed activation record. The pilot additionally lacks its target/request, Direction/route, data authority, CAP-03 behavior, milestone proof, and human product check. |

## Authority and scope

- [x] The user has chosen narrow pre-Program consent with the recorded FS-01-only envelope.
- [x] Direction approval, route approval, and execution authority are represented as distinct states.
- [x] The human canonically adopted verified FS-01 as the Foundation baseline and approved CAP-01 complete; no broader claim follows.
- [x] The 2026-08-03 docs-only packet and the 2026-08-04 status reconciliation each have separately scoped Execution Consent based on their recorded read-only preflight; no broad or future consent may be inferred from either.
- [x] The 2026-08-04 reconciliation preflight basis is `e46c6dc82df54e16ecd39d6ab826c6146d401739`, and its latest-request consent authorizes only the four local status-document edits.
- [x] The selected narrow envelope permits no new Validation or Foundation mutation or expansion; each later packet remains separately gated.
- [x] The coordinator never authorizes external effects or irreversible actions outside current authority. Trusted-local mode explicitly does not claim that an unsandboxed executor is technically prevented from overreaching after dispatch.
- [x] The current handwritten implementation-Python inventory is 5,726 lines excluding tests, within the 4,000–9,000 scope-pressure range. This rough count does not establish broader readiness.
- [x] FirstMate and Knowless are sources or optional primitive providers only; Second Mate has no retrofit dependency on their workflow structures.
- [x] The unrelated nested `firstmate/` checkout is excluded only through the outer checkout's local `.git/info/exclude`; it is neither edited nor tracked, and the exclusion is not portable product state.
- [x] The 2026-08-04 roadmap-reconciliation request authorizes only that local boundary correction and edits to `PROGRAM.md` and this checklist; it authorizes no DIR-INTAKE implementation or external effect.
- [x] The human approved the exact test-first DIR-INTAKE-01 plan and separately authorized only its local shared-lock, Direction-history, CLI, documentation, and proof mutations; provider work, live execution, external effects, pushes, and commits remain excluded.
- [x] The human selected TLX-01: an explicitly unsandboxed trusted-local initial mode with broad machine-access limitations, preserved coordinator controls, a separate per-run activation gate, and SBOX-01 retained as deferred hardening. This design decision authorizes no provider or real run.
- [x] The TLX-01 documentation consent covers only the canonical workflow, Program, checklist, package index, and trusted-local operator contract; it authorizes no provider authentication/call, credential access, live target, system change, real dispatch, CAP-02 implementation, push, or commit.
- [x] The separate CAP-02A consent authorizes only test-first offline adapter source, tests, and fitting canonical documentation. It selects broad trusted-local execution authority, `provider-billing-controls-only` with no Second Mate token cap, and exact-private-artifact cleanup while excluding credentials, billing-project selection, providers, real processes/agents, system changes, live targets, CAP-02B, push, and commit.

## Direction and routing

- [ ] Scaled Sol High Rumble produces a what/why-only candidate Direction Summary.
- [x] The exact approved Direction text is immutable and versioned on material change.
- [x] Raw Rumble material and provider transcripts remain outside repository Direction authority; the implemented packet persists neither.
- [ ] Sol Ultra synthesis and a fresh independent challenge use the same authority sources without shared private reasoning.
- [x] Direct versus Foundation routing records a short evidence-based reason without a score.
- [ ] Small isolated work can stay direct without Map or Foundation ceremony.
- [x] DIR-INTAKE-01 ports only approved-Direction behavior onto current HEAD, preserves separate approval/write authority, keeps durable history portable, and emits the schema consumed by `draft`.

## Foundation readiness

- [ ] A compact interaction view is created only when shared relationships or dangerous unknowns warrant it.
- [ ] A Validation Slice, when selected, names one decision-changing question, realistic envelope, evidence, limits, and discard boundary.
- [ ] Disposable code cannot enter the permanent path merely because it works.
- [x] The Backbone states only evidenced concepts, ownership/lifecycle, invariants, compatibility, boundaries, and proof seams.
- [x] The canonically adopted FS-01 Foundation Slice exercises its stated representative fixture journey and meets the repository's permanent quality bar; it proves no live-provider or broader-workflow claim.
- [x] The Foundation evidence review separates proved, failed/uncertain, boundary, and future-route consequences.

## Delivery Map readiness

- [x] The Map links Direction to the candidate capability staircase, meaningful product milestones, evidence, and the next candidate frontier without treating it as execution authority.
- [ ] An independent Sol Ultra Challenger checks coverage, product meaning, Foundation fit, order, assumptions, proof, and packet breadth.
- [x] The human approved the initial Foundation route and its material trade-offs; this does not by itself approve the candidate post-FS-01 staircase or any later mutation.
- [x] The human approved the exact test-first DIR-INTAKE-01 plan before its separately authorized mutation.
- [ ] Only the next one or two `ready` packets carry detailed contracts.
- [x] Route status and binding Direction coverage remain distinct.
- [x] The Map is not a full backlog, dependency graph, universal task schema, or Milestone Spine.

## Packet execution and close

- [x] Every ready packet has one outcome, a coherent boundary, and claim-fit proof.
- [x] Preflight resolves repository state, instructions, dependencies, baseline behavior, existing failures, authority, and irreversible-change risk.
- [ ] User-facing bugs are reproduced end to end before the fix and replayed after it.
- [ ] The working model may plan, diagnose, implement, test, and iterate freely inside the contract.
- [x] Clean close replays the real affected interaction at the final revision.
- [x] Evidence, route/coverage status, residual uncertainty, pressure classification, and handoff are written in one recoverable transition.
- [x] A failed packet cannot unlock or detail new frontier work.

## Safeguards and evidence

- [ ] High-cost-to-reverse mutations trigger independent review, rollback/migration proof where applicable, and any required human authority.
- [ ] Each meaningful product milestone has one human product check, without packet-by-packet approval.
- [ ] Validation, Foundation, packets, milestones, and stabilization use evidence proportional to their claims.
- [ ] Executable, structural, end-to-end, manual, and human evidence are combined only when the claim needs them.
- [x] Existing repository quality gates remain floors; no giant universal early suite is introduced.
- [x] Recovery chooses Packet, Map, Foundation, or Direction pressure at the smallest invalid premise.
- [ ] Major architecture and recovery work routes to Sol Ultra; ready implementation routes to Sol xhigh; trivial low-risk work may use Sol High.

## Runtime and pilot readiness

- [ ] Persistence is limited to Direction, the route reason, applicable Foundation Backbone/review, Map, evidence/status, handoff, and the clean-close transaction.
- [x] Credentials, leases, transcripts, and disposable provider state remain outside project authority and are minimized and stored privately. Trusted-local mode does not claim they are technically unreachable to an unsandboxed executor.
- [x] No dashboard, mesh, numerical score, generalized control plane, RAG/code graph, giant schema, or universal template/test system is present without repeated pilot evidence.
- [x] Second Mate's first workflow is operated manually rather than self-orchestrated.
- [x] TLX-01 explicitly defines the initial mode as trusted-local and unsandboxed, narrows its evidence claim, records its machine/repository trust assumptions, and preserves SBOX-01 as a later non-downgrading path.
- [x] The POC spend policy is `provider-billing-controls-only`: Second Mate imposes no token-spend cap, while provider/billing controls remain unavoidable and a billing project is still required before any real run.
- [ ] PRV-01 selects exactly one provider/host and its authentication source, billing project, permitted data, intended provider/network effect, cancellation, unknown-running, exact-session continuation, retention, exact version, and later trusted-target class.
- [x] LIVE-BOUNDARY-01 proves offline one explicit trusted-local activation boundary, private session binding, strict bounded event parsing, unknown-running recovery, provider-independent target-evidence requirement, exact unsandboxed activation record, and identity-bound cleanup limited to exact private run artifacts. It does not prove a live process or provider.
- [x] CAP-02A proves one concrete trusted-local adapter entirely offline over an injected mock control plane with interruption/failure injection while preserving FS-01 unchanged; it makes no sandbox, credential, provider, live-process, or provider-call claim.
- [x] Recovery cleanup validates the dedicated private run directory, durable session record, exact filename set, recorded artifact identities, and retained one-shot activation marker before deleting only `session.json`, `transcript.jsonl`, `control.tmp`, and the empty run directory; it never deletes the marker, makes authority reusable, recurses, or touches repository/system/provider-side data.
- [ ] CAP-02B receives separate provider/data/cost/retention authority plus per-run trusted-local risk acknowledgment and proves one real direct run without trusting provider output as completion evidence or claiming absence of outside-machine effects.
- [ ] SBOX-01, when a trust/data/deployment need pulls it forward, proves filesystem, environment, credential, network, optional-capability, cancellation, and cleanup containment in the actual environment and fails closed without automatic trusted-local downgrade.
- [ ] The pilot target is medium-sized, baseline-known, and rich enough to exercise Foundation choice, several packets, one meaningful milestone, and honest recovery if evidence demands it.
- [ ] Pilot observations cover Direction fidelity, decisive evidence, integration, closure, handoff, product progress, rework, missed outcomes, artifact burden, and human intervention.
- [ ] Pilot conclusions are scoped to observed evidence and do not claim universal superiority.
