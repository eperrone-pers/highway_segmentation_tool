"""Unified data filter dialog for route groups and milepoint range.

Replaces RouteFilterDialog when direction_column or lane_column are active.
Shows a per-component multi-select section for each active grouping column
(route, direction, lane) and a milepoint range section.

Public API:
    DataFilterDialog(...).show() -> dict | None
    Return value: {"selected_routes": list|None, "x_min": float|None, "x_max": float|None}
    None means the user cancelled.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import tkinter as tk
from tkinter import messagebox, ttk

from route_utils import decompose_route_id


class _ComponentSection:
    """Compact multi-select section for one route component.

    Embeds search, Select All / None buttons, and a Listbox inside a LabelFrame.
    Calls on_change() whenever the selection changes.
    """

    def __init__(
        self,
        container: tk.Widget,
        *,
        label: str,
        items: Sequence[str],
        initially_selected: Set[str],
        on_change,
    ) -> None:
        self._all_items = list(items)
        self._selected: Set[str] = set(initially_selected) & set(self._all_items)
        self._filtered: List[str] = list(self._all_items)
        self._on_change = on_change

        lf = ttk.LabelFrame(container, text=label)
        lf.pack(fill="both", expand=True, padx=6, pady=(4, 2))
        lf.columnconfigure(0, weight=1)

        # Search row
        sr = ttk.Frame(lf)
        sr.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 2))
        sr.columnconfigure(0, weight=1)
        self._search_var = tk.StringVar()
        ttk.Entry(sr, textvariable=self._search_var, width=18).grid(row=0, column=0, sticky="ew")
        ttk.Button(sr, text="Clear", command=lambda: self._search_var.set("")).grid(row=0, column=1, padx=(4, 0))

        # Actions row
        ar = ttk.Frame(lf)
        ar.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 2))
        ttk.Button(ar, text="All", width=4, command=self._select_all).pack(side="left")
        ttk.Button(ar, text="None", width=5, command=self._clear_all).pack(side="left", padx=(4, 0))
        self._status_var = tk.StringVar()
        ttk.Label(ar, textvariable=self._status_var, foreground="steelblue").pack(side="right")

        # Listbox
        lbf = ttk.Frame(lf)
        lbf.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 6))
        lbf.columnconfigure(0, weight=1)
        lbf.rowconfigure(0, weight=1)
        lf.rowconfigure(2, weight=1)
        self._lb = tk.Listbox(lbf, selectmode="extended", height=5, exportselection=False)
        self._lb.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(lbf, orient="vertical", command=self._lb.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._lb.configure(yscrollcommand=sb.set)

        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        self._lb.bind("<<ListboxSelect>>", lambda _: self._on_listbox_select())

        self._rebuild()
        self._sync()
        self._refresh_status()

    @property
    def selected(self) -> Set[str]:
        return set(self._selected)

    def _apply_filter(self) -> None:
        text = (self._search_var.get() or "").strip().lower()
        self._filtered = [i for i in self._all_items if not text or text in i.lower()]
        self._rebuild()
        self._sync()

    def _rebuild(self) -> None:
        self._lb.delete(0, tk.END)
        for item in self._filtered:
            self._lb.insert(tk.END, item)

    def _sync(self) -> None:
        self._lb.selection_clear(0, tk.END)
        for i, item in enumerate(self._filtered):
            if item in self._selected:
                self._lb.selection_set(i)

    def _on_listbox_select(self) -> None:
        indices = set(self._lb.curselection())
        for item in self._filtered:
            self._selected.discard(item)
        for idx in indices:
            if 0 <= idx < len(self._filtered):
                self._selected.add(self._filtered[idx])
        self._refresh_status()
        self._on_change()

    def _select_all(self) -> None:
        self._selected.update(self._all_items)
        self._sync()
        self._refresh_status()
        self._on_change()

    def _clear_all(self) -> None:
        self._selected.clear()
        self._sync()
        self._refresh_status()
        self._on_change()

    def _refresh_status(self) -> None:
        n, total = len(self._selected), len(self._all_items)
        self._status_var.set(f"{n} / {total}")


class DataFilterDialog:
    """Unified filter dialog for route groups and milepoint range.

    Args:
        parent: Parent Tkinter widget.
        available_routes: All composite route IDs from the loaded data.
        component_order: List of active source column names in join order.
            E.g. ["RDB", "DIRECTION", "LANE"]. Pass [] or None for single-route mode.
        route_column: Column name whose values are the route component.
        direction_column: Column name whose values are the direction component.
        lane_column: Column name whose values are the lane component.
        selected_routes: Currently applied route selection (None = all).
        x_min: Current lower milepoint bound (None = no bound).
        x_max: Current upper milepoint bound (None = no bound).
        x_extent: Tuple (data_min, data_max) for the hint label.
    """

    def __init__(
        self,
        parent: tk.Misc,
        *,
        available_routes: Sequence[str],
        component_order: Optional[List[str]] = None,
        route_column: Optional[str] = None,
        direction_column: Optional[str] = None,
        lane_column: Optional[str] = None,
        selected_routes: Optional[Sequence[str]] = None,
        x_min: Optional[float] = None,
        x_max: Optional[float] = None,
        x_extent: Optional[Tuple[float, float]] = None,
    ) -> None:
        self.parent = parent
        self.available_routes = [str(r) for r in (available_routes or [])]
        self.component_order: List[str] = list(component_order or [])
        self.direction_column = direction_column
        self.lane_column = lane_column

        self._decomposed = [
            decompose_route_id(r, self.component_order, direction_column, lane_column)
            for r in self.available_routes
        ]

        # Map each source column in component_order to a semantic role.
        self._active_roles: List[Tuple[str, str]] = []  # [(role, col_name), ...]
        for col in self.component_order:
            if col == direction_column:
                self._active_roles.append(("direction", col))
            elif col == lane_column:
                self._active_roles.append(("lane", col))
            else:
                self._active_roles.append(("route", col))

        selected_set: Optional[Set[str]] = (
            set(selected_routes) if selected_routes is not None else None
        )

        self._role_sections: Dict[str, _ComponentSection] = {}
        self.result: Optional[Dict[str, Any]] = None

        # ---- build the window ----
        self._dlg = tk.Toplevel(parent)
        self._dlg.title("Filter Data")
        self._dlg.resizable(True, True)
        self._dlg.transient(parent)
        self._dlg.grab_set()
        self._dlg.protocol("WM_DELETE_WINDOW", self._cancel)
        self._dlg.bind("<Escape>", lambda _: self._cancel())
        self._dlg.bind("<Return>", lambda _: self._ok())

        outer = ttk.Frame(self._dlg, padding="8")
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)

        current_row = 0

        # ---- component sections (one per active grouping column) ----
        if self._active_roles:
            sections_frame = ttk.Frame(outer)
            sections_frame.grid(row=current_row, column=0, sticky="nsew")
            sections_frame.columnconfigure(0, weight=1)
            outer.rowconfigure(current_row, weight=1)
            current_row += 1

            for role, col_name in self._active_roles:
                unique_vals = self._unique_for_role(role)
                initial_sel = self._initial_sel_for_role(role, unique_vals, selected_set)
                section = _ComponentSection(
                    sections_frame,
                    label=col_name,
                    items=unique_vals,
                    initially_selected=initial_sel,
                    on_change=self._refresh_status,
                )
                self._role_sections[role] = section

        # ---- milepoint range section ----
        mp_lf = ttk.LabelFrame(outer, text="Milepoint Range (X Column)")
        mp_lf.grid(row=current_row, column=0, sticky="ew", padx=6, pady=(6, 2))
        current_row += 1

        self._x_min_var = tk.StringVar(value="" if x_min is None else str(x_min))
        self._x_max_var = tk.StringVar(value="" if x_max is None else str(x_max))

        mp_inner = ttk.Frame(mp_lf)
        mp_inner.pack(fill="x", padx=6, pady=4)
        ttk.Label(mp_inner, text="From:").grid(row=0, column=0, sticky="w", padx=(0, 4))
        ttk.Entry(mp_inner, textvariable=self._x_min_var, width=12).grid(row=0, column=1, sticky="w")
        ttk.Label(mp_inner, text="To:").grid(row=0, column=2, sticky="w", padx=(12, 4))
        ttk.Entry(mp_inner, textvariable=self._x_max_var, width=12).grid(row=0, column=3, sticky="w")

        if x_extent is not None:
            hint = f"Data range: {x_extent[0]:.4g} – {x_extent[1]:.4g}"
            ttk.Label(mp_inner, text=hint, foreground="gray").grid(
                row=1, column=0, columnspan=4, sticky="w", pady=(2, 0)
            )

        # ---- status bar ----
        self._status_var = tk.StringVar()
        status_row = ttk.Frame(outer)
        status_row.grid(row=current_row, column=0, sticky="ew", pady=(6, 0))
        ttk.Label(status_row, textvariable=self._status_var, foreground="steelblue").pack(side="left")
        current_row += 1

        # ---- OK / Cancel ----
        btn_row = ttk.Frame(outer)
        btn_row.grid(row=current_row, column=0, sticky="ew", pady=(6, 0))
        btn_row.columnconfigure(0, weight=1)
        ttk.Button(btn_row, text="Cancel", command=self._cancel).grid(row=0, column=1, padx=(6, 0))
        ttk.Button(btn_row, text="OK", command=self._ok).grid(row=0, column=2, padx=(6, 0))

        self._refresh_status()
        self._center()

    # ---- public API --------------------------------------------------------

    def show(self) -> Optional[Dict[str, Any]]:
        """Block until the dialog closes.

        Returns:
            Dict with keys ``selected_routes``, ``x_min``, ``x_max``, or None
            if the user cancelled.
        """
        self._dlg.wait_window()
        return self.result

    # ---- private -----------------------------------------------------------

    def _unique_for_role(self, role: str) -> List[str]:
        seen: List[str] = []
        seen_set: Set[str] = set()
        for d in self._decomposed:
            val = d.get(role)
            if val is not None and val not in seen_set:
                seen.append(val)
                seen_set.add(val)
        return seen

    def _initial_sel_for_role(
        self, role: str, unique_vals: List[str], selected_set: Optional[Set[str]]
    ) -> Set[str]:
        if selected_set is None:
            return set(unique_vals)
        result: Set[str] = set()
        for composite, decomposed in zip(self.available_routes, self._decomposed):
            if composite in selected_set:
                val = decomposed.get(role)
                if val is not None:
                    result.add(val)
        return result

    def _matching_composites(self) -> List[str]:
        """Return composites where every role's value is in the selected set."""
        selections = {role: sec.selected for role, sec in self._role_sections.items()}
        result = []
        for composite, decomposed in zip(self.available_routes, self._decomposed):
            if all(
                decomposed.get(role) in sel
                for role, sel in selections.items()
                if decomposed.get(role) is not None
            ):
                result.append(composite)
        return result

    def _refresh_status(self) -> None:
        if not self.available_routes:
            self._status_var.set("")
            return
        matching = len(self._matching_composites())
        total = len(self.available_routes)
        self._status_var.set(f"{matching} of {total} route group(s) will be analyzed")

    def _parse_float(self, var: tk.StringVar) -> Optional[float]:
        text = var.get().strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _ok(self) -> None:
        x_min = self._parse_float(self._x_min_var)
        x_max = self._parse_float(self._x_max_var)

        if x_min is not None and x_max is not None and x_min > x_max:
            messagebox.showerror(
                "Invalid Range",
                f"X From ({x_min}) must be ≤ X To ({x_max}).",
                parent=self._dlg,
            )
            return

        matching = self._matching_composites()
        # None = no filter (all routes selected)
        selected_routes: Optional[List[str]] = (
            None if set(matching) == set(self.available_routes) else matching
        )

        self.result = {
            "selected_routes": selected_routes,
            "x_min": x_min,
            "x_max": x_max,
        }
        try:
            self._dlg.destroy()
        except Exception:
            pass

    def _cancel(self) -> None:
        self.result = None
        try:
            self._dlg.destroy()
        except Exception:
            pass

    def _center(self) -> None:
        try:
            self._dlg.update_idletasks()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            n_sections = len(self._active_roles)
            w = 420
            h = max(300, 180 + n_sections * 180)
            x = max(0, px + pw // 2 - w // 2)
            y = max(0, py + ph // 2 - h // 2)
            self._dlg.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            self._dlg.geometry("420x480")
