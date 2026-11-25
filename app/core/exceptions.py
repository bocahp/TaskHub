class AppException(Exception):
    status_code = 500

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundException(AppException):
    status_code = 404


class ConflictException(AppException):
    status_code = 409


class UnauthorizedException(AppException):
    status_code = 401


class ForbiddenException(AppException):
    status_code = 403


class UnprocessableEntityException(AppException):
    status_code = 422


class ServiceUnavailableException(AppException):
    status_code = 503
