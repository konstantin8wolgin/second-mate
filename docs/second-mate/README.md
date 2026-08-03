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

## Prospective authority record — 2026-08-03

The human has prospectively approved exact Direction D-01, the documented
evidence-based Foundation route, Python 3.12 and ENV-01, and adoption of the
already verified FS-01 implementation as the Foundation baseline. The selected
POL-01 policy is narrow pre-Program consent: bounded local, no-external
Foundation work may proceed before a provider is selected.

These records do not backdate the missing bootstrap grant. Separately, the
human has granted Execution Consent for the local repository mutations needed
to finish the approved first workflow, but only after a fresh read-only
preflight for each bounded packet. That consent excludes provider or host
selection, credentials, external execution, pushing, publishing, deployment,
and any other external commitment. Direction approval, route approval, and
Execution Consent remain distinct records.

The remaining product gate for the accepted FS-01 baseline is the documented
human check of the fixture operator journey. A real provider/host selection is
an intentionally later, blocked decision; FS-01 evidence does not authorize it.
