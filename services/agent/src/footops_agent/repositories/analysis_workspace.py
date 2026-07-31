"""Persistence boundary for analysis workspaces."""

from threading import RLock
from typing import Protocol

from footops_agent.artifacts import AnalysisWorkspace


class WorkspaceNotFoundError(LookupError):
    """Raised when a requested workspace does not exist."""


class AnalysisWorkspaceRepository(Protocol):
    """Storage contract kept independent from HTTP and Agent orchestration."""

    def save(self, workspace: AnalysisWorkspace) -> AnalysisWorkspace:
        """Create or replace one workspace snapshot."""

    def get(self, workspace_id: str) -> AnalysisWorkspace | None:
        """Return one workspace snapshot when it exists."""


class InMemoryAnalysisWorkspaceRepository:
    """Thread-safe development repository replaceable by SQLAlchemy later."""

    def __init__(self) -> None:
        self._items: dict[str, AnalysisWorkspace] = {}
        self._lock = RLock()

    def save(self, workspace: AnalysisWorkspace) -> AnalysisWorkspace:
        snapshot = workspace.model_copy(deep=True)
        with self._lock:
            self._items[workspace.workspace_id] = snapshot
        return snapshot.model_copy(deep=True)

    def get(self, workspace_id: str) -> AnalysisWorkspace | None:
        with self._lock:
            workspace = self._items.get(workspace_id)
            return workspace.model_copy(deep=True) if workspace is not None else None
