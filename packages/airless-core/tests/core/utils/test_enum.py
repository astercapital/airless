
from airless.core.utils import BaseEnum


class TestEnum(BaseEnum):
    A = {
        'id': 'a',
        'name': 'test-a'
    }
    B = {
        'id': 'b',
        'name': 'test-b'
    }


def test_list_size():
    assert len(TestEnum.list()) == 2


def test_list_values():
    assert TestEnum.list() == [TestEnum.A, TestEnum.B]


def test_eq_enum():
    assert TestEnum.A == TestEnum.A
    assert TestEnum.A != TestEnum.B


def test_eq_dict():
    assert TestEnum.A == {'id': 'a', 'name': 'test-a'}
    assert TestEnum.A != {'id': 'b', 'name': 'test-b'}


def test_eq_str():
    assert TestEnum.A == 'a'
    assert TestEnum.B == 'b'
    assert TestEnum.A != 'A'


def test_find_by_id():

    assert TestEnum.find_by_id('a') == TestEnum.A
    assert TestEnum.find_by_id('b') != TestEnum.A
    assert TestEnum.find_by_id('c') is None
