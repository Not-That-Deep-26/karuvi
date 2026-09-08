"""
Architecture Reconstruction Engine Exceptions
============================================
"""
from __future__ import annotations


class ArchitectureError(Exception):
    """Base exception for all architecture reconstruction errors."""
    pass


class GraphValidationError(ArchitectureError):
    """Raised when an input graph fails validation constraints."""
    pass


class ComponentResolutionError(ArchitectureError):
    """Raised when component discovery or aggregation encounters an invalid state."""
    pass


class MissingDependencyError(ArchitectureError):
    """Raised when an optional dependency required for an architecture stage is missing."""
    pass
