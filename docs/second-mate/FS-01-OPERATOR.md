# FS-01 operator guide

FS-01 proves one supervised, local direct-packet lifecycle with a deterministic
fixture executor. It does not call a model provider, run arbitrary commands,
schedule work, publish, deploy, or authorize a later provider adapter.

## Environment

Run from a clean Second Mate checkout with Python 3.12 and `uv`. Keep generated
dependencies and caches inside that checkout:

```sh
export UV_CACHE_DIR="$PWD/.cache/uv"
export UV_PROJECT_ENVIRONMENT="$PWD/.venv"
export UV_PYTHON=python3.12
uv sync --locked
mkdir -p .tmp/fs01/control
```

Set `FS01_TARGET` to a clean Git worktree created from
`tests/fixtures/fs01_target`. Initialize and commit the copied fixture before
preflight. The target's `probe.py` must report `before\n`, and its
`sentinel.txt` must be unchanged throughout the journey.

## Draft and read-only preflight

Drafting validates the immutable approved Direction and the packet without
writing the target:

```sh
uv run second-mate draft \
  --direction tests/fixtures/fs01_operator/direction.json \
  --packet tests/fixtures/fs01_operator/packet.json \
  > .tmp/fs01/control/draft.json
```

Preflight reads Git HEAD, tracked and visible untracked content, applicable
`AGENTS.md` instructions, dependency files, and the fixture baseline. Write its
output outside the target so the target worktree, index, branch, and dependency
state remain unchanged:

```sh
uv run second-mate preflight \
  --target "$FS01_TARGET" \
  --draft .tmp/fs01/control/draft.json \
  > .tmp/fs01/control/preflight.json
```

Inspect the report. `eligible` and `affected_baseline.result` must both be
positive, existing failures must be empty, and the irreversible-change
assessment must still fit this one recoverable fixture mutation.

## Exact consent and one dispatch

`start` requires `--grant`; omitting it is an executable pre-consent refusal and
must leave the target unchanged. The human-authored grant is a distinct JSON
document. It must contain exactly schema version 1 and these fields:

- its own `id`, `granted_by`, and `granted_at` approval record;
- the draft's `direction_id`, `direction_digest`, and `packet_digest`;
- the preflight's `preflight_digest`, target HEAD, and target fingerprint;
- the packet's repository identity, allowed paths, allowed effects, and stop
  conditions.

Second Mate deliberately has no command that manufactures this grant. A wrong
field, extra field, stale target revision or applicable instruction file,
ineligible preflight, or changed Direction or packet refuses execution before
creating target state or invoking the executor. Applicable instructions remain
part of this check even when Git ignores them.

After reviewing and recording the exact fixture grant:

```sh
uv run second-mate start \
  --target "$FS01_TARGET" \
  --draft .tmp/fs01/control/draft.json \
  --preflight .tmp/fs01/control/preflight.json \
  --grant .tmp/fs01/control/grant.json \
  --owner fs01-owner-1 \
  --executor fixture \
  > .tmp/fs01/control/start.json
```

The only executor choice is `fixture`. It receives the frozen packet,
preflight, and grant through the production dispatch port, changes only
`artifact.txt` from its declared before value to its declared after value, and
returns the changed path. Second Mate persists the owner before dispatch. A
duplicate start is refused.

If dispatch fails before mutation, retry only with the same owner:

```sh
uv run second-mate restart \
  --target "$FS01_TARGET" \
  --owner fs01-owner-1 \
  --executor fixture
```

If interruption occurred after the exact fixture mutation, restart reconciles
that after-state without invoking the executor again. Any other revision drift
or applicable-instruction drift blocks restart.

## Evidence and clean close

Record evidence only after execution:

```sh
uv run second-mate evidence --target "$FS01_TARGET" \
  > .tmp/fs01/control/evidence.json
```

The fixed probe compares the full target snapshot with preflight and permits
exactly the declared `artifact.txt` change. It also compares the artifact with
the declared after value, compares the sentinel hash with preflight, checks the
executor's one changed path, and binds the result to fresh target and applicable
instruction fingerprints. Instruction files are inspected independently so an
ignored applicable `AGENTS.md` remains inside the authority boundary. An
instruction change or any unrelated tracked or visible untracked file fails
evidence and blocks close.

A failed observation leaves the route open with Packet recovery pressure. After
repairing only the bounded target drift, run the same `evidence` command again.
It re-probes the existing run without invoking the executor, retains the failed
observation, and appends the repaired result. It becomes ready to close only
when the latest observation passes.

Close only passing evidence, and state Direction coverage explicitly rather
than inferring it from route completion:

```sh
uv run second-mate close \
  --target "$FS01_TARGET" \
  --direction-coverage still_remaining \
  --residual-uncertainty "Live provider behavior was not exercised." \
  --handoff "FS-01 is closed; human product review remains." \
  > .tmp/fs01/control/close.json
```

Clean close journals the complete final state before replacing
`.second-mate/state.json`. If replacement is interrupted, the previous state
remains truthful and `show` recovers the entire journaled close or reports a
divergence; it never assembles a partial completed state:

```sh
uv run second-mate show --target "$FS01_TARGET"
```

Immediately before journaling, close re-reads both the target revision and the
applicable instructions and refuses if either differs from the passing evidence
record, including drift in an ignored `AGENTS.md`.

At review, confirm route status `completed` is separate from Direction coverage,
evidence says only what the fixture probe observed, residual uncertainty and
handoff are present, `probe.py` reports `after\n`, and Git shows no change to
`sentinel.txt` or `probe.py`. Durable JSON is versioned, sorted, replayable, and
contains neither the sentinel's fixture secret nor credentials or transcripts.

## Repository proof gates

Use the same repository-owned environment for every gate:

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src/second_mate
uv run pytest
uv build
uv run pytest tests/test_e2e_fixture.py -q
```

The resulting evidence proves only the FS-01 local lifecycle, refusal behavior,
fixture executor seam, deterministic persistence, single-run recovery, and
recoverable close. It does not prove a live model run, provider security,
autonomous recovery, broad workflow correctness, or pilot usefulness.
