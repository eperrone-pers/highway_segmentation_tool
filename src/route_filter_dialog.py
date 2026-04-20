"""
Route Filter Dialog Module for Highway Segmentation GA

This module provides a popup dialog for selecting which routes to process
in multi-route optimization, featuring multi-select functionality, search filtering,
and standard Windows selection patterns.
"""

import tkinter as tk
from tkinter import ttk


class RouteFilterDialog:
    """
    Dialog for filtering and selecting routes for processing.
    
    Supports:
    - Multi-select with Ctrl+click and Shift+click
    - Search/filter functionality
    - Select All / Clear All buttons
    - Standard Windows selection patterns
    """
    
    def __init__(self, parent, available_routes, selected_routes):
        """
        Initialize the route filter dialog.
        
        Args:
            parent: Parent window
            available_routes (list): List of all available route names
            selected_routes (list): List of currently selected route names
        """
        self.parent = parent
        self.available_routes = available_routes.copy()
        self.selected_routes = selected_routes.copy()
        self.filtered_routes = available_routes.copy()
        self.result = None
        self.search_timer = None  # For debounced search
        
        # Dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Filter Routes")
        self.dialog.geometry("500x600")
        self.dialog.grab_set()  # Make modal
        self.dialog.resizable(True, True)
        
        # Center the dialog
        self._center_dialog()
        
        # Create UI
        self._create_widgets()
        
        # Bind events
        self._bind_events()
        
        # Initialize route display
        self._update_routes_display()
    
    def _center_dialog(self):
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        
        # Get parent window position and size
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Calculate center position
        dialog_width = 500
        dialog_height = 600
        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def _create_widgets(self):
        """Create the dialog widgets."""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Select Routes to Process", 
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Type-ahead combobox frame
        combo_frame = ttk.Frame(main_frame)
        combo_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(combo_frame, text="Type to search and select routes:").pack(side="left")
        
        # Create combobox with type-ahead filtering
        self.route_combo_var = tk.StringVar()
        self.route_combo = ttk.Combobox(combo_frame, textvariable=self.route_combo_var, 
                                       width=40, state="normal")
        self.route_combo.pack(side="left", padx=(5, 10), fill="x", expand=True)
        
        # Set initial values
        self.route_combo['values'] = self.available_routes
        
        # Clear combobox button
        ttk.Button(combo_frame, text="Clear", 
                  command=self._clear_combo).pack(side="right", padx=(5, 0))
        
        # Add button to add selected route
        ttk.Button(combo_frame, text="Add Route", 
                  command=self._add_selected_route).pack(side="right", padx=(5, 5))
        
        # Selection buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(button_frame, text="Select All Routes", 
                  command=self._select_all).pack(side="left", padx=(0, 5))
        ttk.Button(button_frame, text="Clear All Routes", 
                  command=self._clear_all).pack(side="left", padx=(5, 5))
        
        # Status label
        self.status_label = ttk.Label(button_frame, text="", foreground="blue")
        self.status_label.pack(side="right")
        
        # All routes display frame with scrollbar
        routes_frame = ttk.LabelFrame(main_frame, text="All Routes (click to select/deselect)", padding=5)
        routes_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Create frame for listbox and scrollbar
        list_container = ttk.Frame(routes_frame)
        list_container.pack(fill="both", expand=True)
        
        # Listbox to show all routes with selection indicators
        self.routes_listbox = tk.Listbox(list_container, selectmode="single", 
                                        font=("Consolas", 10), height=10)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", 
                                 command=self.routes_listbox.yview)
        self.routes_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.routes_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store route data for easy lookup
        self.displayed_routes = []  # Will store routes in display order
        
        # Remove selected route button
        remove_button_frame = ttk.Frame(routes_frame)
        remove_button_frame.pack(fill="x", pady=(5, 0))
        
        ttk.Label(remove_button_frame, 
                 text="Tip: Click any route to select/deselect it", 
                 font=("Arial", 8), foreground="gray").pack(side="left")
        
        ttk.Button(remove_button_frame, text="Toggle Selected", 
                  command=self._toggle_selected_route).pack(side="right")
        
        # Instructions
        instructions = ttk.Label(main_frame, 
                               text="Instructions: Type in dropdown to filter • Press Enter to add • Click routes below to select/deselect",
                               font=("Arial", 9), foreground="gray")
        instructions.pack(pady=(0, 10))
        
        # Action buttons frame
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill="x")
        
        ttk.Button(action_frame, text="OK", 
                  command=self._ok_clicked).pack(side="right", padx=(5, 0))
        ttk.Button(action_frame, text="Cancel", 
                  command=self._cancel_clicked).pack(side="right")
        
        # Route count summary
        self.summary_label = ttk.Label(action_frame, text="", foreground="blue")
        self.summary_label.pack(side="left")
    
    def _bind_events(self):
        """Bind event handlers."""
        # Combobox type-ahead filtering
        self.route_combo_var.trace("w", self._on_combo_change)
        
        # Combobox selection and keyboard events
        self.route_combo.bind("<<ComboboxSelected>>", self._on_combo_selected)
        self.route_combo.bind("<Return>", self._on_combo_return)
        self.route_combo.bind("<KeyRelease>", self._on_combo_keyrelease)
        
        # Routes listbox events
        self.routes_listbox.bind("<Button-1>", self._on_route_click)
        self.routes_listbox.bind("<Double-Button-1>", self._toggle_selected_route)
        
        # Global keyboard shortcuts
        self.dialog.bind("<Control-a>", lambda e: self._select_all())
        self.dialog.bind("<Escape>", lambda e: self._cancel_clicked())
        
        # Focus on combobox
        self.route_combo.focus_set()
    
    def _on_combo_change(self, *_):
        """Handle combobox text changes with type-ahead filtering."""
        # Cancel previous timer if it exists
        if self.search_timer:
            self.dialog.after_cancel(self.search_timer)
        
        # Set new timer for responsive filtering
        self.search_timer = self.dialog.after(100, self._filter_combobox)
    
    def _filter_combobox(self):
        """Filter combobox options based on typed text."""
        typed_text = self.route_combo_var.get().strip()
        
        if not typed_text:
            # Show all routes when no text
            self.route_combo['values'] = self.available_routes
            return
            
        typed_lower = typed_text.lower()
        
        # Filter routes with smart matching
        exact_matches = []
        starts_with_matches = []
        contains_matches = []
        
        for route in self.available_routes:
            route_lower = route.lower()
            if route_lower == typed_lower:
                exact_matches.append(route)
            elif route_lower.startswith(typed_lower):
                starts_with_matches.append(route)
            elif typed_lower in route_lower:
                contains_matches.append(route)
        
        # Combine results with priority
        filtered_routes = exact_matches + starts_with_matches + contains_matches
        
        if filtered_routes:
            self.route_combo['values'] = filtered_routes
            
            # If there's an exact match, don't auto-complete
            # If only one starts-with match, suggest auto-completion
            if not exact_matches and len(starts_with_matches) == 1:
                best_match = starts_with_matches[0]
                # Store current cursor position
                cursor_pos = len(typed_text)  # Use length of typed text as cursor position
                # Set the full text
                self.route_combo_var.set(best_match)
                # Select the auto-completed part
                self.route_combo.selection_range(cursor_pos, len(best_match))
                self.route_combo.icursor(cursor_pos)
        else:
            # No matches found
            self.route_combo['values'] = []
    
    def _on_combo_keyrelease(self, event=None):
        """Handle key release events for better user experience."""
        # If user presses Tab or Right arrow, accept the suggestion
        if event and event.keysym in ['Tab', 'Right']:
            if self.route_combo.selection_present():
                self.route_combo.selection_clear()
                self.route_combo.icursor(len(self.route_combo.get()))
    
    def _on_combo_selected(self, event=None):
        """Handle combobox selection."""
        selected_route = self.route_combo.get()
        if selected_route and selected_route in self.available_routes:
            self._add_route_to_selection(selected_route)
    
    def _on_combo_return(self, event=None):
        """Handle Enter key in combobox - add best match to selection."""
        typed_text = self.route_combo.get().strip()
        
        if not typed_text:
            return
        
        # First check for exact match
        if typed_text in self.available_routes:
            self._add_route_to_selection(typed_text)
            return
        
        # Look for best match from available routes
        typed_lower = typed_text.lower()
        best_match = None
        
        # Try to find the best match in priority order
        for route in self.available_routes:
            route_lower = route.lower()
            
            # Exact case-insensitive match
            if route_lower == typed_lower:
                best_match = route
                break
            
            # Starts with match (if we don't have a better match yet)
            if not best_match and route_lower.startswith(typed_lower):
                best_match = route
        
        # If we found a match, add it
        if best_match:
            self._add_route_to_selection(best_match)
        else:
            # No match found - show user feedback
            if hasattr(self, 'status_label'):
                original_text = self.status_label.cget('text')
                self.status_label.config(text=f"No match found for '{typed_text}'", foreground="red")
                # Reset after 2 seconds
                self.dialog.after(2000, lambda: self.status_label.config(text=original_text, foreground="blue"))
    
    def _add_selected_route(self):
        """Add currently selected/typed route to the selection."""
        selected_route = self.route_combo.get()
        if selected_route and selected_route in self.available_routes:
            self._add_route_to_selection(selected_route)
    
    def _add_route_to_selection(self, route):
        """Add a route to the selected routes list."""
        if route not in self.selected_routes:
            self.selected_routes.append(route)
            self._update_routes_display()
            # Clear the combobox for next selection and reset to show all routes
            self.route_combo_var.set("")
            self.route_combo['values'] = self.available_routes
            # Keep focus on combobox for continuous selection
            self.route_combo.focus_set()
    
    def _on_route_click(self, event=None):
        """Handle single click on route in listbox."""
        selection = self.routes_listbox.curselection()
        if selection:
            # Single click just selects the item in the listbox
            # Double click or button will toggle the selection
            pass
    
    def _toggle_selected_route(self, event=None):
        """Toggle selection of the currently selected route in the listbox."""
        selection = self.routes_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.displayed_routes):
                route = self.displayed_routes[index]
                if route in self.selected_routes:
                    self.selected_routes.remove(route)
                else:
                    self.selected_routes.append(route)
                self._update_routes_display()
                # Restore selection to the same index
                if index < self.routes_listbox.size():
                    self.routes_listbox.selection_set(index)
    
    def _update_routes_display(self):
        """Update the routes listbox to show all routes with selected ones at the top."""
        # Clear current display
        self.routes_listbox.delete(0, tk.END)
        self.displayed_routes.clear()
        
        # Sort selected routes alphabetically
        selected_sorted = sorted(self.selected_routes)
        
        # Sort unselected routes alphabetically
        unselected_routes = [r for r in self.available_routes if r not in self.selected_routes]
        unselected_sorted = sorted(unselected_routes)
        
        # Combine: selected routes first, then unselected
        self.displayed_routes = selected_sorted + unselected_sorted
        
        # Add routes to listbox with visual indicators
        for i, route in enumerate(self.displayed_routes):
            if route in self.selected_routes:
                # Selected route - show with checkmark and highlight
                display_text = f"✓ {route}"
                self.routes_listbox.insert(tk.END, display_text)
                # Highlight selected routes with color
                self.routes_listbox.itemconfig(i, {'bg': '#e6f3ff', 'fg': '#0066cc'})
            else:
                # Unselected route - show normally
                display_text = f"  {route}"
                self.routes_listbox.insert(tk.END, display_text)
                # Alternate row colors for unselected
                if i % 2 == 0:
                    self.routes_listbox.itemconfig(i, {'bg': '#f8f8f8'})
        
        # Update status label with enhanced information
        self._update_status_label()
    
    def _update_status_label(self):
        """Update the status label with selection information."""
        count = len(self.selected_routes)
        total = len(self.available_routes)
        
        if count == 0:
            self.status_label.config(text="No routes selected - click routes below or type above", foreground="gray")
        elif count == 1:
            self.status_label.config(text="1 route selected ✓", foreground="green")
        elif count == total:
            self.status_label.config(text=f"All {count} routes selected ✓", foreground="blue")
        else:
            self.status_label.config(text=f"{count} of {total} routes selected ✓", foreground="blue")
    
    def _clear_combo(self):
        """Clear the combobox and reset values."""
        self.route_combo_var.set("")
        self.route_combo['values'] = self.available_routes
        self.route_combo.focus_set()
    
    def _select_all(self):
        """Select all available routes."""
        self.selected_routes = self.available_routes.copy()
        self._update_routes_display()
    
    def _clear_all(self):
        """Clear all route selections."""
        self.selected_routes.clear()
        self._update_routes_display()
    
    def _cancel_clicked(self):
        """Handle Cancel button click."""
        self._cleanup_timer()
        self.result = None
        self.dialog.destroy()
    
    def _ok_clicked(self):
        """Handle OK button click."""
        self._cleanup_timer()
        self.result = self.selected_routes.copy()  # Return copy of selected routes
        self.dialog.destroy()
    
    def _cleanup_timer(self):
        """Clean up any pending search timer."""
        if self.search_timer:
            self.dialog.after_cancel(self.search_timer)
            self.search_timer = None
    
    def show(self):
        """Show the dialog and return the result."""
        self.dialog.wait_window()
        self._cleanup_timer()  # Ensure cleanup even if dialog closed via X button
        return self.result