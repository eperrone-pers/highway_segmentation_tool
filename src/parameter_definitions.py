"""
Declarative parameter-definition classes for the extensible method framework.

Each class describes one parameter: its display name, validation rules, and
how to create/read/write the corresponding Tkinter widget. Method authors add
parameter definitions to their method's parameter list in config.py; the UI
builder and parameter manager consume them generically.

All names are re-exported from config.py for backward compatibility.
"""

from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional, Union, TYPE_CHECKING

from value_parsing import parse_optional_float, parse_optional_int

if TYPE_CHECKING:
    import tkinter as tk


@dataclass
class ParameterDefinition(ABC):
    """Base class for declarative parameter definitions."""

    name: str
    display_name: str
    description: str
    group: str
    order: int
    default_value: Any
    required: bool = True

    @abstractmethod
    def create_widget(self, parent) -> "tk.Widget":
        """Create the appropriate Tkinter widget for this parameter."""

    @abstractmethod
    def get_widget_value(self, widget: "tk.Widget") -> Any:
        """Read the current value from the widget."""

    @abstractmethod
    def set_widget_value(self, widget: "tk.Widget", value: Any) -> None:
        """Write a value into the widget."""

    @abstractmethod
    def validate_value(self, value: Any) -> tuple[bool, str]:
        """Return (is_valid, error_message)."""


@dataclass
class NumericParameter(ParameterDefinition):
    """Parameter definition for numeric (int or float) values."""

    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: float = 1.0
    decimal_places: int = 0
    widget_width: int = 10

    def create_widget(self, parent) -> "tk.Entry":
        import tkinter as tk
        widget = tk.Entry(parent, width=self.widget_width)
        self.set_widget_value(widget, self.default_value)
        return widget

    def get_widget_value(self, widget: "tk.Entry") -> Union[int, float]:
        try:
            value = float(widget.get())
            if math.isnan(value):
                raise ValueError("NaN is not a valid numeric value")
            return int(value) if self.decimal_places == 0 else round(value, self.decimal_places)
        except ValueError:
            return self.default_value

    def set_widget_value(self, widget: "tk.Entry", value: Union[int, float]) -> None:
        import tkinter as tk
        widget.delete(0, tk.END)
        if self.decimal_places == 0:
            widget.insert(0, str(int(value)))
        else:
            widget.insert(0, f"{value:.{self.decimal_places}f}")

    def validate_value(self, value: Any) -> tuple[bool, str]:
        try:
            num_value = float(value)
            if math.isnan(num_value):
                return False, f"{self.display_name} must be a valid number"
            if self.min_value is not None and num_value < self.min_value:
                return False, f"{self.display_name} must be >= {self.min_value}"
            if self.max_value is not None and num_value > self.max_value:
                return False, f"{self.display_name} must be <= {self.max_value}"
            if self.decimal_places == 0 and not float(num_value).is_integer():
                return False, f"{self.display_name} must be an integer"
            return True, ""
        except (ValueError, TypeError):
            return False, f"{self.display_name} must be a valid number"


@dataclass
class OptionalNumericParameter(ParameterDefinition):
    """Parameter definition for optional numeric values that may be None."""

    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: float = 1.0
    decimal_places: int = 0
    none_text: str = "(None)"
    widget_width: int = 10

    def create_widget(self, parent) -> "tk.Entry":
        import tkinter as tk
        widget = tk.Entry(parent, width=self.widget_width)
        self.set_widget_value(widget, self.default_value)
        return widget

    def get_widget_value(self, widget: "tk.Entry") -> Union[int, float, None]:
        try:
            if self.decimal_places == 0:
                return parse_optional_int(widget.get())
            value = parse_optional_float(widget.get())
            return None if value is None else round(value, self.decimal_places)
        except ValueError:
            return self.default_value

    def set_widget_value(self, widget: "tk.Entry", value: Union[int, float, None]) -> None:
        import tkinter as tk
        widget.delete(0, tk.END)
        if value is None:
            widget.insert(0, self.none_text)
        elif self.decimal_places == 0:
            widget.insert(0, str(int(value)))
        else:
            widget.insert(0, f"{value:.{self.decimal_places}f}")

    def validate_value(self, value: Any) -> tuple[bool, str]:
        if value is None:
            return True, ""
        try:
            num_value = float(value)
            if math.isnan(num_value):
                return False, f"{self.display_name} must be a valid number or None"
            if self.min_value is not None and num_value < self.min_value:
                return False, f"{self.display_name} must be >= {self.min_value} or None"
            if self.max_value is not None and num_value > self.max_value:
                return False, f"{self.display_name} must be <= {self.max_value} or None"
            if self.decimal_places == 0 and not float(num_value).is_integer():
                return False, f"{self.display_name} must be an integer or None"
            return True, ""
        except (ValueError, TypeError):
            return False, f"{self.display_name} must be a valid number or None"


@dataclass
class SelectParameter(ParameterDefinition):
    """Parameter definition for selection from predefined options."""

    options: Optional[List[tuple]] = None  # List of (display_text, value) tuples

    def __post_init__(self):
        if self.options is None:
            self.options = []

    def create_widget(self, parent) -> "tk.StringVar":
        import tkinter as tk
        widget_var = tk.StringVar(parent)
        default_display = next(
            (display for display, val in self.options if val == self.default_value),
            self.options[0][0] if self.options else "",
        )
        widget_var.set(default_display)
        return widget_var

    def get_widget_value(self, widget: "tk.StringVar") -> Any:
        display_text = widget.get()
        for display, value in self.options:
            if display == display_text:
                return value
        return self.default_value

    def set_widget_value(self, widget: "tk.StringVar", value: Any) -> None:
        display_text = next(
            (display for display, val in self.options if val == value),
            self.options[0][0] if self.options else "",
        )
        widget.set(display_text)

    def validate_value(self, value: Any) -> tuple[bool, str]:
        valid_values = [val for _, val in self.options]
        if value in valid_values:
            return True, ""
        return False, f"{self.display_name} must be one of: {', '.join(str(v) for v in valid_values)}"


@dataclass
class ColumnSelectParameter(ParameterDefinition):
    """Parameter for selecting a single CSV column by header name."""

    widget_width: int = 25

    def create_widget(self, parent) -> "tk.StringVar":
        import tkinter as tk
        widget_var = tk.StringVar(parent)
        widget_var.set(str(self.default_value) if self.default_value is not None else "")
        return widget_var

    def get_widget_value(self, widget: "tk.StringVar") -> str:
        return str(widget.get()).strip()

    def set_widget_value(self, widget: "tk.StringVar", value: Any) -> None:
        widget.set("" if value is None else str(value))

    def validate_value(self, value: Any) -> tuple[bool, str]:
        if value is None:
            return (not self.required), ("" if not self.required else f"{self.display_name} is required")
        col = str(value).strip()
        if not col:
            if self.required:
                return False, f"{self.display_name} is required"
            return True, ""
        return True, ""


@dataclass
class MultiColumnSelectParameter(ParameterDefinition):
    """Parameter for selecting multiple CSV columns by header name."""

    def create_widget(self, parent) -> "tk.Variable":
        import tkinter as tk
        widget_var = tk.Variable(parent)
        widget_var.set(list(self.default_value or []))
        return widget_var

    def get_widget_value(self, widget) -> List[str]:
        try:
            value = widget.get()
        except Exception:
            value = None
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        return []

    def set_widget_value(self, widget, value: Any) -> None:
        try:
            widget.set(list(value or []))
        except Exception:
            pass

    def validate_value(self, value: Any) -> tuple[bool, str]:
        if value is None:
            value = []
        if not isinstance(value, list):
            return False, f"{self.display_name} must be a list of column names"
        cleaned: List[str] = []
        for v in value:
            s = "" if v is None else str(v).strip()
            if not s:
                return False, f"{self.display_name} must contain non-empty column names"
            cleaned.append(s)
        if self.required and len(cleaned) == 0:
            return False, f"{self.display_name} is required"
        return True, ""


@dataclass
class BoolParameter(ParameterDefinition):
    """Parameter definition for boolean (checkbox) values."""

    def create_widget(self, parent) -> "tk.BooleanVar":
        import tkinter as tk
        widget_var = tk.BooleanVar(parent)
        widget_var.set(self.default_value)
        return widget_var

    def get_widget_value(self, widget: "tk.BooleanVar") -> bool:
        return widget.get()

    def set_widget_value(self, widget: "tk.BooleanVar", value: bool) -> None:
        widget.set(bool(value))

    def validate_value(self, value: Any) -> tuple[bool, str]:
        if isinstance(value, bool):
            return True, ""
        return False, f"{self.display_name} must be True or False"


@dataclass
class TextParameter(ParameterDefinition):
    """Parameter definition for text/string values."""

    min_length: int = 0
    max_length: Optional[int] = None
    allowed_chars: Optional[str] = None
    widget_width: int = 30
    multiline: bool = False

    def create_widget(self, parent) -> "Union[tk.Entry, tk.Text]":
        import tkinter as tk
        if self.multiline:
            widget = tk.Text(parent, width=self.widget_width, height=3)
            widget.insert("1.0", str(self.default_value))
        else:
            widget = tk.Entry(parent, width=self.widget_width)
            widget.insert(0, str(self.default_value))
        return widget

    def get_widget_value(self, widget) -> str:
        import tkinter as tk
        if isinstance(widget, tk.Text):
            return widget.get("1.0", tk.END).strip()
        return widget.get()

    def set_widget_value(self, widget, value: str) -> None:
        import tkinter as tk
        if isinstance(widget, tk.Text):
            widget.delete("1.0", tk.END)
            widget.insert("1.0", str(value))
        else:
            widget.delete(0, tk.END)
            widget.insert(0, str(value))

    def validate_value(self, value: Any) -> tuple[bool, str]:
        str_value = str(value)
        if len(str_value) < self.min_length:
            return False, f"{self.display_name} must be at least {self.min_length} characters"
        if self.max_length and len(str_value) > self.max_length:
            return False, f"{self.display_name} must be at most {self.max_length} characters"
        if self.allowed_chars and not re.match(self.allowed_chars, str_value):
            return False, f"{self.display_name} contains invalid characters"
        return True, ""
