from __future__ import absolute_import, print_function
import os
import inspect
import pprint
import sys
import functools
import traceback
import json
import contextlib
import logging
import time
import types
import s


_state = {}


_json_types = (list,
               str,
               dict,
               int,
               float,
               tuple,
               bool,
               type(None))
try:
    _json_types += (unicode,)
except:
    _json_types += (bytes,)


def _trace(val):
    try:
        text = json.dumps(val)
    except:
        text = json.dumps('failed to jsonify: {}'.format(val))
    getattr(logging, 'trace', lambda x: None)(text)


_trace_funcs = {
    'logic': {
        'in': lambda name, fntype, *a, **kw: _trace({
            'name': name,
            'direction': 'in',
            'fntype': fntype,
            'args': a,
            'kwargs': kw,
            'time': time.time(),
            'stack': _stack(),
            'cwd': os.getcwd(),
        }),
        'out': lambda name, fntype, val=None, traceback=None: _trace({
            'name': name,
            'direction': 'out',
            'fntype': fntype,
            'value': val,
            'time': time.time(),
            'stack': _stack(),
            'traceback': traceback,
            'cwd': os.getcwd(),
        })
    }
}


for name in ['glue', 'flow', 'bad']:
    _trace_funcs[name] = _trace_funcs['logic']


@contextlib.contextmanager
def _state_layer(name):
    _backup_stack = _state['_stack'] = _state.get('_stack') or ()
    _state['_stack'] += (name,)
    try:
        yield
    except:
        raise
    finally:
        _val = _state['_stack'][:-1]
        assert _val == _backup_stack, 'stack mutated during function call: {} != {}'.format(_val, _backup_stack)
        _state['_stack'] = _backup_stack


def _get_state(offset=0):
    try:
        return (_state.get('_stack') or ())[-(1 + offset)].split(':')[0]
    except IndexError:
        return ()


def _stack():
    return _state.get('_stack') or ()


def _module_name(fn):
    module = fn.__module__
    with s.exceptions.ignore():
        if module == '__main__':
            for x in range(20):
                _module = '.'.join(__file__.split('.')[0].split('/')[x:])
                if _module in sys.modules:
                    return _module
    return module


def _make_fn_type(kind, rules, skip_return_check=False, immutalize=False):
    def decorator(decoratee):
        if inspect.isgeneratorfunction(decoratee):
            return _gen_type(decoratee, kind, rules, immutalize)
        fn = _fn_type(decoratee, kind, rules, skip_return_check, immutalize)
        return fn
    return decorator


def _fn_type(decoratee, kind, rules, skip_return_check, immutalize):
    if immutalize:
        decoratee = _immutalize(decoratee)
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        # TODO assert all args are _json_types
        name = '{}:{}:{}'.format(kind, _module_name(decoratee), decoratee.__name__)
        _trace_funcs[kind]['in'](name, 'fn', *a, **kw)
        with _state_layer(name):
            try:
                rules()
                val = decoratee(*a, **kw)
                assert not isinstance(val, types.GeneratorType)
            except:
                _trace_funcs[kind]['out'](name, 'fn', traceback=traceback.format_exc())
                raise
            else:
                assert skip_return_check or isinstance(val, _json_types), 'must return data from function: {}'.format(name)
            _trace_funcs[kind]['out'](name, 'fn', val=val)
        return val
    return decorated


def _gen_type(decoratee, kind, rules, immutalize):
    if immutalize:
        decoratee = _immutalize(decoratee)
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        # TODO assert args are _json_types
        name = '{}:{}:{}'.format(kind, _module_name(decoratee), decoratee.__name__)
        _trace_funcs[kind]['in'](name, 'gen', *a, **kw)
        generator = decoratee(*a, **kw)
        assert isinstance(generator, types.GeneratorType)
        to_send = None
        while True:
                with _state_layer(name):
                    try:
                        rules()
                        # TODO assert to_send is _json_types or None
                        to_yield = generator.send(to_send)
                    except StopIteration as e:
                        _trace_funcs[kind]['out'](name, 'gen', val=e)
                        raise
                    except:
                        _trace_funcs[kind]['out'](name, 'gen', traceback=traceback.format_exc())
                        raise
                    else:
                        _trace_funcs[kind]['out'](name, 'gen', val=to_yield)
                # TODO assert to_yield is _json_types
                to_send = yield to_yield
    return decorated


def _rule_violation_message():
    caller = s.hacks.get_caller(4)
    with open(caller['filename']) as _fio:
        line = _fio.read().splitlines()[caller['linenum'] - 1].strip()
    return '\n'.join([
        '',
        '[{}:{}] {}'.format(caller['filename'], caller['linenum'], line),
        'attempted illegal transtion: {} -> {}'.format(*_stack()[-2:]),
        '_stack:\n{}'.format(pprint.pformat(_stack())),
        '',
    ])


def _glue_rules():
    assert _get_state(offset=1) != 'logic', 'logic cannot contain glue\n{}'.format(_rule_violation_message())
glue = _make_fn_type('glue', _glue_rules)


# todo, define better the difference between glue and flow. are two types necessary?
def _flow_rules():
    assert _get_state(offset=1) != 'logic', 'logic cannot contain flow\n{}'.format(_rule_violation_message())
flow = _make_fn_type('flow', _flow_rules)


def _logic_rules():
    assert _get_state(offset=1) != 'glue', 'glue cannot contain logic\n{}'.format(_rule_violation_message())
logic = _make_fn_type('logic', _logic_rules, immutalize=True)


bad = _make_fn_type('bad', lambda: True, skip_return_check=True) # use for tests, and other non-system functions


def inline(*funcs):
    """inline(f, g)(x) == g(f(x))"""
    for fn in funcs:
        assert callable(fn), '{} is not callable'.format(fn)
    def _fn(val):
        for func in funcs:
            val = func(val)
        return val
    return _fn


def thrush(value, *funcs):
    """thread(123, f, g) == g(f(123))"""
    return inline(*funcs)(value)


def _immutalize(decoratee):
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        try:
            a = map(s.data.immutalize, a)
            kw = s.data.immutalize(kw)
        except Exception as e:
            try:
                name = '{}.{}'.format(decoratee.__module__, decoratee.__name__)
            except:
                name = decoratee
            raise Exception('for {}, {}'.format(name, e))
        return decoratee(*a, **kw)
    return decorated
