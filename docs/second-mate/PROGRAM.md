# Second Mate bootstrap Program

Status: challenged candidate Program; human decisions and execution blocked

Date: 2026-08-02

This is the implementation Program for building Second Mate itself. It applies
the canonical [workflow specification](workflow-spec.md) and
[readiness checklist](implementation-checklist.md) without changing either.
The [Foundation-First reference](../placeholder/foundation-first/foundation-first-delivery-design.md)
is context only, as described by the [canonical package index](README.md).

The Program deliberately stops at one permanent Foundation Slice and one
detailed frontier packet. It is not permission to implement, publish, deploy,
or use external services.

## 1. Authority and current readiness

The user's latest explicit instructions and the canonical Second Mate package
are the authority sources. No runtime exists, no code experiment has run, and
no implementation evidence exists.

The Program is complete enough for challenge and human decision, but it is not
yet a canonical complete Program or `planning-ready`. A packet cannot have
canonical route status `ready` while required authority is absent, so the one
frontier packet below is contract-complete but remains `blocked`. Calling it
ready now would contradict the workflow.

Before any runtime mutation, the human must:

1. approve the exact Direction in section 2;
2. choose the product consent policy in decision POL-01;
3. choose the initial runtime/toolchain in decision T-01;
4. approve the revised route represented by this Program; and
5. after a fresh non-mutating preflight, grant Execution Consent for the exact
   packet, repository revision, paths, resources, and effects.

Direction approval, route approval, and Execution Consent remain distinct even
if the human supplies them in one response.

For Second Mate's own bootstrap, only inspection and planning have occurred.
That observed non-mutation is not a consent-policy choice. POL-01 still requires
an explicit human decision before any Validation or Foundation code is written;
the human may choose full-Program-first specifically for this bootstrap.

## 2. Candidate Direction D-01

- **DIR-01 — Purpose (binding):** Build Second Mate as a lean coordinator that
  carries a human-approved software outcome into coherent AI coding work while
  keeping authority, evidence, and continuation honest.
- **DIR-02 — Human authority (binding):** Preserve exact human meaning and
  prevent work outside explicit human authority. Planning or silence must never
  be treated as permission.
- **DIR-03 — Working autonomy (binding):** Give a capable working model freedom
  to solve the technical problem inside a small, agreed outcome boundary rather
  than replacing its judgment with coordinator policy.
- **DIR-04 — Truthful completion (binding):** Distinguish plausible output from
  proved progress and leave durable continuation state that a fresh capable
  model can understand without private reasoning.
- **DIR-05 — Initial scale (binding):** The first useful form supports one
  manually supervised run at a time and keeps human attention at consequential
  choices rather than routine engineering steps.
- **DIR-06 — Product boundary (binding):** Second Mate is not First Mate rebuilt
  under a new name or a broad control plane. It does not provide portfolio or
  backlog management, a multi-agent workforce, repository-knowledge retrieval,
  generalized workflow administration, or an operations dashboard. First Mate
  and Knowless may inform quality, but their workflow structures are not
  dependencies.

Success means DIR-01 through DIR-05 hold in observable use while DIR-06 remains
absent. Failure includes authority drift, unevidenced completion, continuation
that depends on private context, repeated human intervention for ordinary
engineering, or coordinator machinery becoming the product.

This exact text is a candidate until the human approves it. Any material change
creates D-02 rather than editing D-01 in place.

## 3. Foundation decision and open decisions

### Proposed program decisions

These decisions become accepted only through human route approval.

| ID | State | Decision | Basis and consequence |
|---|---|---|---|
| FND-01 | **PROPOSED** | **New foundation.** | There is no runtime, while every later capability depends on the same authority, packet, evidence, and recovery semantics. A direct one-off implementation would cause those concepts to be reinvented. |
| VAL-01 | **PROPOSED** | **No separate Validation Slice now.** | No concrete technical unknown has yet been shown to need disposable code. The permanent lifecycle slice is the cheapest faithful test. Reopen this only if T-01 preflight exposes a decision-changing feasibility risk that the permanent slice cannot safely test. |
| EXE-01 | **PROPOSED** | **Second Mate does not coordinate its own bootstrap.** | A human starts the approved coding run manually. Second Mate is tested against an isolated fixture repository; it is not used to plan, authorize, or execute its own implementation. |
| EXE-02 | **PROPOSED** | **A manually launched Sol xhigh coding agent executes the Foundation Slice.** | Sol Ultra owns the architecture/route challenge and any material recovery review; it is not the default code writer. If a later Validation Slice is authorized, a separately contracted Sol xhigh coding run executes it within its discard boundary. These are bootstrap assignments, not permanent runtime roles or an agent mesh. |
| ENV-01 | **PROPOSED** | **The first compatibility target is one trusted local operator, this repository's Git worktree model, and the operating-system/filesystem family verified by T-01 preflight.** | It makes revision, lock, and recovery claims testable without pretending to support multi-user authority, every VCS, remote workspaces, or cross-platform atomicity. |
| ADP-01 | **PROPOSED** | **The first permanent slice has no live provider adapter.** | It proves the coordinator's durable lifecycle and executor boundary with a deterministic test executor using the production dispatch path. A single real provider adapter is the next candidate capability. No generic arbitrary-command runner or provider plug-in system is justified. |

### Decisions that remain open

| ID | State | Decision needed | What it blocks | Resolution |
|---|---|---|---|---|
| POL-01 | **DECISION-BLOCKED** | Choose narrow pre-Program consent or full-Program-first control as Second Mate's product policy, including which choice governs this bootstrap. | Any Validation or Foundation code, including FS-01, and the medium pilot. | Human choice recorded alongside its exact authority boundary. |
| T-01 | **DECISION-BLOCKED** | Select the initial runtime/toolchain and verify the ENV-01 OS/filesystem, Git, locking, atomic-write/recovery, packaging, and operator assumptions. The viable default candidates are TypeScript/Node and Python; decide from the intended environment, distribution path, provider SDK fit, typed transition ergonomics, and test burden. | Foundation Slice implementation. | A short Ultra recommendation grounded in the target operating environment and a read-only feasibility check, explicitly accepted by the human. Do not select from preference alone. |
| PRV-01 | **DECISION-BLOCKED, LATER** | Select the first real provider/host integration and its credential, interruption, and continuation boundary. | A live AI coding run and pilot, but not the fixture-based Foundation Slice. | Evidence-based adapter decision after Foundation review; choose one provider, not an abstraction framework. |

T-01 is not safely reversible after permanent code accumulates, so this Program
does not invent the answer. Serialization details are locally reversible and
remain implementer choices, provided they satisfy the Backbone invariants
below.

## 4. Minimal Foundation Backbone B-01

The Backbone is a small domain core, a repository/state adapter, and a thin
operator surface. The domain core must not depend on a specific model provider,
UI, task database, or orchestration framework.

### Stable concepts

- **Direction Version:** immutable approved text plus a stable identifier and
  its explicit approval record.
- **Route Decision:** `direct` or `foundation`, with a short evidence-based
  reason and the Direction version it interprets.
- **Packet:** one outcome, boundary, and proof contract, plus its route status.
  The packet has a stable digest once preflight begins.
- **Preflight Record:** target repository identity and revision/fingerprint,
  applicable instructions, dependency state, affected baseline, existing
  failures, and irreversible-change assessment. Preflight is read-only with
  respect to the target worktree, index, branch, dependencies, and external
  systems.
- **Authority Grant:** the human's explicit consent bound to the exact Direction,
  packet digest, preflight basis, allowed mutation/effect boundary, and stop
  conditions. It is not inferred from another approval.
- **Run:** at most one active executor invocation, frozen to the packet,
  preflight, and grant it received.
- **Evidence Record:** a claim, method, observation or command result, target
  revision, and pass/fail/uncertain result. It never becomes broader than what
  was observed.
- **Clean Close:** one atomic or recoverable transition that records route
  status, Direction coverage, evidence, residual uncertainty, recovery
  pressure, and handoff together.

The Living Delivery Map uses these concepts later; it is not required to
execute a single direct packet.

### Ownership and lifecycle

| Concern | Owner | Durable rule |
|---|---|---|
| Product meaning and changes | Human | Only exact approval creates a Direction Version; only the human changes binding meaning. |
| Consent and external authority | Human | Only an explicit, scoped Authority Grant permits mutation or effects. |
| Route and packet proposal | Planning model, challenged when leverage warrants | Proposals remain non-authoritative until the applicable human gate closes. |
| Transition validation and shareable state | Second Mate | It validates ordering and writes only recoverable, diffable state; it cannot manufacture consent or evidence. |
| Implementation tactics and evidence production | Working coding agent | The agent is autonomous inside the frozen packet and grant, and must stop on boundary drift. |
| Accepted project state | Target repository | Shareable Direction, route, evidence, and handoff live with the project; secrets, raw transcripts, private reasoning, and disposable runtime state do not. |

The canonical direct-packet order is:

`draft -> non-mutating preflight -> explicit consent -> mutation -> clean close`

Preflight may produce an ephemeral or private candidate report, but must not
change the target or cause external effects. If the target revision,
instructions, dependency basis, packet digest, or requested effect boundary
changes, preflight and consent are stale and mutation is refused.

### Invariants

1. A missing, stale, or mismatched grant prevents the coordinator from invoking
   its executor port.
2. The coordinator never invokes an executor during draft or preflight.
3. Only one run is active for a target packet; restart behavior is explicit and
   cannot create two owners of the same mutation boundary.
4. Route status and Direction coverage are separate. `completed` cannot imply
   `proven` beyond linked evidence.
5. Clean close is all-or-recoverable: status, evidence, pressure, and handoff
   cannot be left in a falsely completed partial state.
6. Outside mutation cannot be prevented by a local coordinator. Revision drift
   is detected and blocks or invalidates the run; the product claims enforcement
   only for execution it launches.
7. Durable formats are deterministic, reviewable, versioned, and migrate
   explicitly. They contain no credentials, transcripts, or private reasoning.
8. Failure preserves the last truthful state and a next recovery action; it
   never unlocks the next frontier automatically.

### Implementation seams and variable choices

Keep a pure transition core around the concepts above. Put filesystem and
revision inspection, durable write/recovery, clock/identifier generation, and
executor invocation behind narrow ports so tests can control failure and
replay. A thin CLI or equivalent operator surface may call that core after
T-01; it must not become a general workflow engine.

The exact language, command names, file names, serialization, and local
identifier format are not Backbone commitments. The implementer may choose
them after T-01 when the choice is deterministic, documented, does not weaken
the invariants, and remains local to an adapter.

## 5. Permanent Foundation Slice FS-01

**Outcome.** From a clean checkout, an operator can take one approved direct
packet against an isolated fixture repository through draft, read-only
preflight, exact consent, one deterministic mutation, claim-fit evidence, and a
recoverable clean close. An attempted start before consent and a start after
revision drift are both refused without target mutation.

**Permanent boundary.** The slice includes the transition core, durable
state/recovery adapter, target-revision and instruction inspection needed by
preflight, a thin operator surface, and a permanent end-to-end fixture. The
executor is an injected port; its Foundation test implementation performs one
safe deterministic fixture mutation through the same dispatch path a later live
adapter must use, with no test-only orchestration bypass. Production provider
calls, free-form shell execution, model prompting, Rumble automation,
Foundation-route automation, multi-run scheduling, UI, deployment, and remote
state are excluded.

**Representative journey.** The fixture is a real version-controlled target
with local instructions, a checked-in baseline probe that reports a known
`before` state, one allowed artifact the executor changes to a named `after`
state, and an untouched sentinel outside the grant. The operator drafts a
packet, runs preflight and the baseline probe, observes a denied pre-consent
start, records a fixture-scoped test grant, starts the injected executor through
the production dispatch path, runs the final probe, records the resulting
evidence, and cleanly closes. A second scenario changes the target after
preflight and proves that the stale basis blocks execution. Failure injection
during close proves recovery to one truthful state.

The test grant inside this journey is fixture data used to exercise B-01. It is
not the human's bootstrap Execution Consent, which separately authorizes the
coding agent to change the Second Mate repository.

**Claim-fit proof.** At the exact final revision, retain:

- an end-to-end replay from a clean Second Mate checkout and clean fixture;
- negative executable proof that no executor call or target change occurs
  before consent, on consent mismatch, or after revision drift;
- transition tests covering failure, retry, duplicate start, restart ownership,
  and the distinction between route completion and Direction proof;
- deterministic before/after fixture probes showing the one allowed artifact
  changed and the out-of-boundary sentinel did not;
- crash/failure-injection evidence for recoverable clean close;
- structural inspection that durable state is deterministic, versioned,
  reviewable, and contains no fixture secret or private transcript field;
- the selected toolchain's full repository lint, type/static, test, and build
  gates; and
- one human review of CLI/output clarity and whether the observed journey still
  matches D-01.

This evidence may prove only the local lifecycle, refusal behavior, durable
state, and executor seam exercised by the fixture. It does **not** prove a live
model run, provider security, broad workflow correctness, autonomous recovery,
or pilot usefulness.

The post-slice Foundation review must record what held, what failed or remained
unexercised, whether any Backbone invariant changed, and the consequence for
PRV-01 and the remaining Map. Those results cannot be written in advance.

## 6. Living Delivery Map MAP-01

| Capability or milestone | Direction coverage | Status now | Dependencies and proof intent |
|---|---|---|---|
| CAP-01: Durable authority and direct-packet lifecycle | DIR-01, DIR-02, DIR-04, DIR-05; supports DIR-03; constrained by DIR-06 | `blocked` | D-01, POL-01, T-01/ENV-01, route approval, fresh preflight, and Execution Consent. Proved only by FS-01 evidence. |
| MS-01: Foundation Slice proven | The FS-01 subset of DIR-01, DIR-02, DIR-04, DIR-05; DIR-03 and full product use remain | `blocked` | CAP-01 plus clean-close evidence and the Foundation review. Human checks the actual operator journey once. |
| CAP-02: One real provider-owned direct run | DIR-01 through DIR-05; constrained by DIR-06 | `candidate` | MS-01, PRV-01, credential/privacy boundary, interruption recovery, and a newly consented packet. Proof must include a real user-facing change and final-revision replay. |
| MS-02: Usable manually supervised coordinator | DIR-01 through DIR-06 within one-provider direct-route scope | `candidate` | CAP-02; one real direct packet closes without authority drift or hidden remaining work. Human product check required. |
| CAP-03: Foundation-route records and Map frontier | DIR-01 through DIR-05; constrained by DIR-06 | `candidate` | MS-01 evidence and CAP-01 concepts; implement only the minimal Backbone/evidence/Map states required by a selected pilot. |
| MS-03: Medium Foundation-route pilot | DIR-01 through DIR-06 at the pilot envelope | `blocked` | POL-01, CAP-02, CAP-03, an external target with known baseline, separate pilot consent, several packets, and one meaningful milestone. |
| CAP-04: Hardening or additional automation | Unassigned until evidence shows which Direction claim needs it | `uncertain` | Only repeated pilot failures may justify more persistence, roles, concurrency, UI, provider abstraction, or repository knowledge machinery. |

Binding DIR-01 through DIR-06 coverage is currently `still remaining`. MS-01
may prove only the foundation journey it exercises. MS-02 or MS-03 must not
declare the whole Direction proven without evidence for the actual completion
claim.

The Map changes only from evidence or an authorized Direction change. Distant
candidates intentionally have no packet-level implementation detail.

## 7. Frontier implementation packet IP-01

Status: **BLOCKED** on D-01 approval, POL-01, T-01/ENV-01, route approval,
non-mutating preflight, and Execution Consent. It becomes `ready` only when all
six are recorded against the same current basis.

**Outcome.** Deliver and prove FS-01 as one coherent permanent vertical slice.

**Boundary.** Implement B-01 only as exercised by FS-01. Own the new runtime,
tests, fixture, and minimal operator documentation in paths established after
T-01/ENV-01. Preserve all canonical design documents. Do not add a live provider,
network calls, arbitrary command runner, dashboard, database service,
background worker, generalized workflow/schema framework, RAG/code graph,
multi-agent scheduler, or First Mate/Knowless dependency. Do not publish,
deploy, push, or use real credentials or user data.

**Executor and writer.** One manually launched Sol xhigh coding agent is the
single writer for the packet. A fresh Sol Ultra reviewer may inspect the final
diff and evidence but does not share write ownership. Second Mate itself is not
used to dispatch or authorize either agent.

**Bootstrap run order.** This packet text is the draft. After D-01, POL-01,
T-01/ENV-01, and route approval are resolved, the coding agent performs a
read-only preflight and returns the exact repository revision, applicable
instructions, proposed owned paths, toolchain/environment availability,
baseline commands/results, existing failures, dependency or network needs, and
irreversible-change assessment. The human then grants or denies exact bootstrap
Execution Consent. Only after that grant may the coding agent mutate the Second
Mate repository. The run ends with claim-fit replay and one clean handoff; a
commit is optional, local, and only after all gates pass.

**Proof.** Satisfy every FS-01 proof item. Preserve the commands, exit results,
fixture observations, exact revision, and any manual review result in a compact
evidence record. A green unit suite without the clean fixture journey is not
completion.

**Stop and recovery conditions.** Stop before mutation if any gate or baseline
is unclear. Stop during execution on scope/authority drift, an unapproved
external effect, a runtime decision that would broaden B-01, inability to
demonstrate pre-consent non-execution, or evidence that the atomic/recoverable
close design is false. Classify the smallest pressure layer; do not silently
expand the packet or reopen Direction.

**Unlock.** A proved MS-01 permits an evidence-informed decision and packet for
exactly one live provider adapter. It does not authorize that work.

No second implementation packet is detailed because IP-01 is not yet ready and
its evidence may change the provider boundary. Detailing CAP-02 now would create
a speculative backlog.

## 8. Traceability and readiness

| Outcome | Requirement | Risk or constraint | Design response | Responsibility | Required evidence |
|---|---|---|---|---|---|
| Human meaning survives implementation | Immutable Direction and separate coverage | Direction drift or silent deferral | Direction Version, exact approval, separate coverage status | Human approves; coordinator preserves | Approval record plus mapped evidence at close |
| No mutation is laundered through planning | Draft, preflight, consent, mutation order | Stale or inferred authority | Bound digests/fingerprints and executor guard | Human grants; coordinator validates | Negative no-call/no-change tests and grant record |
| Completion is truthful and recoverable | Claim-fit proof and all-or-recoverable close | Plausible output or partial writeback | Evidence Record and Clean Close | Working agent produces; coordinator validates/persists | Clean replay, failure injection, exact revision |
| Product remains lean | One local run and earned mechanisms only | Recreating First Mate/control-plane scope | FS-01 exclusions and evidence-gated Map | Planner and human at route gate | Diff inspection, dependency review, pilot observations |
| A fresh agent can continue | Durable compact handoff | Private reasoning or stale backlog becomes authority | Repository-local state and only one detailed frontier packet | Coordinator writes; next agent verifies | Clean-checkout reconstruction and handoff review |

### Readiness gates

- **Planning-ready:** D-01, POL-01, and T-01/ENV-01 are resolved; the independent
  challenge corrections are incorporated; the human has approved the revised
  route. Until then the Program is truthfully blocked, not partially authorized.
- **Foundation-execution-ready:** planning-ready plus current non-mutating
  preflight and exact IP-01 Execution Consent.
- **Pilot-ready:** MS-01 and CAP-02 are proved; POL-01 is chosen; the target
  pilot has a known baseline, bounded data/provider authority, approved
  Direction and route, and claim-fit milestone proof.
- **Release/expansion-ready:** binding completion coverage is proven or
  explicitly and humanly changed/deferred; project-wide quality and relevant
  security, compatibility, migration/rollback, and failure-path evidence pass;
  no unresolved Foundation or Direction pressure remains.

## 9. Rejected scope and reopening conditions

The Program rejects a First Mate retrofit, universal backlog or dependency
graph, fixed permanent agent roles, parallel worker mesh, dashboard, RAG/code
graph, numerical risk/confidence gates, generic workflow engine, giant early
test portfolio, multiple provider adapters, and self-hosting the bootstrap.

Reopen the Foundation only if cross-capability evidence contradicts a named
concept, owner, lifecycle, invariant, compatibility boundary, or proof seam in
B-01. A local implementation difficulty, different file layout, failed test, or
better packet order is Packet or Map pressure, not permission to build a
platform.

## 10. Next human action

Approve or revise D-01, choose POL-01 and T-01/ENV-01, and approve or revise the
route. These may share one human touchpoint but remain separate decisions. After
they close, request the read-only IP-01 preflight. Review its exact basis before
granting any bootstrap Execution Consent.

## 11. Launch prompt after the human gates close

> Read `docs/second-mate/PROGRAM.md` and the canonical workflow specification.
> Execute only IP-01. First perform its read-only preflight against the current
> Second Mate revision; do not modify files, install dependencies, call a
> provider, or create external effects. Return the applicable instructions,
> proposed owned paths, selected toolchain/environment basis, baseline
> commands/results, existing failures, dependencies, and irreversible-change
> assessment. Stop for exact human Execution Consent bound to that preflight.
> After consent, implement only B-01 as exercised by FS-01, using one writer and
> no live provider or generalized orchestration machinery. Record the required
> clean-fixture, refusal, duplicate-start, recovery, structural, and repository
> quality evidence at the final revision. Stop and classify pressure if scope,
> authority, Backbone, or proof no longer fits. Do not publish, deploy, or push.
