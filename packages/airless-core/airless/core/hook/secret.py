
from airless.core.hook import BaseHook


class SecretManagerHook(BaseHook):

    def __init__(self):
        super().__init__()

    def list_secrets(self):
        raise NotImplementedError()

    def list_secret_versions(self, secret_name, filter):
        raise NotImplementedError()

    def destroy_secret_version(self, secret_name, version):
        raise NotImplementedError()

    def get_secret(self, project, id, parse_json=False):
        raise NotImplementedError()

    def add_secret_version(self, project, id, value):
        raise NotImplementedError()
