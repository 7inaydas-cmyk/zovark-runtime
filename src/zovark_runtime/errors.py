"""Runtime skeleton errors."""


class ZovarkRuntimeError(Exception):
    """Base error for the Zovark runtime skeleton."""


class NotImplementedRuntimeCapability(ZovarkRuntimeError):
    """Raised when future runtime behavior is called in Phase 1 skeleton code."""

