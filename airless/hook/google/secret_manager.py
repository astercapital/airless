
import json

from google.cloud import secretmanager


class SecretManagerHook():

    def __init__(self):
        self.client = secretmanager.SecretManagerServiceClient()

    def list_secrets(self, project_id):
        request = {
            'parent': f'projects/{project_id}'
        }
        return [secret.name.split('/')[-1] for secret in self.client.list_secrets(request=request)]

    def list_secret_versions(self, project_id, secret_name, filter='state:(ENABLED OR DISABLED)'):
        request = {
            'parent': self.client.secret_path(project_id, secret_name),
            'filter': filter
        }

        return [version.name.split('/')[-1] for version in self.client.list_secret_versions(request=request)]

    def destroy_secret_version(self, project_id, secret_name, version):
        request = {
            'name': f'projects/{project_id}/secrets/{secret_name}/versions/{version}'
        }
        response = self.client.destroy_secret_version(request=request)

        return response.name

    def get_secret(self, project, id, parse_json=False):
        name = f'projects/{project}/secrets/{id}/versions/latest'
        response = self.client.access_secret_version(request={'name': name})
        decoded_response = response.payload.data.decode("UTF-8")

        if parse_json:
            return json.loads(decoded_response)
        else:
            return decoded_response

    def add_secret_version(self, project, id, value):
        parent = self.client.secret_path(project, id)
        payload = json.dumps(value) if isinstance(value, dict) else value
        response = self.client.add_secret_version(
            request={'parent': parent, 'payload': {"data": payload.encode('UTF-8')}}
        )
        return response
