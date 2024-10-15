from airless.core.service.base import BaseService


class CaptchaService(BaseService):
    """Service for solving captchas."""

    def __init__(self) -> None:
        """Initializes the CaptchaService."""
        super().__init__()

    def solve(self, version: str, key: str, url: str, action: str = 'verify') -> str:
        """Solves a captcha.

        Args:
            version (str): The version of the captcha (e.g., 'v2' or 'v3').
            key (str): The captcha key.
            url (str): The URL where the captcha is located.
            action (str, optional): The action to perform. Defaults to 'verify'.

        Raises:
            Exception: If the captcha version is not implemented.

        Returns:
            str: The solution to the captcha.
        """
        raise NotImplementedError()
