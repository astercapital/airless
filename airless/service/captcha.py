
from airless.service.base import BaseService


class CaptchaService(BaseService):

    def __init__(self):
        super().__init__()

    def run(self, version, key, url, action='verify'):
        raise NotImplementedError()
