from airless.core.hook import BaseHook


class SecretManagerHook(BaseHook):
    """Hook for interacting with a secret management system."""

    def __init__(self) -> None:
        """Initializes the SecretManagerHook."""
        super().__init__()

    def list_secrets(self) -> None:
        """Lists all secrets.

        Raises:
            NotImplementedError: This method needs to be implemented in a subclass.
        """
        raise NotImplementedError()

    def list_secret_versions(self, secret_name: str, filter: str) -> None:
        """Lists all versions of a specific secret.

        Args:
            secret_name (str): The name of the secret.
            filter (str): The filter to apply.

        Raises:
            NotImplementedError: This method needs to be implemented in a subclass.
        """
        raise NotImplementedError()

    def destroy_secret_version(self, secret_name: str, version: str) -> None:
        """Destroys a specific version of a secret.

        Args:
            secret_name (str): The name of the secret.
            version (str): The version of the secret to destroy.

        Raises:
            NotImplementedError: This method needs to be implemented in a subclass.
        """
        raise NotImplementedError()

    def get_secret(self, project: str, id: str, parse_json: bool = False) -> None:
        """Retrieves a secret.

        Args:
            project (str): The project name.
            id (str): The ID of the secret.
            parse_json (bool, optional): Whether to parse the secret as JSON. Defaults to False.

        Raises:
            NotImplementedError: This method needs to be implemented in a subclass.
        """
        raise NotImplementedError()

    def add_secret_version(self, project: str, id: str, value: str) -> None:
        """Adds a new version of a secret.

        Args:
            project (str): The project name.
            id (str): The ID of the secret.
            value (str): The value of the secret.

        Raises:
            NotImplementedError: This method needs to be implemented in a subclass.
        """
        raise NotImplementedError()
