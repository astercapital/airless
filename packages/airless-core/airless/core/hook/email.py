from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from airless.core.hook import BaseHook


class EmailHook(BaseHook):
    """EmailHook class to build and send email messages.

    This class is responsible for constructing email messages that may
    include attachments and other related information. However, the
    sending functionality is not implemented.

    Inherits from:
        BaseHook: The base class for hooks in the airless framework.
    """

    def __init__(self):
        """Initializes the EmailHook class.

        This constructor calls the superclass constructor.
        """
        super().__init__()

    def build_message(
        self,
        subject: str,
        content: str,
        recipients: list,
        sender: str,
        attachments: list = [],
        mime_type: str = 'plain',
    ) -> MIMEMultipart:
        """Builds an email message with optional attachments.

        Args:
            subject (str): The subject of the email.
            content (str): The body content of the email.
            recipients (list): A list of recipient email addresses.
            sender (str): The email address of the sender.
            attachments (list, optional): A list of attachment dictionaries.
                Each dictionary should contain 'name' and 'content'
                Defaults to an empty list.
            mime_type (str, optional): The MIME type of the email body content.
                Defaults to 'plain'.

        Returns:
            MIMEMultipart: The constructed email message object.
        """

        msg = MIMEMultipart()
        msg.attach(MIMEText(content, mime_type))
        msg['Subject'] = subject
        msg['To'] = ','.join(recipients)
        msg['From'] = sender

        for att in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(att['content'])
            encoders.encode_base64(part)
            part['Content-Disposition'] = 'attachment; filename="%s"' % att['name']
            msg.attach(part)
        return msg

    def send(
        self,
        subject: str,
        content: str,
        recipients: list,
        sender: str,
        attachments: list,
        mime_type: str,
    ):
        """Sends the constructed email message.

        This method is not implemented and will raise a NotImplementedError.

        Args:
            subject (str): The subject of the email.
            content (str): The body content of the email.
            recipients (list): A list of recipient email addresses.
            sender (str): The email address of the sender.
            attachments (list): A list of attachment dictionaries.
            mime_type (str): The MIME type of the email body content.

        Raises:
            NotImplementedError: This method has not been implemented.
        """

        raise NotImplementedError()
