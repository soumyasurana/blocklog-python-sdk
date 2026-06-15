"""
blocklog.exceptions
~~~~~~~~~~~~~~~~~~~
Exceptions raised by the Blocklog SDK. All custom exceptions inherit from BlocklogError.
"""

class BlocklogError(Exception):
    """Base exception for all Blocklog SDK errors."""
    pass


class BlocklogCommitError(BlocklogError):
    """Raised when a decision context fails to commit to the backend."""
    pass


class BlocklogAuthError(BlocklogError):
    """Raised when authentication or authorization fails."""
    pass
