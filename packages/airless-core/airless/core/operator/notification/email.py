from airless.operator.base import BaseEventOperator
from airless.hook.notification.email import EmailHook
from airless.hook.google.storage import GcsHook


class EmailSendOperator(BaseEventOperator):

    def __init__(self):
        super().__init__()
        self.email_hook = EmailHook()
        self.gcs_hook = GcsHook()

    def execute(self, data, topic):
        subject = data['subject']
        content = data['content']
        recipients = data['recipients']
        sender = data.get('sender', 'Airless notification')
        attachments = data.get('attachments', [])
        mime_type = data.get('mime_type', 'plain')

        attachment_contents = []
        for att in attachments:
            attachment_contents.append({
                'type': att.get('type', 'text'),
                'content': self.gcs_hook.read(att['bucket'], att['filepath'], att['encoding'])
            })

        self.email_hook.send(subject, content, recipients, sender, attachment_contents, mime_type)
