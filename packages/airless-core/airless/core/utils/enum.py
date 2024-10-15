from enum import Enum


class BaseEnum(Enum):
    """Base class for enumerations."""

    @classmethod
    def list(cls) -> list:
        """Lists all enumeration values.

        Returns:
            list: A list of enumeration values.
        """
        return list(map(lambda c: c, cls))

    @classmethod
    def find_by_id(cls, id: str) -> 'BaseEnum':
        """Finds an enumeration by its ID.

        Args:
            id (str): The ID to search for.

        Returns:
            BaseEnum: The found enumeration or None if not found.
        """
        return next(filter(lambda x: x == id, cls.list()), None)

    def __eq__(self, other) -> bool:
        """Checks equality with another object.

        Args:
            other (BaseEnum | dict | str): The object to compare with.

        Returns:
            bool: True if equal, False otherwise.
        """
        if isinstance(other, BaseEnum):
            return self.value['id'] == other.value['id']

        elif isinstance(other, dict):
            return self.value['id'] == other['id']

        else:
            return self.value['id'] == other
