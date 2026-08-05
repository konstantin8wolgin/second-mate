# Second Mate workflow specification

Status: canonical design; POL-01 narrowly selected and FS-01 canonically
adopted as the Foundation baseline; CAP-01, MS-01, and DIR-INTAKE-01 are
complete, with MS-01 closed only under the 2026-08-04 one-time scoped
acceptance
Date: 2026-08-03

The implementation currently exercises manual approved-Direction intake and
one supervised, fixture-based direct packet. Its evidence does not prove
automated Rumble, a live provider path, or the broader workflow. The human
separately approved D-01, the documented Foundation route, Python 3.12 and
ENV-01, selected narrow pre-Program POL-01, canonically adopted the verified
FS-01 baseline, and later approved and authorized the bounded DIR-INTAKE-01
packet. This resolves no broad or future Execution Consent; the exact narrow
envelopes and remaining limits are in [PROGRAM.md](PROGRAM.md).

## 1. Direction basis

Second Mate coordinates a software change from human intent to verified delivery with the least structure that keeps meaning, evidence, and continuation honest.

Its priorities, in order, are:

1. preserve human meaning and explicit authority;
2. maintain evidence-based technical truth;
3. give the working model autonomy inside a compact outcome boundary;
4. produce coherent, integrated product progress rather than activity;
5. keep artifacts, approvals, and runtime machinery lean; and
6. leave durable continuation state when a run or session ends.

Quality references are the proportional Rumble/Direction discipline and the useful Validation, Foundation, and Living Delivery distinctions in the temporary Foundation-First reference. Those references are inputs, not authority. Existing execution primitives may be reused only when they fit this design cleanly; Second Mate is not a FirstMate retrofit.

Failure signals are Direction drift, premature implementation, plausible-but-unproved completion, hidden remaining work, repeated human escalation for ordinary engineering, unnecessary maps or agents, Foundation churn caused by local failures, stale detailed backlogs, and coordinator machinery becoming the product.

## 2. Lifecycle and authority

The normal lifecycle is:

1. scaled Rumble;
2. exact human approval of a Direction Summary;
3. Ultra synthesis and independent challenge;
4. selection of the direct route or the Foundation route;
5. resolution and recording of the applicable execution authority before the first mutation;
6. an approved Living Delivery Map for substantial work;
7. execution of only the next one or two ready packets;
8. evidence/status writeback and pressure classification at clean close;
9. one human product check at each meaningful product milestone; and
10. stabilization and completion evidence matched to the final claim.

The lifecycle is adaptive. Small, isolated work may go from approved Direction directly to one packet. Substantial work uses only the Foundation and Delivery artifacts that resolve a concrete uncertainty or continuity risk.

Three approvals have different meanings:

- **Direction approval** confirms the exact what and why. It authorizes neither implementation nor external effects.
- **Delivery Map approval** accepts a revisable route theory and material trade-offs. It is not packet-by-packet approval and is not Execution Consent unless the chosen consent policy explicitly makes it part of that decision.
- **Execution Consent** permits named mutations and effects inside a stated packet or route boundary. An earlier explicit grant in the user's request may supply it only when its scope still exactly fits the approved Direction and current route; otherwise obtain a fresh grant. Record it as a distinct authority state even when it shares a human interaction with route approval. It cannot be inferred from silence, planning activity, Direction approval, or a persistence instruction to finish the project.

### Pre-Program consent policy

Every program must select one of these controls before canonically adopting
existing Validation or Foundation slice evidence as a Foundation baseline, or
before any new Validation or Foundation mutation or expansion. The presence of
FS-01 code alone is historical evidence, not a convenient default:

1. **Narrow pre-Program consent.** A written consent names the dangerous question, code/data/infrastructure boundary, resource and side-effect limits, discard policy, and at most one permanent Foundation Slice. Material learning that changes the permanent boundary requires refreshed consent. Expansion still waits for full Execution Consent.
2. **Full-Program-first control.** Before the complete Program and Execution Consent, only non-mutating inspection, research, modeling, and challenge are allowed. Validation and Foundation execution occur afterward.

The current Second Mate record selects narrow pre-Program consent. Its exact
dangerous question is whether the existing fixture-only FS-01 is sufficient as
Second Mate's permanent authority, evidence, and recovery foundation. Its
boundary is the clean checkout, existing Python FS-01 implementation and tests,
and checked-in fixture; its resources are local Python 3.12, Git, filesystem,
CPU, and disk; it permits no network, credentials, provider, external target,
or external commitment; disposable run state is discarded and at most the
existing FS-01 Foundation Slice is retained. On that basis the human
canonically adopted verified FS-01 and approved CAP-01 complete. The selection
cannot retroactively establish the missing bootstrap authority record, and it
does not create broad or future Execution Consent; see [PROGRAM.md](PROGRAM.md)
for the current decisions and limits.

For this policy decision, a **complete Second Mate Program** means the approved Direction, grounded route decision, non-mutating Backbone and planned Foundation Slice boundary when applicable, revised and human-approved Living Delivery Map, and the outcome, proof, risk, and authority boundaries needed for the first execution. It does not silently import a Metric Charter, Implementation Atlas, Program Landmarks, or any other artifact from the noncanonical reference; add a project-specific artifact only when the approved Direction or completion claim genuinely requires it.

Under narrow pre-Program consent, only the named Validation/Foundation envelope
may authorize its canonical adoption or execution before the complete Program;
expansion still requires Execution Consent over the approved Map. Under
full-Program-first control, the initial Map uses non-mutating evidence and
marks unavailable Foundation evidence `uncertain` or `blocked`; the complete
Program and exactly fitting Execution Consent precede canonical adoption or
Validation/Foundation execution, and material Foundation evidence must revise
and, when needed, re-challenge the Map before expansion.

The 2026-08-03 docs-only packet had its own scoped Execution Consent based on
its recorded current read-only preflight. It changed only the four authorized
canonical documents and authorized neither a later packet nor any runtime
mutation or expansion. At that time, MS-01 was blocked on the human
operator/product check; binding Direction coverage remained `still_remaining`.

On 2026-08-04, read-only preflight recorded repository basis
`e46c6dc82df54e16ecd39d6ab826c6146d401739`. The latest request supplies
Execution Consent only for local status-document edits to `README.md`, this
specification, `PROGRAM.md`, and `implementation-checklist.md`. The human
accepted plan-conformant FS-01 completion without personally observing the
fixture CLI/output journey and declined further FS-01 decision requests. For
MS-01 only, that one-time scoped acceptance replaces the former
personal-observation gate and completes MS-01. It records no human review,
observation, CLI/output-clarity judgment, or D-01-fit proof; those unobserved
qualities remain accepted residual uncertainty. The fixed FS-01 first workflow
is terminal with no further user decision. This exception does not amend the
general milestone human-product-review rule below, widen technical evidence,
or change binding Direction coverage from `still_remaining`; all later provider,
credentials, CAP-02 onward, pilot, Rumble, push, publication, deployment, and
external work remain separately unauthorized future scope.

The later 2026-08-04 DIR-INTAKE-01 request separately approved its exact
test-first plan and authorized only local shared mutation coordination,
portable immutable Direction history, separate preparation/approval/promotion
authority, CLI prepare/promote/show, operator documentation, and end-to-end
handoff into `draft`. It authorized no provider work, live execution, external
effect, push, or commit. The resulting implementation is described in
[DIRECTION-OPERATOR.md](DIRECTION-OPERATOR.md); its completion unlocks only the
separate PRV-01 decision/evidence gate.

The later 2026-08-04 trusted-local decision changes the near-term live-runtime
boundary without rewriting those earlier records. The initial local execution
mode does not require a sandbox. It is permitted only as an explicitly
activated **trusted-local** mode on a human-selected machine, operating-system
account, repository, and worktree. Sandboxed execution remains a distinct
later hardening or deployment path. This decision is design authority for the
mode and for this documentation revision; it is not authority to authenticate,
use a provider, select or mutate a live target, or dispatch an agent.

## 3. Scaled Rumble and Direction

Rumble runs on Sol at high reasoning effort. It accepts nonlinear input and scales to the request:

- a clear bounded change receives a few natural lines and zero questions when no consequential ambiguity remains;
- broader or conflicting intent receives only questions whose plausible answers could change product meaning, priority, scope, a failure signal, or an authority class; and
- technical discovery questions wait until after Direction unless their answer changes what the user is asking for.

Direction-bearing statements may be marked **binding**, **preferred**, **exploratory**, or **rejected** when the distinction matters. Rejected ideas remain visible as boundaries or anti-examples; they are not silently promoted or forgotten.

The Direction Summary contains only applicable what/why information:

- context, purpose, and desired outcome;
- priority among competing outcomes or qualities;
- desired behavior and product capabilities;
- examples, references, and meaningful language to preserve;
- in-scope and non-goal boundaries;
- accepted constraints and trade-offs;
- observable success and failure signals; and
- explicitly deferred product decisions.

It contains no architecture, APIs, files, schemas, libraries, model routing, tasks, owners, estimates, test mechanics, or technical sequence. A technical suggestion is restated as the outcome, constraint, trade-off, or quality reference it protects.

The human approves the exact text shown. Approved versions are immutable; a material meaning change creates a new version and a short change note. Raw Rumble transcripts and scratch reasoning are not repository authority.

## 4. Ultra synthesis, challenge, and route choice

After Direction approval, an Ultra synthesis grounds the request in current repository evidence and proposes the lightest honest route. A fresh Ultra Challenger receives the same authoritative inputs and proposed result, but not the synthesizer's private reasoning or persuasive transcript. It checks Direction coverage, factual support, hidden coupling, hard-to-reverse choices, proof gaps, and avoidable process.

The synthesizer adopts justified corrections, revises the proposal, and records any concrete disagreement. Reviewer agreement or objection count is not evidence.

The resulting route decision is one of:

- **Direct route:** existing concepts and boundaries can carry a small, isolated, low-coupling outcome through one coherent verified run.
- **Foundation route:** substantial or uncertain work introduces shared concepts, state ownership, lifecycle, compatibility, trust, or integration assumptions that later capabilities could otherwise reinterpret independently.

Record the choice and one-line evidence-based reason. Route choice is revisable when evidence changes; it is not a numerical risk score.

## 5. Direct route

The direct route has no artificial Backbone document, Delivery Map, milestone graph, or separate planning gate. It uses:

1. the approved Direction slice;
2. baseline preflight;
3. one compact outcome/boundary/proof packet;
4. resolved and recorded Execution Consent for that packet boundary;
5. one coherent implementation run with internal iteration; and
6. claim-fit close replay plus evidence and handoff writeback.

A trivial, low-risk fix uses Sol High. A nontrivial ready packet uses Sol xhigh. If the run exposes shared durable assumptions, hidden dependencies, or a route that no longer fits one coherent close, classify the pressure and move to the Foundation or Delivery path instead of stretching the packet.

## 6. Foundation route

Foundation means the minimum durable concepts and boundaries several later capabilities must share. It is not a platform layer or a synonym for project size.

### Foundation decision and interaction view

Classify the need as **no new foundation**, **extension foundation**, or **new foundation**. For extension or new Foundation work, create only the compact relationship view needed to expose actors, shared state, ownership, lifecycle, invariants, compatibility, failure/change scenarios, and dangerous unknowns. This view may be a paragraph or table; it is not a mandatory graph, schema catalog, or standalone file.

Stop expanding the view once remaining unknowns cannot plausibly change the validation choice, materially rewrite the Backbone, violate Direction, or make planned capabilities incompatible.

### Optional Validation Slice

A Validation Slice answers one dangerous unknown that could change the durable design. It records:

- the exact question and decision it can change;
- the minimum realistic interaction or scale needed;
- the observation that would support, contradict, or leave the premise open;
- strict code, data, infrastructure, time, resource, and side-effect boundaries;
- the discard boundary; and
- returned evidence and residual uncertainty.

Use no separate slice when current evidence already answers the question or when the permanent Foundation Slice is the cheapest faithful test. Disposable code is discarded by default. Reuse requires independent proof that it meets the permanent Backbone and repository quality bar; “it already works” is not evidence of durability.

### Foundation Backbone

The Backbone is the smallest evidence-informed durable design commitment. It names only:

- stable concepts and relationships;
- ownership and lifecycle of important state;
- invariants and compatibility obligations;
- capability boundaries for observed or Direction-required variation;
- proof and observability seams; and
- intentionally variable decisions plus evidence that would reopen them.

It must not generalize from one probe into speculative framework machinery. Proceed when no known uncertainty can plausibly force a material rewrite of the first permanent slice's stable contracts or violate its applicable Direction.

### Permanent Foundation Slice

The Foundation Slice is the first permanent, representative implementation of the Backbone. It carries one real user or external-system journey through the actual product, exercises the important state and compatibility boundaries, meets the repository's permanent quality bar, and exposes enough evidence to diagnose false success.

It proves only the exercised journey and named invariants at an exact revision. It does not prove unbuilt expansion or complete the product by implication.

### Foundation evidence review

At the slice revision, record four compact results:

1. what the evidence proves;
2. what failed, was not exercised, or remains uncertain;
3. which Backbone boundary held or needs an explicitly authorized change; and
4. how the evidence changes future capabilities, proof, or route assumptions.

This evidence informs the Program and Living Delivery Map. It is not a retrospective essay or automatic authority to continue.

## 7. Living Delivery Map

Substantial work receives a Living Delivery Map: a durable, revisable theory from stable Direction to observable capabilities, meaningful product milestones, the ready frontier, and evidence. It is not a complete backlog, universal dependency graph, task decomposition, or Milestone Spine.

An Ultra planner proposes the Map from approved Direction, current repository evidence, the Foundation boundary and evidence when applicable, and accepted architectural constraints. A fresh Ultra Challenger receives the same sources and candidate Map without planner reasoning. It checks:

- coverage of binding outcomes, boundaries, examples, and failure signals;
- whether milestones are meaningful integrated product or learning states;
- Foundation compatibility and evidence limits;
- hidden dependencies, unsafe order, and missing integration paths;
- assumptions presented as facts;
- claim-fit milestone proof; and
- packet candidates too broad for one coherent close.

The planner applies justified corrections. The human then approves the capability order, meaningful milestones, deferred scope, and material route trade-offs. One Challenger pass is normal; repeat only after a material contradiction caused a substantial revision.

The Map stores only:

- its Direction and Foundation evidence basis;
- capabilities and mapped binding Direction items;
- meaningful milestones and observable proof;
- actual dependencies, high-impact unknowns, and Foundation touchpoints;
- candidate packets, with full detail only for the next one or two ready packets;
- evidence references and statuses; and
- short evidence-driven revision notes.

Route status is one of:

| Status | Meaning |
|---|---|
| `candidate` | Plausible future route item; deliberately not detailed or ready. |
| `ready` | Authority, dependencies, current evidence, and one coherent close are present. |
| `blocked` | A named decision, dependency, authority, access, or external condition prevents execution. |
| `uncertain` | A consequential premise remains unresolved and must not masquerade as ready. |
| `completed` | The stated outcome has claim-fit evidence and clean-close writeback. |
| `invalidated` | Evidence or an authorized change disproved the item; retain its reason and successor if any. |

Binding Direction coverage is tracked separately as `proven`, `explicitly deferred`, `intentionally changed`, or `still_remaining`. A completed packet does not by itself prove its broader Direction item. Relevant completion is blocked while a binding item remains `still_remaining`.

## 8. Packet contract and run

A ready packet is one coherent verified agent run. It may plan, inspect, implement, debug, test, review, and iterate internally. “One run” does not mean one model attempt or a fixed time box.

Its mandatory contract is compact:

- **Outcome:** the single observable, integrated state the run must leave true.
- **Boundary:** applicable Direction and Foundation constraints, dependencies, in-scope work, and named non-scope.
- **Proof:** the executable, structural, end-to-end, manual, or human observations that distinguish completion from plausible output.

Add an unlock or exact artifact/revision reference only when it materially helps continuation. Do not turn the packet into a universal schema or prescribe the implementer's internal plan.

### Baseline preflight

Before mutation, the run:

1. resolves the exact repository state, local instructions, and authority boundary;
2. confirms dependencies and that the packet is still ready;
3. replays the smallest affected baseline or user journey that makes the later claim interpretable;
4. records or repairs pre-existing failures rather than normalizing them; and
5. evaluates the irreversible-change trigger before any high-cost-to-reverse action.

For a user-facing bug, preflight reproduces the failure end to end as the user encounters it as closely as practical. The fix preserves that reproduction as regression evidence at close.

### Implementation autonomy

Ready packet implementation normally uses Sol xhigh; a truly trivial low-risk direct fix may use Sol High. The agent owns technical tactics, internal decomposition, diagnosis, and iteration inside the contract. It may not weaken the outcome, proof, tests, safeguards, or authority to manufacture closure.

### Claim-fit clean close

At the exact final revision, replay the affected baseline and the packet's real interaction from a clean enough state to test the claim. Run the targeted automated and structural checks the claim requires, inspect resulting behavior or artifacts, and retain any required manual or human evidence.

Clean close is one durable transition that writes together:

- resulting route and Direction-coverage statuses;
- evidence references and exact revision when material;
- residual uncertainty or invalidated assumptions;
- the recovery-pressure classification; and
- a compact handoff that makes the next ready frontier reconstructible.

Only a `completed` clean close, or an explicit recovery decision recorded after another status, may promote or detail the next one or two packets. Narrative confidence, a diff, or a green local unit test alone is not closure.

## 9. Recovery classification

After material failure or surprising evidence, classify the smallest premise that is wrong:

| Pressure | Test | Response |
|---|---|---|
| **Packet** | The outcome remains valid; implementation, bounded scope, or proof was wrong. | Diagnose, repair, split, or retry without replanning the project. |
| **Map** | Direction and Foundation hold, but order, dependency, milestone, or remaining route is wrong. | Revise only the affected Map and preserve accepted evidence. |
| **Foundation** | Cross-packet evidence conflicts with a Backbone concept, owner, lifecycle, invariant, compatibility, or extension boundary. | Pause dependent work, run an Ultra recovery review, and obtain required authority for a Foundation change. |
| **Direction pressure** | Evidence contradicts or makes incompatible a binding human requirement. | Pause dependent work, present evidence and consequences, and let the human preserve or version Direction. Independent work may continue. |

Ordinary technical difficulty is not a human decision. Major architecture or recovery synthesis uses Ultra. Route changes alone do not reopen Foundation, and a local packet failure does not become Direction pressure for convenience.

## 10. Hard safeguards

### Irreversible-change trigger

Trigger stronger review before a mutation that can destroy or irreversibly transform user data, change public compatibility or security boundaries, alter access/billing/legal commitments, publish or deploy externally, or cannot be cheaply and faithfully rolled back.

The triggered packet requires an independent review, explicit migration or rollback evidence where applicable, a stronger claim-fit replay, and human approval whenever the action exceeds already delegated authority. The trigger is categorical and evidence-based, not a numerical risk score.

### Milestone human product review

Each meaningful product milestone has one human product check against the approved Direction, actual integrated behavior, and material failure signals. This is not approval for every packet, commit, or test result. Technical evidence remains necessary; human satisfaction does not make technical claims true.

## 11. Evidence and testing posture

Evidence grows with the claim. There is no giant early suite or universal proof template.

| Stage | Claim | Fit-for-claim evidence |
|---|---|---|
| Direction and design | Meaning is faithfully captured; route assumptions are explicit. | Human approval, source references, scenario/contradiction challenge. No code claim. |
| Validation Slice | One dangerous premise is supported, contradicted, or unresolved within a stated envelope. | Lightest faithful diagnostic, benchmark, simulation, rehearsal, integration probe, or manual observation. |
| Foundation Slice | One permanent representative journey and named invariants work at an exact revision. | Real end-to-end replay, targeted executable and structural checks, compatibility evidence, diagnostic/manual evidence where automation is insufficient. |
| Packet | One bounded integrated outcome is complete. | Targeted tests and static/structural checks plus the real affected interaction; user-facing bug reproduction when applicable. |
| Milestone | An integrated human-meaningful capability or learning plateau is real. | Cross-packet end-to-end evidence, material failure-path checks, independent review when leverage warrants it, and one human product check. |
| Stabilization and completion | The release/completion claim survives relevant breadth and failure conditions. | Project-mandated full suite, cross-cutting integration and regression checks, applicable security/performance/migration/rollback evidence, manual or human proof for subjective behavior, and final claim-fit replay. |

Evidence categories are complementary:

- **executable:** tests, builds, linters, benchmarks, migration rehearsals, and diagnostics;
- **structural:** static invariants, contracts, dependency boundaries, schemas, and artifact inspection;
- **end to end:** the actual user or external-system path across real integration boundaries;
- **manual:** observed behavior that current automation cannot establish faithfully; and
- **human:** product meaning, usability, and accepted trade-offs at the milestone leverage point.

Existing repository quality gates remain floors. A disposable Validation Slice avoids unrelated hardening, but permanent code never uses “still learning” to bypass the repository's standards.

## 12. Minimal runtime and persistence boundary

The first implementation supports only the state required to survive a clean handoff:

- immutable approved Direction versions;
- the recorded route decision and reason;
- the Foundation Backbone and Foundation evidence review when the Foundation route is used;
- one current Living Delivery Map when the direct route is insufficient;
- packet outcome/boundary/proof plus evidence and status writeback;
- a compact handoff with repository revision, unresolved pressure, and next ready frontier; and
- one atomic or recoverable clean-close transition that updates evidence, status, and handoff together.

Accepted product meaning and shareable delivery state live in the target repository. Credentials, raw Rumble material, provider transcripts, leases, and disposable runtime state stay local and private. Provider-native continuation is an accelerator, not authority.

### Initial trusted-local execution mode

The first live execution mode is **trusted-local**. It deliberately makes no
technical-containment claim. The coding-agent process and any repository code
it invokes may read, modify, delete, or transmit anything available to the
selected operating-system account, including unrelated files, credentials,
local services, and network destinations. Environment filtering, disabled
optional capabilities, a clean worktree, and operator supervision reduce
ordinary exposure but do not turn this mode into a sandbox. It is unsuitable
for hostile or materially untrusted repository content.

The guarantees that survive in this mode are coordinator guarantees:

- exact approved Direction, packet, read-only preflight, and separately scoped
  Execution Consent remain prerequisites to dispatch;
- one durable owner and one exact provider session identity prevent automatic
  duplicate execution;
- interruption, lost output, ambiguous exit, or uncertain provider state
  becomes `unknown-running`, never an inferred failure or automatic retry;
- provider transcripts, credentials, session state, and private reasoning stay
  outside repository authority;
- changed paths, final revision, tests, and claim-fit evidence are verified
  independently of the provider's report; and
- clean close remains atomic or recoverable and never widens evidence beyond
  what was observed.

Those guarantees do **not** prove that the executor stayed inside the grant.
Target-repository inspection cannot prove the absence of writes elsewhere on
the machine, credential access, network egress, remote effects, or destructive
commands that leave no target diff. Trusted-local evidence therefore proves
only coordinator ordering, recorded authority, observed target state, and
recovery behavior. It cannot by itself prove adversarial containment, complete
DIR-02 enforcement after dispatch, provider security, or absence of outside
effects. Binding Direction coverage remains `still_remaining` until evidence
fits the stronger claim or the human versions Direction explicitly.

The following controls remain non-negotiable even though containment is not:

1. A human must designate the machine/account and repository as trusted for the
   exact run, confirm a recoverable target baseline, and acknowledge that the
   agent may reach the account's broader files, credentials, services, and
   network.
2. The run must not execute as root or with an intentionally exposed privilege
   escalation path. Secrets and optional execution surfaces are minimized:
   do not deliberately forward credentials to model-generated commands, and
   keep hooks, MCP servers, plugins, apps, browser/computer control, and
   subagents disabled unless separately named in the grant.
3. Authentication source, billing project, permitted repository data, intended
   network/provider effect, spend policy, transcript retention, exact CLI
   version, target revision, allowed target changes, stop conditions,
   cancellation, and `unknown-running` recovery must be resolved before
   activation. The initial proof-of-concept spend policy is
   `provider-billing-controls-only`: Second Mate adds no token-spend cap of its
   own and cannot bypass or promise away provider or billing controls.
4. Authority or revision mismatch fails closed. Cancellation never transfers
   ownership, and recovery never resumes or redispatches without an exact
   session identity plus an explicit human recovery decision.
5. A real run requires a separate activation record that explicitly says it is
   unsandboxed trusted-local execution. Approval of this design, a provider
   choice, Direction, a Map, or a packet alone is not activation consent.
6. Recovery cleanup is limited to exact private session, transcript, and
   temporary control artifacts that the run created and identity-recorded in
   its dedicated private directory. It must refuse unexpected or replaced
   entries and must never recursively delete, follow provider-supplied paths,
   alter repository work, remove arbitrary system files, or claim to delete
   provider-side data.

The activation record is defined operationally in
[TRUSTED-LOCAL-OPERATOR.md](TRUSTED-LOCAL-OPERATOR.md).

CAP-02A now exercises these coordinator-side activation, session, event,
ambiguity, evidence, and cleanup rules entirely offline over an injected mock
control plane. CAP-02C additionally provides a dormant library-only Codex CLI
subprocess boundary: exact binary/probe/prompt/environment/argv qualification,
private JSONL and stderr handling, Linux process identity, owned process-group
cancellation, and restart-to-unknown behavior are proved against temporary fake
executables. The package still contains no trusted-local CLI dispatch route,
and CAP-02C made no provider call or real-target claim. Neither proof satisfies
a current provider, target, human-usability, or per-run activation gate; every
real use still needs a fresh exact boundary and separately scoped activation.

### Deferred sandboxed execution path

Sandboxed execution remains a later hardening or deployment capability, not a
prerequisite for the first trusted-local adapter or real supervised run. It
must preserve the coordinator guarantees above and additionally prove its
effective filesystem, credential, environment, network, optional-capability,
cancellation, and cleanup boundaries in the actual operator environment. A
sandbox startup failure must fail closed and must never silently downgrade to
trusted-local mode. Selecting that later path creates a new bounded packet and
claim; it does not retroactively make trusted-local evidence containment proof.

The initial coordinator should be roughly 4,000–9,000 lines of handwritten implementation code, excluding tests, generated files, and design/reference documents. This is a scope-pressure heuristic, not a quality target or estimate; exceeding it requires a concrete pilot-derived need.

The first runtime may be a small CLI or library. It does not include a dashboard, agent mesh, numerical scoring, generalized workflow engine, RAG/code graph, mandatory giant schema, universal packet template, or universal test harness. It coordinates one provider-owned run at a time unless a later pilot proves a repeated need for more.

## 13. Model routing

| Work | Default route |
|---|---|
| Scaled Rumble and ordinary grilling | Sol High |
| Post-Direction route synthesis/challenge; Foundation design/review; Delivery Map planner/Challenger; major architecture or recovery | Sol Ultra |
| Ready packet implementation | Sol xhigh |
| Trivial, isolated, low-risk fix | Sol High |

Routing follows the work's consequence and ambiguity, not prestige. A forced fallback is recorded with its reason; it must not silently reduce required challenge or proof.

## 14. Medium pilot protocol

The first pilot is manual. It does not use Second Mate to implement or coordinate Second Mate itself.

Prerequisites are a candidate request suitable for Direction shaping, an explicit choice of the pre-Program consent policy, a target repository with a known baseline, and a medium-sized change with shared state or integration uncertainty. The change should be large enough to exercise a Foundation decision, several packets, at least one meaningful product milestone, and an evidence-driven Map revision if reality warrants one.

Run the pilot as follows:

1. conduct scaled Rumble and obtain exact Direction approval;
2. run Ultra synthesis/challenge and select the route;
3. apply the chosen pre-Program control and resolve or obtain the applicable Execution Consent before its first mutation;
4. if warranted, perform the bounded Validation, Backbone, permanent Foundation Slice, and evidence review;
5. plan/challenge/revise the Living Delivery Map and obtain human route approval;
6. execute and clean-close only the next one or two ready packets at a time under the recorded authority;
7. perform the milestone human product check;
8. classify surprises at the smallest pressure layer and revise only that layer; and
9. stabilize against the final claim.

Record whether the workflow improved Direction fidelity, time to decisive evidence, integration quality, clean closure, handoff continuity, and coherent product progress. Also record duplicated implementation, missed binding outcomes, artifact/review burden, avoidable human intervention, and any coordinator mechanism that failed to earn its cost.

Pilot success authorizes learning and a next comparison, not claims of universal superiority. Add automation, roles, persistence fields, or coordination topology only after a repeated observed failure demonstrates the need.
