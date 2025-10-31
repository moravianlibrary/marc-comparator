from fastapi import HTTPException, status

from entities.settings import SettingsScope


class SettingsNotFoundError(HTTPException):
    def __init__(self, scope: SettingsScope):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Settings for scope '{scope}' not found.",
        )


class SettingsPartNotFoundError(HTTPException):
    def __init__(self, scope: SettingsScope, part: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"The settings part '{part}' was not found "
                f"under the '{scope}' scope."
            ),
        )
