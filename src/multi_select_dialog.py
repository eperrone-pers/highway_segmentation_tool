"""Reusable Tkinter multi-select dialog.

This is intended to provide a consistent, standard UX for choosing one or more
items from a list (routes, columns, etc.) with:
- Search/filter box
- Extended selection (Ctrl/Shift)
- Select All / Clear
- OK / Cancel

The dialog returns a list of selected item strings or None on cancel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

import tkinter as tk
from tkinter import ttk


@dataclass(frozen=True)
class MultiSelectDialogResult:
    """Return value from a MultiSelectDialog interaction."""

    selected: List[str]


class MultiSelectDialog:
    """Modal Tkinter dialog for multi-item selection with search and bulk actions.

    Use the classmethod `ask()` for the typical blocking usage pattern.
    """

    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        items: Sequence[str],
        selected: Optional[Iterable[str]] = None,
        prompt: str = "Select one or more items:",
        width: int = 520,
        height: int = 560,
    ) -> None:
        self.parent = parent
        self.items = [str(i) for i in (items or [])]
        self._index_by_item = {v: idx for idx, v in enumerate(self.items)}
        self._selected_set = {str(s) for s in (selected or []) if str(s)}
        self._filtered_items: List[str] = list(self.items)

        self.result: Optional[MultiSelectDialogResult] = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry(f"{int(width)}x{int(height)}")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        main = ttk.Frame(self.dialog, padding="10")
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        ttk.Label(main, text=prompt).grid(row=0, column=0, sticky="w")

        self.search_var = tk.StringVar(value="")
        search_row = ttk.Frame(main)
        search_row.grid(row=1, column=0, sticky="ew", pady=(6, 6))
        search_row.columnconfigure(0, weight=1)

        self.search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=0, sticky="ew")
        clear_btn = ttk.Button(search_row, text="Clear", command=self._clear_search)
        clear_btn.grid(row=0, column=1, padx=(8, 0))

        actions = ttk.Frame(main)
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        actions.columnconfigure(2, weight=1)

        ttk.Button(actions, text="Select All", command=self._select_all_visible).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(actions, text="Clear", command=self._clear_all).grid(row=0, column=1, padx=(0, 6))

        self.status_var = tk.StringVar(value="None")
        ttk.Label(actions, textvariable=self.status_var, foreground="blue").grid(row=0, column=2, sticky="e")

        list_frame = ttk.Frame(main)
        list_frame.grid(row=3, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # exportselection=False keeps the highlight visible even when focus is
        # in the search box (otherwise it can look like nothing happened).
        self.listbox = tk.Listbox(list_frame, selectmode="extended", height=10, exportselection=False)
        self.listbox.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        btns = ttk.Frame(main)
        btns.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        btns.columnconfigure(0, weight=1)

        ttk.Button(btns, text="Cancel", command=self._cancel).grid(row=0, column=1, padx=(6, 0))
        ttk.Button(btns, text="OK", command=self._ok).grid(row=0, column=2, padx=(6, 0))

        self.dialog.protocol("WM_DELETE_WINDOW", self._cancel)
        self.search_var.trace_add("write", lambda *_: self._apply_filter())
        self.search_entry.bind("<Return>", self._on_search_enter)
        self.search_entry.bind("<KP_Enter>", self._on_search_enter)
        self.listbox.bind("<<ListboxSelect>>", lambda _e: self._on_listbox_select())
        self.listbox.bind("<Return>", lambda _e: self._ok())
        self.listbox.bind("<KP_Enter>", lambda _e: self._ok())
        self.dialog.bind("<Escape>", lambda _e: self._cancel())
        # Robust Enter routing: handle Return/KP_Enter at the dialog level based on focus.
        # (Some platforms/keyboards treat keypad Enter differently, and focus can drift.)
        self.dialog.bind("<Return>", self._route_enter)
        self.dialog.bind("<KP_Enter>", self._route_enter)

        self._center_dialog(width, height)
        self._rebuild_listbox()
        self._sync_listbox_selection()
        self._update_status()

        try:
            self.search_entry.focus_set()
        except Exception:
            pass

    @classmethod
    def ask(
        cls,
        parent: tk.Misc,
        *,
        title: str,
        items: Sequence[str],
        selected: Optional[Iterable[str]] = None,
        prompt: str = "Select one or more items:",
        width: int = 520,
        height: int = 560,
    ) -> Optional[List[str]]:
        """Open a modal multi-select dialog and return the chosen items.

        Args:
            parent: Parent Tkinter widget.
            title: Dialog window title.
            items: All available items to display.
            selected: Pre-selected items (optional).
            prompt: Instruction text shown above the list.
            width: Initial dialog width in pixels.
            height: Initial dialog height in pixels.

        Returns:
            List of selected item strings, or None if the user cancelled.
        """
        dlg = cls(
            parent,
            title=title,
            items=items,
            selected=selected,
            prompt=prompt,
            width=width,
            height=height,
        )
        dlg.dialog.wait_window()
        return None if dlg.result is None else dlg.result.selected

    def _center_dialog(self, width: int, height: int) -> None:
        try:
            self.dialog.update_idletasks()
            parent_x = self.parent.winfo_rootx()
            parent_y = self.parent.winfo_rooty()
            parent_w = self.parent.winfo_width()
            parent_h = self.parent.winfo_height()
            x = max(0, int(parent_x + (parent_w // 2) - (width // 2)))
            y = max(0, int(parent_y + (parent_h // 2) - (height // 2)))
            self.dialog.geometry(f"{int(width)}x{int(height)}+{x}+{y}")
        except Exception:
            # Non-fatal: keep default geometry.
            pass

    def _clear_search(self) -> None:
        self.search_var.set("")

    def _apply_filter(self) -> None:
        text = (self.search_var.get() or "").strip().lower()
        if not text:
            self._filtered_items = list(self.items)
        else:
            self._filtered_items = [i for i in self.items if text in i.lower()]
        self._rebuild_listbox()
        self._sync_listbox_selection()
        # Make the first visible item active so Enter has a deterministic target.
        try:
            if self._filtered_items:
                self.listbox.activate(0)
                self.listbox.see(0)
        except Exception:
            pass

    def _rebuild_listbox(self) -> None:
        self.listbox.delete(0, tk.END)
        for item in self._filtered_items:
            self.listbox.insert(tk.END, item)

    def _sync_listbox_selection(self) -> None:
        # Apply current selection set to the visible list.
        self.listbox.selection_clear(0, tk.END)
        for i, item in enumerate(self._filtered_items):
            if item in self._selected_set:
                self.listbox.selection_set(i)

        # Keep a sensible active item for keyboard operations.
        try:
            if self._filtered_items:
                self.listbox.activate(0)
        except Exception:
            pass

    def _on_listbox_select(self) -> None:
        # Rebuild selection set based on visible list + selected indices.
        visible = self._filtered_items
        selected_indices = set(self.listbox.curselection())

        # Remove any visible items from the set first, then add back selected ones.
        for item in visible:
            self._selected_set.discard(item)
        for idx in selected_indices:
            if 0 <= idx < len(visible):
                self._selected_set.add(visible[idx])

        self._update_status()

    def _on_search_enter(self, _event=None):
        """Handle Enter in the search box.

        UX goal: typed filter + Enter should *select/add* a match, not immediately
        close the dialog.
        """
        if not self._filtered_items:
            return "break"

        # Prefer the active row when possible; otherwise choose the first visible.
        try:
            active = int(self.listbox.index(tk.ACTIVE))
        except Exception:
            active = 0

        if active < 0 or active >= len(self._filtered_items):
            active = 0

        item = self._filtered_items[active]
        if item:
            if item in self._selected_set:
                self._selected_set.discard(item)
            else:
                self._selected_set.add(item)
            self._sync_listbox_selection()
            self._update_status()

            # Ensure the toggled item is visible/active for feedback.
            try:
                self.listbox.activate(active)
                self.listbox.see(active)
            except Exception:
                pass

            # Keep focus in the search box for quick successive adds.
            try:
                self.search_entry.selection_range(0, tk.END)
            except Exception:
                pass

        return "break"

    def _route_enter(self, _event=None):
        """Route Enter based on focused widget.

        - If search box has focus: toggle the active/first visible match.
        - If listbox has focus: OK.
        - Otherwise: OK.
        """
        try:
            focused = self.dialog.focus_get()
        except Exception:
            focused = None

        if focused == self.search_entry:
            return self._on_search_enter(_event)
        if focused == self.listbox:
            self._ok()
            return "break"

        # Default: OK
        self._ok()
        return "break"

    def _select_all_visible(self) -> None:
        for item in self._filtered_items:
            self._selected_set.add(item)
        self._sync_listbox_selection()
        self._update_status()

    def _clear_all(self) -> None:
        self._selected_set.clear()
        self._sync_listbox_selection()
        self._update_status()

    def _update_status(self) -> None:
        count = len(self._selected_set)
        self.status_var.set("None" if count == 0 else f"{count} selected")

    def _ok(self) -> None:
        # Deterministic output order: preserve original items order.
        selected_sorted = sorted(self._selected_set, key=lambda v: self._index_by_item.get(v, 10**9))
        self.result = MultiSelectDialogResult(selected=selected_sorted)
        try:
            self.dialog.destroy()
        except Exception:
            pass

    def _cancel(self) -> None:
        self.result = None
        try:
            self.dialog.destroy()
        except Exception:
            pass
