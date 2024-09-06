
from airless.operator.base import BaseEventOperator
from time import sleep


class DelayOperator(BaseEventOperator):

    """
    Operator that adds a delay to the pipeline. The maximum delay is 500 due
    to Cloud Functions time constraint of 540 of execution time

    It can receive 1 parameter:
    seconds: number of seconds to wait

    """

    def __init__(self):
        super().__init__()

    def execute(self, data, topic):
        seconds = data['seconds']
        seconds = min(seconds, 500)
        sleep(seconds)
