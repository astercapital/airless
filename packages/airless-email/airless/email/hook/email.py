
import smtplib
from typing import List

from airless.core.hook import EmailHook
from airless.core.utils import get_config

from airless.google.cloud.secret_manager.hook import GoogleSecretManagerHook


class GoogleEmailHook(EmailHook):
    """Hook for sending emails using Google Email service."""

    def __init__(self) -> None:
        """Initializes the GoogleEmailHook."""
        super().__init__()
        secret_manager_hook = GoogleSecretManagerHook()
        self.smtp = secret_manager_hook.get_secret(get_config('GCP_PROJECT'), get_config('SECRET_SMTP'), parse_json=True)

    def send(self, subject: str, content: str, recipients: List[str], sender: str, attachments: List[dict], mime_type: str) -> None:
        """Sends an email.

        Args:
            subject (str): The subject of the email.
            content (str): The content of the email.
            recipients (List[str]): The list of email recipients.
            sender (str): The sender's email address.
            attachments (List[dict]): The list of attachments.
            mime_type (str): The MIME type of the email content.
        """
        msg = self.build_message(subject, content, recipients, sender, attachments, mime_type)
        server = smtplib.SMTP_SSL(self.smtp['host'], self.smtp['port'])

        try:
            server.login(self.smtp['user'], self.smtp['password'])
            server.sendmail(sender, recipients, msg.as_string())
        finally:
            server.close()
