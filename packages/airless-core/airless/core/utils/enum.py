
from enum import Enum


class BaseEnum(Enum):

    @classmethod
    def list(cls):
        return list(map(lambda c: c, cls))

    @classmethod
    def find_by_id(cls, id):
        return next(filter(lambda x: x == id, cls.list()), None)

    def __eq__(self, other):
        if isinstance(other, BaseEnum):
            return self.value['id'] == other.value['id']

        elif isinstance(other, dict):
            return self.value['id'] == other['id']

        else:
            return self.value['id'] == other
