# Second Mate design

Status: canonical pre-implementation design

Second Mate is a lean coordinator for AI coding work. It preserves human-owned product Direction, gives capable models room to solve technical problems, and requires evidence that fits each completion claim. It is a clean project, not a retrofit of FirstMate, Knowless, or their backlog and worker structures.

No Second Mate coordinator or runtime has been implemented. Its first workflows must be operated manually; Second Mate must not self-orchestrate before its own core capabilities have been proven.

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

## Open execution-policy gate

The user must choose one policy before any pre-Program Validation Slice or Foundation Slice code is written:

- explicit narrow consent for a named, bounded pre-Program learning and Foundation envelope; or
- full-Program-first control, under which pre-Program work remains non-mutating until the complete Program receives Execution Consent.

This package intentionally does not choose. Direction approval and Delivery Map approval do not silently authorize code or external effects.
