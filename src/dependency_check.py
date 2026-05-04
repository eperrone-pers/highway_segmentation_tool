"""Centralized dependency checks for the application.

This module is intentionally lightweight and import-safe so it can be used early
in GUI startup (before other modules are imported).
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import sys
from typing import Iterable, List


@dataclass(frozen=True)
class Dependency:
    module: str
    label: str
    pip_package: str


REQUIRED_DEPENDENCIES: tuple[Dependency, ...] = (
    Dependency("numpy", "Core numeric library", "numpy"),
    Dependency("pandas", "Core dataframe library", "pandas"),
    Dependency("scipy", "Statistical utilities", "scipy"),
    Dependency("matplotlib", "Plotting / visualization", "matplotlib"),
    Dependency("openpyxl", "Excel export", "openpyxl"),
    Dependency("markdown", "Help / documentation rendering", "markdown"),
    Dependency("ruptures", "PELT Segmentation method", "ruptures"),
    Dependency("jsonschema", "JSON schema validation", "jsonschema"),
)


def is_module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def missing_dependencies(
    dependencies: Iterable[Dependency] = REQUIRED_DEPENDENCIES,
) -> List[Dependency]:
    missing: list[Dependency] = []
    for dep in dependencies:
        if not is_module_available(dep.module):
            missing.append(dep)
    return missing


def install_cmd(pip_package: str) -> str:
    # Use the current interpreter explicitly to reduce confusion.
    return f"Run: {sys.executable} -m pip install {pip_package}"


def format_missing_dependencies_message(missing: Iterable[Dependency]) -> str:
    missing_list = list(missing)
    lines = [
        "One or more required Python packages are missing.",
        "",
        f"Interpreter in use:\n  {sys.executable}",
        "",
        "Missing:",
    ]
    for dep in missing_list:
        lines.append(f"- {dep.module}: {dep.label}")
        lines.append(f"  {install_cmd(dep.pip_package)}")
    return "\n".join(lines)
