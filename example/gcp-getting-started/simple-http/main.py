
import json
import functions_framework

from airless.core.utils import get_config

exec(f'{get_config("OPERATOR_IMPORT")} as op')


@functions_framework.http
def route(request):
    response = op().run(request)  # noqa
    code = response['code']
    content = response['response']
    headers = {'Content-Type': 'application/json; charset=utf-8'}

    return (json.dumps({'content': content}, ensure_ascii=False), int(code), headers)
