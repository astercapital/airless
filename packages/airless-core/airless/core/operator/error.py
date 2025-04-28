
import json
import time

from typing import Dict, Any

from airless.core.hook import DatalakeHook
from airless.core.operator import BaseEventOperator
from airless.core.utils import get_config


class ErrorReprocessOperator(BaseEventOperator):
    """Operator to handle processing of erroneous events.

    This operator manages the retry logic for events that fail.
    It can reprocess events based on configured retries and intervals,
    and if the maximum retries are exceeded, it saves the error
    details to the datalake
    """
    
    def __init__(self):
        """Initializes the ErrorReprocessOperator.
        
        Inherits from the BaseEventOperator and performs any necessary 
        initialization.  
        """
        super().__init__()
        self.datalake_hook = DatalakeHook()

    def execute(self, data, topic):
        """Executes the error processing logic for the given data.

        Args:
            data (dict): The event data that needs to be processed.
            topic (str): The topic from which the event is received.

        Raises:
            KeyError: If required keys are missing in the data dictionary.

        This method retrieves necessary metadata from the input data, 
        handles retries based on the specified parameters, and publishes 
        either the retried event back to the original topic or saves the
        error details to the datalake if maximum retries have
        been exceeded.
        """
        
        project = data.get('project')

        input_type = data['input_type']
        origin = data.get('origin', 'undefined')
        message_id = data.get('event_id')
        original_data = data['data']
        metadata = original_data.get('metadata', {})

        retry_interval = metadata.get('retry_interval', 5)
        retries = metadata.get('retries', 0)
        max_retries = metadata.get('max_retries', 2)
        max_interval = metadata.get('max_interval', 480)
        error_dataset = metadata.get('dataset')
        error_table = metadata.get('table')

        if (input_type == 'event') and (retries < max_retries) and (origin != topic):
            time.sleep(min(retry_interval ** retries, max_interval))
            original_data.setdefault('metadata', {})['retries'] = retries + 1
            self.queue_hook.publish(
                project=project or get_config('ERROR_OPERATOR_PROJECT', False),  # if not set, defaults to the function project
                topic=origin,
                data=original_data)

        else:
            self.datalake_hook.send_to_landing_zone(
                data=data,
                dataset=error_dataset or get_config('ERROR_DATASET'),
                table=error_table or get_config('ERROR_TABLE'),
                message_id=message_id,
                origin=origin,
                time_partition=True)

            self._notify_email(origin=origin, message_id=message_id, data=data)
            self._notify_slack(origin=origin, message_id=message_id, data=data)

    def _notify_email(self, origin: str, message_id: str, data: Dict[str, Any]) -> None:
        """Sends an error notification to email if the env var `QUEUE_TOPIC_EMAIL_SEND` is defined

        Args:
            origin (str): The origin of the error.
            message_id (str): The ID of the message.
            data (Dict[str, Any]): The data related to the error.
        """
        email_send_topic = get_config('QUEUE_TOPIC_EMAIL_SEND', False)
        if email_send_topic and (origin != email_send_topic):
            email_message = {
                'sender': get_config('EMAIL_SENDER_ERROR'),
                'recipients': eval(get_config('EMAIL_RECIPIENTS_ERROR')),
                'subject': f'{origin} | {message_id}',
                'content': f'Input Type: {data["input_type"]} Origin: {origin}\nMessage ID: {message_id}\n\n {json.dumps(data["data"])}\n\n{data["error"]}'
            }
            self.queue_hook.publish(
                project=get_config('EMAIL_OPERATOR_PROJECT', False),  # if not set, defaults to the function project
                topic=email_send_topic,
                data=email_message)

    def _notify_slack(self, origin: str, message_id: str, data: Dict[str, Any]) -> None:
        """Sends an error notification to Slack if the env var `QUEUE_TOPIC_SLACK_SEND` is defined

        Args:
            origin (str): The origin of the error.
            message_id (str): The ID of the message.
            data (Dict[str, Any]): The data related to the error.
        """
        slack_send_topic = get_config('QUEUE_TOPIC_SLACK_SEND', False)
        if slack_send_topic and (origin != slack_send_topic):
            slack_message = {
                'channels': eval(get_config('SLACK_CHANNELS_ERROR')),
                'message': f'{origin} | {message_id}\n\n{json.dumps(data["data"])}\n\n{data["error"]}'
            }
            self.queue_hook.publish(
                project=get_config('SLACK_OPERATOR_PROJECT', False),  # if not set, defaults to the function project
                topic=slack_send_topic,
                data=slack_message)
