
from airless.operator.base import BaseEventOperator

from airless.config import get_config


class RedirectOperator(BaseEventOperator):

    """
    Operator that receives one event from a pubsub topic
    and publish multiple messages to another topic.

    It can receive 4 parameters:
    project: the project where the destination pubsub is hosted
    topic: the pubsub topic it must publish the newly generated messages
    messages: a list of messages to publish the topic
    params: a list of dicts containing a key and a list of values

    The output messages will be the product of messages and every param values list
    """

    def __init__(self):
        super().__init__()

    def execute(self, data, topic):
        to_project = data.get('project', get_config('GCP_PROJECT'))
        to_topic = data['topic']
        messages = data.get('messages', [{}])
        params = data.get('params', [])

        messages = self.add_params_to_messages(messages, params)

        for msg in messages:
            self.pubsub_hook.publish(to_project, to_topic, msg)

    def add_params_to_messages(self, messages, params):
        for param in params:
            messages = self.add_param_to_messages(messages, param)
        return messages

    def add_param_to_messages(self, messages, param):
        messages_with_param = []
        for message in messages:
            messages_with_param += self.add_param_to_message(message, param)
        return messages_with_param

    def add_param_to_message(self, message, param):
        messages = []
        for value in param['values']:
            tmp_message = message.copy()
            keys = param['key'].split('.')
            tmp_message = self.add_key(tmp_message, keys, value)
            messages.append(tmp_message)
        return messages

    def add_key(self, obj, keys, value):
        tmp_obj = obj.copy()
        if len(keys) == 1:
            tmp_obj[keys[0]] = value
        else:
            nested_obj = tmp_obj.setdefault(keys[0], {})
            tmp_obj[keys[0]] = self.add_key(nested_obj, keys[1:], value)
        return tmp_obj
