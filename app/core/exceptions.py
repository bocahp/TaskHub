class NotFoundException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ConflictException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
