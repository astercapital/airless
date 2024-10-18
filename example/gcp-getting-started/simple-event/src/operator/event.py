
from airless.google.cloud.storage.hook import GcsDatalakeHook
from airless.google.cloud.core.operator import GoogleBaseEventOperator
from airless.core.utils import get_config

from src.hook.event import PasteBinHook


class PasteBinOperator(GoogleBaseEventOperator):

    def __init__(self):
        super().__init__()
        self.datalake_hook = GcsDatalakeHook()
        self.paste_bin_hook = PasteBinHook()

    def execute(self, data, topic):
        request_type = data['request_type']

        if request_type == 'list-ids':
            self.list_ids(data, topic)
        elif request_type == 'get-content':
            self.get_content(data, topic)
        else:
            raise Exception(f'Request type {request_type} not implemented')

    def list_ids(self, data, topic):
        ids = self.paste_bin_hook.list_ids()

        for id_ in ids:
            self.queue_hook.publish(
                project=get_config('GCP_PROJECT'),
                topic=topic,
                data={'request_type': 'get-content', 'id': id_}
            )

    def get_content(self, data, topic):
        id_ = data['id']
        res = self.paste_bin_hook.get_content(id_)

        self.datalake_hook.send_to_landing_zone(
            data=res['response'],
            dataset='paste_bin_raw',
            table='content',
            message_id=self.message_id,
            origin=topic,
            time_partition=True)  # Time partition is an attribute to allow HDFS like partitioning
