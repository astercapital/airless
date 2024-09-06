
import json
import time

from datetime import datetime

from airless.config import get_config
from airless.dto.pubsub_to_bq import PubsubToBqDto
from airless.operator.base import BaseEventOperator


class ErrorReprocessOperator(BaseEventOperator):

    def __init__(self):
        super().__init__()

    def execute(self, data, topic):

        input_type = data['input_type']
        origin = data.get('origin', 'undefined')
        message_id = data.get('event_id')
        original_data = data['data']
        metadata = original_data.get('metadata', {})

        retry_interval = metadata.get('retry_interval', 5)
        retries = metadata.get('retries', 0)
        max_retries = metadata.get('max_retries', 2)

        if (input_type == 'event') and (retries < max_retries):
            time.sleep(min(retry_interval ** retries, 480))  # Cloud function max execution time is 540s (9 min), so set it to wait max 480s (8 min)
            original_data.setdefault('metadata', {})['retries'] = retries + 1
            self.pubsub_hook.publish(
                project=get_config('GCP_PROJECT'),
                topic=origin,
                data=original_data)

        else:
            dto = PubsubToBqDto(
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
            self.pubsub_hook.publish(
                project=get_config('GCP_PROJECT'),
                topic=get_config('PUBSUB_TOPIC_PUBSUB_TO_BQ'),
                data=dto.as_dict())

            email_send_topic = get_config('PUBSUB_TOPIC_EMAIL_SEND', False)
            if email_send_topic and (origin != email_send_topic):
                self.notify_email(origin, message_id, data)

            slack_send_topic = get_config('PUBSUB_TOPIC_SLACK_SEND', False)
            if slack_send_topic and (origin != slack_send_topic):
                self.notify_slack(origin, message_id, data)

    def notify_email(self, origin, message_id, data):
        email_message = {
            'sender': get_config('EMAIL_SENDER_ERROR'),
            'recipients': eval(get_config('EMAIL_RECIPIENTS_ERROR')),
            'subject': f'{origin} | {message_id}',
            'content': f'Input Type: {data["input_type"]} Origin: {origin}\nMessage ID: {message_id}\n\n {json.dumps(data["data"])}\n\n{data["error"]}'
        }
        self.pubsub_hook.publish(
            project=get_config('GCP_PROJECT'),
            topic=get_config('PUBSUB_TOPIC_EMAIL_SEND'),
            data=email_message)

    def notify_slack(self, origin, message_id, data):
        slack_message = {
            'channels': eval(get_config('SLACK_CHANNELS_ERROR')),
            'message': f'{origin} | {message_id}\n\n{json.dumps(data["data"])}\n\n{data["error"]}'
        }
        self.pubsub_hook.publish(
            project=get_config('GCP_PROJECT'),
            topic=get_config('PUBSUB_TOPIC_SLACK_SEND'),
            data=slack_message)

    def prepare_row(self, row, message_id, origin):
        return {
            '_event_id': message_id or 1234,
            '_resource': origin or 'local',
            '_json': json.dumps(row),
            '_created_at': str(datetime.now())
        }

    def prepare_rows(self, data, message_id, origin):
        prepared_rows = data if isinstance(data, list) else [data]
        return [self.prepare_row(row, message_id, origin) for row in prepared_rows]
