"""Reusable Treeview component for displaying and editing method parameters.

This module provides a shared component that handles parameter display and inline editing
for both optimization and preprocessing methods.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Optional, Callable, Any


class ParameterTreeView:
    """Reusable Treeview for displaying and editing method parameters with inline editing.
    
    Features:
    - Double-click to edit values inline
    - Boolean parameter toggle on double-click
    - Validation before accepting changes
    - Reset to default functionality
    - Auto-formatting based on parameter type
    """
    
    def __init__(self, parent, app, height: int = 4, on_change_callback: Optional[Callable] = None):
        """Initialize the parameter tree view.
        
        Args:
            parent: Parent tkinter widget
            app: Main application instance (for accessing available_columns, etc.)
            height: Height of the treeview in rows
            on_change_callback: Optional callback function when parameter values change
        """
        self.app = app
        self.on_change_callback = on_change_callback
        self.param_defs = {}  # {param_name: ParameterDefinition}
        self.cell_editor = {"widget": None, "param_name": None}
        self.current_method_key = None
        self.current_method_type = None  # "optimization" or "preprocessing"
        self.param_values = {}  # {param_name: value} - current values
        
        # Tooltip support
        self.tooltip = None
        self.tooltip_id = None
        
        # Create tree frame
        tree_frame = ttk.Frame(parent)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Create Treeview
        columns = ("parameter", "value")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                selectmode="browse", height=height)
        self.tree.heading("parameter", text="Parameter")
        self.tree.heading("value", text="Value")
        self.tree.column("parameter", width=180, anchor="w")
        self.tree.column("value", width=150, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Bind events
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-1>", self._on_single_click)
        self.tree.bind("<Motion>", self._on_motion)
        self.tree.bind("<Leave>", self._on_leave)
        
        # Fix mousewheel scrolling to work within treeview instead of parent
        self.tree.bind("<MouseWheel>", self._on_mousewheel)
        self.tree.bind("<Button-4>", self._on_mousewheel)  # Linux scroll up
        self.tree.bind("<Button-5>", self._on_mousewheel)  # Linux scroll down
        
        # Store reference to tree frame for gridding
        self.frame = tree_frame
    
    def refresh(self, method_key: str, method_type: str = "optimization", param_values: Optional[Dict] = None):
        """Refresh the tree with parameters for the specified method.
        
        Args:
            method_key: The method key to display parameters for
            method_type: "optimization" or "preprocessing"
            param_values: Optional dict of parameter values to display (defaults to method defaults)
        """
        self.current_method_key = method_key
        self.current_method_type = method_type
        
        # Cancel any active editing
        self._cancel_edit()
        
        # Clear existing items
        self.tree.delete(*self.tree.get_children())
        self.param_defs.clear()
        
        # Get method config
        if method_type == "optimization":
            from config import get_optimization_method
            method_config = get_optimization_method(method_key)
        else:  # preprocessing
            from config import get_preprocessing_method
            method_config = get_preprocessing_method(method_key)
        
        # Build param_defs dictionary
        self.param_defs = {param.name: param for param in method_config.parameters}
        
        # Use provided values or defaults
        if param_values is None:
            self.param_values = {param.name: param.default_value for param in method_config.parameters}
        else:
            self.param_values = {
                param.name: param_values.get(param.name, param.default_value)
                for param in method_config.parameters
            }
        
        # Populate tree (sorted by group then order)
        params_sorted = sorted(method_config.parameters, key=lambda p: (p.group, p.order))
        for param_def in params_sorted:
            value = self.param_values[param_def.name]
            formatted_value = self._format_value(param_def, value)
            # Use param name as iid for easy lookup
            self.tree.insert("", "end", iid=param_def.name, 
                           values=(param_def.display_name, formatted_value))
    
    def get_values(self) -> Dict[str, Any]:
        """Get current parameter values."""
        return self.param_values.copy()
    
    def set_value(self, param_name: str, value: Any):
        """Set a specific parameter value and update the display."""
        if param_name not in self.param_defs:
            return
        
        self.param_values[param_name] = value
        param_def = self.param_defs[param_name]
        formatted_value = self._format_value(param_def, value)
        self.tree.item(param_name, values=(param_def.display_name, formatted_value))
    
    def reset_selected_to_default(self):
        """Reset the currently selected parameter to its default value."""
        selection = self.tree.selection()
        if not selection:
            return
        
        param_name = selection[0]
        param_def = self.param_defs.get(param_name)
        if not param_def:
            return
        
        self.set_value(param_name, param_def.default_value)
        
        if self.on_change_callback:
            try:
                self.on_change_callback()
            except Exception:
                pass
    
    def _format_value(self, param_def, value) -> str:
        """Format a parameter value for display in the tree."""
        from config import (
            NumericParameter,
            OptionalNumericParameter,
            SelectParameter,
            BoolParameter,
            ColumnSelectParameter,
            MultiColumnSelectParameter,
        )
        
        if isinstance(param_def, OptionalNumericParameter) and value is None:
            return param_def.none_text
        if isinstance(param_def, BoolParameter):
            return "True" if bool(value) else "False"
        if isinstance(param_def, SelectParameter):
            for display, v in param_def.options:
                if v == value:
                    return str(display)
            return str(value)
        if isinstance(param_def, ColumnSelectParameter):
            return "" if value is None else str(value)
        if isinstance(param_def, MultiColumnSelectParameter):
            if not isinstance(value, list):
                return "None"
            cleaned = [str(v).strip() for v in value if str(v).strip()]
            return "None" if len(cleaned) == 0 else f"{len(cleaned)} selected"
        if isinstance(param_def, NumericParameter):
            try:
                if param_def.decimal_places == 0:
                    return str(int(value))
                return f"{float(value):.{param_def.decimal_places}f}"
            except Exception:
                return str(value)
        return str(value)
    
    def _on_single_click(self, event=None):
        """Handle single click - commit any active editing."""
        self._commit_edit()
    
    def _on_double_click(self, event):
        """Handle double-click to edit a parameter value."""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        col = self.tree.identify_column(event.x)
        if col != "#2":  # Only value column is editable
            return
        
        row_iid = self.tree.identify_row(event.y)
        if not row_iid:
            return
        
        param_name = row_iid
        param_def = self.param_defs.get(param_name)
        if not param_def:
            return
        
        current_value = self.param_values.get(param_name, param_def.default_value)
        
        # Handle boolean toggle immediately
        from config import BoolParameter, SelectParameter, OptionalNumericParameter, ColumnSelectParameter, MultiColumnSelectParameter
        
        if isinstance(param_def, BoolParameter):
            new_value = not bool(current_value)
            ok, msg = param_def.validate_value(new_value)
            if not ok:
                messagebox.showerror("Parameter Validation Error", msg or "Invalid value")
                return
            self.set_value(param_name, new_value)
            if self.on_change_callback:
                try:
                    self.on_change_callback()
                except Exception:
                    pass
            return
        
        # Handle multi-column selector with dialog
        if isinstance(param_def, MultiColumnSelectParameter):
            try:
                from multi_select_dialog import MultiSelectDialog
                
                available_columns = getattr(self.app, 'available_columns', None)
                items = available_columns if isinstance(available_columns, list) else []
                preselected = current_value if isinstance(current_value, list) else []
                
                selected = MultiSelectDialog.ask(
                    self.app.root if hasattr(self.app, 'root') else self.tree,
                    title=f"Select {param_def.display_name}",
                    items=items,
                    selected=preselected,
                    prompt="Select one or more columns:",
                )
                
                if selected is None:
                    return
                
                ok, msg = param_def.validate_value(selected)
                if not ok:
                    messagebox.showerror("Parameter Validation Error", msg or "Invalid value")
                    return
                
                # Enforce membership when headers are known
                if isinstance(items, list) and items:
                    for col_name in selected:
                        if col_name not in items:
                            messagebox.showerror(
                                "Parameter Validation Error",
                                f"{param_def.display_name} must contain columns from the loaded data file",
                            )
                            return
                
                self.set_value(param_name, selected)
                if self.on_change_callback:
                    try:
                        self.on_change_callback()
                    except Exception:
                        pass
                return
            except Exception as e:
                messagebox.showerror("Parameter Editor Error", str(e))
                return
        
        # Start inline editing for other types
        self._cancel_edit()
        bbox = self.tree.bbox(row_iid, "value")
        if not bbox:
            return
        x, y, width, height = bbox
        
        if isinstance(param_def, SelectParameter):
            display_values = [display for display, _ in param_def.options]
            editor = ttk.Combobox(self.tree, values=display_values, state="readonly")
            current_display = next((d for d, v in param_def.options if v == current_value), 
                                  display_values[0] if display_values else "")
            editor.set(str(current_display))
            editor.place(x=x, y=y, width=width, height=height)
            editor.focus_set()
            editor.bind("<<ComboboxSelected>>", lambda _e: self._commit_edit())
        elif isinstance(param_def, ColumnSelectParameter):
            available_columns = getattr(self.app, 'available_columns', None)
            if isinstance(available_columns, list) and available_columns:
                editor = ttk.Combobox(self.tree, values=available_columns, state="readonly")
                if current_value is not None and str(current_value) in available_columns:
                    editor.set(str(current_value))
                else:
                    editor.set("")
                editor.place(x=x, y=y, width=width, height=height)
                editor.focus_set()
                editor.bind("<<ComboboxSelected>>", lambda _e: self._commit_edit())
            else:
                editor = ttk.Entry(self.tree)
                editor.insert(0, "" if current_value is None else str(current_value))
                editor.place(x=x, y=y, width=width, height=height)
                editor.focus_set()
                editor.selection_range(0, tk.END)
                editor.bind("<Return>", lambda _e: self._commit_edit())
        else:
            editor = ttk.Entry(self.tree)
            if isinstance(param_def, OptionalNumericParameter) and current_value is None:
                editor.insert(0, "")
            else:
                editor.insert(0, str(current_value))
            editor.place(x=x, y=y, width=width, height=height)
            editor.focus_set()
            editor.selection_range(0, tk.END)
            editor.bind("<Return>", lambda _e: self._commit_edit())
        
        editor.bind("<Escape>", lambda _e: self._cancel_edit())
        editor.bind("<FocusOut>", lambda _e: self._commit_edit())
        
        self.cell_editor = {
            "widget": editor,
            "param_name": param_name,
        }
    
    def _cancel_edit(self):
        """Cancel any active inline editing."""
        if self.cell_editor.get("widget"):
            try:
                self.cell_editor["widget"].destroy()
            except Exception:
                pass
        self.cell_editor = {"widget": None, "param_name": None}
    
    def _commit_edit(self):
        """Commit the current inline edit."""
        widget = self.cell_editor.get("widget")
        if widget is None:
            return
        
        param_name = self.cell_editor.get("param_name")
        if not param_name:
            self._cancel_edit()
            return
        
        param_def = self.param_defs.get(param_name)
        if not param_def:
            self._cancel_edit()
            return
        
        try:
            value = self._read_editor_value(param_def, widget)
        except Exception as e:
            messagebox.showerror("Invalid Value", str(e))
            try:
                widget.focus_set()
            except Exception:
                pass
            return
        
        ok, msg = param_def.validate_value(value)
        if not ok:
            messagebox.showerror("Parameter Validation Error", msg or "Invalid value")
            try:
                widget.focus_set()
            except Exception:
                pass
            return
        
        # Enforce column membership for column selectors
        try:
            from config import ColumnSelectParameter
            if isinstance(param_def, ColumnSelectParameter):
                available_columns = getattr(self.app, 'available_columns', None)
                if isinstance(available_columns, list) and available_columns:
                    col_name = ("" if value is None else str(value)).strip()
                    if col_name and col_name not in available_columns:
                        messagebox.showerror(
                            "Parameter Validation Error",
                            f"{param_def.display_name} must be a column from the loaded data file",
                        )
                        try:
                            widget.focus_set()
                        except Exception:
                            pass
                        return
        except Exception:
            pass
        
        # Update value
        self.set_value(param_name, value)
        self._cancel_edit()
        
        # Trigger callback
        if self.on_change_callback:
            try:
                self.on_change_callback()
            except Exception:
                pass
    
    def _read_editor_value(self, param_def, widget):
        """Read value from inline editor widget."""
        from config import (
            NumericParameter,
            OptionalNumericParameter,
            SelectParameter,
            ColumnSelectParameter,
        )
        from value_parsing import parse_optional_float, parse_optional_int
        
        raw_value = widget.get()
        
        if isinstance(param_def, SelectParameter):
            # Map display name back to actual value
            for display, value in param_def.options:
                if str(display) == str(raw_value):
                    return value
            raise ValueError(f"Invalid selection: {raw_value}")
        
        if isinstance(param_def, ColumnSelectParameter):
            stripped = str(raw_value).strip()
            return None if not stripped else stripped
        
        if isinstance(param_def, OptionalNumericParameter):
            # Parse optional numeric values (can be None)
            if param_def.decimal_places == 0:
                parsed = parse_optional_int(raw_value)
            else:
                parsed = parse_optional_float(raw_value)
                if parsed is not None:
                    parsed = round(parsed, param_def.decimal_places)
            return parsed
        
        if isinstance(param_def, NumericParameter):
            # Parse numeric values (cannot be None)
            value = float(raw_value)
            if param_def.decimal_places == 0:
                return int(value)
            else:
                return round(value, param_def.decimal_places)
        
        # Default: return as-is
        return raw_value
    
    def _on_motion(self, event):
        """Handle mouse motion to show tooltips for parameter descriptions."""
        # Get item under cursor
        item_id = self.tree.identify_row(event.y)
        
        if not item_id or item_id not in self.param_defs:
            self._hide_tooltip()
            return
        
        # Get parameter definition
        param_def = self.param_defs[item_id]
        
        # Show tooltip if parameter has a description
        if hasattr(param_def, 'description') and param_def.description:
            self._show_tooltip(event, param_def.description)
        else:
            self._hide_tooltip()
    
    def _on_leave(self, event):
        """Hide tooltip when mouse leaves the treeview."""
        self._hide_tooltip()
    
    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling within the treeview."""
        # Determine scroll direction and amount
        if event.num == 4 or event.delta > 0:  # Scroll up
            delta = -1
        elif event.num == 5 or event.delta < 0:  # Scroll down
            delta = 1
        else:
            return "break"
        
        # Scroll the treeview
        self.tree.yview_scroll(delta, "units")
        
        # Return "break" to prevent event propagation to parent
        return "break"
    
    def _show_tooltip(self, event, text):
        """Show tooltip at cursor position."""
        # Cancel any pending hide
        if self.tooltip_id:
            self.tree.after_cancel(self.tooltip_id)
            self.tooltip_id = None
        
        # Create tooltip if it doesn't exist
        if self.tooltip is None:
            self.tooltip = tk.Toplevel(self.tree)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_attributes("-topmost", True)
            
            # Create label with description
            label = tk.Label(
                self.tooltip,
                text=text,
                justify="left",
                background="#ffffe0",
                relief="solid",
                borderwidth=1,
                font=("TkDefaultFont", 9),
                wraplength=300,
                padx=5,
                pady=3
            )
            label.pack()
        else:
            # Update existing tooltip text
            label = self.tooltip.winfo_children()[0]
            label.config(text=text)
        
        # Position tooltip near cursor (slightly offset)
        x = event.x_root + 15
        y = event.y_root + 10
        self.tooltip.wm_geometry(f"+{x}+{y}")
        self.tooltip.deiconify()
    
    def _hide_tooltip(self):
        """Hide and destroy the tooltip."""
        if self.tooltip:
            self.tooltip.withdraw()
            # Schedule destruction after a short delay to avoid flicker
            if self.tooltip_id:
                self.tree.after_cancel(self.tooltip_id)
            self.tooltip_id = self.tree.after(100, self._destroy_tooltip)
    
    def _destroy_tooltip(self):
        """Destroy the tooltip widget."""
        if self.tooltip:
            try:
                self.tooltip.destroy()
            except Exception:
                pass
            self.tooltip = None
        self.tooltip_id = None
