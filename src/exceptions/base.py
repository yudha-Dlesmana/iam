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
