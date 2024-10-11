import time

from airless.core.dto.base import BaseDto
from airless.core.operator import BaseEventOperator


class ErrorReprocessOperator(BaseEventOperator):
    """Operator to handle processing of erroneous events.

    This operator manages the retry logic for events that fail.
    It can reprocess events based on configured retries and intervals, 
    and if the maximum retries are exceeded, it forwards the error 
    details to a specified destination.
    """
    
    def __init__(self):
        """Initializes the ErrorReprocessOperator.
        
        Inherits from the BaseEventOperator and performs any necessary 
        initialization.  
        """
        super().__init__()

    def execute(self, data, topic):
        """Executes the error processing logic for the given data.

        Args:
            data (dict): The event data that needs to be processed.
            topic (str): The topic from which the event is received.

        Raises:
            KeyError: If required keys are missing in the data dictionary.

        This method retrieves necessary metadata from the input data, 
        handles retries based on the specified parameters, and publishes 
        either the retried event back to the original topic or the 
        error details to the destination topic if maximum retries have 
        been exceeded.
        """
        
        project = data.get('project', 'undefined')

        input_type = data['input_type']
        origin = data.get('origin', 'undefined')
        message_id = data.get('event_id')
        original_data = data['data']
        metadata = original_data.get('metadata', {})

        retry_interval = metadata.get('retry_interval', 5)
        retries = metadata.get('retries', 0)
        max_retries = metadata.get('max_retries', 2)
        max_interval = metadata.get('max_interval', 480)

        destination_topic = metadata['destination']
        dataset = metadata['dataset']
        table = metadata['table']

        if (input_type == 'event') and (retries < max_retries):
            time.sleep(min(retry_interval ** retries, max_interval))
            original_data.setdefault('metadata', {})['retries'] = retries + 1
            self.queue_hook.publish(
                project=project,
                topic=origin,
                data=original_data)

        else:
            dto = BaseDto(
                event_id=message_id,
                resource=origin,
                to_project=project,
                to_dataset=dataset,
                to_table=table,
                to_schema=None,
                to_partition_column='_created_at',
                to_extract_to_cols=False,
                to_keys_format=None,
                data=data)
            self.queue_hook.publish(
                project=project,
                topic=destination_topic,
                data=dto.as_dict())
