"""Helpers for rendering project markdown docs in a browser.

This module keeps the GUI class smaller by centralizing the markdown->HTML
rendering and temporary file lifecycle used by the Documentation dialog.

Intentionally lightweight; the caller provides tkinter root/messagebox.
"""

from __future__ import annotations

import os
import tempfile
import webbrowser
from typing import Any


def render_markdown_to_html(markdown_module: Any, markdown_content: str, title: str) -> str:
    """Convert markdown to a styled HTML document with TOC."""
    md = markdown_module.Markdown(
        extensions=[
            "toc",
            "extra",
            "codehilite",
            "nl2br",
        ]
    )

    html_content = md.convert(markdown_content)
    toc_html = getattr(md, "toc", "")

    return f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
    <script>
        // Render LaTeX math in docs using MathJax.
        // Supports inline: $...$ or \\(...\\) and display: $$...$$ or \\[...]\\.
        window.MathJax = {{
            tex: {{
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
            }},
            options: {{
                skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
            }},
        }};
    </script>
    <script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; line-height: 1.6; }}
    .toc {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
    .toc h2 {{ margin-top: 0; color: #333; }}
    .toc ul {{ margin: 0; padding-left: 20px; }}
    .toc a {{ color: #0066cc; text-decoration: none; }}
    .toc a:hover {{ text-decoration: underline; }}
    h1, h2, h3, h4 {{ color: #2c3e50; }}
    h1 {{ border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
    h2 {{ border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }}
    pre {{ background: #f8f8f8; padding: 10px; border-radius: 5px; overflow-x: auto; }}
    code {{ background: #f0f0f0; padding: 2px 4px; border-radius: 3px; }}
    blockquote {{ border-left: 4px solid #3498db; padding-left: 15px; margin: 15px 0; color: #555; }}
    table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background-color: #f2f2f2; }}
  </style>
</head>
<body>
  <div class="toc">
    <h2>📋 Table of Contents</h2>
    {toc_html}
  </div>
  <hr>
  {html_content}
</body>
</html>
'''


def open_markdown_path_in_browser(
    *,
    root: Any,
    markdown_path: str,
    title: str,
    messagebox: Any,
    markdown_available: bool,
    markdown_module: Any,
) -> None:
    """Render a markdown file to HTML and open it in the browser."""
    if not os.path.exists(markdown_path):
        messagebox.showerror("Not Found", f"File not found:\n{markdown_path}")
        return

    if not markdown_available or markdown_module is None:
        messagebox.showerror(
            "Markdown Not Available",
            "HTML documentation view requires the 'markdown' package. "
            "Install it (pip install markdown) or use the packaged environment.",
        )
        return

    try:
        with open(markdown_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        html = render_markdown_to_html(markdown_module, markdown_content, title=title)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(html)
            temp_path = tmp.name

        webbrowser.open("file://" + os.path.abspath(temp_path))

        # Best-effort cleanup after a delay (keep file long enough for browser to load).
        def cleanup() -> None:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

        root.after(5000, cleanup)

    except Exception as e:
        messagebox.showerror("Error", f"Could not open browser: {e}")
