"""Typed harness failures mapped by the HTTP layer."""


class HarnessError(Exception):
    """Base error carrying a run identifier and public message."""

    code = "harness_error"
    status_code = 500

    def __init__(self, message: str, run_id: str | None = None) -> None:
        super().__init__(message)
        self.public_message = message
        self.run_id = run_id


class InputTooLongError(HarnessError):
    code = "input_too_long"
    status_code = 413


class ModelUnavailableError(HarnessError):
    code = "model_unavailable"
    status_code = 503


class RunTimeoutError(HarnessError):
    code = "run_timeout"
    status_code = 504


class UpstreamModelError(HarnessError):
    code = "upstream_model_error"
    status_code = 502
