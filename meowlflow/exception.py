class MeowlflowException(Exception):
    status_code = 500
    errorcode = "internal-error"

    def __init__(self, message, payload=None):
        super().__init__()
        self.payload = dict(payload or ())
        self.message = message

    def to_dict(self):
        return {
            "code": self.errorcode,
            "message": self.message,
            "details": self.payload,
        }

    def __str__(self):
        return self.message


class InvalidUsage(MeowlflowException):
    status_code = 400
    errorcode = "invalid-usage"


class InvalidParams(MeowlflowException):
    status_code = 422
    errorcode = "invalid-parameters"


class ResourceNotFound(MeowlflowException):
    status_code = 404
    errorcode = "resource-not-found"


class Forbidden(MeowlflowException):
    status_code = 403
    errorcode = "forbidden"


class UnauthorizedAccess(MeowlflowException):
    status_code = 401
    errorcode = "unauthorized-access"


class Unsupported(MeowlflowException):
    status_code = 501
    errorcode = "unsupported"


class Unexpected(MeowlflowException):
    status_code = 500
    errorcode = "unexpected-error"
