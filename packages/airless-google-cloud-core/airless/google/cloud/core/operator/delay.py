
from time import sleep

from airless.core.operator.delay import DelayOperator
from airless.google.cloud.core.base import BaseGoogleEventOperator



class GoogleDelayOperator(BaseGoogleEventOperator, DelayOperator):

    """
    Operator that adds a delay to the pipeline. The maximum delay is 500 due
    to Cloud Functions time constraint of 540 of execution time

    It can receive 1 parameter:
    seconds: number of seconds to wait
    """

    def __init__(self):
        super().__init__()
