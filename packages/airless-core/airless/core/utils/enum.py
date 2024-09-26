
from enum import Enum


class BaseEnum(Enum):

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    @classmethod
    def find_by_id(cls, id):
        matches = [s for s in cls.list() if s['id'] == id]
        return matches[0] if matches else None

    def __eq__(self, other):
        return self.value['id'] == other['id']
