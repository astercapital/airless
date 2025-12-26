import unittest

from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase

from airless.core.hook import EmailHook


class TestEmailHook(unittest.TestCase):
    def setUp(self):
        """Set up an instance of EmailHook for testing."""
        self.email_hook = EmailHook()

    def test_build_message_plain_text(self):
        """Test building a plain text email message."""
        subject = 'Test Subject'
        content = 'This is a test email.'
        recipients = ['recipient@example.com']
        sender = 'sender@example.com'

        message = self.email_hook.build_message(subject, content, recipients, sender)

        self.assertIsInstance(message, MIMEMultipart)
        self.assertEqual(message['Subject'], subject)
        self.assertEqual(message['To'], ','.join(recipients))
        self.assertEqual(message['From'], sender)

    def test_build_message_with_attachments(self):
        """Test building an email message with attachments."""
        subject = 'Test Subject with Attachment'
        content = 'This email has an attachment.'
        recipients = ['recipient@example.com']
        sender = 'sender@example.com'
        attachments = [
            {
                'name': 'test.txt',
                'content': b'This is a test file.',
            },
            {
                'name': 'image.png',
                'content': b'This is a fake image.',
            },
        ]

        message = self.email_hook.build_message(
            subject, content, recipients, sender, attachments
        )

        self.assertIsInstance(message, MIMEMultipart)
        self.assertEqual(message['Subject'], subject)
        self.assertEqual(message['To'], ','.join(recipients))
        self.assertEqual(message['From'], sender)

        # Check the attachments
        self.assertEqual(
            len(message.get_payload()), 3
        )  # Ensure two attachments are added

        # Check the first attachment
        part1 = message.get_payload()[1]  # The first payload will be the text part
        self.assertIsInstance(part1, MIMEBase)
        self.assertEqual(part1.get_filename(), 'test.txt')

        # Check the second attachment
        part2 = message.get_payload()[2]
        self.assertIsInstance(part2, MIMEBase)
        self.assertEqual(part2.get_filename(), 'image.png')

    def test_send_method_not_implemented(self):
        """Test that the send method raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.email_hook.send(
                'subject',
                'content',
                ['to@example.com'],
                'from@example.com',
                [],
                'plain',
            )


if __name__ == '__main__':
    unittest.main()
