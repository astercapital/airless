
import smtplib

from airless.core.hook.email import EmailHook
from airless.core.config import get_config

from airless.google.secret_manager import SecretManagerHook


class GoogleEmailHook(EmailHook):

    def __init__(self):
        super().__init__()
        secret_manager_hook = SecretManagerHook()
        self.smtp = secret_manager_hook.get_secret(get_config('SECRET_SMTP'), parse_json=True)

    def send(self, subject, content, recipients, sender, attachments, mime_type):

        msg = self.build_message(subject, content, recipients, sender, attachments, mime_type)
        server = smtplib.SMTP_SSL(self.smtp['host'], self.smtp['port'])

        try:
            server.login(self.smtp['user'], self.smtp['password'])
            server.sendmail(sender, recipients, msg.as_string())
        finally:
            server.close()
