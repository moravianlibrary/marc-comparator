from fastapi import HTTPException, status


class RegistrationError(HTTPException):
    def __init__(self, message: str = "User registration failed"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


class AuthenticationError(HTTPException):
    def __init__(self, message: str = "Could not authenticate user"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)
