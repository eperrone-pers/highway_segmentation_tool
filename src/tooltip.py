"""Tooltip support for the Highway Segmentation GUI.

Provides:
  ParameterTreeTooltip — shows ParameterDefinition.description for hovered Treeview rows.
  attach_tooltip        — attaches a hover tooltip to any Tkinter widget.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

_DELAY_MS = 300
_WRAPLENGTH = 280


def _tooltip_colors(widget: tk.Widget) -> tuple[str, str]:
    """Return (background, foreground) suited to the current light/dark theme.

    On macOS, checks ::tk::mac::isDark first — this is set by the Tk framework
    itself and is immune to the winfo_rgb/system-color-name resolution bug that
    causes dark mode to be misdetected on newer macOS releases.

    On other platforms, falls back to resolving the ttk TFrame background via
    winfo_rgb() and computing luminance.

    Returns:
        (bg_hex, fg_hex) — explicit color strings safe to pass to tk.Label.
    """
    is_dark = False
    try:
        # Reliable on macOS: Tk sets this variable when the OS is in dark mode.
        is_dark = bool(widget.tk.getvar("::tk::mac::isDark"))
    except tk.TclError:
        # Not macOS — fall back to luminance check on the TFrame background.
        try:
            style = ttk.Style(widget)
            bg_name = style.lookup('TFrame', 'background') or 'white'
            r16, g16, b16 = widget.winfo_rgb(bg_name)   # 0–65535 range
            luminance = (0.299 * r16 + 0.587 * g16 + 0.114 * b16) / 65535
            is_dark = luminance < 0.45
        except Exception:
            pass

    if is_dark:
        # Dark mode: near-black background, warm cream text
        return '#1e1e18', '#f5f5dc'
    # Light mode: classic tooltip yellow, near-black text (never inherit from OS)
    return '#ffffe0', '#1a1a1a'


class _TooltipWindow:
    """A small borderless popup showing a single text label.

    Colors are resolved at creation time so the tooltip is readable in both
    light and dark OS appearances.
    """

    def __init__(self, parent: tk.Widget, text: str, x: int, y: int) -> None:
        bg, fg = _tooltip_colors(parent)

        self._tip = tk.Toplevel(parent)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x + 14}+{y + 14}")
        # Set the Toplevel background to a slightly contrasting border color.
        try:
            self._tip.configure(background=fg)
        except Exception:
            pass
        tk.Label(
            self._tip,
            text=text,
            justify="left",
            background=bg,
            foreground=fg,
            relief="flat",
            borderwidth=0,
            wraplength=_WRAPLENGTH,
            padx=6,
            pady=4,
        ).pack(padx=1, pady=1)

    def destroy(self) -> None:
        self._tip.destroy()


class ParameterTreeTooltip:
    """Shows ParameterDefinition.description for the Treeview row under the cursor.

    The caller passes a getter for the current ``{iid: ParameterDefinition}`` dict
    because the dict is rebuilt each time the method selection changes.

    Usage::

        ParameterTreeTooltip(tree, lambda: self.app.dynamic_params_defs)
    """

    def __init__(
        self,
        tree: tk.Widget,
        params_defs_getter: Callable[[], dict],
    ) -> None:
        self._tree = tree
        self._get_defs = params_defs_getter
        self._tip: _TooltipWindow | None = None
        self._after_id: str | None = None
        self._current_iid: str | None = None

        tree.bind("<Motion>", self._on_motion, add="+")
        tree.bind("<Leave>", self._on_leave, add="+")

    def _on_motion(self, event: tk.Event) -> None:
        iid = self._tree.identify_row(event.y)
        if iid == self._current_iid:
            return
        self._current_iid = iid
        self._hide()
        defs = self._get_defs()
        if iid and iid in defs:
            self._schedule_show(event.x_root, event.y_root, defs[iid].description)

    def _on_leave(self, event: tk.Event) -> None:
        self._current_iid = None
        self._hide()

    def _schedule_show(self, x: int, y: int, text: str) -> None:
        self._cancel_pending()
        self._after_id = self._tree.after(_DELAY_MS, lambda: self._show(x, y, text))

    def _cancel_pending(self) -> None:
        if self._after_id is not None:
            self._tree.after_cancel(self._after_id)
            self._after_id = None

    def _show(self, x: int, y: int, text: str) -> None:
        self._destroy_tip()
        self._tip = _TooltipWindow(self._tree, text, x, y)

    def _destroy_tip(self) -> None:
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None

    def _hide(self) -> None:
        self._cancel_pending()
        self._destroy_tip()


def attach_tooltip(widget: tk.Widget, text: str) -> None:
    """Attach a hover tooltip to any Tkinter widget.

    Safe to call on Entry, Label, Combobox, Button, etc.
    """
    state: dict = {"tip": None, "after_id": None}

    def _show(x: int, y: int) -> None:
        _clear_tip()
        state["tip"] = _TooltipWindow(widget, text, x, y)

    def _clear_tip() -> None:
        if state["tip"] is not None:
            state["tip"].destroy()
            state["tip"] = None

    def on_enter(event: tk.Event) -> None:
        state["after_id"] = widget.after(_DELAY_MS, lambda: _show(event.x_root, event.y_root))

    def on_leave(event: tk.Event) -> None:
        if state["after_id"] is not None:
            widget.after_cancel(state["after_id"])
            state["after_id"] = None
        _clear_tip()

    widget.bind("<Enter>", on_enter, add="+")
    widget.bind("<Leave>", on_leave, add="+")
