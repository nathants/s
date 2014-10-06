import pytest
import s


def test_logic_immutalizes():
    @s.fn.logic
    def fn(x):
        x[1] = 2
    with pytest.raises(ValueError):
        fn({})


def test_stack():
    start = s.fn._stack()
    @s.fn.logic
    def fn1():
        assert s.fn._stack() == ('logic:{}:fn1'.format(__name__),)
        return fn2()
    @s.fn.logic
    def fn2():
        assert s.fn._stack() == ('logic:{}:fn1'.format(__name__),
                                 'logic:{}:fn2'.format(__name__))
        return True
    fn1()
    assert s.fn._stack() == start


def test_flow_in_logic():
    @s.fn.flow
    def flow():
        return True
    @s.fn.logic
    def logic():
        flow()
    with pytest.raises(AssertionError):
        logic()


def test_immutalize():
    val = {'a': 1}
    @s.fn._immutalize
    def fn2(x):
        x['a'] = 3
    with pytest.raises(ValueError):
        fn2(val)


def test_glue_in_logic():
    @s.fn.glue
    def glue():
        return True
    @s.fn.logic
    def logic():
        return glue()
    with pytest.raises(AssertionError):
        logic()


def _plus_one(x, *a):
    return x + 1


def _times_two(x):
    return x * 2


def _three_minus(x):
    return 3 - x


def test_inline():
    assert s.fn.inline(_plus_one, _times_two, _three_minus)(1) == -1
    assert s.fn.inline(_plus_one, _times_two, _three_minus)(1) == _three_minus(_times_two(_plus_one(1)))
    assert s.fn.inline(_three_minus, _times_two, _plus_one)(1) == 5
    assert s.fn.inline(_three_minus, _times_two, _plus_one)(1) == _plus_one(_times_two(_three_minus(1)))


def test_inline_noncallable():
    with pytest.raises(AssertionError):
        s.fn.inline(_three_minus, _times_two, 1)(1)


def test_thrush():
    assert s.fn.thrush(1, _plus_one, _times_two, _three_minus) == -1


def test_thread_noncallable():
    with pytest.raises(AssertionError):
        s.fn.thrush(1, _plus_one, _times_two, 2)


def test_logic_generator():
    @s.fn.logic
    def logic():
        for x in range(3):
            assert s.fn._stack() == ('logic:test_s.fast.fn:logic',)
            yield x
    for i, x in enumerate(logic()):
        assert i == x
        assert s.fn._stack() == ()


def test_logic_raise():
    @s.fn.logic
    def logic():
        1 / 0
    with pytest.raises(ZeroDivisionError):
        logic()


def test_logic_gen_raise():
    @s.fn.logic
    def logic():
        for x in range(3):
            yield x
        1 / 0
    with pytest.raises(ZeroDivisionError):
        for i, x in enumerate(logic()):
            assert i == x
