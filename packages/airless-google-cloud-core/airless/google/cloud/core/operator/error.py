
import json
import time
from typing import Any, Dict, List, Optional

from datetime import datetime

from airless.core.utils import get_config
from airless.core.dto import BaseDto
from airless.google.cloud.core.operator import GoogleBaseEventOperator


class GoogleErrorReprocessOperator(GoogleBaseEventOperator):
    """Operator for reprocessing errors in Google Cloud."""

    def __init__(self) -> None:
        """Initializes the GoogleErrorReprocessOperator."""
        super().__init__()

    def execute(self, data: Dict[str, Any], topic: str) -> None:
        """Executes the error reprocessing logic.

        Args:
            data (Dict[str, Any]): The input data containing error information.
            topic (str): The Pub/Sub topic to publish messages to.
        """
        input_type = data['input_type']
        origin = data.get('origin', 'undefined')
        message_id = data.get('event_id')
        original_data = data['data']
        metadata = original_data.get('metadata', {})

        retry_interval = metadata.get('retry_interval', 5)
        retries = metadata.get('retries', 0)
        max_retries = metadata.get('max_retries', 2)
        max_interval = metadata.get('max_interval', 480)

        if (input_type == 'event') and (retries < max_retries):
            time.sleep(min(retry_interval ** retries, max_interval))
            original_data.setdefault('metadata', {})['retries'] = retries + 1
            self.queue_hook.publish(
                project=get_config('GCP_PROJECT'),
                topic=origin,
                data=original_data)

        else:
            dto = BaseDto(
                event_id=message_id,
                resource=origin,
                to_project=get_config('GCP_PROJECT'),
                to_dataset=get_config('BIGQUERY_DATASET_ERROR'),
                to_table=get_config('BIGQUERY_TABLE_ERROR'),
                to_schema=None,
                to_partition_column='_created_at',
                to_extract_to_cols=False,
                to_keys_format=None,
                data=data)
            self.queue_hook.publish(
                project=get_config('GCP_PROJECT'),
                topic=get_config('QUEUE_TOPIC_PUBSUB_TO_BQ'),
                data=dto.as_dict())

            email_send_topic = get_config('QUEUE_TOPIC_EMAIL_SEND', False)
            if email_send_topic and (origin != email_send_topic):
                self.notify_email(origin, message_id, data)

            slack_send_topic = get_config('QUEUE_TOPIC_SLACK_SEND', False)
            if slack_send_topic and (origin != slack_send_topic):
                self.notify_slack(origin, message_id, data)

    def notify_email(self, origin: str, message_id: str, data: Dict[str, Any]) -> None:
        """Sends a notification email.

        Args:
            origin (str): The origin of the error.
            message_id (str): The ID of the message.
            data (Dict[str, Any]): The data related to the error.
        """
        email_message = {
            'sender': get_config('EMAIL_SENDER_ERROR'),
            'recipients': eval(get_config('EMAIL_RECIPIENTS_ERROR')),
            'subject': f'{origin} | {message_id}',
            'content': f'Input Type: {data["input_type"]} Origin: {origin}\nMessage ID: {message_id}\n\n {json.dumps(data["data"])}\n\n{data["error"]}'
        }
        self.queue_hook.publish(
            project=get_config('GCP_PROJECT'),
            topic=get_config('QUEUE_TOPIC_EMAIL_SEND'),
            data=email_message)

    def notify_slack(self, origin: str, message_id: str, data: Dict[str, Any]) -> None:
        """Sends a notification to Slack.

        Args:
            origin (str): The origin of the error.
            message_id (str): The ID of the message.
            data (Dict[str, Any]): The data related to the error.
        """
        slack_message = {
            'channels': eval(get_config('SLACK_CHANNELS_ERROR')),
            'message': f'{origin} | {message_id}\n\n{json.dumps(data["data"])}\n\n{data["error"]}'
        }
        self.queue_hook.publish(
            project=get_config('GCP_PROJECT'),
            topic=get_config('QUEUE_TOPIC_SLACK_SEND'),
            data=slack_message)

    def prepare_row(self, row: Dict[str, Any], message_id: Optional[str], origin: Optional[str]) -> Dict[str, Any]:
        """Prepares a row for insertion.

        Args:
            row (Dict[str, Any]): The row data.
            message_id (Optional[str]): The message ID.
            origin (Optional[str]): The origin of the message.

        Returns:
            Dict[str, Any]: The prepared row.
        """
        return {
            '_event_id': message_id or 1234,
            '_resource': origin or 'local',
            '_json': json.dumps(row),
            '_created_at': str(datetime.now())
        }

    def prepare_rows(self, data: Any, message_id: Optional[str], origin: Optional[str]) -> List[Dict[str, Any]]:
        """Prepares multiple rows for insertion.

        Args:
            data (Any): The data to prepare.
            message_id (Optional[str]): The message ID.
            origin (Optional[str]): The origin of the message.

        Returns:
            List[Dict[str, Any]]: The list of prepared rows.
        """
        prepared_rows = data if isinstance(data, list) else [data]
        return [self.prepare_row(row, message_id, origin) for row in prepared_rows]
