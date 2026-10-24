"""Output layer: console rendering and the two generated Markdown reports.

Reports take data in and return text or write a file; they never read the model
state on their own, so a report can be regenerated from a CSV alone.
"""

from .bounds import bound_report
from .console import print_table, report
from .ladder import report_table, write_markdown

__all__ = ["report", "print_table", "bound_report", "report_table", "write_markdown"]
