"""Context Compaction Memory validation errors."""


class ContextMemoryValidationError(Exception):
    """Base class for Context Compaction Memory validation failures."""


class RangeValidationError(ContextMemoryValidationError):
    """Raised when a memory range is not semantically valid."""


class RetrievalResultValidationError(ContextMemoryValidationError):
    """Raised when a retrieval result is not semantically valid."""

