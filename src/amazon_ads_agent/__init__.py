"""Synthetic-data Amazon Ads agent proof of concept."""

from .models import WorkflowResult
from .workflow import run_workflow

__all__ = ["WorkflowResult", "run_workflow"]
__version__ = "0.1.0"
