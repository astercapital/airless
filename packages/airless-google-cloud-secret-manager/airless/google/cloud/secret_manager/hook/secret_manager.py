
import json
from typing import Any, List

from airless.core.utils import get_config
from airless.core.hook import SecretManagerHook

from google.cloud import secretmanager


class GoogleSecretManagerHook(SecretManagerHook):
    """Hook for interacting with Google Secret Manager."""

    def __init__(self) -> None:
        """Initializes the GoogleSecretManagerHook."""
        super().__init__()
        self.client = secretmanager.SecretManagerServiceClient()

    def list_secrets(self) -> List[str]:
        """Lists all secrets in the project.

        Returns:
            List[str]: A list of secret names.
        """
        request = {
            'parent': f"projects/{get_config('GCP_PROJECT')}"
        }
        return [secret.name.split('/')[-1] for secret in self.client.list_secrets(request=request)]

    def list_secret_versions(self, secret_name: str, filter: str = 'state:(ENABLED OR DISABLED)') -> List[str]:
        """Lists all versions of a specified secret.

        Args:
            secret_name (str): The name of the secret.
            filter (str, optional): The filter for the versions. Defaults to 'state:(ENABLED OR DISABLED)'.

        Returns:
            List[str]: A list of secret version names.
        """
        request = {
            'parent': self.client.secret_path(get_config('GCP_PROJECT'), secret_name),
            'filter': filter
        }

        return [version.name.split('/')[-1] for version in self.client.list_secret_versions(request=request)]

    def destroy_secret_version(self, secret_name: str, version: str) -> str:
        """Destroys a specific version of a secret.

        Args:
            secret_name (str): The name of the secret.
            version (str): The version of the secret to destroy.

        Returns:
            str: The name of the destroyed version.
        """
        request = {
            'name': f"projects/{get_config('GCP_PROJECT')}/secrets/{secret_name}/versions/{version}"
        }
        response = self.client.destroy_secret_version(request=request)

        return response.name

    def get_secret(self, project: str, id: str, parse_json: bool = False) -> Any:
        """Retrieves the latest version of a secret.

        Args:
            project (str): The project ID.
            id (str): The secret ID.
            parse_json (bool, optional): Whether to parse the secret as JSON. Defaults to False.

        Returns:
            Any: The secret value, parsed if requested.
        """
        name = f'projects/{project}/secrets/{id}/versions/latest'
        response = self.client.access_secret_version(request={'name': name})
        decoded_response = response.payload.data.decode("UTF-8")

        if parse_json:
            return json.loads(decoded_response)
        else:
            return decoded_response

    def add_secret_version(self, project: str, id: str, value: Any) -> Any:
        """Adds a new version to a secret.

        Args:
            project (str): The project ID.
            id (str): The secret ID.
            value (Any): The value to store in the secret.

        Returns:
            Any: The response from the secret manager.
        """
        parent = self.client.secret_path(project, id)
        payload = json.dumps(value) if isinstance(value, dict) else value
        response = self.client.add_secret_version(
            request={'parent': parent, 'payload': {"data": payload.encode('UTF-8')}}
        )
        return response
