"""Route selection dialog.

This module intentionally wraps the generic multi-select dialog so route
filtering uses the same standard UX as other multi-select features.

Public API contract (used by gui_main):
- RouteFilterDialog(...).show() -> list[str] | None
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import tkinter as tk

from multi_select_dialog import MultiSelectDialog


class RouteFilterDialog:
    """Dialog for selecting which routes to process."""

    def __init__(
        self,
        parent: tk.Misc,
        available_routes: Sequence[str],
        selected_routes: Optional[Sequence[str]] = None,
    ) -> None:
        self.parent = parent
        self.available_routes = [str(r) for r in (available_routes or [])]
        self.selected_routes = [str(r) for r in (selected_routes or [])]

    def show(self) -> Optional[List[str]]:
        """Show the dialog.

        Returns:
            list[str]: Selected routes (possibly empty if user cleared all).
            None: User cancelled.

        Note: Upstream code may treat an empty list as "none selected".
        """
        return MultiSelectDialog.ask(
            self.parent,
            title="Filter Routes",
            items=self.available_routes,
            selected=self.selected_routes,
            prompt="Select routes to process:",
        )
