
from airless.core.hook.base import BaseHook


class QueueHook(BaseHook):

    def __init__(self):
        super().__init__()

    def publish(self, project, topic, data):
        raise NotImplementedError()
