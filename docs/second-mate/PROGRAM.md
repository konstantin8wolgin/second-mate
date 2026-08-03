# Second Mate bootstrap Program

Status: candidate initial Program; POL-01 narrowly selected, FS-01 canonically
adopted as the Foundation baseline, and CAP-01 complete; MS-01 remains blocked
only on the human operator/D-01 product check

Date: 2026-08-03

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
are the authority sources. Repository evidence now supersedes the Program's
original no-runtime premise: local `main` contains the merged Python FS-01
Foundation Slice, and the fixture lifecycle has executable implementation
evidence. The still-visible `fs01-foundation-slice` branch is historical; its
tip is already an ancestor of merge commit `d06937d` on `main` and is not a
second implementation to replay or merge.

The human made the following recorded decisions on 2026-08-03. They remain
separate records even when supplied in one instruction.

| Record | Accepted fact | Scope and consequence |
|---|---|---|
| Direction approval | Exact D-01 in section 2 | Confirms the product meaning; it does not itself authorize mutation or effects. |
| Route approval | The documented evidence-based Foundation route | Accepts FND-01 through ADP-01 as the initial route, subject to their stated boundaries. |
| POL-01 | **Selected: narrow pre-Program consent.** The dangerous question is whether fixture-only FS-01 is sufficient as Second Mate's permanent authority, evidence, and recovery foundation. | The envelope is this clean checkout, existing Python FS-01 implementation/tests, and checked-in fixture; resources are local Python 3.12, Git, filesystem, CPU, and disk; no network, credentials, provider, external target, or external commitment; discard disposable run state and retain at most existing FS-01. It canonically adopts verified FS-01 and completes CAP-01 only. |
| T-01 / ENV-01 | Python 3.12 and the recorded local Git/filesystem environment | Accepts the verified initial runtime boundary, not cross-platform or remote support. |
| FS-01 technical evidence | The verified FS-01 implementation and local repository evidence are canonically adopted as the Foundation baseline | Its claims remain limited to the fixture lifecycle; the adoption does not prove a live model/provider run, broad workflow, autonomous recovery, provider security, pilot usefulness, or product completion. |
| Current preflight | The recorded clean preflight covers exact pre-mutation repository basis `ede1bcb61358c48679c09e850d044752c7493d6f` for this documentation packet | Repository verification and historical fixture evidence do not substitute for a later packet's current read-only preflight. |
| Execution Consent | This docs-only packet has separately scoped Execution Consent bound to that recorded preflight and exact pre-mutation basis | It permits only the four authorized canonical-document mutations. No broad or future Execution Consent is recorded; every later bounded mutating packet needs its own current read-only preflight and exactly fitting Execution Consent. |

The historical repository cannot prove which pre-Program control or Execution
Consent governed the original bootstrap. This record does not rewrite or
backdate that history, nor does it authorize a future local packet. Provider/host
selection, credentials, external execution, push, publication, deployment,
Rumble integration, and pilots remain unauthorized.

POL-01 selection removes the prior policy block: verified FS-01 is canonically
adopted and CAP-01 is complete. MS-01 remains blocked only on the distinct
human operator/product check of the observed fixture journey. Binding Direction
coverage remains `still_remaining`. These states remain separate from Direction
approval, route approval, toolchain/environment acceptance, current preflight,
and this packet's scoped Execution Consent.

## 2. Approved Direction D-01

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

This exact text was approved on 2026-08-03. Any material change creates D-02
rather than editing D-01 in place.

## 3. Foundation decision and open decisions

### Accepted initial route decisions

| ID | State | Decision | Basis and consequence |
|---|---|---|---|
| FND-01 | **ACCEPTED** | **New foundation route.** | This accepts only the documented Foundation route. Canonical FS-01 adoption is a separate POL-01 authority record in section 1 and cannot be inferred from route approval. |
| VAL-01 | **ACCEPTED** | **No separate Validation Slice now.** | No concrete technical unknown has yet shown a need for disposable code; reopen only for a decision-changing feasibility risk. |
| EXE-01 | **ACCEPTED** | **Second Mate does not coordinate its own bootstrap.** | A human starts approved coding runs manually; the fixture does not plan, authorize, or execute its own implementation. |
| EXE-02 | **ACCEPTED** | **A manually launched Sol xhigh coding agent executes the Foundation Slice.** | Sol Ultra owns architecture/route challenge and material recovery review; this is not a permanent agent mesh. |
| ENV-01 | **ACCEPTED** | **The first compatibility target is one trusted local operator, this repository's Git worktree model, and the operating-system/filesystem family verified by T-01 preflight.** | This does not claim multi-user, every-VCS, remote-workspace, or cross-platform support. |
| ADP-01 | **ACCEPTED** | **The first permanent slice has no live provider adapter.** | FS-01 proves only the deterministic executor seam; one real provider adapter remains a later candidate, not an abstraction framework. |

### Decisions that remain open

| ID | State | Decision needed | What it blocks | Resolution |
|---|---|---|---|---|
| T-01 | **ACCEPTED** | Python 3.12 plus ENV-01's tested Linux/filesystem, Git, locking, atomic-write/recovery, packaging, and operator assumptions. | Establishes the accepted initial local runtime boundary for later separately authorized local work, each with its own current preflight and exactly fitting Execution Consent. | It does not claim product acceptance for other platforms or providers. |
| PRV-01 | **DECISION-BLOCKED, LATER** | Select the first real provider/host integration and its credential, interruption, and continuation boundary. | A live AI coding run and pilot, but not the fixture-based Foundation Slice. | Evidence-based adapter decision after Foundation review; choose one provider, not an abstraction framework. |

Serialization details remain locally reversible implementer choices, provided
they satisfy the Backbone invariants below.

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
not evidence that a human bootstrap Execution Consent existed, and it does not
authorize the coding agent to change the Second Mate repository. A separate
human grant would have been required for that historical bootstrap mutation,
but the repository cannot prove it.

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

### FS-01 repository evidence review — 2026-08-03

This review applies to the FS-01 hardening baseline at `b9efece`. It records
technical repository evidence separately from the authority records in section
1.

1. **Proved.** The Python 3.12 CLI and library replay one clean fixture journey
   through draft, read-only preflight, pre-consent refusal, exact fixture grant,
   one dispatch, claim-fit evidence, and recoverable close. Negative and
   failure-injection tests cover stale or ambiguous authority, revision and
   instruction drift, duplicate ownership, restart reconciliation, unrelated
   target mutation, filesystem aliases, malformed durable state, evidence
   forgery, and interrupted close. Locked offline environment sync, Ruff lint
   and format checks, strict mypy, the full pytest suite, source/wheel build,
   the dedicated end-to-end replay, and isolated wheel install/import/CLI smoke
   all pass in the repository-owned environment.
2. **Failed, unexercised, or uncertain.** No current automated FS-01 check is
   failing. The slice does not call a live model, exercise credentials or
   provider interruption, automate Rumble/Direction or Foundation routing,
   validate a medium pilot, prove autonomous recovery, or establish general
   security or compatibility. The required human review of CLI/output clarity
   and fit to approved D-01 has not been recorded. Python/ENV-01 acceptance is
   recorded separately in section 1; it does not widen those technical claims.
3. **Backbone consequence.** The exercised B-01 concepts and invariants held;
   no broader Backbone was earned. Verification tightened existing boundaries
   rather than adding a platform: strict JSON/schema parsing; semantic state,
   failed-evidence, executor-result, and close-transition validation; exact
   physical-worktree/branch/index-stage/index-flag and evidence binding; serialized
   evidence/close/recovery; durable first-owner persistence; and refusal of
   reserved-path collisions or aliased proof, instruction, state, journal,
   lock, and scratch paths. Strengthened preflight, run-state, and close-journal
   formats are explicitly version 2 and refuse the weaker local version 1
   forms; unsafe revision or instruction inspection is retained as failed
   evidence rather than disappearing after repair. Owner-private, randomized,
   content-addressed scratches backed by durable Git-private intent markers
   retaining the intended document make an interrupted partial state or journal
   write retryable without treating a pathname, digest, Unix owner, or private
   mode as ownership.
4. **Future-route consequence.** Selected narrow POL-01 canonically adopts the
   verified FS-01 Foundation baseline and completes CAP-01. MS-01 is blocked
   only on the distinct documented human operator/product check. PRV-01 remains
   a later human decision about one real adapter; it unlocks neither an adapter
   nor a pilot. CAP-02 and later Map items remain candidates or blocked as
   shown below. Direction coverage remains `still_remaining`.

The repository has therefore reached a truthful technical terminal state for
the fixed FS-01 fixture route, not a completed Second Mate Program or product.

## 6. Living Delivery Map MAP-01

| Capability or milestone | Direction coverage | Status now | Dependencies and proof intent |
|---|---|---|---|
| CAP-01: Durable authority and direct-packet lifecycle | DIR-01, DIR-02, DIR-04, DIR-05; supports DIR-03; constrained by DIR-06 | `completed` | The human selected the narrow FS-01 envelope, canonically adopted verified FS-01 as the Foundation baseline, and approved this capability complete. Its evidence remains limited to the local fixture lifecycle. |
| MS-01: Foundation Slice proven | The FS-01 subset of DIR-01, DIR-02, DIR-04, DIR-05; DIR-03 and full product use remain | `blocked` | The only remaining gate is the human check of the actual operator journey for CLI/output clarity and D-01 fit. The repository evidence review cannot replace that product judgment. |
| CAP-02: One real provider-owned direct run | DIR-01 through DIR-05; constrained by DIR-06 | `candidate` | MS-01, PRV-01, credential/privacy boundary, interruption recovery, and a newly consented packet. Proof must include a real user-facing change and final-revision replay. |
| MS-02: Usable manually supervised coordinator | DIR-01 through DIR-06 within one-provider direct-route scope | `candidate` | CAP-02; one real direct packet closes without authority drift or hidden remaining work. Human product check required. |
| CAP-03: Foundation-route records and Map frontier | DIR-01 through DIR-05; constrained by DIR-06 | `candidate` | MS-01 evidence and CAP-01 concepts; implement only the minimal Backbone/evidence/Map states required by a selected pilot. |
| MS-03: Medium Foundation-route pilot | DIR-01 through DIR-06 at the pilot envelope | `blocked` | CAP-02, CAP-03, an external target with known baseline, separately scoped pilot consent, several packets, and one meaningful milestone. |
| CAP-04: Hardening or additional automation | Unassigned until evidence shows which Direction claim needs it | `uncertain` | Only repeated pilot failures may justify more persistence, roles, concurrency, UI, provider abstraction, or repository knowledge machinery. |

Binding DIR-01 through DIR-06 coverage is currently `still_remaining`. MS-01
may prove only the foundation journey it exercises. MS-02 or MS-03 must not
declare the whole Direction proven without evidence for the actual completion
claim.

The Map changes only from evidence or an authorized Direction change. Distant
candidates intentionally have no packet-level implementation detail.

## 7. Frontier implementation packet IP-01

Evidence classification: **technically verified and canonically adopted within
the selected narrow envelope**. The implementation already exists, its
technical proof has been replayed, and CAP-01 is complete. MS-01 remains
blocked only on the human operator/product check. This historical packet must
not be treated as prospective permission to reimplement or expand FS-01.

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

**Bootstrap run order.** The required order was D-01, POL-01, T-01/ENV-01, and
route approval; read-only preflight; exact bootstrap Execution Consent; then
mutation and claim-fit close. The repository does not contain the records needed
to prove that historical order. The acceptance in section 1 is prospective and
does not backdate a grant. Every new mutating packet still needs a fresh
preflight and exact Execution Consent.

**Proof.** The automated, structural, packaging, recovery, and clean-fixture
items are recorded in the repository evidence review above. The human
CLI/output and D-01 product review remains outstanding. A green unit suite alone
would not have been completion; the dedicated fixture journey was replayed.

**Stop and recovery conditions.** Stop before mutation if any gate or baseline
is unclear. Stop during execution on scope/authority drift, an unapproved
external effect, a runtime decision that would broaden B-01, inability to
demonstrate pre-consent non-execution, or evidence that the atomic/recoverable
close design is false. Classify the smallest pressure layer; do not silently
expand the packet or reopen Direction.

**Unlock.** A proved MS-01 permits an evidence-informed decision and packet for
exactly one live provider adapter. It does not authorize that work.

No second implementation packet is detailed. The remaining FS-01 product check
does not justify a new runtime packet, and detailing CAP-02 before PRV-01 would
create a speculative backlog.

## 8. Traceability and readiness

| Outcome | Requirement | Risk or constraint | Design response | Responsibility | Required evidence |
|---|---|---|---|---|---|
| Human meaning survives implementation | Immutable Direction and separate coverage | Direction drift or silent deferral | Direction Version, exact approval, separate coverage status | Human approves; coordinator preserves | Approval record plus mapped evidence at close |
| No mutation is laundered through planning | Draft, preflight, consent, mutation order | Stale or inferred authority | Bound digests/fingerprints and executor guard | Human grants; coordinator validates | Negative no-call/no-change tests and grant record |
| Completion is truthful and recoverable | Claim-fit proof and all-or-recoverable close | Plausible output or partial writeback | Evidence Record and Clean Close | Working agent produces; coordinator validates/persists | Clean replay, failure injection, exact revision |
| Product remains lean | One local run and earned mechanisms only | Recreating First Mate/control-plane scope | FS-01 exclusions and evidence-gated Map | Planner and human at route gate | Diff inspection, dependency review, pilot observations |
| A fresh agent can continue | Durable compact handoff | Private reasoning or stale backlog becomes authority | Repository-local state and only one detailed frontier packet | Coordinator writes; next agent verifies | Clean-checkout reconstruction and handoff review |

### Readiness gates

- **Planning-ready:** POL-01 is selected and the FS-01 adoption/CAP-01 record
  is complete. This authorizes no new packet, provider, pilot, or runtime work.
- **Foundation-execution-ready:** the historical FS-01 implementation is not
  replayed as a new packet. The narrow envelope adopted FS-01 only; any new
  Validation or Foundation mutation or expansion needs its own current
  non-mutating preflight and exactly fitting Execution Consent.
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

Personally review the observed fixture operator journey and judge its CLI/output
clarity and D-01 fit; that explicit product observation is the only remaining
MS-01 gate. Do not infer it from technical evidence. Do not select a
provider/host or continue into a runtime packet.

## 11. Continuation prompt while human gates are open

> Read `docs/second-mate/PROGRAM.md` and the canonical workflow specification.
> Do not reimplement FS-01 merely because its historical branch remains visible;
> it is already merged. First verify the recorded human decisions, including
> the selected narrow POL-01 envelope, canonical FS-01 adoption, and CAP-01
> completion. Treat the existing implementation and evidence as limited to the
> fixture lifecycle, not as proof of a broader product or a future grant.
> If the human product check is still missing, operate the documented fixture
> journey without mutation to Second Mate itself and return that observation.
> Do not select or build a provider adapter, pilot, generalized orchestration
> machinery, or other next packet without the chosen POL-01 control, current
> read-only preflight, and exactly fitting Execution Consent. Stop and classify
> pressure if authority, Direction, Backbone, or proof no longer fits. Do not
> publish, deploy, or push.
