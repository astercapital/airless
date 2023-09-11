
import json
import logging
import time
import traceback

from base64 import b64decode

from airless.config import get_config
from airless.hook.google.pubsub import PubsubHook


class BaseOperator():

    def __init__(self):
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')
        logging.basicConfig(level=logging.getLevelName(get_config('LOG_LEVEL')))
        logging.debug(f'Created class instance {self.__class__.__name__}')
        self.pubsub_hook = PubsubHook()
        self.trigger_type = None
        self.message_id = None

    def extract_message_id(self, cloud_event):
        return cloud_event['id']

    def report_error(self, message, data=None):
        if get_config('ENV') == 'prod':
            logging.error(f'Error {message}')
        else:
            logging.debug(f'[DEV] Error {message}')

        error_obj = self.build_error_message(message, data)
        self.pubsub_hook.publish(
            project=get_config('GCP_PROJECT'),
            topic=get_config('PUBSUB_TOPIC_ERROR'),
            data=error_obj)

    def build_error_message(self, message, data):
        raise NotImplementedError()

    def chain_messages(self, messages):
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

    def __init__(self):
        super().__init__()

        self.trigger_type = 'file'
        self.trigger_origin = None
        self.cloud_event = None

    def execute(self, bucket, filepath):
        raise NotImplementedError()

    def run(self, cloud_event):
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

    def build_error_message(self, message, data):
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

    def __init__(self):
        super().__init__()

        self.trigger_type = 'event'
        self.trigger_event_topic = None
        self.trigger_event_data = None

    def execute(self, data, topic):
        raise NotImplementedError()

    def run(self, cloud_event):
        self.logger.debug(cloud_event)
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

    def build_error_message(self, message, data):
        return {
            'input_type': self.trigger_type,
            'origin': self.trigger_event_topic,
            'error': message,
            'event_id': self.message_id,
            'data': data or self.trigger_event_data
        }


class BaseHttpOperator(BaseOperator):

    def __init__(self):
        super().__init__()

        self.trigger_type = 'http'
        self.trigger_base_url = None
        self.trigger_request = None

    def execute(self, request):
        raise NotImplementedError()

    def run(self, request):
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

            self.execute(request)

        except Exception as e:
            self.report_error(f'{str(e)}\n{traceback.format_exc()}')

    def build_error_message(self, message, request):
        return {
            'input_type': self.trigger_type,
            'origin': self.trigger_base_url,
            'error': message,
            'event_id': int(time.time() * 1000),
            'data': request or self.trigger_request
        }
