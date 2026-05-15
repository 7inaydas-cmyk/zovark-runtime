"""Storage-layer exceptions for investigation_memory."""


class InvestigationMemoryError(Exception):
    """Base class for investigation_memory storage failures."""


class MemoryObjectValidationError(InvestigationMemoryError):
    """Raised when memory object identity or metadata is invalid."""


class MemoryObjectTamperError(InvestigationMemoryError):
    """Raised when stored content does not match recorded metadata."""


class MemoryObjectNotFoundError(InvestigationMemoryError):
    """Raised when a memory object cannot be found."""
