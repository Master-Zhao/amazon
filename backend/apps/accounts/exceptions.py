from rest_framework.exceptions import APIException


class AuthenticationAPIException(APIException):
    status_code = 401

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        super().__init__(detail=message, code=error_code)
