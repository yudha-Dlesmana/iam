class AppException(Exception):
    status_code: int = 500
    message: str = "internal server error"

    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)


class NotFoundError(AppException):
    status_code = 404
    message = "resource not found"


class ConflictError(AppException):
    status_code = 409
    message = "resource conflict"


class ValidationError(AppException):
    status_code = 422
    message = "validation error"


class UnauthorizedError(AppException):
    status_code = 401
    message = "unauthorized"


class ForbiddenError(AppException):
    status_code = 403
    message = "forbidden"


class TooManyRequestsError(AppException):
    status_code = 429
    message = "too many requests"

    def __init__(self, message: str | None = None, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after
