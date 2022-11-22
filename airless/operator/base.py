
import json
import time
import traceback

from base64 import b64decode

from airless.config import get_config
from airless.hook.google.pubsub import PubsubHook


class BaseOperator():

    def __init__(self):
        print(f'Class instance {self.__class__.__name__}')
        self.pubsub_hook = PubsubHook()
        self.trigger_type = None
        self.message_id = None

    def extract_message_id(self, cloud_event):
        return cloud_event['id']

    def report_error(self, message):
        if get_config('ENV') == 'prod':
            print(f'Error {message}')
        else:
            print(f'[DEV] Error {message}')

        error_obj = self.build_error_message(message)
        self.pubsub_hook.publish(
            project=get_config('GCP_PROJECT'),
            topic=get_config('PUBSUB_TOPIC_ERROR'),
            data=error_obj)

    def build_error_message(self, message):
        raise NotImplementedError()


class BaseFileOperator(BaseOperator):

    def __init__(self):
        super().__init__()

        self.trigger_type = 'file'
        self.trigger_origin = None
        self.cloud_event = None

    def execute(self, message_id, origin):
        raise NotImplementedError()

    def run(self, cloud_event):
        try:
            self.message_id = self.extract_message_id(cloud_event)
            self.cloud_event = cloud_event
            trigger_file_bucket = cloud_event['bucket']
            trigger_file_path = cloud_event['subject']
            self.trigger_origin = f'{trigger_file_bucket}/{trigger_file_path}'
            self.execute(self.trigger_origin)

        except Exception as e:
            self.report_error(f'{str(e)}\n{traceback.format_exc()}')

    def build_error_message(self, message):
        return {
            'input_type': self.trigger_type,
            'origin': self.trigger_origin,
            'error': message,
            'event_id': self.message_id,
            'data': self.cloud_event
        }


class BaseEventOperator(BaseOperator):

    def __init__(self):
        super().__init__()
        self.pubsub_hook = PubsubHook()

        self.trigger_type = 'event'
        self.trigger_event_topic = None
        self.trigger_event_data = None

    def execute(self, data, topic):
        raise NotImplementedError()

    def run(self, cloud_event):
        try:
            self.message_id = self.extract_message_id(cloud_event)
            decoded_data = b64decode(cloud_event.data['message']['data']).decode('utf-8')
            self.trigger_event_data = json.loads(decoded_data)
            self.trigger_event_topic = cloud_event['source'].split('/')[-1]

            self.execute(self.trigger_event_data, self.trigger_event_topic)

            tasks = self.trigger_event_data.get('metadata', {}).get('run_next', [])
            self.run_next(tasks)

        except Exception as e:
            self.report_error(f'{str(e)}\n{traceback.format_exc()}')

    def run_next(self, tasks):
        if tasks:
            time.sleep(10)
        for t in tasks:
            self.pubsub_hook.publish(
                project=t.get('project', get_config('GCP_PROJECT')),
                topic=t['topic'],
                data=t['data'])

    def build_error_message(self, message):
        return {
            'input_type': self.trigger_type,
            'origin': self.trigger_event_topic,
            'error': message,
            'event_id': self.message_id,
            'data': self.trigger_event_data
        }
