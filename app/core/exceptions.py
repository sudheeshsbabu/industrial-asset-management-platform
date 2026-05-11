class AppError(Exception):
    status_code = 500
    message = "Internal server error"

    def __init__(self, message=None):
        if message:
            self.message = message

class NotFoundError(AppError):
    status_code = 404
    message = "Resource not found"

class BadRequestError(AppError):
    status_code = 400
    message = "Bad request"