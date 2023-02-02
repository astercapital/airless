
import smtplib

from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from airless.hook.base import BaseHook
from airless.hook.google.secret_manager import SecretManagerHook

from airless.config import get_config


class EmailHook(BaseHook):

    def __init__(self):
        super().__init__()
        secret_manager_hook = SecretManagerHook()
        self.smtp = secret_manager_hook.get_secret(get_config('GCP_PROJECT'), 'smtp', parse_json=True)

    def build_message(self, subject, content, recipients, sender, attachments=[], mime_type='plain'):

        msg = MIMEText(content, mime_type)
        if attachments:
            msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['To'] = ','.join(recipients)
        msg['From'] = sender

        for att in attachments:
            if att.get('type', 'text') == 'text':
                part = MIMEApplication(
                    att['content'],
                    Name=att['name']
                )
            else:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(att['content'])
                encoders.encode_base64(part)
            part['Content-Disposition'] = 'attachment; filename="%s"' % att['name']
            msg.attach(part)
        return msg

    def send(self, subject, content, recipients, sender, attachments, mime_type):

        msg = self.build_message(subject, content, recipients, sender, attachments, mime_type)
        server = smtplib.SMTP_SSL(self.smtp['host'], self.smtp['port'])

        try:
            server.login(self.smtp['user'], self.smtp['password'])
            server.sendmail(sender, recipients, msg.as_string())
        finally:
            server.close()
