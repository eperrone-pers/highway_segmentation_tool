"""Export CLI Run dialog.

Replaces the previous one-click 'Copy CLI Command' flow with a modal dialog
that lets the user review and adjust paths before a run-spec is written and
a CLI command is copied.

Execution modes
---------------
Single file   — generates ``python src/cli.py run --spec "..."``
Directory batch — generates ``python src/cli.py run --spec "..." --input-dir "..." --output-dir "..."``
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from run_spec import (
    build_batch_manifest,
    build_command_for_batch_run,
    build_command_for_run_spec,
    build_run_spec,
    default_batch_manifest_path,
    default_batch_output_dir,
    default_batch_summary_path,
    default_run_spec_path_for_output,
)


class CLIExportDialog:
    """Modal dialog for exporting a CLI run command from the current GUI state.

    Initialise with the state dict produced by
    ``HighwaySegmentationGUI._collect_current_analysis_export_state()``, then
    call ``show()`` to block until the user acts.

    Usage::

        dlg = CLIExportDialog(root, state=state, log_callback=self.log_message)
        result = dlg.show()   # 'copy', 'save', or None
    """

    _WIDTH = 600
    _HEIGHT_SINGLE = 390
    _HEIGHT_BATCH = 570

    def __init__(
        self,
        parent: tk.Misc,
        *,
        state: Dict[str, Any],
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.parent = parent
        self.state = state
        self._log = log_callback or (lambda _msg: None)
        self.result: Optional[str] = None

        # Both modes share the same run-spec format and default path.
        self._default_single_spec = str(
            default_run_spec_path_for_output(state["output_json_path"])
        )

        self._dialog = tk.Toplevel(parent)
        self._dialog.title("Export CLI Run")
        self._dialog.geometry(f"{self._WIDTH}x{self._HEIGHT_SINGLE}")
        self._dialog.resizable(False, False)
        self._dialog.transient(parent)
        try:
            self._dialog.grab_set()
        except Exception:
            pass  # safe to skip in headless / test environments

        self._build()
        self._update_preview()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self) -> Optional[str]:
        """Block until the dialog closes.

        Returns:
            'copy'  — spec written and command copied to clipboard.
            'save'  — spec written, clipboard not touched.
            None    — user cancelled.
        """
        self.parent.wait_window(self._dialog)
        return self.result

    @classmethod
    def open(
        cls,
        parent: tk.Misc,
        *,
        state: Dict[str, Any],
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Optional[str]:
        """Convenience classmethod: create, show, and return the result."""
        return cls(parent, state=state, log_callback=log_callback).show()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        outer = ttk.Frame(self._dialog, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)

        self._outer = outer
        row = 0

        # ---- Execution mode ----------------------------------------
        mode_frame = ttk.LabelFrame(outer, text="Execution mode", padding=(8, 4))
        mode_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        self._mode_var = tk.StringVar(value="single")
        self._mode_var.trace_add("write", self._on_mode_change)

        ttk.Radiobutton(
            mode_frame,
            text="Single file",
            variable=self._mode_var,
            value="single",
        ).grid(row=0, column=0, sticky="w", padx=(0, 16))

        ttk.Radiobutton(
            mode_frame,
            text="Directory batch",
            variable=self._mode_var,
            value="batch",
        ).grid(row=0, column=1, sticky="w")

        ttk.Label(
            mode_frame,
            text="All matched files must share the same column layout.",
            foreground="gray",
        ).grid(row=0, column=2, sticky="w", padx=(12, 0))

        row += 1

        # ---- Run spec path -----------------------------------------
        spec_frame = ttk.LabelFrame(outer, text="Run spec", padding=(8, 4))
        spec_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        spec_frame.columnconfigure(1, weight=1)

        ttk.Label(spec_frame, text="Run spec path").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        self._spec_path_var = tk.StringVar(value=self._default_single_spec)
        self._spec_path_var.trace_add("write", self._on_field_change)
        ttk.Entry(spec_frame, textvariable=self._spec_path_var).grid(
            row=0, column=1, sticky="ew", padx=(0, 6)
        )
        ttk.Button(
            spec_frame, text="Browse…", width=8, command=self._browse_spec_path
        ).grid(row=0, column=2)

        row += 1
        self._options_row = row  # both mode frames go in this row

        # ---- Single-file options -----------------------------------
        self._sf_frame = ttk.LabelFrame(outer, text="Single-file options", padding=(8, 4))
        self._sf_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        self._sf_frame.columnconfigure(1, weight=1)

        ttk.Label(self._sf_frame, text="Input file").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        self._input_file_var = tk.StringVar(value=self.state["data_file_path"])
        self._input_file_var.trace_add("write", self._on_field_change)
        ttk.Entry(self._sf_frame, textvariable=self._input_file_var).grid(
            row=0, column=1, sticky="ew", padx=(0, 6)
        )
        ttk.Button(
            self._sf_frame, text="Browse…", width=8, command=self._browse_input_file
        ).grid(row=0, column=2)

        ttk.Label(self._sf_frame, text="Output JSON").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(4, 0)
        )
        self._output_json_var = tk.StringVar(value=self.state["output_json_path"])
        self._output_json_var.trace_add("write", self._on_field_change)
        ttk.Entry(self._sf_frame, textvariable=self._output_json_var).grid(
            row=1, column=1, sticky="ew", padx=(0, 6), pady=(4, 0)
        )
        ttk.Button(
            self._sf_frame, text="Browse…", width=8, command=self._browse_output_json
        ).grid(row=1, column=2, pady=(4, 0))

        # ---- Batch options (built but hidden) ----------------------
        self._batch_frame = ttk.LabelFrame(outer, text="Batch options", padding=(8, 4))
        self._batch_frame.columnconfigure(1, weight=1)
        self._build_batch_frame()
        self._batch_frame.grid_remove()  # hidden until batch mode selected

        row += 1

        # ---- Command preview ---------------------------------------
        preview_frame = ttk.LabelFrame(outer, text="Command preview", padding=(8, 4))
        preview_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)

        self._preview_text = tk.Text(
            preview_frame,
            height=3,
            wrap="word",
            state="disabled",
            relief="sunken",
            background="#f5f5f5",
            font=("Courier", 9),
        )
        self._preview_text.grid(row=0, column=0, sticky="ew")

        row += 1

        # ---- Action buttons ----------------------------------------
        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=row, column=0, sticky="e")

        ttk.Button(
            btn_frame, text="Copy command", command=self._on_copy
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            btn_frame, text="Save spec files", command=self._on_save
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            btn_frame, text="Cancel", command=self._on_cancel
        ).pack(side="left")

    def _build_batch_frame(self) -> None:
        f = self._batch_frame
        pad_y = (0, 3)

        # Default values derived from the analysis state
        default_out_dir = str(default_batch_output_dir(self.state["output_json_path"]))
        default_manifest = str(default_batch_manifest_path(self.state["output_json_path"]))
        default_summary = str(default_batch_summary_path(default_out_dir))

        r = 0

        # Input directory
        ttk.Label(f, text="Input directory", width=16, anchor="w").grid(
            row=r, column=0, sticky="w", padx=(0, 8), pady=pad_y
        )
        self._batch_input_dir_var = tk.StringVar(value="")
        self._batch_input_dir_var.trace_add("write", self._on_batch_field_change)
        ttk.Entry(f, textvariable=self._batch_input_dir_var).grid(
            row=r, column=1, sticky="ew", padx=(0, 6), pady=pad_y
        )
        ttk.Button(f, text="Browse…", width=8, command=self._browse_batch_input_dir).grid(
            row=r, column=2, pady=pad_y
        )
        r += 1

        # File pattern
        ttk.Label(f, text="File pattern", width=16, anchor="w").grid(
            row=r, column=0, sticky="w", padx=(0, 8), pady=pad_y
        )
        self._batch_glob_var = tk.StringVar(value="*.csv")
        self._batch_glob_var.trace_add("write", self._on_batch_field_change)
        ttk.Entry(f, textvariable=self._batch_glob_var, width=20).grid(
            row=r, column=1, sticky="w", padx=(0, 6), pady=pad_y
        )
        r += 1

        # Include subdirectories
        self._batch_recurse_var = tk.BooleanVar(value=False)
        self._batch_recurse_var.trace_add("write", self._on_batch_field_change)
        ttk.Checkbutton(
            f,
            text="Include subdirectories",
            variable=self._batch_recurse_var,
        ).grid(row=r, column=1, sticky="w", pady=pad_y)
        r += 1

        # Output directory
        ttk.Label(f, text="Output directory", width=16, anchor="w").grid(
            row=r, column=0, sticky="w", padx=(0, 8), pady=pad_y
        )
        self._batch_output_dir_var = tk.StringVar(value=default_out_dir)
        self._batch_output_dir_var.trace_add("write", self._on_batch_field_change)
        ttk.Entry(f, textvariable=self._batch_output_dir_var).grid(
            row=r, column=1, sticky="ew", padx=(0, 6), pady=pad_y
        )
        ttk.Button(f, text="Browse…", width=8, command=self._browse_batch_output_dir).grid(
            row=r, column=2, pady=pad_y
        )
        r += 1

        # Export Excel workbooks
        self._batch_export_excel_var = tk.BooleanVar(value=False)
        self._batch_export_excel_var.trace_add("write", self._on_field_change)
        ttk.Checkbutton(
            f,
            text="Export Excel workbooks (.xlsx per result)",
            variable=self._batch_export_excel_var,
        ).grid(row=r, column=1, sticky="w", pady=pad_y)
        r += 1

        # Manifest path
        ttk.Label(f, text="Manifest path", width=16, anchor="w").grid(
            row=r, column=0, sticky="w", padx=(0, 8), pady=pad_y
        )
        self._batch_manifest_var = tk.StringVar(value=default_manifest)
        self._batch_manifest_var.trace_add("write", self._on_field_change)
        ttk.Entry(f, textvariable=self._batch_manifest_var).grid(
            row=r, column=1, sticky="ew", padx=(0, 6), pady=pad_y
        )
        ttk.Button(f, text="Browse…", width=8, command=self._browse_batch_manifest).grid(
            row=r, column=2, pady=pad_y
        )
        r += 1

        # Summary JSON path
        ttk.Label(f, text="Summary JSON", width=16, anchor="w").grid(
            row=r, column=0, sticky="w", padx=(0, 8), pady=pad_y
        )
        self._batch_summary_var = tk.StringVar(value=default_summary)
        self._batch_summary_var.trace_add("write", self._on_field_change)
        ttk.Entry(f, textvariable=self._batch_summary_var).grid(
            row=r, column=1, sticky="ew", padx=(0, 6), pady=pad_y
        )
        ttk.Button(f, text="Browse…", width=8, command=self._browse_batch_summary).grid(
            row=r, column=2, pady=pad_y
        )
        r += 1

        # Continue on error
        self._batch_continue_on_error_var = tk.BooleanVar(value=True)
        self._batch_continue_on_error_var.trace_add("write", self._on_field_change)
        ttk.Checkbutton(
            f,
            text="Continue on error (process remaining files if one fails)",
            variable=self._batch_continue_on_error_var,
        ).grid(row=r, column=1, sticky="w", pady=pad_y)
        r += 1

        # Preflight separator + info
        ttk.Separator(f, orient="horizontal").grid(
            row=r, column=0, columnspan=3, sticky="ew", pady=(6, 4)
        )
        r += 1

        self._preflight_matched_var = tk.StringVar(value="")
        self._preflight_warnings_var = tk.StringVar(value="")

        ttk.Label(f, text="Matched files", width=16, anchor="w").grid(
            row=r, column=0, sticky="w", padx=(0, 8)
        )
        ttk.Label(f, textvariable=self._preflight_matched_var, foreground="gray").grid(
            row=r, column=1, sticky="w"
        )
        r += 1

        ttk.Label(f, text="Warnings", width=16, anchor="w").grid(
            row=r, column=0, sticky="w", padx=(0, 8)
        )
        self._preflight_warn_label = ttk.Label(
            f, textvariable=self._preflight_warnings_var
        )
        self._preflight_warn_label.grid(row=r, column=1, columnspan=2, sticky="w")

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def _on_mode_change(self, *_args) -> None:
        if self._mode_var.get() == "batch":
            self._sf_frame.grid_remove()
            self._batch_frame.grid(
                row=self._options_row, column=0, sticky="ew", pady=(0, 8)
            )
            self._dialog.geometry(f"{self._WIDTH}x{self._HEIGHT_BATCH}")
            self._update_batch_preflight()
        else:
            self._batch_frame.grid_remove()
            self._sf_frame.grid(
                row=self._options_row, column=0, sticky="ew", pady=(0, 8)
            )
            self._dialog.geometry(f"{self._WIDTH}x{self._HEIGHT_SINGLE}")
        self._update_preview()

    # ------------------------------------------------------------------
    # Field change / preview
    # ------------------------------------------------------------------

    def _on_field_change(self, *_args) -> None:
        self._update_preview()

    def _on_batch_field_change(self, *_args) -> None:
        self._update_batch_preflight()
        self._update_preview()

    def _update_preview(self) -> None:
        if self._mode_var.get() == "batch":
            cmd = self._build_batch_command_preview()
        else:
            spec = self._spec_path_var.get().strip()
            cmd = build_command_for_run_spec(spec) if spec else ""

        self._preview_text.config(state="normal")
        self._preview_text.delete("1.0", "end")
        self._preview_text.insert("1.0", cmd)
        self._preview_text.config(state="disabled")

    def _build_batch_command_preview(self) -> str:
        spec = self._spec_path_var.get().strip()
        input_dir = self._batch_input_dir_var.get().strip()
        output_dir = self._batch_output_dir_var.get().strip()
        if not spec or not input_dir or not output_dir:
            return ""
        return build_command_for_batch_run(
            spec,
            input_dir,
            output_dir,
            glob_pattern=self._batch_glob_var.get().strip() or "*.csv",
            recurse=self._batch_recurse_var.get(),
            summary_json=self._batch_summary_var.get().strip() or None,
            continue_on_error=self._batch_continue_on_error_var.get(),
            export_excel=self._batch_export_excel_var.get(),
        )

    def get_preview_text(self) -> str:
        """Return the current command preview text (used in tests)."""
        return self._preview_text.get("1.0", "end").strip()

    # ------------------------------------------------------------------
    # Batch preflight
    # ------------------------------------------------------------------

    def _update_batch_preflight(self, *_args) -> None:
        input_dir = self._batch_input_dir_var.get().strip()
        glob_pattern = self._batch_glob_var.get().strip() or "*.csv"
        recurse = self._batch_recurse_var.get()

        if not input_dir or not Path(input_dir).is_dir():
            self._preflight_matched_var.set("(choose a directory to see matches)")
            self._preflight_warnings_var.set("")
            self._preflight_warn_label.config(foreground="gray")
            return

        base = Path(input_dir)
        matched = sorted(base.rglob(glob_pattern) if recurse else base.glob(glob_pattern))

        if not matched:
            self._preflight_matched_var.set("0 files matched")
            self._preflight_warnings_var.set("No files matched the selected directory and pattern.")
            self._preflight_warn_label.config(foreground="orange")
            return

        self._preflight_matched_var.set(f"{len(matched)} file(s) matched")

        stems = [f.stem for f in matched]
        duplicates = {s for s in stems if stems.count(s) > 1}
        if duplicates:
            self._preflight_warnings_var.set(
                f"WARNING: {len(duplicates)} duplicate output stem(s). "
                "Adjust directory, pattern, or recursion setting."
            )
            self._preflight_warn_label.config(foreground="red")
        else:
            self._preflight_warnings_var.set("No naming collisions detected.")
            self._preflight_warn_label.config(foreground="gray")

    # ------------------------------------------------------------------
    # Browse buttons
    # ------------------------------------------------------------------

    def _browse_spec_path(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self._dialog,
            title="Save run spec as",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=Path(self._spec_path_var.get()).name if self._spec_path_var.get() else "",
        )
        if path:
            self._spec_path_var.set(path)

    def _browse_input_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self._dialog,
            title="Select input CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self._input_file_var.set(path)

    def _browse_output_json(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self._dialog,
            title="Save output JSON as",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=Path(self._output_json_var.get()).name if self._output_json_var.get() else "",
        )
        if path:
            self._output_json_var.set(path)

    def _browse_batch_input_dir(self) -> None:
        path = filedialog.askdirectory(
            parent=self._dialog, title="Select input directory"
        )
        if path:
            self._batch_input_dir_var.set(path)

    def _browse_batch_output_dir(self) -> None:
        path = filedialog.askdirectory(
            parent=self._dialog, title="Select output directory"
        )
        if path:
            self._batch_output_dir_var.set(path)

    def _browse_batch_manifest(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self._dialog,
            title="Save batch manifest as",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self._batch_manifest_var.set(path)

    def _browse_batch_summary(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self._dialog,
            title="Save batch summary as",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self._batch_summary_var.set(path)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> bool:
        if not self._spec_path_var.get().strip():
            messagebox.showerror(
                "Missing path", "Please choose a run spec path.", parent=self._dialog
            )
            return False

        if self._mode_var.get() == "single":
            if not self._input_file_var.get().strip():
                messagebox.showerror(
                    "Missing path", "Please choose an input file.", parent=self._dialog
                )
                return False
            if not self._output_json_var.get().strip():
                messagebox.showerror(
                    "Missing path", "Please choose an output JSON path.", parent=self._dialog
                )
                return False
        else:
            input_dir = self._batch_input_dir_var.get().strip()
            if not input_dir:
                messagebox.showerror(
                    "Missing path", "Please choose an input directory.", parent=self._dialog
                )
                return False
            if not Path(input_dir).is_dir():
                messagebox.showerror(
                    "Invalid directory",
                    f"The input directory does not exist:\n{input_dir}",
                    parent=self._dialog,
                )
                return False
            if not self._batch_glob_var.get().strip():
                messagebox.showerror(
                    "Missing pattern",
                    "Please enter a file pattern (e.g. *.csv).",
                    parent=self._dialog,
                )
                return False
            if not self._batch_output_dir_var.get().strip():
                messagebox.showerror(
                    "Missing path", "Please choose an output directory.", parent=self._dialog
                )
                return False
            # Block on naming collisions
            stems = self._get_matched_stems()
            duplicates = {s for s in stems if stems.count(s) > 1}
            if duplicates:
                messagebox.showerror(
                    "Naming collision",
                    f"{len(duplicates)} matched file(s) would produce duplicate output names. "
                    "Adjust the directory, pattern, or recursion setting.",
                    parent=self._dialog,
                )
                return False

        return True

    def _get_matched_stems(self) -> list:
        """Return a list of stems for all files matching the current batch settings."""
        input_dir = self._batch_input_dir_var.get().strip()
        glob_pattern = self._batch_glob_var.get().strip() or "*.csv"
        recurse = self._batch_recurse_var.get()
        if not input_dir or not Path(input_dir).is_dir():
            return []
        base = Path(input_dir)
        matched = list(base.rglob(glob_pattern) if recurse else base.glob(glob_pattern))
        return [f.stem for f in matched]

    # ------------------------------------------------------------------
    # Artifact writing
    # ------------------------------------------------------------------

    def _write_artifacts(self) -> dict:
        """Build and persist the run-spec (and batch manifest in batch mode).

        Returns a dict with keys: mode, spec_path, cmd, and (batch only)
        manifest_path, output_dir, summary_json, export_excel.
        """
        if self._mode_var.get() == "batch":
            return self._write_batch_artifacts()
        return self._write_single_artifacts()

    def _write_single_artifacts(self) -> dict:
        spec_path = Path(self._spec_path_var.get().strip())
        output_json_path = self._output_json_var.get().strip()

        merged = dict(self.state)
        merged["data_file_path"] = self._input_file_var.get().strip()
        merged["output_json_path"] = output_json_path

        spec = build_run_spec(
            data_file_path=merged["data_file_path"],
            x_column=merged["x_column"],
            y_column=merged["y_column"],
            gap_threshold=merged["gap_threshold"],
            must_break_columns=merged["must_break_columns"],
            secondary_break_columns=merged["secondary_break_columns"],
            route_column=merged["route_column"],
            selected_routes=merged["selected_routes"],
            method_key=merged["method_key"],
            method_parameters=merged["method_parameters"],
            output_json_path=output_json_path,
            overwrite=True,
            application_version=merged["app_version"],
        )

        spec_path.parent.mkdir(parents=True, exist_ok=True)
        with open(spec_path, "w", encoding="utf-8") as fh:
            json.dump(spec, fh, indent=2, ensure_ascii=False)

        cmd = build_command_for_run_spec(str(spec_path))
        self._log(f"Run spec written: {spec_path}")
        return {"mode": "single", "spec_path": spec_path, "cmd": cmd}

    def _write_batch_artifacts(self) -> dict:
        spec_path = Path(self._spec_path_var.get().strip())
        output_dir = self._batch_output_dir_var.get().strip()
        glob_pattern = self._batch_glob_var.get().strip() or "*.csv"
        recurse = self._batch_recurse_var.get()
        summary_json = self._batch_summary_var.get().strip()
        manifest_path = Path(self._batch_manifest_var.get().strip())
        continue_on_error = self._batch_continue_on_error_var.get()
        export_excel = self._batch_export_excel_var.get()

        # Write the batch template run spec (uses the currently loaded state as template)
        spec = build_run_spec(
            data_file_path=self.state["data_file_path"],
            x_column=self.state["x_column"],
            y_column=self.state["y_column"],
            gap_threshold=self.state["gap_threshold"],
            must_break_columns=self.state["must_break_columns"],
            secondary_break_columns=self.state["secondary_break_columns"],
            route_column=self.state["route_column"],
            selected_routes=self.state["selected_routes"],
            method_key=self.state["method_key"],
            method_parameters=self.state["method_parameters"],
            output_json_path=self.state["output_json_path"],
            overwrite=True,
            application_version=self.state["app_version"],
        )

        spec_path.parent.mkdir(parents=True, exist_ok=True)
        with open(spec_path, "w", encoding="utf-8") as fh:
            json.dump(spec, fh, indent=2, ensure_ascii=False)
        self._log(f"Batch template run spec written: {spec_path}")

        # Write the batch manifest
        manifest = build_batch_manifest(
            run_spec_path=str(spec_path),
            input_dir=self._batch_input_dir_var.get().strip(),
            glob=glob_pattern,
            recurse=recurse,
            output_dir=output_dir,
            summary_json=summary_json,
            continue_on_error=continue_on_error,
            export_excel=export_excel,
            application_version=self.state["app_version"],
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)
        self._log(f"Batch manifest written: {manifest_path}")

        cmd = build_command_for_batch_run(
            str(spec_path),
            self._batch_input_dir_var.get().strip(),
            output_dir,
            glob_pattern=glob_pattern,
            recurse=recurse,
            summary_json=summary_json or None,
            continue_on_error=continue_on_error,
            export_excel=export_excel,
        )
        return {
            "mode": "batch",
            "spec_path": spec_path,
            "manifest_path": manifest_path,
            "output_dir": output_dir,
            "summary_json": summary_json,
            "export_excel": export_excel,
            "cmd": cmd,
        }

    # ------------------------------------------------------------------
    # Success messages
    # ------------------------------------------------------------------

    def _single_success_msg(self, artifacts: dict, *, copied: bool) -> str:
        lines = [
            f"Run spec: {artifacts['spec_path']}",
            f"\nCommand:\n{artifacts['cmd']}",
        ]
        if copied:
            lines.insert(0, "The command has been copied to your clipboard.\n")
        return "\n".join(lines)

    def _batch_success_msg(self, artifacts: dict, *, copied: bool) -> str:
        excel_status = "enabled" if artifacts["export_excel"] else "disabled"
        lines = [
            f"Run spec: {artifacts['spec_path']}",
            f"Batch manifest: {artifacts['manifest_path']}",
            f"Output directory: {artifacts['output_dir']}",
            f"Summary JSON: {artifacts['summary_json']}",
            f"Excel export: {excel_status}",
            f"\nCommand:\n{artifacts['cmd']}",
        ]
        if copied:
            lines.insert(0, "The command has been copied to your clipboard.\n")
        return "\n".join(lines)

    def _success_msg(self, artifacts: dict, *, copied: bool) -> str:
        if artifacts["mode"] == "batch":
            return self._batch_success_msg(artifacts, copied=copied)
        return self._single_success_msg(artifacts, copied=copied)

    def _success_title(self, artifacts: dict, *, copied: bool) -> str:
        if copied:
            return "Command Copied"
        return "Spec Saved" if artifacts["mode"] == "single" else "Batch Spec Saved"

    # ------------------------------------------------------------------
    # Button actions
    # ------------------------------------------------------------------

    def _on_copy(self) -> None:
        if not self._validate():
            return
        try:
            artifacts = self._write_artifacts()
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc), parent=self._dialog)
            return

        try:
            self.parent.clipboard_clear()
            self.parent.clipboard_append(artifacts["cmd"])
            self.parent.update_idletasks()
        except Exception:
            pass

        self._log("Copied command line to clipboard")
        messagebox.showinfo(
            self._success_title(artifacts, copied=True),
            self._success_msg(artifacts, copied=True),
            parent=self._dialog,
        )
        self.result = "copy"
        self._dialog.destroy()

    def _on_save(self) -> None:
        if not self._validate():
            return
        try:
            artifacts = self._write_artifacts()
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc), parent=self._dialog)
            return

        messagebox.showinfo(
            self._success_title(artifacts, copied=False),
            self._success_msg(artifacts, copied=False),
            parent=self._dialog,
        )
        self.result = "save"
        self._dialog.destroy()

    def _on_cancel(self) -> None:
        self._dialog.destroy()
