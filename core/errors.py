class AIONError(Exception):
    code = "UNKNOWN_ERROR"
    message = "Unknown error"

    def to_dict(self):
        return {
            "status": "ERROR",
            "error": {
                "code": self.code,
                "message": self.message
            }
        }


class AuthorityNotFound(AIONError):
    code = "AUTH_NOT_FOUND"
    message = "Authority ID not found"


class AuthorityRevoked(AIONError):
    code = "AUTH_REVOKED"
    message = "Authority has been revoked"


class AuthorityExpired(AIONError):
    code = "AUTH_EXPIRED"
    message = "Authority has expired"


class AuthorityConsumed(AIONError):
    code = "AUTH_CONSUMED"
    message = "Authority already consumed"


class InvalidSignature(AIONError):
    code = "INVALID_SIGNATURE"
    message = "Invalid authority signature"
