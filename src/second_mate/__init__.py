"""Second Mate foundation-slice runtime."""

from second_mate.direction import (
    ApprovedDirectionVersion,
    DirectionCandidateEnvelope,
    DirectionConflictError,
    load_direction,
    prepare_direction,
    promote_direction,
)
from second_mate.domain import Draft, ValidationError, create_draft
from second_mate.fixture import FixtureExecutor
from second_mate.repository import PreflightEnvelope, preflight
from second_mate.service import (
    AuthorityError,
    CloseFailure,
    ExecutionFailure,
    Executor,
    RunConflictError,
    RunState,
    clean_close,
    load_state,
    record_evidence,
    restart_run,
    start_run,
)
from second_mate.trusted_local import (
    OfflineControlPlane,
    OfflineLaunchRequest,
    OfflineProcess,
    OfflineTrustedLocalAdapter,
    TrustedLocalAuthorityError,
    TrustedLocalBasis,
    TrustedLocalBoundaryError,
    TrustedLocalRun,
)

__all__ = [
    "ApprovedDirectionVersion",
    "AuthorityError",
    "CloseFailure",
    "DirectionCandidateEnvelope",
    "DirectionConflictError",
    "Draft",
    "ExecutionFailure",
    "Executor",
    "FixtureExecutor",
    "OfflineControlPlane",
    "OfflineLaunchRequest",
    "OfflineProcess",
    "OfflineTrustedLocalAdapter",
    "PreflightEnvelope",
    "RunConflictError",
    "RunState",
    "TrustedLocalAuthorityError",
    "TrustedLocalBasis",
    "TrustedLocalBoundaryError",
    "TrustedLocalRun",
    "ValidationError",
    "__version__",
    "clean_close",
    "create_draft",
    "load_direction",
    "load_state",
    "preflight",
    "prepare_direction",
    "promote_direction",
    "record_evidence",
    "restart_run",
    "start_run",
]

__version__ = "0.1.0"
