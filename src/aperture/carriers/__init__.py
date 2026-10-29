"""Importing this package registers every built-in carrier. Third-party packages add more through the
`aperture.carriers` entry-point group (no changes to Aperture needed)."""

from importlib.metadata import entry_points

from . import arabic, hidden, markup  # noqa: F401  (importing registers)
from .base import AR, EN, FIXES, REGISTRY, Carrier, carrier, select

for _ep in entry_points(group="aperture.carriers"):
    _ep.load()

__all__ = ["AR", "EN", "FIXES", "REGISTRY", "Carrier", "carrier", "select"]
