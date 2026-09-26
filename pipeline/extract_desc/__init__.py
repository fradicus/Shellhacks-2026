"""Deterministic extraction for DESC public project-card filings."""

from .parser import build_outputs, parse_desc_pdf, write_outputs

__all__ = ["build_outputs", "parse_desc_pdf", "write_outputs"]
