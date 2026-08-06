# Second Mate bootstrap Program

Status: candidate initial Program; POL-01 narrowly selected, FS-01 canonically
adopted as the Foundation baseline, CAP-01 and MS-01 complete, and
DIR-INTAKE-01, CAP-02A, CAP-02C, EVA-01, EVA-02, EVA-03, and EVA-04 implemented and
locally verified; PRV-01 and CAP-02B are historically closed for one consumed
run with partial independent evidence retained. One CAP-02C disposable exercise
is also consumed and conservatively closed as `unknown-running`; MS-02 now
awaits the normal-use conversation bridge and human product check

Date: 2026-08-03

This is the implementation Program for building Second Mate itself. It applies
the canonical [workflow specification](workflow-spec.md) and
[readiness checklist](implementation-checklist.md) without changing either.
The [Foundation-First reference](../placeholder/foundation-first/foundation-first-delivery-design.md)
is context only, as described by the [canonical package index](README.md).

The Program retains one completed permanent Foundation Slice and the completed
provider-free recovery audits compactly detailed. It does not
select a product frontier before the MS-02 human product check and is not
permission to publish, deploy, or use external services.

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
| 2026-08-03 packet preflight | The recorded clean preflight covers exact pre-mutation repository basis `ede1bcb61358c48679c09e850d044752c7493d6f` for that documentation packet | Repository verification and historical fixture evidence do not substitute for a later packet's current read-only preflight. |
| 2026-08-03 Execution Consent | That docs-only packet had separately scoped Execution Consent bound to its recorded preflight and exact pre-mutation basis | It permitted only the four authorized canonical-document mutations. No broad or future Execution Consent was recorded. |
| 2026-08-04 read-only preflight | The current read-only preflight covers exact repository basis `e46c6dc82df54e16ecd39d6ab826c6146d401739` for this status reconciliation | It is evidence only for this local close and does not substitute for a later packet's current read-only preflight. |
| 2026-08-04 Execution Consent | The latest request supplies scoped Execution Consent only for local status-document edits to `README.md`, `workflow-spec.md`, this Program, and `implementation-checklist.md` | It authorizes no runtime mutation, later packet, provider, credential, external target, push, publication, deployment, or external effect. Every later bounded mutating packet needs its own current read-only preflight and exactly fitting Execution Consent. |
| 2026-08-04 roadmap-reconciliation preflight | Fresh inspection reconfirmed tracked basis `95c7a145da8fe4dafe1147ecea787e5e9592c51b`; the only outer-checkout dirt was the unrelated nested `firstmate/` repository, which made the root Ruff gate fail and made Second Mate revision inspection reject an unsupported directory entry. | The nested repository remains separate user-owned content. A local `.git/info/exclude` entry now removes it from outer Git discovery without editing, tracking, or configuring FirstMate; this checkout-local boundary is not portable product state. |
| 2026-08-04 roadmap-reconciliation Execution Consent | The delegated request authorizes only that local workspace-boundary correction and edits to this Program and `implementation-checklist.md`, after revalidation. | It authorizes no DIR-INTAKE implementation, provider selection or call, credential use, external target, push, publication, deployment, or other runtime mutation. |
| 2026-08-04 DIR-INTAKE-01 preflight | Fresh inspection reconfirmed tracked basis `95c7a145da8fe4dafe1147ecea787e5e9592c51b`, visible revision fingerprint `c2768892aa7e7b9b799e64bbf3c368000af6aac616496ea45ab195a0dc7ccbcd`, the two authorized roadmap edits, no visible `firstmate/` content, and a green 193-test baseline. | The preflight covered this local packet only. It carried forward no provider, credential, network, target, push, commit, publication, deployment, or external authority. |
| 2026-08-04 DIR-INTAKE-01 plan and Execution Consent | The human approved the exact test-first Direction-intake plan and authorized shared mutation coordination, immutable approved Direction history, separate preparation/approval/promotion authority, CLI prepare/promote/show, operator documentation, and end-to-end draft integration. | It authorizes this bounded local packet only. It explicitly excludes provider work, live execution, external effects, pushes, and commits. |
| 2026-08-04 trusted-local design preflight | Fresh read-only inspection reconfirmed tracked basis `95c7a145da8fe4dafe1147ecea787e5e9592c51b`, the existing authorized roadmap and DIR-INTAKE-01 working-tree changes, and a clean `git diff --check` before this revision. | This basis supports only the product-contract analysis and documentation packet. It is not a live-target or provider preflight. |
| 2026-08-04 TLX-01 decision and documentation Execution Consent | The human selected an explicitly trusted-local, unsandboxed initial live mode and retained sandboxed execution as later hardening/deployment. The same request authorizes the corresponding design, Program, readiness, package-index, and operator-document revisions. | It authorizes no provider authentication or call, credential use, live-target selection or mutation, system configuration, real dispatch, CAP-02 implementation, push, or commit. Every later real run still needs its own current preflight and exact unsandboxed activation consent. |
| 2026-08-04 CAP-02A trusted-local POC plan and Execution Consent | The human authorized the offline/mock adapter packet with broad local execution authority represented only in its activation contract, no Second Mate token-spend cap beyond unavoidable provider/billing controls, and cleanup limited to exact identity-recorded private run artifacts. | It authorizes test-first local source, test, and canonical-document mutations for CAP-02A only. It authorizes no authentication, credential creation/use, provider call, billing-project selection, system configuration, live target, real process/agent dispatch, CAP-02B, push, or commit. |
| 2026-08-04 CAP-02B provider boundary, preflight, and Execution Consent | The human selected local Codex CLI `0.146.0` with the existing ChatGPT login/account controls, normal provider and repository network access, current public Second Mate HEAD `94c21707ab13294b8e756049691e89cba1c91725` as the baseline-known trusted target, ephemeral CLI session storage, private transcript retention through clean close, no automatic retry/resume, `provider-billing-controls-only`, and exact-private-artifact cleanup. The exact activation, packet, allowed paths, risk acknowledgments, stop conditions, and independent evidence requirements were recorded before dispatch. | It authorized exactly one unsandboxed run to audit activation, streamed JSONL, recovery, and cleanup and to fix at most one proved defect with a regression. It authorized no second dispatch, credential/account/billing/system change, unrelated path, push, PR, destructive repository cleanup, or provider-side deletion. |
| 2026-08-04 CAP-02B clean close | The contemporaneous close records activation `cap02b-20260804t224244z-94c21707-audit01`, one 31-event lifecycle ending in `turn.completed`, process exit zero, exactly two allowed paths, one recovery defect, close digest `21a5c91a5c2c4d11c85c24fcdd00c54a8570683c1e64a43f465e881ae7e8cbf6`, and exact cleanup. Its transcript/session/control/close artifacts were intentionally deleted. | The retained marker independently proves the exact activation and bindings are consumed; Git independently proves the two-path fix. The event stream, close document, and cleanup identities are non-replayable historical records. The run remains terminal and not retryable; no absence-of-outside-effects or provider-side-erasure claim follows. |
| 2026-08-05 CAP-02B review and overnight continuation | Git independently shows that `3ecf0fe` contains only the one-line positive-exit predicate and signal-exit regression in the two allowed paths; the current suite replays the behavior. The contemporaneous review records the historical quality-gate replay. The human also authorized plan-consistent routine local continuation. | The historical gate output itself is not retained in the checkout. The continuation permits truthful local evidence reconciliation and other dependency-ready non-live work while prohibiting retry/resume/redispatch of CAP-02B, provider/credential/account/billing/system changes, unrelated paths, push, and PR. It cannot manufacture the MS-02 human product check. |
| 2026-08-05 CAP-02C provider-free adapter preflight and Execution Consent | Fresh inspection at `2a698d056d3e50e2662313f2549ab8d08e5ead5f` and visible fingerprint `37f548dc40adb27edb9d6d1597606391ed4ed8c13e322ff741f7297e5a097cce` found a clean checkout, the retained CAP-02B consumed marker unchanged, a green 261-test baseline, and local Codex CLI `0.146.0` help that supports JSONL, ephemeral storage, ignored user configuration, stdin prompts, fixed working directory, and explicit unsandboxed execution. The human expressly authorized autonomous plan-consistent local work, including reusable live-adapter preparation when it can be proved without a provider call. | This authorizes CAP-02C source, tests, canonical documentation, routine repairs, and local commits only. It prohibits invoking `codex exec` or another provider, authentication or credential access, retry/resume/redispatch of CAP-02B, real activation, live-target work, system configuration, `firstmate/`, push, and PR. CAP-02C must use only a temporary fake executable and must expose no CLI dispatch route. |
| 2026-08-05 EVA-01 evidence audit preflight and Execution Consent | Fresh inspection at clean `34dc2aef1efab136e82ccd45b245dbc49e0d1fa3` reconfirmed the retained CAP-02B marker at mode `0600` and SHA-256 `0567cd80dddba22b159932ce828648d1e5d1068513a3823bb0991824998dd344`, 273 collected tests, the dormant library-only adapter, and no tracked `firstmate/` content. The latest overnight instructions require every remaining claim, prerequisite, and completion label to receive proportionate independent evidence, truthful unproved/deferred wording, or a bounded provider-free proof path. | This authorizes systematic local evidence reconciliation, provider-free tests and repairs, canonical documentation, and local commits. It prohibits provider/live dispatch, CAP-02B replay, credential/authentication access, push/PR, system configuration, user-data deletion, and `firstmate/` changes. Human product judgment remains outside this authority. |
| 2026-08-05 EVA-01 provider-free close | Plan commit `47804bd` froze the evidence model and bounded repairs; implementation/evidence commit `eda5d19` records phase/disposition/process-ownership cleanup gates, `skill_search` minimization, `py.typed`, red-green regressions, and canonical claim reconciliation. Fresh close replay passed 57 trusted-local and 277 total tests, Ruff lint/format, configured and explicit strict mypy for 11 modules, locked-offline sync, source/wheel build and contents, and isolated wheel import/CLI/type-marker smoke. | The retained CAP-02B marker remained mode `0600` with SHA-256 `0567cd80dddba22b159932ce828648d1e5d1068513a3823bb0991824998dd344`; `firstmate/` remained ignored and untouched. No installed Codex execution, provider, credential/authentication state, live target, system change, push, PR, or user-data deletion occurred. EVA-01 closes locally and leaves MS-02 as the irreducible human gate. |
| 2026-08-05 EVA-02 remaining-plan and target-binding preflight and Execution Consent | Fresh inspection at clean `196dbbcd9a838529b4640098e3110677aa3e0770`, visible fingerprint `42a20b984fff2b7632a97a1d2e2706602b4e10ef747bed628600f637e6cbf533`, and a green 278-test baseline found that commit `196dbbc` conservatively handles cancellation-drain setup failure but is not yet reflected in the canonical close. Whole-plan tracing also found two provider-free contradictions: CAP-02C does not independently recompute the actual target head/fingerprint or bind its resolved root before probes and activation consumption, and its latest durable `unknown-running` state cannot cancel a process the same adapter still owns. | The latest delegation authorizes plan-consistent local code, tests, claim reconciliation, and local commits needed to close those provider-free gaps and classify every remaining checklist item by its actual dependency. It prohibits provider/auth/credential use, CAP-02B replay/resume/redispatch, live dispatch, push/PR, system changes, user-data deletion, `firstmate/` changes, or a fabricated MS-02 judgment. |
| 2026-08-05 EVA-02 provider-free close | Plan commit `79592eb` froze the exact target/recovery and remaining-plan audit; implementation/evidence commit `503048e` records resolved-root/current-revision binding, cancellation from owned durable `unknown-running`, ownership retention through cancellation ambiguity, 5 new red-green regressions, and canonical dependency reconciliation. Fresh close replay passed 63 trusted-local and 283 total tests, Ruff lint/format, configured and explicit strict mypy for 11 modules, locked-offline sync, source/wheel build and contents, and isolated wheel import/CLI/type-marker/target-binding smoke. | Commit `196dbbc` is now reconciled in the canonical history. The retained CAP-02B marker remained mode `0600` with SHA-256 `0567cd80dddba22b159932ce828648d1e5d1068513a3823bb0991824998dd344`; `firstmate/` remained ignored and untouched. No Codex execution, provider, auth/credential access, live target, system change, push, PR, or user-data deletion occurred. EVA-02 closes locally; only MS-02 and its downstream external or contingent decisions remain. |
| 2026-08-05 EVA-03 interrupted-cleanup preflight and Execution Consent | Fresh inspection at clean `ee32d05cc824acfa5c7387544dd3aa82d2424e56`, visible fingerprint `572dccc24964df8947e50d1b53c8648187162b4fcb2ef692ad7532b6f84c7048`, 6,408 implementation lines, and a green 283-test baseline found one provider-free contradiction after EVA-02: cleanup validates the exact private set before deletion, but a failure after the first successful unlink leaves no durable cleanup intent, so fresh reload rejects the partial directory and cannot finish the already-authorized narrow cleanup. | The latest delegation authorizes the smallest test-first local repair, adversarial proof, canonical documentation, verification, and local commits. It may add only a durable phase inside the existing identity-recorded session and exact resumption of the three run-owned files or final empty directory. It prohibits broader deletion, recursive cleanup, repository/provider data deletion, live/provider/auth/credential use, CAP-02B replay, push/PR, system changes, `firstmate/`, or a fabricated MS-02 judgment. |
| 2026-08-05 EVA-03 independent safety review correction | A separate read-only review proved that an empty directory alone cannot establish prior cleanup intent: it can also result from pre-session interruption, outside deletion, or replacement of the original directory. The first red test then proved that immediate remove/recreate can reuse the same device/inode. Accepting either signal alone would bypass the missing-evidence and replacement gates. | Before unlinking, enrich only the already-retained consumption marker with cleanup authorization bound to the exact run-directory device/inode and the private root's directory-change identity, in addition to the session phase. File unlinks inside the run do not change that parent token; removing/recreating the run directory does. Empty recovery must match both. This is an evidence-driven correction to the initial no-marker-mutation assumption; it adds no file, path, deletion target, provider/live authority, or recursive behavior. |
| 2026-08-05 EVA-03 provider-free close | Plan commit `0b87907` froze interrupted-cleanup recovery; review-correction commits `9e8eb35` and `1b215ba` bind empty recovery to the exact run directory and private-root change identity after red tests disproved weaker evidence; implementation/evidence commit `a44c7b0` records durable cleanup authorization, exact restart, adversarial refusals, stopped-process descriptor closure, and canonical/operator wording. Fresh replay passed 73 trusted-local and 293 total warnings-as-errors tests, full Ruff lint/format, configured strict mypy for 11 modules, locked-offline sync, source/wheel build and contents, and isolated wheel import/CLI/type-marker smoke. One independent read-only review and its focused re-review found no remaining Critical or Important defect. | The retained CAP-02B marker remained mode `0600` with SHA-256 `0567cd80dddba22b159932ce828648d1e5d1068513a3823bb0991824998dd344`; `firstmate/` remained ignored and untouched. No installed Codex execution, provider, auth/credential access, live target, system change, user-data deletion, push, or PR occurred. This close correctly bounded deletion and restart after unlink, but its conclusion that only MS-02 remained was superseded when EVA-04 independently reproduced a pre-unlink cleanup-record persistence gap. |
| 2026-08-05 EVA-04 cleanup-record crash-safety preflight and Execution Consent | Fresh inspection at clean `52db12f2b585b39c8b40610b1d500ef56f5763c4` replayed all 293 warnings-as-errors tests and the package gates, then an independent provider-free audit reproduced interruption while persisting both cleanup records. The current in-place truncate/write can leave `session.json` or the retained consumption marker as invalid partial JSON before any unlink, so fresh reload fails closed but cannot resume the already-authorized exact cleanup. | The latest delegation authorizes plan-consistent provider-free gap repair, adversarial tests, canonical documentation, verification, and local commits. EVA-04 may change only persistence and parsing of the existing identity-recorded session and marker, preserving their inodes, exact artifact names, cleanup boundary, parent/run-directory identity checks, strict complete-record validation, and legacy single-document compatibility. It prohibits new deletion targets, provider/live/auth/credential use, CAP-02B replay, push/PR, system changes, `firstmate/`, or a fabricated MS-02 judgment. |
| 2026-08-05 EVA-04 provider-free close | Plan commit `0f6fc45` froze the same-inode framed-record design; implementation/evidence commit `bb7b7f7` records append-only cleanup updates, bounded linear parsing, exact incomplete-tail recovery, strict complete-frame refusal, and durable retry re-sync. Red-green tests cover interruption while persisting both session intent and marker authorization, invalid digests and suffixes, impossible/oversized lengths, parser resource bounds, and ambiguous final `fsync`. Fresh replay passed 95 trusted-local and 315 total warnings-as-errors tests, full Ruff lint/format, configured strict mypy for 11 modules, locked-offline sync, source/wheel build and contents, and isolated wheel import/CLI/type-marker smoke. Independent specification and quality re-reviews found no remaining Critical or Important product-path defect. | The retained CAP-02B marker remained mode `0600` with SHA-256 `0567cd80dddba22b159932ce828648d1e5d1068513a3823bb0991824998dd344`; `firstmate/` remained ignored and untouched. The protocol preserves the existing inodes, exact three-artifact cleanup set, and legacy single-document files. EVA-04 supersedes EVA-03's overbroad persistence conclusion without changing its deletion authority. No provider, auth/credential access, live target, CAP-02B replay, system change, user-data deletion, push, or PR occurred. Only the MS-02 human product judgment and its downstream external or contingent decisions remain. |
| 2026-08-06 MS-02 usability-acceptance preparation and bounded documentation authority | Fresh inspection at clean `f024fbb87cd2e9931b3762e930e05655b74c17b4` reconfirmed the fixture-only CLI, consumed CAP-02B marker, dormant public CAP-02C library adapter with no CLI route, exact activation/recovery contract, and open human D-01 judgment. The safe representative exercise is the deterministic FS-01 mutation in a disposable local worktree; it cannot prove model autonomy or live-provider usability. | The latest delegation authorizes only a concise operator-ready hands-on walkthrough, claim verification, and necessary local documentation/package-index changes. It prohibits provider or network calls, authentication/credential use, live adapter dispatch, live targets, CAP-02B replay, system configuration, push/PR, or manufacturing the MS-02 judgment. Any real CAP-02C exercise remains a distinct future one-shot activation and invocation packet. |
| 2026-08-06 CAP-02C disposable exercise preflight and Execution Consent | After an earlier pre-dispatch refusal on a group-writable native package binary, the user permission-hardened the installation. Fresh inspection at clean source HEAD `374c3f3779a2a2af8c5d6cbd6c8916c08b4352cf` passed 315 tests, 95 trusted-local tests, Ruff, format, and strict mypy. The frozen packet bound fresh target HEAD `887d0da07b70ff7b602873122a419ed23d39b72f`, target fingerprint `b631e1746dfb6ea450174c9f7bf651d6a853170bdb134ae19f01eeb876da3ca0`, the unaliased owner-owned `0755` native Codex `0.146.0` ELF at SHA-256 `2e863156ed35ecc5253b1e2f907a9143077b9f7cb51942070c61996471ff6e04`, help digest `9f86f0115238ddde2514587e5f95b0ab0aa6b89495e5912878d49ad26038aa19`, model `gpt-5.6-luna`, prompt/environment digests, existing ChatGPT login, no target config/remote, and provider boundary digest `178155bc55f431efbf2764937de870255d167a4d7fa00214b59a397953183a1e`. | The human authorized exactly one fresh non-retryable trusted-local activation on that disposable target. It permitted the existing authentication/provider network path and exact target-file effect while prohibiting prior-activation reuse, retry/resume/redispatch, push/PR, system changes, credential exposure, unrelated data access, or a real project target. Activation `cap02c-live-20260806-02-4ybb2d` exhausts this authority. |
| 2026-08-06 CAP-02C consumed `unknown-running` close and test-first correction | The contemporaneous close records one provider process, exact untracked `result.txt`, a canonical session plus `turn.completed`, process exit and stopped identity, a deprecated `web_search_request` error before `turn.started`, strict `unknown-running` classification, no retry, and exact abandoned cleanup of three identity-recorded files plus the run directory. [Sanitized event types, hashes, and classifications](evidence/CAP-02C-20260806.json) retain no transcript/result content, credentials, or private paths; those live observations are therefore non-replayable. The `0600` marker remains at SHA-256 `fd4f77dfd93c07cf7d3c7978f7dcfcfd650f3d6430cb7d54d835f5aa2c57efb8` and independently proves only that this exact activation and its frozen bindings are consumed. | A red-green provider-free regression removes only the deprecated default-disabled feature flag while retaining explicit `standalone_web_search` denial. Fake-process tests prove the corrected argv; no second live call occurred. Current code reproducibly proves the provider-free contract, while the live launch/transport, exact target effect, conservative ambiguity, no retry, and exact cleanup remain a non-replayable historical close. Nothing proves a terminal corrected live CAP-02C close, absence of outside effects, provider-side erasure, or ordinary usability. |
| 2026-08-06 normal-use First Mate direction | The user states the product goal: normal use begins as a First Mate conversation; research and discussion produce an explicit scope and human approval, then First Mate invokes Second Mate's framework to carry ownership, preflight, execution, evidence, and recovery behind the scenes. | This is an **ACCEPTED** usability requirement, not permission to infer approval or merge Direction approval with Execution Consent. Ordinary use must not require the human to manage executable permissions, activation JSON, digests, or private-state paths. This packet may analyze and record the smallest safe bridge only; implementation begins only under a separately approved provider-free packet, and any later real run still needs fresh one-shot consent. |

The historical repository cannot prove which pre-Program control or Execution
Consent governed the original bootstrap. This record does not rewrite or
backdate that history. The later CAP-02B record authorizes and closes only its
one exact provider run; it is not reusable authority for another provider,
target, session, or mutation. Credential/account changes, push, publication,
deployment, Rumble integration, and pilots remain unauthorized.

TLX-01 changes only the near-term containment requirement. It does not weaken
or replace Direction, packet, preflight, grant, one-owner, session-binding,
unknown-running, independent-evidence, or recoverable-close requirements. It
also does not claim that an unsandboxed executor can be prevented from acting
outside its grant. That limitation is explicit in the workflow and operator
contract and remains unproved DIR-02 coverage rather than being laundered into
a guarantee.

### Evidence classes used by current status labels

The 2026-08-05 EVA-01 through EVA-04 audits do not accept this Program's prose as
proof. They use four explicit evidence classes:

- **R — reproducible now:** executable tests, build/type/lint/package gates, Git
  structure, or current filesystem facts can be rerun without a provider;
- **I — independently retained:** an immutable Git object or exact durable
  artifact remains available for inspection, but the original event cannot be
  replayed;
- **H — human decision record:** the coordinator received the exact decision or
  authority; this is authority evidence, not technical proof; and
- **N — non-replayable historical record:** the contemporaneous close records a
  fact, but its private underlying artifact was intentionally deleted and the
  checkout cannot independently re-prove that detail.

These classes audit every Delivery Map label and its prerequisites:

| Item | Evidence class at this revision | What is independently established now |
|---|---|---|
| D-01, FND-01, POL-01, T-01/ENV-01, MS-01, TLX-01 | **H**, with **R** only for the current Python/Linux/Git behavior | The decisions and narrow acceptances are recorded; current local code can replay only the technical subset. No missing human observation is inferred. |
| CAP-01 / FS-01 | **H + R** | Adoption/completion is a human decision; fixture authority, mutation, evidence, recovery, and close behavior are reproducible. |
| DIR-INTAKE-01 | **H + R** | Its grant is recorded and its immutable-history, authority, race, recovery, clone, CLI, and draft behavior are reproducible. Automated Rumble remains open. |
| PRV-01 | **H + I** | The selected one-run boundary is recorded; the retained marker independently binds the consumed activation to the recorded provider digest and frozen target, but not to deleted provider output. |
| CAP-02A | **R** | Offline authority, JSONL, ownership, ambiguity, cleanup, and no-reuse behavior are reproducible without a provider. |
| CAP-02B | **I + N** | The marker proves the exact activation is consumed; Git proves the two-path recovery commit and current regression. The deleted transcript/session/control/close artifacts mean the 31-event lifecycle and exact cleanup sequence remain a contemporaneous close record, not replayable checkout proof. |
| CAP-02C | **R + I + N** | Fake-executable qualification, exact resolved-target/current-revision binding, dispatch, streaming, cancellation from owned durable state, recovery, and cleanup behavior are reproducible. The retained marker independently proves the exact real activation is consumed and binds its provider boundary and disposable target. The sanitized record preserves hashes and classifications, but the deleted raw session, transcript, and control artifacts leave event ordering and exact cleanup as non-replayable historical evidence; the corrected argv has no terminal live proof. |
| EVA-01 | **H + R** | The grant and clean basis are recorded; the three technical contradictions were reproduced red, repaired minimally, and replayed through current repository/package gates. |
| EVA-02 | **H + R** | The grant and clean basis are recorded; target-root/revision drift, durable-state cancellation, and ambiguous-cancellation ownership were reproduced red, repaired minimally, and replayed through current repository/package gates. Every remaining unchecked item is tied to its exact external or contingent dependency. |
| EVA-03 | **H + R** | The grant and clean basis are recorded; interrupted exact-cleanup recovery, directory-bound authorization, replacement refusal, and cancellation-drain ownership were reproduced and replayed. EVA-04 later corrected its cleanup-record persistence crash window. |
| EVA-04 | **H + R** | The grant and clean basis are recorded; partial session/marker writes and ambiguous durability were reproduced red, then repaired with same-inode framed records, bounded linear parsing, strict corruption refusal, and retry re-sync. |
| MS-02 | **open H gate** | No technical result can supply the required product judgment. |
| SBOX-01, PILOT-SELECT-01, CAP-03, MS-03, CAP-04 | **deferred, blocked, or uncertain** | No sandbox, selected pilot, pilot packet, pilot milestone, or repeated-pilot evidence exists. |

Completion labels based on **H** remain valid human decisions. CAP-02B remains
terminal because its exact marker is consumed, but only the **I** facts above
are independently retained; EVA-01 through EVA-04 do not recreate or replay the
deleted **N** evidence.

POL-01 selection removes the prior policy block: verified FS-01 is canonically
adopted and CAP-01 is complete. On 2026-08-04, the human accepted
plan-conformant FS-01 completion without personally observing the fixture
CLI/output journey and declined further FS-01 decision requests. For MS-01
only, this one-time scoped acceptance replaces the former personal-observation
gate and completes MS-01. It does not record a human review, observation,
CLI/output-clarity judgment, or D-01-fit proof; those unobserved qualities
remain accepted residual uncertainty. The fixed FS-01 first workflow is
terminal with no further user decision. Binding Direction coverage remains
`still_remaining`. These states remain separate from Direction approval, route
approval, toolchain/environment acceptance, current preflight, and each
packet's scoped Execution Consent. The general milestone human-product-review
rule remains unchanged.

The 2026-08-04 roadmap reconciliation establishes a truthful candidate route
from the terminal FS-01 baseline. It does not approve that route as Execution
Consent. In particular, the preserved `rumble-direction-handoff` branch is
useful behavior and test evidence, but it diverged before current schema-v2
authority, evidence, locking, and recovery hardening and must not be merged or
ported wholesale.

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
| TLX-01 | **ACCEPTED** | **The first live execution mode is explicitly trusted-local and does not require a sandbox.** | The human accepts that the selected local account, agent, and repository code may have broad machine and network access. Second Mate continues to guarantee coordinator authority, ownership, recovery, and observed target evidence, but makes no containment or no-outside-effects claim. This decision does not activate a run. |
| SBOX-01 | **ACCEPTED AS DEFERRED HARDENING** | **Sandboxed execution remains a separate later hardening/deployment path.** | It is not a prerequisite for the initial trusted-local adapter or supervised real run. When selected, it must prove its actual filesystem, credential, environment, network, capability, cancellation, and cleanup boundaries and must never silently downgrade. |

### Runtime boundary and one-run provider decision

| ID | State | Decision needed | What it blocks | Resolution |
|---|---|---|---|---|
| T-01 | **ACCEPTED** | Python 3.12 plus ENV-01's tested Linux/filesystem, Git, locking, atomic-write/recovery, packaging, and operator assumptions. | Establishes the accepted initial local runtime boundary for later separately authorized local work, each with its own current preflight and exactly fitting Execution Consent. | It does not claim product acceptance for other platforms or providers. |
| PRV-01 | **ACCEPTED FOR ONE CONSUMED CAP-02B PROOF** | Local Codex CLI `0.146.0`; existing ChatGPT login/account controls with no API billing-project change; current public Second Mate data; normal provider/repository network access; ephemeral CLI storage; private transcript retention through close; exact-session binding; no automatic retry/resume; `unknown-running` on ambiguity; and the current branch as the trusted target. | Enabled exactly one CAP-02B proof run, not a reusable production integration or pilot. | Any later run, host/version change, different data/target, retention change, account/billing change, resume, or retry needs a new current boundary and exact authority. Sandbox qualification was not required for this trusted-local run. |

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
- the originally planned human review of CLI/output clarity and whether the
  observed journey still matches D-01. That observation was not supplied;
  instead, the 2026-08-04 one-time scoped acceptance completes MS-01 without
  claiming that review, clarity judgment, or D-01-fit proof. The unobserved
  qualities remain accepted residual uncertainty.

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
   security or compatibility. The human did not personally observe the
   CLI/output journey or record a clarity or D-01-fit judgment. The 2026-08-04
   one-time scoped acceptance completes MS-01 without converting that missing
   observation into evidence; it remains accepted residual uncertainty.
   Python/ENV-01 acceptance is recorded separately in section 1; it does not
   widen those technical claims.
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
   verified FS-01 Foundation baseline and completes CAP-01. The 2026-08-04
   one-time scoped acceptance completes MS-01 without a personal observation;
   the fixed FS-01 first workflow is terminal with no further user decision.
   TLX-01 now selects an unsandboxed trusted-local initial mode while SBOX-01
   preserves sandboxing as deferred hardening. CAP-02A completes the offline
   coordinator-side adapter proof. PRV-01 and CAP-02B later closed exactly one
   manually enveloped real Codex proof. CAP-02C added a library process adapter;
   its later disposable exercise consumed one activation as `unknown-running`
   and selected a provider-free correction without pilot authority. The accepted
   normal-use requirement now selects a conversation bridge before MS-02.
   Direction coverage remains `still_remaining`.

The fixed FS-01 fixture route remains terminal. The overall repository is not
terminal because CONV-BRIDGE-01 is now a decision-ready provider-free frontier;
Second Mate is still not a completed Program or product.

## 6. Living Delivery Map MAP-01

| Capability or milestone | Direction coverage | Status now | Dependencies and proof intent |
|---|---|---|---|
| CAP-01: Durable authority and direct-packet lifecycle | DIR-01, DIR-02, DIR-04, DIR-05; supports DIR-03; constrained by DIR-06 | `completed` | The human selected the narrow FS-01 envelope, canonically adopted verified FS-01 as the Foundation baseline, and approved this capability complete. Its evidence remains limited to the local fixture lifecycle. |
| MS-01: Foundation Slice close | The FS-01 subset of DIR-01, DIR-02, DIR-04, DIR-05; DIR-03 and full product use remain | `completed` | The 2026-08-04 one-time scoped acceptance replaces the former personal-observation gate. It records no human review, observation, CLI/output-clarity judgment, or D-01-fit proof; those remain accepted residual uncertainty. |
| DIR-INTAKE-01: Approved-Direction intake | DIR-01, DIR-02, and DIR-04; supports DIR-03 and DIR-05; constrained by DIR-06 | `completed` | Current-HEAD behavior now proves read-only preparation, exact separate Direction approval and ledger-write authority, immutable linear versions, stale/mismatched/open/pending/racing refusal, portable clone-readable history, shared FS-01 mutation coordination, recoverable atomic writes, and output consumed by `draft`. It adds no Rumble automation or provider path. |
| TLX-01: Trusted-local initial execution decision | Preserves coordinator-side DIR-02 and DIR-04 behavior; supports DIR-03 and DIR-05; does not prove executor containment | `completed` | The human selected an unsandboxed trusted-local initial mode, explicitly accepted its broad local-machine limitation, and retained sandboxing as a later path. This design decision authorizes no implementation or run. |
| PRV-01: One provider/host boundary | Enables DIR-03 and DIR-05 evidence; constrained by DIR-02, DIR-04, and DIR-06 | `completed for one proof` | CAP-02B selected local Codex CLI `0.146.0`, existing ChatGPT authentication/account controls, current public Second Mate data and target, normal provider/repository network access, ephemeral CLI storage, private-until-close transcript retention, exact-session/no-retry recovery, and `provider-billing-controls-only`. No API billing project or account setting changed. This boundary is consumed, not reusable. |
| LIVE-BOUNDARY-01: Trusted-local live-direct and recovery contract | Coordinator-side DIR-02 through DIR-05; does not prove containment after dispatch | `offline/fake proof reproducible; two live activations consumed` | CAP-02A reproducibly proves activation, lifecycle, no-retry recovery, evidence, and exact cleanup. CAP-02B is one partial historical terminal record. CAP-02C reproducibly proves the library boundary; its retained marker proves one disposable activation and frozen bindings are consumed, while the contemporaneous close records real transport, exact target output, conservative pre-turn-diagnostic ambiguity, stopped-process recovery, and exact abandoned cleanup as non-replayable history. The corrected argv has no terminal live proof. |
| CAP-02A: Offline trusted-local adapter implementation | Coordinator-side DIR-01 through DIR-05; constrained by the trusted-local limitation and DIR-06 | `completed` | One offline-only library adapter over an injected mock local control plane proves activation/basis matching, streamed JSONL lifecycle, exact session binding, interruption/failure ambiguity, persistent private state, no provider-as-proof promotion, and non-recursive identity-bound cleanup while preserving FS-01. It supplies no sandbox, credential, provider, production process, network, live target, CAP-02B, or token-cap implementation. |
| CAP-02B: One real trusted-local provider-owned direct run | Observed coordinator-side DIR-01 through DIR-05 only; no adversarial-containment claim | `historically closed once; retained evidence partial` | The retained marker proves one exact activation is consumed, and Git proves the two-path recovery fix. The contemporaneous close records a completed real lifecycle and exact cleanup, but those private artifacts were intentionally deleted and cannot be independently replayed now. No outside-machine-effects claim is made; retry is prohibited. |
| CAP-02C: Codex CLI process adapter | Coordinator-side DIR-02 through DIR-05; no usability or containment claim | `provider-free complete; one live unknown-running exercise consumed` | The library boundary remains reproducible with fake executables and has no CLI route. The retained marker proves the disposable activation and its hardened-binary/target bindings are consumed. The contemporaneous close records the intended file and deprecated-feature diagnostic that prevented a terminal claim; those raw observations were deleted. A red-green fix omits that default-disabled deprecated flag while retaining supported web-search denial; no second live dispatch occurred. |
| CONV-BRIDGE-01: Approved conversation handoff | DIR-01, DIR-02, DIR-04, and DIR-05; supports the normal-use requirement without granting execution | `decision-ready; not implemented` | A transport-neutral handoff must prepare one exact proposed Direction read-only, then require its digest-bound human approval and a distinct promotion-basis-bound one-ledger-write grant before existing immutable Direction promotion and draft creation. It must be idempotent, reject stale/mismatched/replayed authority, persist no raw conversation transcript, and stop at `ready-for-preflight`; it cannot manufacture route approval or Execution Consent. |
| RUN-FACADE-01: High-level Second Mate execution facade | DIR-02 through DIR-05; trusted-local limitations remain explicit | `blocked on CONV-BRIDGE-01` | After an approved handoff, Second Mate should resolve native executable/security and private-state details internally, show a concise human scope/effects/risk preview, require separate one-shot Execution Consent, and own lifecycle/evidence/recovery. First prove this end to end with fake/offline control planes; any live proof is a later separate activation. |
| EVA-01: Evidence-claim and lifecycle hardening | Truthful evidence classification plus coordinator-side DIR-02 and DIR-04 | `completed provider-free` | Every current status and checked readiness claim is classified as reproducible, retained, human-authority, structural, non-replayable, or open. Red-green repairs now preserve active/ambiguous forensics, minimize `skill_search`, and make configured package typing plus wheel metadata executable. |
| EVA-02: Remaining-plan and target/recovery hardening | Truthful dependency closure plus coordinator-side DIR-02 and DIR-04 | `completed provider-free` | The then-dormant adapter was changed to bind one resolved target root, independently recompute Git HEAD/fingerprint before local probes or activation consumption, cancel an exact still-owned process from the latest durable `unknown-running` state, and retain ownership if cancellation itself is ambiguous. Every then-open readiness item was classified without advancing an external gate. |
| EVA-03: Interrupted exact-cleanup recovery | Coordinator-side DIR-02 and DIR-04; no provider, target, or containment claim | `completed provider-free` | Exact cleanup now persists session intent plus directory-bound authorization before unlink, resumes only identity-recorded remaining artifacts or the same empty directory, rejects absent intent/authorization, artifact/directory replacement including inode reuse, and unexpected entries, and never widens the three-file deletion boundary. |
| EVA-04: Crash-safe cleanup-record persistence | Coordinator-side DIR-02 and DIR-04; no provider, target, or containment claim | `completed provider-free` | Cleanup-only session and marker updates append bounded, digest-checked records to the same identity-recorded files. Fresh recovery accepts only the last complete valid record plus an exact incomplete final frame, uses linear bounded parsing, re-syncs ambiguous visible updates before unlink, and refuses complete corruption or impossible lengths. |
| MS-02: Usable manually supervised trusted-local coordinator | One-provider direct-route scope with explicit trusted-local residual risk | `blocked on normal-use bridge and human product check` | The consumed CAP-02C exercise makes the current usability gap concrete: normal work still requires a bespoke Python harness and exposes low-level activation/preflight concerns. CONV-BRIDGE-01 and RUN-FACADE-01 must make a First Mate conversation the ordinary entry while preserving separate approval/consent and no-retry ownership. The human then judges observability, evidence, recovery, cleanup, and D-01 fit. Full executor containment remains unproved. |
| SBOX-01: Sandboxed hardening/deployment path | Strengthens DIR-02 and operational security evidence without changing the coordinator contract | `deferred` | Implement only when deployment, repository trust, data sensitivity, or pilot evidence requires containment. Qualify filesystem, environment, credential, network, optional-capability, cancellation, and cleanup behavior in the actual environment; failure must not downgrade to trusted-local automatically. |
| PILOT-SELECT-01: Medium pilot target and request | Enables pilot-scoped DIR-01 through DIR-06 evidence | `blocked` | MS-02 plus a baseline-known external target, approved Direction/route, bounded data authority, and separate pilot consent. Select it before CAP-03 so Map/Foundation behavior is earned by the real pilot. |
| CAP-03: Foundation-route records and Map frontier | DIR-01 through DIR-05; constrained by DIR-06 | `blocked` | PILOT-SELECT-01 and the limited FS-01 Backbone; implement only the minimal Foundation evidence and Map behavior the selected pilot requires. |
| MS-03: Medium Foundation-route pilot | DIR-01 through DIR-06 at the pilot envelope | `blocked` | CAP-02B, CAP-03, the selected external target, several one-or-two-at-a-time packets, one meaningful milestone, recovery evidence, stabilization, and separately scoped pilot authority. |
| CAP-04: Hardening or additional automation | Unassigned until evidence shows which Direction claim needs it | `uncertain` | Only repeated pilot failures may justify more persistence, roles, concurrency, UI, provider abstraction, or repository knowledge machinery. |

Binding DIR-01 through DIR-06 coverage is currently `still_remaining`. The
MS-01 scoped acceptance closes only the fixed FS-01 first workflow and does not
prove the unobserved qualities or the whole Direction. MS-02 or MS-03 must not
declare the whole Direction proven without evidence for the actual completion
claim.

CAP-02C and EVA-01 through EVA-04 are complete provider-free, and the one live
CAP-02C exercise is consumed without terminal proof. The newly accepted
normal-use requirement selects CONV-BRIDGE-01 as the smallest provider-free
frontier, then RUN-FACADE-01 and MS-02. PILOT-SELECT-01, CAP-03, and MS-03 remain
downstream. SBOX-01 is a separate deferred
hardening/deployment path and may be pulled forward only by an explicit trust,
data, deployment, or pilot need. The Map changes only from evidence or an
authorized Direction change. Distant candidates intentionally have no
packet-level implementation detail, and CAP-04 remains unassigned.

## 7. Frontier implementation packet IP-01

Evidence classification: **technically verified and canonically adopted within
the selected narrow envelope**. The implementation already exists, its
technical proof has been replayed, and CAP-01 and MS-01 are complete. MS-01 is
complete only under the 2026-08-04 scoped acceptance, not a human observation
or product-fit proof; its unobserved qualities remain accepted residual
uncertainty. The fixed FS-01 first workflow is terminal with no further user
decision. This historical packet must not be treated as prospective permission
to reimplement or expand FS-01.

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
items are recorded in the repository evidence review above. The human did not
personally observe the CLI/output journey or provide a D-01-fit judgment; the
one-time scoped acceptance completes MS-01 without claiming either, and they
remain accepted residual uncertainty. A green unit suite alone would not have
been completion; the dedicated fixture journey was replayed.

**Stop and recovery conditions.** Stop before mutation if any gate or baseline
is unclear. Stop during execution on scope/authority drift, an unapproved
external effect, a runtime decision that would broaden B-01, inability to
demonstrate pre-consent non-execution, or evidence that the atomic/recoverable
close design is false. Classify the smallest pressure layer; do not silently
expand the packet or reopen Direction.

**Unlock.** MS-01 completes only the fixed FS-01 first workflow. Any future
provider-adapter decision or packet remains separate unauthorized scope and
needs a new decision, current read-only preflight, and exactly fitting
Execution Consent.

### Completed frontier — DIR-INTAKE-01

**Outcome.** An operator can prepare exact Direction text without target
mutation, record exact human Direction approval separately from ledger-write
authority, append an immutable approved version, and emit the existing
Direction schema consumed by `draft`.

**Boundary.** Port behavior, not commits, from the preserved
`rumble-direction-handoff` branch onto current HEAD. Preserve external/manual
Rumble and keep raw transcript, prompt source, provider metadata, credentials,
and private reasoning outside repository authority. Durable Direction history
must remain portable and must not retain an absolute checkout path. Do not add
model calls, automated Rumble, provider execution, route/Map logic, voice
integration, transcript persistence, or a generic workflow/schema framework.

**Proof.** Use test-first D-01 and D-02 end-to-end journeys; prove no-write
preparation, separate approval and promotion authority, immutable linear
history, stale/mismatched/racing/open-run refusal, current schema-v2 recovery
compatibility, clone-readable durable Direction, integration with `draft`, all
existing FS-01 evidence, full repository gates, build/wheel smoke, and an
independent authority review.

**Result.** The exact test-first plan, fresh preflight, and separately fitting
Execution Consent were supplied. The current implementation adds one
repository-wide mutation lock, portable immutable Direction history, separate
candidate/approval/promotion records, `direction prepare/promote/show`, and the
[operator flow](DIRECTION-OPERATOR.md). Focused Direction tests cover D-01 and
D-02, missing/mismatched authority, stale revisions, ignored or missing
history, open and closed FS-01 state, competing promotions, atomic install and
append races, marked partial-write recovery, post-exchange exact retry, clone
reconstruction, and existing-`draft` consumption. The integrated suite passes
219 tests. Full
close verification also passes Ruff lint and formatting for 33 files, strict
mypy for nine source files, 26 dedicated Direction-plus-FS-01 end-to-end tests,
source and wheel builds, source-package inclusion of the Direction guide, and
an isolated wheel install/import plus all Direction CLI help paths. This local
completion creates no commit or push.

**Unlock and limit.** DIR-INTAKE-01 completes only manual approved-Direction
intake. It does not prove automated or high-quality Rumble, route/Map execution,
a provider run, or pilot usefulness. TLX-01 separately selects the initial
trusted-local containment posture but authorizes no implementation or run.
At this packet's close, PRV-01 was the next provider decision/evidence packet;
no provider probe or CAP-02 implementation was authorized by either completion.
The separate CAP-02A and CAP-02B records in section 1 govern their later,
narrower work.

### Completed frontier — CAP-02A trusted-local offline adapter

**Outcome.** From an exact coordinator basis and matching unsandboxed
activation record, an offline adapter drives one injected mock local control
process, binds the first valid Codex JSONL session identifier, records a
truthful terminal or `unknown-running` lifecycle, and leaves provider output
explicitly insufficient for target evidence.

**Boundary.** Add one focused trusted-local module and focused tests. The
activation contract represents broad local execution authority, the exact
machine-risk acknowledgments, `provider-billing-controls-only` spend policy,
and `exact-private-run-artifacts-only` cleanup. The control plane is injected
and has no production subprocess/provider implementation or CLI route in this
packet. Do not authenticate, create or use credentials, select a billing
project, call a provider, configure the system, dispatch an agent or real
process, touch a live target, add a sandbox, begin CAP-02B, push, or commit.
Preserve all FS-01 schemas, behavior, and tests.

**Lifecycle and evidence.** Validate the activation independently against the
coordinator basis before creating run state or invoking the control plane.
Persist one owner and mock process identity in an owner-private run directory.
Claim a separate owner-private one-shot activation marker before that directory
is created and retain it after cleanup so deletion cannot make authority
reusable.
Parse bounded UTF-8 JSONL with duplicate-field rejection; the first exact
`thread.started` UUID binds continuation, and a duplicate or changed session,
malformed/truncated event, ambiguous exit, read/wait failure, or cancellation
becomes `unknown-running`. Only a matching `turn.completed` plus successful
process exit is adapter-complete; a validated `turn.failed` is failed. Neither
state closes target evidence: final revision, changed paths, and claim-fit tests
remain independently required.

**Cleanup.** Create only `session.json`, `transcript.jsonl`, and `control.tmp`
inside one dedicated owner-private run directory, record their physical
identities, and expose only explicit cleanup. Cleanup validates the root,
directory, exact names, types, identities, and absence of unexpected entries
before unlinking anything. It never recurses, accepts provider-supplied paths,
touches repository/system files, reverts work, calls provider deletion, or
claims provider-side erasure. Cleanup attests but retains the one-shot
activation marker.

**Proof.** Use red-green tests for exact authority binding and no-launch
refusal; valid and split JSONL; duplicate, malformed, oversized, truncated, and
out-of-order events; completed, failed, cancelled, and ambiguous exits; private
state reload; cleanup success with unrelated sentinels preserved; cleanup
refusal on replacement or unexpected files; the full existing suite, lint,
format, type, build, package, and isolated-install gates. Completion changes
only CAP-02A/LIVE-BOUNDARY-01 evidence. At this packet's close, CAP-02B remained
blocked and needed separate authority.

**Result.** The production package adds one `trusted_local` module and public
library exports, with no CLI route or production control-plane implementation.
Forty-one focused tests cover all eight authority bindings, exact activation
policies, offline-only and disjoint-private-root refusal, single ownership,
split and adversarial JSONL, uncapped transcript retention with bounded parser
state, exact session binding, successful and failed terminals, ambiguous
launch/read/wait/exit, cancellation, no implicit retry, durable restart,
identity drift, unexpected entries, session-record drift, and sentinel-safe
cleanup. Hard-link safety, contradictory failure/exit state, and durable
post-cleanup activation consumption are explicit regressions. The complete
260-test repository suite passes unchanged FS-01 and
Direction behavior. Ruff lint and formatting for 36 files, strict mypy for ten
source files, offline frozen environment checks, source/wheel builds, source
guide inclusion, and an isolated wheel import/CLI smoke all pass. Source is
5,726 handwritten Python lines excluding tests, within the Program's scope
pressure range. No credential, provider, network, real process/agent, live
target, system configuration, CAP-02B, commit, or push was used.

**Historical next gate.** CAP-02A supplied neither a provider decision nor run
authority. PRV-01 and CAP-02B were later resolved only for the separate consumed
proof below.

### Completed frontier — CAP-02B one-run trusted-local proof

**Outcome.** Use one exact real local Codex host to audit CAP-02A's activation,
streamed JSONL lifecycle, recovery classification, and exact private-artifact
cleanup against the current public Second Mate branch. Fix at most one proved
defect with a regression; otherwise change nothing.

**Boundary.** The frozen target was public branch
`gnhf/bring-the-first-inte-1c3fd1` at
`94c21707ab13294b8e756049691e89cba1c91725`. The selected host was local Codex
CLI `0.146.0` using the already authenticated ChatGPT account, normal provider
and repository network access, ignored user configuration, ephemeral CLI
session storage, and no Second Mate spend cap beyond existing account/provider
controls. Permitted repository writes were only
`src/second_mate/trusted_local.py` and `tests/test_trusted_local.py`. One-shot
activation `cap02b-20260804t224244z-94c21707-audit01` allowed exactly one
dispatch and prohibited resume, retry, another provider call, credential or
account/billing change, system configuration, unrelated paths, push, and PR.

**Lifecycle and retained evidence.** The contemporaneous private-envelope close
records the current revision and fingerprint, Direction/packet/preflight/provider
digests, allowed paths, risk acknowledgments, cleanup policy, one owner, a bound
session, 31 strict JSONL events, a final `turn.completed`, and process exit zero.
Those transcript, session, control, and close documents were then intentionally
deleted under the recorded cleanup policy, so this checkout cannot replay those
event-level or cleanup details. Provider output remains only a historical claim.

What is independently retained is narrower: the mode-`0600` consumed marker
binds the exact activation, owner, provider digest, frozen target and fingerprint;
Git commit `3ecf0fe` modifies exactly the two authorized paths and contains the
signal-exit regression plus minimal predicate fix; the current suite replays
that recovery behavior. These artifacts do not prove the deleted 31-event stream,
the original final-gate run, or the physical identities removed at cleanup.

**Defect and close.** The run reproduced one recovery defect before mutation:
a valid `turn.failed` followed by a signal-style negative process return code
was persisted as definitive `failed`, although signal termination cannot prove
an orderly terminal. A regression failed with observed `failed` versus required
`unknown-running`; the minimal fix accepts only a strictly positive return code
as corroboration. The contemporaneous review records a replay of the green
regression, 42 adapter tests, 261 repository tests, and all repository proof
gates. Git independently shows that only the two authorized paths were committed
as `3ecf0fe`; current tests reproduce the signal-exit behavior. The historical
command output is not retained. No push occurred.

The contemporaneous close records clean-close evidence digest
`21a5c91a5c2c4d11c85c24fcdd00c54a8570683c1e64a43f465e881ae7e8cbf6`
before deletion and states that cleanup identity-checked and removed only the
exact private transcript, control, session files, and empty run directory. The
digest document and identities are not retained for replay. The consumed marker
does remain, so the activation cannot be reused. No provider-side deletion or
absence of unrelated-machine effects is claimed.

**Limit.** CAP-02B is historically closed once and independently retains one
consumed marker plus one recovery correction. Its event-level and cleanup close
are non-replayable records, not current checkout proof. It does not add a production subprocess
implementation or trusted-local CLI route, prove sandbox containment, establish
reusable provider authority, close broader Direction coverage, or prove product
usability. MS-02 now blocks on its required human product check; technical
evidence cannot manufacture that judgment.

### Completed provider-free frontier — CAP-02C Codex CLI process adapter

**Outcome.** Prepare the smallest reusable trusted-local process path without
calling a provider: from one exact CAP-02A activation and a matching immutable
Codex CLI boundary, launch one local process, stream its stdout through the
existing JSONL lifecycle, retain stderr privately, bind the process identity,
and preserve conservative cancellation and restart behavior.

**Chosen shape and rejected alternatives.** A command builder alone would not
prove streaming, descriptor ownership, process identity, or process-group
cancellation. A user-facing command would create an avoidable real-dispatch
surface before another activation exists. At that provider-free close, CAP-02C
therefore added a dormant library adapter whose complete process behavior was
exercised against a
temporary fake executable. The public entry remains the activation-validating
adapter; the subprocess control plane stays private, one-shot, and unavailable
as a standalone dispatch API.

**Frozen boundary.** Bind an absolute unaliased executable and its SHA-256,
exact `--version` text and `exec --help` digest, explicit model, raw-prompt
digest, exact environment names plus value digests, fixed capability-reduction
arguments, and bounded interrupt/terminate timings into the provider-boundary
digest. Runtime environment values and the raw prompt remain memory-only.
Qualification runs only the selected executable's local `--version` and
`exec --help` probes, refuses target-local `.codex/config.toml`, and completes
before activation consumption or private run state. Launch uses stdin for the
prompt, JSONL stdout, the exact identity-recorded `control.tmp` for stderr,
ephemeral session storage, ignored user configuration, no MCP configuration,
explicitly disabled optional app/browser/computer/hook/plugin/subagent/web
features, fixed repository working directory, and unsandboxed trusted-local
mode. These switches minimize capability; they do not create containment.

**Lifecycle and recovery.** Reuse CAP-02A authority, marker, session, transcript,
strict JSONL, independent-evidence, load, and exact-cleanup behavior. Add the
control path and physical identity to the internal launch request. The process
must start in its own session/process group and record a Linux boot/start-time
token before it can become `running`. Cancellation verifies that identity and
uses bounded `SIGINT`, `SIGTERM`, then `SIGKILL`; the durable result remains
`unknown-running` because a cancellation request is not completion proof.
Launch, prompt-write, stream, wait, signal, identity, or exit ambiguity never
retries and never becomes successful evidence.

**Test-first proof.** First add failing tests that name the important breaks:
boundary mismatch, binary or probe drift, prompt/environment drift, forbidden
target config, and a second launch all refuse without dispatch; a real temporary
fake executable receives the hand-derived exact argv/prompt/environment,
streams split JSONL, writes stderr only to the private control artifact, and
finishes through the existing adapter; an uncooperative fake process is stopped
through its owned group while the run stays `unknown-running`; reload cannot
reattach or retry; exact cleanup preserves unrelated sentinels. No test or
qualification may execute the installed Codex binary beyond the already
recorded read-only version/help/features inventory, contact a provider, inspect
auth, or use a real target. Preserve FS-01 and all existing trusted-local regressions,
then run the complete lint, format, type, test, frozen-environment, build,
package-content, and isolated-install gates.

**Result.** The package exports `CodexCliProviderBoundary` and
`CodexCliTrustedLocalAdapter` while keeping the subprocess control plane
private and adding no CLI route. Twelve focused tests prove authority/boundary
refusal, exact local probes, prompt/environment drift, target-config refusal,
descriptor-bound replacement resistance, real fake-process streaming and
private stderr, one-shot activation, group cancellation with a child process,
transcript-tail retention, restart-to-unknown, and sentinel-safe cleanup. All
54 trusted-local tests and the complete 273-test repository suite passed at the
CAP-02C close. Ruff,
strict mypy for eleven source files, offline locked-environment, source/wheel,
package-content, and isolated wheel import/CLI smoke gates passed at that close.
Source was 6,357 handwritten Python lines excluding tests, within the Program's scope
pressure range. Commits `cad7f0b` and `041697b` record the frozen packet and
test-first implementation. No `codex exec`, authentication inspection,
credential use, provider/network call, real activation, live target, system
configuration, `firstmate/` change, push, or PR occurred; the installed CLI was
used only for local version/help/features inventory.

**Stop.** Completion may update only the adapter source/exports, focused tests,
and fitting Program/checklist/workflow/operator/package documentation, then
commit locally. It does not add a CLI route, activate the adapter, reuse
CAP-02B, establish current provider authority, close MS-02, select a pilot,
contact a provider, push, or open a PR. A future real adapter run still requires
a new exact model/host/auth/data/target boundary, current preflight, and
one-shot human activation.

This stop records the historical provider-free close. The separately granted
2026-08-06 exercise later activated the library once and is governed by the
newer authority and evidence records in section 1; it did not retroactively
widen this packet.

### Completed frontier — EVA-01 evidence-claim and lifecycle hardening

**Outcome.** Make the canonical status reconstructible without treating its own
prose as proof, and repair only provider-free defects that directly contradict
an existing completion or safety claim.

**Evidence model.** Classify each Program status and checked readiness item as
one of four things: currently reproducible executable/structural evidence;
retained independent historical evidence; an exact human decision or authority
record; or a historical close assertion whose underlying private artifact was
intentionally deleted. A decision may remain accepted, but a deleted transcript
or close document must not be described as independently replayable from the
checkout. Open human, provider, target, sandbox, and pilot gates remain open.

**Bounded repairs.** First reproduce each technical contradiction. Cleanup must
refuse an active run and require an explicit recovery disposition before an
`unknown-running` envelope can lose its forensic artifacts. The fixed Codex argv
must disable the already inventoried `skill_search` optional surface in addition
to the existing effect surfaces. The configured no-argument strict-mypy package
gate must work and the wheel must carry the standard typed-package marker. Do
not redesign launch/resume, add a command, activate an adapter, or infer
containment.

**Test-first proof.** Add one failing behavioral regression per repair and name
the production change that makes it pass: an active cleanup refusal plus an
explicit unknown-running recovery gate; an argv assertion independent of the
production disabled-feature tuple; and an importable packaged `py.typed`
marker. Observe each red failure before the minimal implementation. Then replay
the complete trusted-local, fixture, Direction, lint, format, configured strict
mypy, locked-offline environment, build, package-content, and isolated-wheel
smoke gates. No installed Codex executable or provider is used.

**Result.** Five focused red failures first reproduced active, undispositioned,
and still-owned-process cleanup hazards, the missing `skill_search` launch
argument, and the missing typed-package marker. The minimal implementation
refuses cleanup in `launching` or `running`, requires exact
`recovery_disposition="abandoned"` for `unknown-running`, preserves artifacts
while the adapter still owns the process, adds `skill_search` to the immutable
disabled-feature policy, and packages `py.typed`. Fifty-seven trusted-local
tests and all 277 repository
tests pass. Ruff checks and formatting cover 38 Python files; both configured
and explicit strict mypy pass across 11 modules; locked-offline sync, source and
wheel builds, package-content inspection, and isolated wheel import/CLI/type-
marker smoke pass. Source is 6,381 handwritten Python lines excluding tests.
The evidence audit downgrades deleted CAP-02B lifecycle/cleanup details to
non-replayable historical records while retaining the consumed-marker and
two-path-fix evidence. No Codex executable, provider, credential/authentication
state, live target, `firstmate/`, system configuration, push, or PR was used.
Commits `47804bd` and `eda5d19` record the frozen packet and implementation.

**Stop.** Update only the trusted-local adapter, focused tests, packaging marker,
and canonical/operator wording required by the audit. Preserve the consumed
CAP-02B marker and all repository/user data. Do not close MS-02, prepare a pilot,
touch `firstmate/`, push, or open a PR.

### Completed frontier — EVA-02 remaining-plan and target/recovery hardening

**Outcome.** Exhaust the remaining provider-free plan work without promoting a
documentation assertion into proof. Correct two current CAP-02C boundary gaps,
reconcile the unrecorded `196dbbc` cancellation-drain repair, and leave every
other open item attached to its exact human, provider, sandbox, target, or pilot
dependency.

**Target binding.** Extend the immutable CAP-02C provider boundary to bind one
absolute resolved target root. Before the executable version/help probes or
activation consumption, inspect the actual Git worktree through the existing
read-only revision inspector and require its root, HEAD, and visible fingerprint
to match the provider boundary and frozen trusted-local basis. An identical
clone is a different target and target drift fails before a fake process can be
launched.

**Unknown-running recovery.** Preserve `unknown-running` as the durable result
of stream or cancellation ambiguity, but allow an explicit cancellation call
on that latest state when this adapter still owns the exact recorded process.
The owned Linux process group must receive the same bounded cancellation,
available transcript tail must be retained when safe, and cleanup must remain
blocked until ownership is released or recovery reloads without reattachment.

**Test-first proof.** First add focused failures showing that current target
drift and an identical clone reach probes/launch, and that a real fake-process
group remains alive when `finish` returns `unknown-running` before cancellation.
Also prove that signal ambiguity cannot silently release in-memory ownership.
Make the minimum implementation pass, then retain existing mismatch,
replacement, JSONL, private-stderr, process-group, one-shot, recovery, cleanup,
FS-01, Direction, package, type, lint, build, and isolated-install evidence. Use
only temporary Git repositories and fake local executables.

**Remaining-plan audit.** For each unchecked readiness item, record whether a
current narrow subset is reproducible, the item is deliberately contingent and
therefore not selected, or completion needs a human product decision, a model
run, sandbox qualification, an external target, pilot authority, or pilot
observations. Do not implement a generic Map, Rumble, model router, sandbox, or
pilot merely to turn a policy sentence into a checked box.

**Result.** Plan commit `79592eb` and implementation/evidence commit `503048e`
close the bounded packet. Five focused red-green regressions prove target
revision drift, identical-clone substitution, relative-root refusal,
cancellation from durable `unknown-running`, and ownership retention when the
signal sequence is ambiguous. Final evidence passed 63 trusted-local and 283
total tests, all lint/format and configured/strict type gates, locked-offline
sync, source/wheel build and contents, and isolated wheel import/CLI/type-marker
and target-binding smoke. The implementation inventory is 6,408 handwritten
Python lines excluding tests. The complete unchecked-item audit leaves no
provider-free implementation selected before MS-02.

**Stop.** This packet may update the CAP-02C boundary and focused tests plus the
canonical/operator documentation needed for truthful close, then commit
locally. It adds no CLI dispatch route, contacts no provider, reuses no CAP-02B
authority, closes no MS-02 or pilot gate, changes no system configuration or
user data, does not touch `firstmate/`, and does not push or open a PR.

### Completed frontier — EVA-03 interrupted exact-cleanup recovery

**Outcome.** Make an interrupted exact-private-artifact cleanup recoverable
without broadening what Second Mate may delete or treating missing evidence as
a successful clean close.

**Durable intent.** Before the first unlink, rewrite the already
identity-recorded `session.json` to a `cleanup-pending` phase only after the
current phase/disposition, consumed marker, exact directory set, session, and
all three physical identities pass. Then enrich the already-retained
consumption marker with cleanup authorization bound to the exact run-directory
device/inode and the private root's directory-change identity. The latter
detects remove/recreate even if the filesystem immediately reuses an inode.
The marker remains one-shot authority history; add no new file, path, or
deletion target.

**Exact resumption.** Fresh reload may accept a subset of the three recorded
artifacts only when the surviving identity-recorded session proves
`cleanup-pending` and the marker's cleanup authorization matches the physical
run directory plus unchanged private-root directory state; it validates every
remaining identity before deleting only those names. If the session was
already removed and only the exact empty run directory remains, recovery may
remove only that same identity-bound directory under the unchanged private root.
Any absent cleanup authorization, directory replacement, nonempty partial
directory without durable intent/session, artifact replacement, or unexpected
entry remains a refusal.

**Test-first proof.** First inject failure after one successful unlink and show
that current reload rejects the partial directory. Then inject final-directory
removal failure and show that current reload rejects the empty run directory.
The minimum implementation must make both resumable from a fresh adapter while
preserving marker consumption, unrelated sentinels, active/unknown ownership
gates, pre-delete identity refusal, and every existing test. Also prove that an
empty pre-session directory and an empty replacement directory are refused,
and that cleanup interrupted before the first unlink or with only the session
remaining can resume without widening authority.

**Result.** Plan commit `0b87907`, safety-correction commits `9e8eb35` and
`1b215ba`, and implementation/evidence commit `a44c7b0` close the packet. Ten
interruption/adversarial cases prove fresh recovery before any unlink, after
one unlink, with only the session remaining, and after final-directory failure;
they also refuse absent authorization, missing intent/session, unexpected or
replaced artifacts, and an empty replacement even when run-directory inode
reuse is simulated. A warnings-as-errors audit separately exposed and repaired
a stopped-process stdout leak when cancellation-drain setup fails. Final
evidence passed 73 trusted-local and 293 total tests, full Ruff lint/format,
strict mypy for 11 modules, locked-offline sync, source/wheel build and
contents, isolated wheel import/CLI/type-marker smoke, and one independent
read-only review plus focused re-review. The implementation inventory is 6,672
handwritten Python lines excluding tests.

**Stop.** Update only the trusted-local coordinator, its focused tests, and the
canonical/operator wording required for truthful close, then commit locally.
Do not add recursive deletion, a cleanup CLI, provider/session deletion,
repository rollback, dispatch, credentials, network use, CAP-02B replay,
system changes, `firstmate/`, push, PR, or MS-02 judgment.

### Completed frontier — EVA-04 crash-safe cleanup-record persistence

**Outcome.** Preserve the last complete session and consumption-marker record
when interruption occurs during cleanup-intent or cleanup-authorization
persistence, so a fresh adapter can safely retry before any unlink without
weakening corruption or identity refusal.

**Record protocol.** Keep the original deterministic strict-JSON document as
the backward-compatible first record. Cleanup-only updates append a bounded
versioned frame containing an exact byte length, SHA-256 digest, and another
strict-JSON document to the same already-validated `0600` inode, then `fsync`
that inode. A reader selects only the latest complete, digest-valid, strict
record. It may ignore only a structurally exact incomplete final frame; a
complete malformed frame, bad digest, non-frame suffix, unsafe inode, or
oversized record fails closed. Before retry, truncate only the incomplete tail
back to the last validated record, `fsync`, and append again. Add no sidecar,
temporary path, artifact name, recursive operation, or provider/session effect.

**Test-first proof.** First inject partial `os.write` interruption against the
cleanup-pending session append and the marker-authorization append and prove
that fresh load currently fails on invalid JSON. The minimum repair must make
both paths reloadable and exactly cleanable while preserving the consumed
marker and unrelated sentinels. Add adversarial cases proving that a complete
bad-digest frame and a non-frame suffix remain refusals, then replay the full
trusted-local, warnings-as-errors, lint, format, strict-type, locked-offline,
build/package-content, and isolated-wheel gates.

**Result.** Plan commit `0f6fc45` and implementation/evidence commit `bb7b7f7`
close the packet. Cleanup-only updates now append a fixed versioned prefix,
bounded length, SHA-256 digest, and deterministic JSON to the same file inode.
The reader performs a linear structural scan, accepts only the latest complete
valid record plus an exact viable incomplete final frame, and refuses complete
corruption, non-frame suffixes, impossible or oversized lengths, and unsafe
identity. Retry truncates only the incomplete tail and re-`fsync`s any visible
cleanup-pending session or marker authorization before unlink, including after
an ambiguous prior `fsync`. Red-green and adversarial coverage raised the
trusted-local suite to 95 tests and the full warnings-as-errors suite to 315;
Ruff lint/format, strict mypy for 11 modules, locked-offline sync,
source/wheel build and contents, and isolated wheel import/CLI/type-marker
smoke also pass. Independent specification and quality re-reviews found no
remaining Critical or Important product-path defect. The implementation
inventory is 6,893 handwritten Python lines excluding tests.

**Stop.** Update only `trusted_local.py`, its focused tests, and the canonical
and trusted-local operator wording needed for a truthful close, then commit
locally. Do not replace identity-bound files, add cleanup artifacts or paths,
weaken complete-record validation, contact a provider, inspect credentials,
reuse CAP-02B, touch `firstmate/`, change the system, push, open a PR, or close
MS-02.

## 7A. Next decision packet — CONV-BRIDGE-01

Status: **decision-ready, not implemented or authorized by this close**.

**Verified current gap.** A normal conversation cannot enter Second Mate today.
The supported CLI requires the operator to prepare/promote Direction, export it,
create a packet/draft, and later construct preflight and grant files manually.
`CodexCliTrustedLocalAdapter` is a library type with no supported launch facade;
the disposable exercise required a bespoke Python harness and direct knowledge
of executable path, mode, hashes, environment digests, activation JSON, and
private-state paths. Second Mate already owns the underlying immutable Direction,
mutation coordination, one-shot activation, evidence, ambiguity, and cleanup
mechanics, but no boundary connects those mechanics into the conversational
experience the user selected.

**Smallest provider-free outcome.** Add one transport-neutral
`ConversationHandoff` boundary with a read-only preparation step and an exact
apply step. A First Mate-produced proposal first yields the existing candidate,
digest, promotion basis, and concise human review view without writing. The
apply envelope then carries a schema version, source conversation identifier,
target repository identity, proposed Direction identifier/summary/constraints/
acceptance text, candidate digest, a separate approval record naming approver,
decision, time, and that same digest, plus a distinct digest-and-basis-bound
promotion grant for the one Direction-ledger write. It must persist no raw
conversation, private reasoning, model transcript, credential, provider session,
or activation internals.

**Authority and lifecycle.** Conversation research may propose scope; it may not
approve it or grant a repository write. Direction approval, the one-ledger-write
promotion grant, route approval, and later Execution Consent remain distinct
authority states, even if an ordinary interface captures more than one explicit
decision in the same human interaction. Import is idempotent for the exact
envelope and refuses a replayed identifier with different bytes, stale target or
promotion basis, digest, approver, grant, or allowed-path mismatch,
rejected/absent approval, absent promotion authority, non-linear Direction
history, or an open mutation/close. On success it reuses current Direction
promotion and draft construction and returns a concise `ready-for-preflight`
view: approved outcome, target, allowed/prohibited effects, evidence expectation,
and the next human decision. It performs no provider probe, activation, target
mutation beyond the exact Direction-ledger write, or execution.

**Test-first proof.** Begin with one end-to-end red test from a literal handoff
fixture through approved Direction history and draft output. Add focused red
cases for absent or mismatched approval, absent/mismatched promotion authority,
promotion-basis drift, same-ID/different-bytes replay, stale target, concurrent
import versus FS-01 mutation, and interruption recovery.
Existing DIR-INTAKE and FS-01 tests remain unchanged. Close with full warnings-
as-errors tests, Ruff, format, strict mypy, locked-offline sync, build/package,
and isolated-install smoke. No provider, authentication, live adapter, network,
system configuration, `firstmate/` change, push, or PR belongs to this packet.

**Following packet, not bundled.** RUN-FACADE-01 may then wrap current preflight
and trusted-local lifecycle behind one high-level service/command. It should
resolve executable identity and private storage internally, surface insecure
installation or target conditions as concise refusals, show one human-readable
scope/effects/risk preview, and require a separate digest-bound one-shot
Execution Consent before any launch. Prove it first with offline/fake control
planes. Only after that facade is usable may the human perform MS-02 and decide
whether a new disposable terminal live proof is worth a separate activation.

## 8. Traceability and readiness

| Outcome | Requirement | Risk or constraint | Design response | Responsibility | Required evidence |
|---|---|---|---|---|---|
| Human meaning survives implementation | Immutable Direction and separate coverage | Direction drift or silent deferral | Direction Version, exact approval, separate coverage status | Human approves; coordinator preserves | Approval record plus mapped evidence at close |
| Normal conversation reaches the coordinator safely | Explicit proposed Direction handoff with separate approval and execution consent | Conversational assent is inferred as run authority or low-level machinery becomes the user experience | Digest-bound handoff, immutable Direction import, high-level preflight/consent facade, one-shot ownership | First Mate proposes; human approves/consents; Second Mate owns execution and recovery | End-to-end handoff refusals, fake-process facade proof, then human MS-02 observation |
| No mutation is laundered through planning | Draft, preflight, consent, mutation order | Stale or inferred authority | Bound digests/fingerprints and executor guard | Human grants; coordinator validates | Negative no-call/no-change tests and grant record |
| Trusted-local risk is not laundered into containment | Explicit mode and per-run activation acknowledgment | Broad account access or outside effects are mistaken for bounded execution | Separate trusted-local contract, narrow evidence claim, and deferred SBOX-01 | Human accepts the exact environment; coordinator records and limits its claim | Activation record, target proof, residual-uncertainty record, and no containment claim |
| Completion is truthful and recoverable | Claim-fit proof and all-or-recoverable close | Plausible output or partial writeback | Evidence Record and Clean Close | Working agent produces; coordinator validates/persists | Clean replay, failure injection, exact revision |
| Product remains lean | One local run and earned mechanisms only | Recreating First Mate/control-plane scope | FS-01 exclusions and evidence-gated Map | Planner and human at route gate | Diff inspection, dependency review, pilot observations |
| A fresh agent can continue | Durable compact handoff | Private reasoning or stale backlog becomes authority | Repository-local state and only one detailed frontier packet | Coordinator writes; next agent verifies | Clean-checkout reconstruction and handoff review |

### Readiness gates

- **Planning-ready:** POL-01, FS-01/CAP-01, DIR-INTAKE-01, TLX-01, PRV-01,
  CAP-02A/C, and EVA-01 through EVA-04 are closed within their stated evidence
  limits. CAP-02B and CAP-02C each have one consumed live activation; the latter
  remains a nonterminal live record with a provider-free correction. The next
  planning boundary is CONV-BRIDGE-01, then RUN-FACADE-01 and the MS-02 human
  product check. None authorizes a second provider run, credential/account
  change, target mutation, or pilot.
- **Trusted-local activation-ready:** CAP-02A is independently proved offline.
  The contemporaneous record says CAP-02B satisfied this gate once; the retained
  marker independently proves its exact bindings and consumption, not its
  deleted lifecycle. CAP-02C supplies reusable process mechanics and one
  consumed `unknown-running` exercise whose corrected argv has no second live
  proof. Both activations are exhausted. Every future run must re-resolve the
  current host/version/model,
  authentication/account boundary, data and intended network effect, spend
  boundary, retention, cancellation, continuation, target, risk acknowledgment,
  and Execution Consent defined in `TRUSTED-LOCAL-OPERATOR.md`.
- **Foundation-execution-ready:** the historical FS-01 implementation is not
  replayed as a new packet. The narrow envelope adopted FS-01 only; any new
  Validation or Foundation mutation or expansion needs its own current
  non-mutating preflight and exactly fitting Execution Consent.
- **Pilot-ready:** MS-01 is complete only under its documented limited scoped
  acceptance; CAP-02B has a narrow historical close with only partial retained
  evidence. MS-02 and
  PILOT-SELECT-01 remain open; a pilot still needs a known baseline, bounded
  data/provider authority, approved Direction and route, the applicable new
  trusted-local activation or separately proved sandbox boundary, and
  claim-fit milestone proof.
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

No further FS-01, DIR-INTAKE-01, PRV-01 proof-run, CAP-02B replay, or CAP-02C
replay decision is requested. Both live activations are consumed and must not
be retried, resumed, or redispatched. The accepted product direction makes the
next decision concrete: authorize or revise provider-free CONV-BRIDGE-01, the
smallest packet that turns an explicitly approved First Mate conversation
handoff into durable Direction and a preflight-ready draft. It does not call a
provider or grant Execution Consent.

Use the [MS-02 operator walkthrough](MS-02-OPERATOR-WALKTHROUGH.md) for the
provider-free hands-on fixture journey, expected evidence, D-01 acceptance
questions, failure handling, and the exact limits of both consumed live records.

After CONV-BRIDGE-01 and RUN-FACADE-01 are observable, the review should record
one bounded outcome: accept MS-02 within its evidence limits or keep it open and
name the remaining usability gap. If terminal corrected-adapter operation is
still decision-changing, that is a distinct future live dispatch requiring a
new exact provider/target boundary, preflight, and one-shot activation; this
Program does not authorize it.

Until the bridge and check are recorded, PILOT-SELECT-01, CAP-03, and pilot work
remain blocked. A later live run needs a new current provider/target boundary,
preflight, and one-shot activation. No provider retry/call, credential or
account/billing change, live-target activation, pilot, push, publication,
deployment, or other external work is authorized by this close.

## 11. Continuation prompt while human gates are open

> Read `docs/second-mate/PROGRAM.md` and the canonical workflow specification.
> Do not reimplement FS-01 merely because its historical branch remains visible;
> it is already merged. First verify the recorded human decisions, including
> the selected narrow POL-01 envelope, canonical FS-01 adoption, CAP-01
> completion, and the 2026-08-04 scoped MS-01 acceptance. Treat the existing
> implementation and evidence as limited to the fixture lifecycle, not as proof
> of a broader product or a future grant. The fixed FS-01 first workflow is
> terminal; do not request another FS-01 decision or manufacture a human
> observation, clarity judgment, or D-01-fit proof. DIR-INTAKE-01 is locally
> complete; use `DIRECTION-OPERATOR.md` and treat the preserved branch only as
> historical evidence, not as code to merge or a source that elevates its
> placeholder prompt. TLX-01 selects trusted-local unsandboxed execution only
> through an exact per-run activation; read `TRUSTED-LOCAL-OPERATOR.md` and
> preserve its limitations. CAP-02A is the offline reference adapter. CAP-02C
> is a library-only process adapter with no CLI command. Its retained marker
> proves one disposable real activation and its bindings are consumed. The
> contemporaneous close records `unknown-running`, exact target output, strict
> refusal of a false terminal claim, stopped-process recovery, and abandoned
> cleanup, but the raw artifacts are deleted and those observations are
> non-replayable. The deprecated flag was removed under provider-free regression
> only. The retained markers for both
> CAP-02B and CAP-02C are exhausted authority. Do not resume, retry, redispatch,
> or infer a corrected live result from either run. The selected provider-free
> frontier is CONV-BRIDGE-01, which must preserve separate Direction approval,
> ledger-promotion authority, route approval, and Execution Consent. SBOX-01 preserves
> sandboxing as deferred hardening and must never silently downgrade if later
> requested. MS-02 is blocked on a real human product check; do not manufacture
> it. Prepare only non-live prerequisites. Do not probe or call a provider,
> inspect credentials, select or mutate a live target, start a pilot, or add
> generalized orchestration without its own decisions, current preflight, and
> exactly fitting authority. Stop and
> classify pressure if
> Direction, Backbone, authority, or proof no longer fits. Do not publish,
> deploy, or push.
