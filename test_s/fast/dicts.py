import s
import pytest


def test_get():
    assert s.dicts.get({'a': {'b': 'c'}}, 'a', 'b') == 'c'


def test_put():
    assert s.dicts.put({}, 'c', 'a', 'b') == {'a': {'b': 'c'}}


def test_merge_freezes():
    assert s.dicts.merge({'a': 'b'}, {'a': ['c', 'd']}) == {'a': ('c', 'd')}


def test_merge():
    assert s.dicts.merge({'a': {'b': 'c'}},
                         {'a': {'d': 'e'}}) == {'a': {'b': 'c',
                                                'd': 'e'}}


def test_merge_dict_with_nondict():
    assert s.dicts.merge({'a': 'b'}, {'a': {'b': 'c'}}) == {'a': {'b': 'c'}}


def test_mutability_merge_a():
    a = {'a': 'b'}
    assert s.dicts.merge(a, {'a': 'c'}) == {'a': 'c'}
    assert a == {'a': 'b'}


def test_mutability_merge_b():
    b = {'a': 'c'}
    assert s.dicts.merge({'a': 'b'}, b) == {'a': 'c'}
    assert b == {'a': 'c'}


def test_simple_merge():
    assert s.dicts.merge({'a': 'b'},
                         {'a': 'c', 'b': 'd'}) == {'a': 'c', 'b': 'd'}


def test_iterables_concatted():
    assert s.dicts.merge({'a': {'b': ('a', 'b')}},
                         {'a': {'b': ('c', 'd')}}, concat=True) == {'a': {'b': ('a', 'b', 'c', 'd')}}


def test__concatable():
    assert s.dicts._concatable([], [])
    assert s.dicts._concatable((), ())
    assert not s.dicts._concatable((), [])
    assert not s.dicts._concatable([], 'a')


def test_only():
    assert s.dicts.take({'a': True, 'b': True, 'c': True}, 'a', 'b') == {'a': True, 'b': True}


def test_padded_only():
    assert s.dicts.take({'a': True}, 'a', 'b', 'c', padded=None) == {'a': True, 'b': None, 'c': None}


def test_drop():
    assert s.dicts.drop({'a': 'a', 'b': 'b'}, 'a') == {'b': 'b'}


def test__ks():
    assert s.dicts._ks(['a', 'b']) == ('a', 'b')
    assert s.dicts._ks(('a', 'b')) == ('a', 'b')
    with pytest.raises(TypeError):
        s.dicts._ks(None)


def test_new():
    x, y = 'a', 'b'
    assert s.dicts.new(locals(), 'x', 'y') == {'x': 'a', 'y': 'b'}


def test_map():
    fn = lambda k, v: ['{}!!'.format(k), v]
    assert s.dicts.map(fn, {'a': {'b': 'c'}}) == {'a!!': {'b!!': 'c'}}
