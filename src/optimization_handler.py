"""Protocol defining the interface OptimizationController requires from its host app.

OptimizationController calls back into its host for logging, error reporting,
and lifecycle notifications. Any object that provides these attributes and
methods qualifies structurally -- no inheritance required.

Both HighwaySegmentationGUI and CLI runner implement this interface.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class OptimizationHandler(Protocol):
    """Structural interface consumed by OptimizationController.

    Attributes:
        is_running: True while an optimization thread is active.
        stop_requested: Set to True by stop_optimization(); polled by the worker.
    """

    is_running: bool
    stop_requested: bool

    def log_message(self, message: str) -> None: ...

    def handle_error(
        self,
        title: str,
        exc: BaseException | None = None,
        severity: str = "error",
        show_messagebox: bool = True,
    ) -> None: ...

    def on_optimization_started(self) -> None: ...

    def on_stop_requested(self) -> None: ...

    def on_optimization_finished(self, stopped_early: bool) -> None: ...
