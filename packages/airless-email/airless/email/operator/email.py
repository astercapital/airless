from typing import List, Union

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
        recipients: Union[List[str], str] = data['recipients']
        sender: str = data.get('sender', 'Airless notification')
        attachments: List[dict] = data.get('attachments', [])
        mime_type: str = data.get('mime_type', 'plain')

        attachment_contents: List[dict] = []
        for att in attachments:
            attachment_content = self.gcs_hook.read_as_bytes(
                att['bucket'], att['filepath']
            )

            attachment_contents.append(
                {
                    'content': attachment_content,
                    'name': att['filepath'].split('/')[-1],
                }
            )

        recipients_array = self.recipients_string_to_array(recipients)

        self.email_hook.send(
            subject, content, recipients_array, sender, attachment_contents, mime_type
        )

    def recipients_string_to_array(
        self, recipients: Union[List[str], str]
    ) -> List[str]:
        """Transforms input into an array of emails

        @param recipients: Either a comma separated string with emails and/or usernames or a list of emails and/or usernames
        @type  recipients: List[str] or str

        @return: List of emails
        @rtype : List[str]
        """
        default_domain = get_config('DEFAULT_RECIPIENT_EMAIL_DOMAIN')

        recipients_array = (
            recipients if isinstance(recipients, list) else recipients.split(',')
        )

        return [
            (email if '@' in r else f'{email}@{default_domain}').lower()
            for r in recipients_array
            if (email := r.strip())
        ]
