
import smtplib

from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from airless.core.hook import BaseHook


class EmailHook(BaseHook):

    def __init__(self):
        super().__init__()

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
        raise NotImplementedError()
