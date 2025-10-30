from fastapi import HTTPException, status

from entities.settings import SettingsScope


class SettingsNotFoundError(HTTPException):
    def __init__(self, scope: SettingsScope):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Settings for scope '{scope}' not found.",
        )
