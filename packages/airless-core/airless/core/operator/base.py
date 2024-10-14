
import json
import time
import traceback

from base64 import b64decode

from airless.core import BaseClass
from airless.core.utils import get_config
from airless.core.hook import QueueHook


class BaseOperator(BaseClass):
    """BaseOperator class to handle message operations.

    This class provides the foundational functionality for various 
    operators that can handle different triggers, such as events, 
    files, and HTTP requests. It includes basic error handling 
    and message chaining functionalities.

    Inherits from:
        BaseClass: The base class for the operator implementations.
    """

    def __init__(self):
        """Initializes the BaseOperator class.

        Sets up necessary attributes for the operator including 
        a QueueHook instance for message publishing.
        """
        super().__init__()
        self.queue_hook = QueueHook()  # Have to redefine this attribute for each vendor
        self.trigger_type = None
        self.message_id = None
        self.has_error = False

    def extract_message_id(self, cloud_event):
        """Extracts the message ID from the cloud event.

        Args:
            cloud_event (CloudEvent): The cloud event from which to extract the message ID.

        Returns:
            str: The extracted message ID.
        """
        return cloud_event['id']

    def report_error(self, message: str, data: dict=None):
        """Reports an error by logging it and publishing to a queue.

        Args:
            message (str): The error message to report.
            data (dict, optional): Additional data associated with the error. Defaults to None.
        """
        if get_config('ENV') == 'prod':
            self.logger.error(f'Error {message}')
        else:
            self.logger.error(f'[DEV] Error {message}')

        error_obj = self.build_error_message(message, data)
        self.queue_hook.publish(
            project=None,
            topic=get_config('QUEUE_TOPIC_ERROR'),
            data=error_obj)

        self.has_error = True

    def build_error_message(self, message: str, data: dict):
        """Builds an error message.

        This method needs to be implemented in subclasses.

        Args:
            message (str): The error message.
            data (dict): The associated data.

        Raises:
            NotImplementedError: This method should be implemented by subclasses.
        """

        raise NotImplementedError()

    def chain_messages(self, messages: list) -> tuple:
        """Chains messages together for processing.

        Args:
            messages (list): A list of messages to chain.

        Returns:
            tuple: A tuple containing chained message data and the first topic.
        """

        msg_chain = None
        messages.reverse()

        for m in messages:
            new_msg = m['data'].copy()
            if msg_chain:
                new_msg['metadata'] = {**new_msg.get('metadata', {}), **msg_chain}

            msg_chain = {
                'run_next': [{
                    'topic': m['topic'],
                    'data': new_msg
                }]
            }

        chained_messages = msg_chain['run_next'][0]['data']
        first_topic = msg_chain['run_next'][0]['topic']

        return chained_messages, first_topic


class BaseFileOperator(BaseOperator):
    """BaseFileOperator class to handle file trigger operations.

    This class extends BaseOperator for operations triggered by files.
    """

    def __init__(self):
        """Initializes the BaseFileOperator class.

        Sets the trigger type to 'file' and initializes necessary attributes.
        """
        super().__init__()

        self.trigger_type = 'file'
        self.trigger_origin = None
        self.cloud_event = None

    def execute(self, bucket: str, filepath: str):
        """Executes file processing logic.

        This method needs to be implemented in subclasses.

        Args:
            bucket (str): The name of the bucket where the file is located.
            filepath (str): The path to the file within the bucket.

        Raises:
            NotImplementedError: This method should be implemented by subclasses.
        """
        raise NotImplementedError()

    def run(self, cloud_event):
        """Processes the incoming cloud event and executes file logic.

        Args:
            cloud_event (CloudEvent): The cloud event containing metadata about the file.
        """
        self.logger.debug(cloud_event)
        try:
            self.message_id = self.extract_message_id(cloud_event)
            self.cloud_event = cloud_event
            trigger_file_bucket = cloud_event['bucket']
            trigger_file_path = cloud_event.data['name']
            self.trigger_origin = f'{trigger_file_bucket}/{trigger_file_path}'
            self.execute(trigger_file_bucket, trigger_file_path)

        except Exception as e:
            self.report_error(f'{str(e)}\n{traceback.format_exc()}')

    def build_error_message(self, message: str, data: dict):
        """Builds an error message specific to file operations.

        Args:
            message (str): The error message.
            data (dict): The associated data.

        Returns:
            dict: A constructed error message.
        """
        return {
            'input_type': self.trigger_type,
            'origin': self.trigger_origin,
            'error': message,
            'event_id': self.message_id,
            'data': {
                'attributes': self.cloud_event._attributes,
                'data': data or self.cloud_event.data
            }
        }


class BaseEventOperator(BaseOperator):
    """BaseEventOperator class to handle event trigger operations.

    This class extends BaseOperator for operations triggered by events.
    """

    def __init__(self):
        """Initializes the BaseEventOperator class.

        Sets the trigger type to 'event' and initializes necessary attributes.
        """
        super().__init__()

        self.trigger_type = 'event'
        self.trigger_event_topic = None
        self.trigger_event_data = None

    def execute(self, data: dict, topic: str):
        """Executes event processing logic.

        This method needs to be implemented in subclasses.

        Args:
            data (dict): The data associated with the event.
            topic (str): The event topic.

        Raises:
            NotImplementedError: This method should be implemented by subclasses.
        """
        raise NotImplementedError()

    def run(self, cloud_event):
        """Processes the incoming cloud event and executes event logic.

        Args:
            cloud_event (CloudEvent): The cloud event containing metadata about the event.
        """

        self.logger.debug(cloud_event)
        try:
            self.message_id = self.extract_message_id(cloud_event)
            decoded_data = b64decode(cloud_event.data['message']['data']).decode('utf-8')
            self.trigger_event_data = json.loads(decoded_data)
            self.trigger_event_topic = cloud_event['source'].split('/')[-1]

            self.execute(self.trigger_event_data, self.trigger_event_topic)

            if not self.has_error:
                tasks = self.trigger_event_data.get('metadata', {}).get('run_next', [])
                self.run_next(tasks)

        except Exception as e:
            self.report_error(f'{str(e)}\n{traceback.format_exc()}')

    def run_next(self, tasks: list):
        """Executes the next tasks in the pipeline.

        Args:
            tasks (list): A list of tasks to execute next.
        """

        if tasks:
            time.sleep(10)
        for t in tasks:
            self.queue_hook.publish(
                project=t.get('project'),
                topic=t['topic'],
                data=t['data'])

    def build_error_message(self, message: str, data: dict):
        """Builds an error message specific to event operations.

        Args:
            message (str): The error message.
            data (dict): The associated data.

        Returns:
            dict: A constructed error message.
        """

        return {
            'input_type': self.trigger_type,
            'origin': self.trigger_event_topic,
            'error': message,
            'event_id': self.message_id,
            'data': data or self.trigger_event_data
        }


class BaseHttpOperator(BaseOperator):
    """BaseHttpOperator class to handle HTTP trigger operations.

    This class extends BaseOperator for operations triggered by HTTP requests.
    """

    def __init__(self):
        """Initializes the BaseHttpOperator class.

        Sets the trigger type to 'http' and initializes necessary attributes.
        """
        super().__init__()

        self.trigger_type = 'http'
        self.trigger_base_url = None
        self.trigger_request = None

    def execute(self, request):
        """Executes HTTP request processing logic.

        This method needs to be implemented in subclasses.

        Args:
            request (Request): The HTTP request object.

        Raises:
            NotImplementedError: This method should be implemented by subclasses.
        """
        raise NotImplementedError()

    def run(self, request):
        """Processes the incoming HTTP request and executes processing logic.

        Args:
            request (Request): The HTTP request object.
        """
        self.logger.debug(request)
        try:
            self.trigger_request = {
                'url': request.base_url,
                'method': request.method,
                'form': request.form.to_dict(),
                'args': request.args.to_dict(),
                'data': request.data.decode('utf-8')
            }
            self.trigger_base_url = request.base_url

            return self.execute(request)

        except Exception as e:
            self.report_error(f'{str(e)}\n{traceback.format_exc()}')

    def build_error_message(self, message, request):
        """Builds an error message specific to HTTP operations.

        Args:
            message (str): The error message.
            request (Request): The HTTP request object.

        Returns:
            dict: A constructed error message.
        """
        return {
            'input_type': self.trigger_type,
            'origin': self.trigger_base_url,
            'error': message,
            'event_id': int(time.time() * 1000),
            'data': request or self.trigger_request
        }
