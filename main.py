
import functions_framework

from airless.config import get_config

exec(f'{get_config("OPERATOR_IMPORT")} as op')


@functions_framework.cloud_event
def route(cloud_event):
    op().run(cloud_event)  # noqa
