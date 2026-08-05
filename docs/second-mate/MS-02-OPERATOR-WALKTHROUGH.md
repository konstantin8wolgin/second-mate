# MS-02 usability-acceptance walkthrough

Status: operator aid for the open human MS-02 product check; not acceptance,
Execution Consent, or trusted-local activation

This walkthrough lets the operator handle the prototype that exists today and
then judge it against approved Direction D-01 in [PROGRAM.md](PROGRAM.md). It
uses only the deterministic FS-01 fixture in a disposable local Git worktree.
It does not inspect authentication, call a provider, use the dormant Codex
adapter, replay CAP-02B, or prove that a working model has useful autonomy.

## The decision this supports

MS-02 asks whether the current manual experience is a usable, lean coordinator
for one supervised run: meaning and mutation authority remain distinct,
preflight binds the current target, evidence does not overclaim, failure is
recoverable, and a fresh operator can understand the durable handoff.

The approved D-01 criteria are:

- preserve the human-approved outcome and explicit authority;
- allow technical autonomy inside one agreed outcome boundary;
- distinguish plausible output from independently observed progress;
- leave truthful durable continuation for a fresh capable model;
- support one manually supervised run without routine micromanagement; and
- remain a lean coordinator rather than a control plane.

The fixture's short `tests/fixtures/fs01_operator/direction.json` text is test
data, not the full approved product Direction. The exercise below demonstrates
current coordinator mechanics. DIR-03 model autonomy and real-provider
usability remain questions for the historical/live evidence comparison and the
operator's judgment.

## What the prototype does today

The installed `second-mate` CLI can prepare/promote/show approved Direction and
run the fixed FS-01 lifecycle: `draft`, read-only `preflight`, authority-gated
`start` or same-owner `restart`, independent `evidence`, recoverable `close`,
and `show`. Its only executor choice is `fixture`.

Separately, the Python package exposes an offline mock adapter and the dormant
`CodexCliTrustedLocalAdapter`. The latter has one-shot activation, real-process,
JSONL, cancellation, recovery, and exact-cleanup mechanics, but no CLI route
and no real Codex activation. It must not be inferred from the fixture commands
below.

## Local prerequisites

- a clean Second Mate checkout at `f024fbb` or a reviewed descendant;
- Linux, Git, `uv`, and Python 3.12 or later;
- the locked dependencies already present in the local `uv` cache;
- enough space for one disposable `/tmp` worktree; and
- no provider, network, credential, live-target, or system-configuration use.

Run from the Second Mate repository root. If locked offline sync cannot
complete, stop this walkthrough rather than enabling network access.

```sh
export UV_CACHE_DIR="$PWD/.cache/uv"
export UV_PROJECT_ENVIRONMENT="$PWD/.venv"
uv sync --locked --offline

export MS02_REVIEW_ROOT="$(mktemp -d /tmp/second-mate-ms02.XXXXXX)"
export MS02_REVIEW_TARGET="$MS02_REVIEW_ROOT/target"
export MS02_REVIEW_CONTROL="$MS02_REVIEW_ROOT/control"

cp -R tests/fixtures/fs01_target "$MS02_REVIEW_TARGET"
mkdir -p "$MS02_REVIEW_CONTROL"
git -C "$MS02_REVIEW_TARGET" init -q
git -C "$MS02_REVIEW_TARGET" add --all
git -C "$MS02_REVIEW_TARGET" \
  -c user.name=MS02-Operator \
  -c user.email=ms02@example.invalid \
  commit -q -m "MS-02 disposable fixture baseline"
uv run python "$MS02_REVIEW_TARGET/probe.py"
```

The initial probe must report `"artifact":"before\n"`. Keep the printed
`sentinel_sha256` for comparison after execution.

## One safe representative task

The task is intentionally small: change only `artifact.txt` from `before` to
`after`, without changing `sentinel.txt` or `probe.py`.

First freeze the fixture Direction and packet, then inspect the target without
mutating it:

```sh
uv run second-mate draft \
  --direction tests/fixtures/fs01_operator/direction.json \
  --packet tests/fixtures/fs01_operator/packet.json \
  > "$MS02_REVIEW_CONTROL/draft.json"

uv run second-mate preflight \
  --target "$MS02_REVIEW_TARGET" \
  --draft "$MS02_REVIEW_CONTROL/draft.json" \
  > "$MS02_REVIEW_CONTROL/preflight.json"

uv run python -m json.tool "$MS02_REVIEW_CONTROL/preflight.json"
```

Confirm `preflight.eligible` and
`preflight.affected_baseline.result` are positive, and that no
`.second-mate` directory exists in the disposable target.

Now observe the pre-consent refusal. This command deliberately omits `--grant`
and must fail without changing the target:

```sh
if uv run second-mate start \
  --target "$MS02_REVIEW_TARGET" \
  --draft "$MS02_REVIEW_CONTROL/draft.json" \
  --preflight "$MS02_REVIEW_CONTROL/preflight.json" \
  --owner ms02-owner-1 \
  --executor fixture \
  2> "$MS02_REVIEW_CONTROL/pre-consent-refusal.txt"
then
  echo "unexpected: execution succeeded without a grant" >&2
  exit 1
fi
test "$(cat "$MS02_REVIEW_TARGET/artifact.txt")" = "before"
test ! -e "$MS02_REVIEW_TARGET/.second-mate"
```

Prepare the exact fixture grant from the frozen draft and preflight. This local
helper only copies the bound values into the documented grant schema; it does
not approve them. Read the resulting JSON and continue only if you personally
intend to authorize this one disposable mutation.

```sh
uv run python - \
  "$MS02_REVIEW_CONTROL/draft.json" \
  "$MS02_REVIEW_CONTROL/preflight.json" \
  "$MS02_REVIEW_CONTROL/grant.json" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

draft = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
basis = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
packet = draft["packet"]
preflight = basis["preflight"]
grant = {
    "allowed_effects": packet["boundary"]["allowed_effects"],
    "allowed_paths": packet["boundary"]["allowed_paths"],
    "direction_digest": draft["direction_digest"],
    "direction_id": draft["direction"]["id"],
    "granted_at": datetime.now(timezone.utc).isoformat(),
    "granted_by": "ms02-operator",
    "id": "ms02-fixture-grant",
    "packet_digest": draft["packet_digest"],
    "preflight_digest": basis["preflight_digest"],
    "repository_id": packet["repository_id"],
    "schema_version": 1,
    "stop_conditions": packet["boundary"]["stop_conditions"],
    "target_fingerprint": preflight["revision"]["fingerprint"],
    "target_head": preflight["revision"]["head"],
}
Path(sys.argv[3]).write_text(
    json.dumps(grant, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

uv run python -m json.tool "$MS02_REVIEW_CONTROL/grant.json"
```

After reviewing the grant, execute once, record evidence, and close without
claiming full Direction coverage:

```sh
uv run second-mate start \
  --target "$MS02_REVIEW_TARGET" \
  --draft "$MS02_REVIEW_CONTROL/draft.json" \
  --preflight "$MS02_REVIEW_CONTROL/preflight.json" \
  --grant "$MS02_REVIEW_CONTROL/grant.json" \
  --owner ms02-owner-1 \
  --executor fixture \
  > "$MS02_REVIEW_CONTROL/start.json"

uv run second-mate evidence \
  --target "$MS02_REVIEW_TARGET" \
  > "$MS02_REVIEW_CONTROL/evidence.json"

uv run second-mate close \
  --target "$MS02_REVIEW_TARGET" \
  --direction-coverage still_remaining \
  --residual-uncertainty "Live provider behavior was not exercised." \
  --residual-uncertainty "Human product review remains outstanding." \
  --handoff "Fixture lifecycle closed; review MS-02 against D-01." \
  > "$MS02_REVIEW_CONTROL/close.json"

uv run second-mate show --target "$MS02_REVIEW_TARGET" \
  > "$MS02_REVIEW_CONTROL/show.json"
uv run python "$MS02_REVIEW_TARGET/probe.py"
git -C "$MS02_REVIEW_TARGET" diff -- sentinel.txt probe.py
git -C "$MS02_REVIEW_TARGET" status --short
```

## Expected visible evidence

- the missing-grant attempt exits nonzero, leaves `artifact.txt` as `before`,
  and creates no coordinator state;
- `start.json` records one owner and one attempt;
- the final probe reports `"artifact":"after\n"` and the original sentinel
  digest;
- the sentinel/probe diff is empty;
- `evidence.json` contains a passing latest observation based on the target,
  not provider output;
- `close.json` and `show.json` report `route_status: "completed"`,
  `direction_coverage: "still_remaining"`, retained residual uncertainty, and
  a handoff; and
- target status names only the declared fixture mutation plus coordinator
  state. The control JSON stays outside the target.

These observations prove the current deterministic lifecycle only. They do not
prove model judgment, provider behavior, containment, absence of outside
effects, or live CAP-02C usability.

## Failure and interruption handling

For the fixture journey, use `show` before choosing a retry. If no durable run
exists after an interruption around initial state publication, repeat the exact
reviewed `start`. If an `active` run exists for `ms02-owner-1`, do not issue a
duplicate start; use the same-owner `restart --executor fixture`. If evidence
fails after unrelated drift, preserve that failed observation, repair only the
bounded target drift, and rerun `evidence`. Never edit coordinator state to
force a close.

`unknown-running` belongs to a future trusted-local adapter exercise, not this
fixture CLI. If live completion becomes ambiguous, do not retry or redispatch
the execution, and do not reuse the activation. If the same adapter still owns
the exact process group, request bounded cancellation; ambiguity remains
`unknown-running` and blocks cleanup. After reload, CAP-02C does not reattach
or redispatch. Independently
inspect process identity and target state, record outside-effect uncertainty,
and require a human abandonment decision before exact private-artifact cleanup.
Do not manually truncate or replace session/marker records, and do not treat
cleanup as repository rollback or provider-side deletion.

## Historical proof versus reusable preparation

| Surface | What exists | What it proves now | What it does not prove |
|---|---|---|---|
| This FS-01 walkthrough | Current CLI plus deterministic fixture | Reproducible authority, refusal, evidence, continuation, and close mechanics | Working-model autonomy, provider or trusted-local usability |
| CAP-02B | One manually enveloped real run whose activation is consumed | Retained marker proves consumption and Git proves its bounded fix | Deleted event/close artifacts, replayability, or reusable authority |
| CAP-02C | Current public library adapter tested with fake executables | Reproducible binding, JSONL, process, cancellation, recovery, and cleanup mechanics | A user-facing launch route, current provider readiness, or any real activation |

CAP-02B must never be replayed or treated as CAP-02C authority. CAP-02C being
reusable code does not mean it has been qualified or activated in the current
environment.

## Acceptance questions

Record the answers as human product judgment, not technical proof:

1. **Purpose:** Did the workflow keep the requested outcome coherent from
   packet through close, or did the artifacts obscure it?
2. **Authority:** Was the distinction between Direction, read-only preflight,
   exact grant, and execution obvious enough to prevent accidental permission?
3. **Autonomy:** Is the historical one-run record plus the unactivated adapter
   enough to judge useful working-model freedom, or is one fresh live exercise
   still necessary?
4. **Truthful completion:** Were independent evidence, residual uncertainty,
   coverage, and handoff understandable and appropriately narrow?
5. **Supervision:** Could one operator supervise the lifecycle at consequential
   choices without being pulled into routine engineering steps?
6. **Recovery:** Are the no-duplicate, `unknown-running`, cancellation,
   abandonment, and exact-cleanup rules usable under pressure?
7. **Product boundary:** Does this feel like a lean coordinator, or is the
   authority/evidence machinery becoming the product?
8. **Trusted-local risk:** Is the explicit lack of containment acceptable for
   the intended first mode, without mistaking a clean target diff for proof of
   no outside effect?

The valid MS-02 outcomes are either a narrow acceptance with these evidence
limits or an open gate naming the concrete usability gap. This walkthrough
does not choose either outcome.

## Smallest future real exercise

If the unanswered question is actual CAP-02C operation, the smallest next
activation is one new, non-retryable, unsandboxed trusted-local exercise on a
fresh baseline-known disposable target. It is not a CAP-02B replay. Because no
CLI route exists, the packet must also authorize and independently review one
exact invocation harness for the public adapter; activation consent alone
cannot launch it.

Before that single dispatch, record and bind:

- the current native Codex executable's unaliased path, digest, exact version,
  and `exec --help` digest;
- one exact model, prompt digest, environment-name/value digests, fixed reduced
  capabilities, and cancellation timings;
- the named authentication source without copying its secret, permitted data,
  intended provider/network effects, account/billing boundary,
  `provider-billing-controls-only`, and transcript/session retention;
- exact Direction, packet, read-only preflight, repository, target
  HEAD/fingerprint, allowed changes/effects, stop conditions, owner, and an
  owner-private `0700` artifact root disjoint from the target;
- a new schema-version-1 activation identifier with the exact three trusted-
  local risk acknowledgments and `exact-private-run-artifacts-only`; and
- explicit human consent for that one unsandboxed run, independent target
  evidence, no automatic retry/redispatch, `unknown-running` handling, and
  cleanup only after evidence close or explicit abandonment.

Preserve the private transcript/session/control artifacts through independent
close evidence, then delete only those identity-recorded run artifacts. Retain
the consumed activation marker. Any mismatch or ambiguity stops the exercise;
it does not select another binary, target, model, or activation automatically.
