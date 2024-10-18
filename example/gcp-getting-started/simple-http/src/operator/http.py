
from typing import Any, Dict
import logging

from airless.core.operator import BaseHttpOperator

from src.hook.http import PasteBinHook


class PasteBinOperator(BaseHttpOperator):

    def __init__(self):
        super().__init__()
        self.paste_bin_hook = PasteBinHook()

    def execute(self, request):
        data = request['data']

        # In production this method can be called to provide a richer response parse with metadatas
        # url = self.trigger_request['url']
        # data = json.loads(self.trigger_request['data'])

        request_type = data['request_type']

        if request_type == 'get-content':
            res = self.get_content(data)
        else:
            raise Exception(f'Request type {request_type} not implemented')

        logging.debug(res)
        return res

    def get_content(self, data) -> Dict[str, Any]:
        id_ = data['id']
        res = self.paste_bin_hook.get_content(id_)

        return res
