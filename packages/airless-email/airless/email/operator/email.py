from typing import List

from airless.core.utils import get_config
from airless.google.cloud.core.operator import GoogleBaseEventOperator

from airless.google.cloud.storage.hook import GcsHook
from airless.email.hook import GoogleEmailHook


class GoogleEmailSendOperator(GoogleBaseEventOperator):
    """Operator for sending emails using Google Email Hook."""

    def __init__(self) -> None:
        """Initializes the GoogleEmailSendOperator."""
        super().__init__()
        self.email_hook = GoogleEmailHook()
        self.gcs_hook = GcsHook()

    def execute(self, data: dict, topic: str) -> None:
        """Executes the email sending process.

        Args:
            data (dict): The data containing email information.
            topic (str): The Pub/Sub topic.
        """
        subject: str = data['subject']
        content: str = data['content']
        recipients: List[str] | str = data['recipients']
        sender: str = data.get('sender', 'Airless notification')
        attachments: List[dict] = data.get('attachments', [])
        mime_type: str = data.get('mime_type', 'plain')

        attachment_contents: List[dict] = []
        for att in attachments:
            attachment_contents.append(
                {
                    'type': att.get('type', 'text'),
                    'content': self.gcs_hook.read_as_string(
                        att['bucket'], att['filepath'], att['encoding']
                    ),
                }
            )

        recipients_array = self.recipients_string_to_array(recipients)

        self.email_hook.send(
            subject, content, recipients_array, sender, attachment_contents, mime_type
        )

    def recipients_string_to_array(self, recipients) -> List[str]:
        default_domain = get_config('DEFAULT_RECIPIENT_EMAIL_DOMAIN')

        recipients_array = (
            recipients if isinstance(recipients, list) else recipients.split(',')
        )

        return [
            (r.strip() if '@' in r else r.strip() + '@' + default_domain).lower()
            for r in recipients_array
        ]
