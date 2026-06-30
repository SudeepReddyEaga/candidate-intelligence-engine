class CandidateTransformerError(Exception):
    """Base application error."""


class UnsupportedSourceError(CandidateTransformerError):
    """Raised when a source cannot be detected or parsed."""


class ParseError(CandidateTransformerError):
    """Raised when a source parser cannot produce a valid partial candidate."""


class ValidationError(CandidateTransformerError):
    """Raised when transformed output does not satisfy the canonical schema."""
