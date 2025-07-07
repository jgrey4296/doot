"""
Reporter: A Module for structured user-directed messaging.

A Reporter has various ReporterGroup's as attributes,
which enable certain formatted output.

eg:
- TreeGroup for printing a tree of data
- WorkflowGroup for outputing the progress of a workflow as it happens
- SummaryGroup for outputing a summary *after* a workflow completes

Formatting is handled by ReportFormatter's

"""

from .formatter import ReportFormatter
from .basic import BasicReporter
