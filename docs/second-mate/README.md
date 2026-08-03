# Second Mate design

Status: canonical design; FS-01 baseline prospectively accepted, with its
operator/product check still outstanding

Second Mate is a lean coordinator for AI coding work. It preserves human-owned product Direction, gives capable models room to solve technical problems, and requires evidence that fits each completion claim. It is a clean project, not a retrofit of FirstMate, Knowless, or their backlog and worker structures.

The repository contains a small Python 3.12 coordinator for the fixture-only
FS-01 lifecycle. It is operated manually and does not self-orchestrate. Its
local executable evidence is recorded in [PROGRAM.md](PROGRAM.md); that evidence
does not prove a live provider run, the broader workflow, or product readiness.

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

## Prospective decisions and unresolved authority gate — 2026-08-03

The human has prospectively approved exact Direction D-01, the documented
evidence-based Foundation route, Python 3.12 and ENV-01, and adoption of the
already verified FS-01 implementation as the Foundation baseline. POL-01
remains **decision-blocked**: the human must deliberately choose either narrow
pre-Program consent with its exact envelope or full-Program-first control.

These records do not backdate the missing bootstrap grant. No broad or future
Second Mate Execution Consent is recorded: the persistence instruction to
finish the project is not consent for unnamed future packets. After POL-01 is
explicitly chosen, every new bounded mutating packet still needs its own
current read-only preflight followed by exactly fitting Execution Consent.
Direction approval, route approval, and Execution Consent remain distinct
records. Provider or host selection, credentials, external execution, pushing,
publishing, deployment, Rumble integration, and pilots remain unauthorized.

The next human action is to choose POL-01 explicitly. Narrow consent requires
the dangerous question, code/data/infrastructure boundary, resource and
side-effect limits, discard policy, and at most one permanent Foundation Slice;
full-Program-first permits only non-mutating work until a complete Program and
Execution Consent exist. The separate remaining product gate for the accepted
FS-01 baseline is the documented human check of the fixture operator journey.
