"""Synthetic dental notes -> OMOP -> periodontal status benchmark.

Modules
-------
labels    perio chart numerics -> status label (AAP/EFP 2017, simplified)
notes     perio chart + visit context -> synthetic SOAP note text
registry  load models.yaml
paths     where data lives, overridable by env for Databricks
"""

from .labels import PerioChart, Status, label_chart  # noqa: F401
from .notes import render_soap_note  # noqa: F401
from .registry import load_registry  # noqa: F401
