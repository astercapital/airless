
from typing import Any

from airless.core.operator import BaseEventOperator


class RedirectOperator(BaseEventOperator):

    """
    Operator that receives one event from a queue topic and publishes multiple 
    messages to another topic.

    Parameters:
        event: The event received from the queue topic.
        project (str): The project where the destination queue is hosted.
        topic (str): The queue topic to which the newly generated messages will be published.
        messages (list): A list of messages to publish to the topic.
        params (list of dict): A list of dictionaries containing a key and a list of values.

    Returns:
        list: A list of output messages, which will be the product of the initial messages 
              and every list of values in params.
    """

    def __init__(self):
        """Initializes the RedirectOperator."""
        super().__init__()

    def execute(self, data: dict, topic: str):
        """
        Executes the operator, publishing messages to a specified topic.

        Args:
            data (dict): A dictionary containing event data with keys:
                - project (str): The project where the destination queue is hosted.
                - topic (str): The queue topic to which the newly generated messages will be published.
                - messages (list): A list of initial messages to publish.
                - params (list of dict): A list of parameters to modify the messages.
            topic (str): The topic to publish the messages to.

        Returns:
            None
        """

        to_project = data.get('project')
        to_topic = data['topic']
        messages = data.get('messages', [{}])
        params = data.get('params', [])

        messages = self.add_params_to_messages(messages, params)

        for msg in messages:
            self.queue_hook.publish(to_project, to_topic, msg)

    def add_params_to_messages(self, messages: list, params: list):
        """
        Adds parameters to each message in a list of messages.

        Args:
            messages (list): A list of messages to be modified.
            params (list of dict): A list of parameter dictionaries, each containing
                a key and a list of values.

        Returns:
            list: A list of messages with the parameters added.
        """

        for param in params:
            messages = self.add_param_to_messages(messages, param)
        return messages

    def add_param_to_messages(self, messages: list, param: dict):
        """
        Adds a single parameter to each message in a list of messages.

        Args:
            messages (list): A list of messages to modify.
            param (dict): A dictionary containing a 'key' and 'values'.

        Returns:
            list: A list of modified messages with the parameter added.
        """

        messages_with_param = []
        for message in messages:
            messages_with_param += self.add_param_to_message(message, param)
        return messages_with_param

    def add_param_to_message(self, message: dict, param: dict):
        """
        Adds a parameter's values to a single message.

        Args:
            message (dict): The original message to which parameters will be added.
            param (dict): A dictionary containing a 'key' and a list of 'values'.

        Returns:
            list: A list of new messages with the parameter added.
        """

        messages = []
        for value in param['values']:
            tmp_message = message.copy()
            keys = param['key'].split('.')
            tmp_message = self.add_key(tmp_message, keys, value)
            messages.append(tmp_message)
        return messages

    def add_key(self, obj: dict, keys: list, value: Any):
        """Adds a value to a nested dictionary at a specified key path.

        This method takes an object (dictionary), a list of keys representing 
        a path to a location in that dictionary, and a value to insert at 
        that location. If the specified nested keys do not exist in the 
        dictionary, they will be created.

        Args:
            obj (dict): The dictionary to which the keys and value will be added.
            keys (list): A list of keys representing the path in the dictionary.
            value: The value to be set at the specified key path.

        Returns:
            dict: A new dictionary with the value added at the specified key path.

        Example:
            obj = {'a': {'b': 1}}
            keys = ['a', 'c']
            value = 2
            result = add_key(self, obj, keys, value)
            # result will be {'a': {'b': 1, 'c': 2}}
        """

        tmp_obj = obj.copy()
        if len(keys) == 1:
            tmp_obj[keys[0]] = value
        else:
            nested_obj = tmp_obj.setdefault(keys[0], {})
            tmp_obj[keys[0]] = self.add_key(nested_obj, keys[1:], value)
        return tmp_obj
