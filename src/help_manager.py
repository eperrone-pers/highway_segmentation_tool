"""Documentation browser dialog for the Highway Segmentation GUI."""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from docs_browser import open_markdown_path_in_browser


class HelpManager:
    """Manages the documentation browser dialog.

    Provides a modal window that links to the User Guide, per-method analysis
    docs, preprocessing method docs, and developer reference docs, opening
    them in the system browser.
    """

    def __init__(self, app):
        self.app = app

    def show_help(self):
        """Open documentation in the user's browser (preferred UX).

        This dialog intentionally does not render markdown inline. It provides
        config-driven shortcuts to open:
        - USER_GUIDE.md
        - Method-specific README.md files under src/analysis/methods/docs/{method_key}/README.md
        - Preprocessing README.md files under src/preprocessing/methods/docs/{method_key}/README.md
        - Developer reference docs under docs/
        """
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        user_guide_path = os.path.join(project_root, "USER_GUIDE.md")

        help_window = self._create_help_window()
        main_frame = self._build_help_main_frame(help_window)
        self._build_help_header(main_frame)
        self._build_user_guide_section(main_frame, user_guide_path)
        self._build_method_docs_section(main_frame, project_root)
        self._build_preprocessing_docs_section(main_frame, project_root)
        self._build_developer_docs_section(main_frame, project_root)
        self._build_help_close_button(main_frame, help_window)
        self._center_window(help_window)

    def _create_help_window(self) -> tk.Toplevel:
        help_window = tk.Toplevel(self.app.root)
        help_window.title("Documentation")
        help_window.geometry("640x480")
        help_window.minsize(520, 440)
        help_window.resizable(True, False)
        help_window.grab_set()
        return help_window

    def _build_help_main_frame(self, help_window: tk.Toplevel) -> ttk.Frame:
        main_frame = ttk.Frame(help_window, padding=12)
        main_frame.pack(fill="both", expand=True)
        return main_frame

    def _build_help_header(self, main_frame: ttk.Frame) -> None:
        ttk.Label(
            main_frame,
            text="Documentation",
            font=("Arial", 14, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            main_frame,
            text="Open the User Guide, method docs, preprocessing docs, or developer reference in your browser.",
        ).pack(anchor="w", pady=(4, 12))

    def _build_user_guide_section(self, main_frame: ttk.Frame, user_guide_path: str) -> None:
        user_guide_frame = ttk.LabelFrame(main_frame, text="User Guide", padding=10)
        user_guide_frame.pack(fill="x")

        ttk.Button(
            user_guide_frame,
            text="🌐 Open User Guide in Browser",
            command=lambda: self._open_markdown_path_in_browser(user_guide_path, title="User Guide"),
        ).pack(anchor="w")

    def _build_method_docs_section(self, main_frame: ttk.Frame, project_root: str) -> None:
        method_frame = ttk.LabelFrame(main_frame, text="Method Documentation", padding=10)
        method_frame.pack(fill="x", pady=(12, 0))
        method_frame.columnconfigure(1, weight=1)

        available_docs = self._get_available_method_docs(project_root)
        if not available_docs:
            ttk.Label(
                method_frame,
                text="No method README files found under src/analysis/methods/docs/.",
            ).grid(row=0, column=0, columnspan=3, sticky="w")
            return

        ttk.Label(method_frame, text="Method:").grid(row=0, column=0, sticky="w")

        method_display_names = [item[0] for item in available_docs]
        selected_method = tk.StringVar(value=method_display_names[0])

        ttk.Combobox(
            method_frame,
            textvariable=selected_method,
            values=method_display_names,
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", padx=(6, 10))

        def open_selected_method_doc() -> None:
            display_name = selected_method.get()
            for name, _, readme_path in available_docs:
                if name == display_name:
                    self._open_markdown_path_in_browser(readme_path, title=f"Method Doc - {name}")
                    return
            messagebox.showerror("Error", f"Could not resolve README for '{display_name}'")

        ttk.Button(
            method_frame,
            text="Open in Browser",
            command=open_selected_method_doc,
        ).grid(row=0, column=2, sticky="e")

    def _build_preprocessing_docs_section(self, main_frame: ttk.Frame, project_root: str) -> None:
        preprocessing_frame = ttk.LabelFrame(main_frame, text="Preprocessing Documentation", padding=10)
        preprocessing_frame.pack(fill="x", pady=(12, 0))
        preprocessing_frame.columnconfigure(1, weight=1)

        available_docs = self._get_available_preprocessing_docs(project_root)
        if not available_docs:
            ttk.Label(
                preprocessing_frame,
                text="No preprocessing README files found under src/preprocessing/methods/docs/.",
            ).grid(row=0, column=0, columnspan=3, sticky="w")
            return

        ttk.Label(preprocessing_frame, text="Algorithm:").grid(row=0, column=0, sticky="w")

        preprocessing_display_names = [item[0] for item in available_docs]
        selected_preprocessing = tk.StringVar(value=preprocessing_display_names[0])

        ttk.Combobox(
            preprocessing_frame,
            textvariable=selected_preprocessing,
            values=preprocessing_display_names,
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", padx=(6, 10))

        def open_selected_preprocessing_doc() -> None:
            display_name = selected_preprocessing.get()
            for name, _, readme_path in available_docs:
                if name == display_name:
                    self._open_markdown_path_in_browser(
                        readme_path,
                        title=f"Preprocessing Doc - {name}",
                    )
                    return
            messagebox.showerror("Error", f"Could not resolve README for '{display_name}'")

        ttk.Button(
            preprocessing_frame,
            text="Open in Browser",
            command=open_selected_preprocessing_doc,
        ).grid(row=0, column=2, sticky="e")

    def _build_developer_docs_section(self, main_frame: ttk.Frame, project_root: str) -> None:
        dev_frame = ttk.LabelFrame(main_frame, text="Developer Documentation", padding=10)
        dev_frame.pack(fill="x", pady=(12, 0))
        dev_frame.columnconfigure(1, weight=1)

        available_docs = self._get_developer_docs(project_root)
        if not available_docs:
            ttk.Label(
                dev_frame,
                text="No developer docs found under docs/.",
            ).grid(row=0, column=0, columnspan=3, sticky="w")
            return

        ttk.Label(dev_frame, text="Document:").grid(row=0, column=0, sticky="w")

        doc_display_names = [item[0] for item in available_docs]
        selected_doc = tk.StringVar(value=doc_display_names[0])

        ttk.Combobox(
            dev_frame,
            textvariable=selected_doc,
            values=doc_display_names,
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", padx=(6, 10))

        def open_selected_dev_doc() -> None:
            display_name = selected_doc.get()
            for name, doc_path in available_docs:
                if name == display_name:
                    self._open_markdown_path_in_browser(doc_path, title=name)
                    return
            messagebox.showerror("Error", f"Could not resolve doc for '{display_name}'")

        ttk.Button(
            dev_frame,
            text="Open in Browser",
            command=open_selected_dev_doc,
        ).grid(row=0, column=2, sticky="e")

    def _build_help_close_button(self, main_frame: ttk.Frame, help_window: tk.Toplevel) -> None:
        button_row = ttk.Frame(main_frame)
        button_row.pack(fill="x", pady=(14, 0))
        ttk.Button(button_row, text="Close", command=help_window.destroy).pack(side="right")

    def _center_window(self, window: tk.Toplevel) -> None:
        window.update_idletasks()
        x = (window.winfo_screenwidth() // 2) - (window.winfo_width() // 2)
        y = (window.winfo_screenheight() // 2) - (window.winfo_height() // 2)
        window.geometry(f"+{x}+{y}")

    def _get_available_method_docs(self, project_root: str):
        """Return list of (display_name, method_key, readme_path) for methods with docs."""
        try:
            from config import OPTIMIZATION_METHODS
        except Exception:
            return []

        docs_root = os.path.join(project_root, "src", "analysis", "methods", "docs")
        available = []
        for method in OPTIMIZATION_METHODS:
            readme_path = os.path.join(docs_root, method.method_key, "README.md")
            if os.path.exists(readme_path):
                available.append((method.display_name, method.method_key, readme_path))
        return available

    def _get_available_preprocessing_docs(self, project_root: str):
        """Return list of (display_name, method_key, readme_path) for preprocessing methods with docs."""
        try:
            from config import PREPROCESSING_METHODS
        except Exception:
            return []

        docs_root = os.path.join(project_root, "src", "preprocessing", "methods", "docs")
        available = []
        for method in PREPROCESSING_METHODS:
            readme_path = os.path.join(docs_root, method.method_key, "README.md")
            if os.path.exists(readme_path):
                available.append((method.display_name, method.method_key, readme_path))
        return available

    def _get_developer_docs(self, project_root: str):
        """Return list of (display_name, path) for docs/ reference files that exist on disk."""
        docs_dir = os.path.join(project_root, "docs")
        candidates = [
            ("Developer Guide",                    "DEVELOPER_GUIDE.md"),
            ("CLI Usage",                          "CLI_USAGE.md"),
            ("Configuring Analysis Methods",       "configuring_new_analysis_method.md"),
            ("Configuring Preprocessing Methods",  "configuring_new_preprocessing_method.md"),
            ("JSON Format Specification",          "json_format_specification.md"),
        ]
        return [
            (display_name, os.path.join(docs_dir, filename))
            for display_name, filename in candidates
            if os.path.exists(os.path.join(docs_dir, filename))
        ]

    def _open_markdown_path_in_browser(self, markdown_path: str, title: str) -> None:
        """Render a markdown file to HTML and open it in the browser."""
        try:
            import importlib
            markdown_module = importlib.import_module("markdown")
        except Exception:
            markdown_module = None

        open_markdown_path_in_browser(
            markdown_path=markdown_path,
            title=title,
            messagebox=messagebox,
            markdown_available=markdown_module is not None,
            markdown_module=markdown_module,
        )
