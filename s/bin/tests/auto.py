from __future__ import absolute_import, print_function
import blessed
import tornado.websocket
import tornado.ioloop
import tornado.web
import s


_conns = []
_port = 8888
_max_seconds = .01
_state = {}


def _server():
    class Handler(tornado.websocket.WebSocketHandler):
        def check_origin(self, origin):
            return True
        def open(self):
            _conns.append(self)
            _write_to_conns()
        def on_close(self):
            with s.exceptions.ignore():
                _conns.remove(self)
    tornado.web.Application([(r'/ws', Handler)]).listen(_port)
    tornado.ioloop.IOLoop.instance().start()


def _view(test_data):
    failures = [x['result'] for x in test_data if x['result']]
    slows = ['{} ran in {}s, max is {}s'.format(x['path'],
                                                x['seconds'],
                                                _max_seconds)
             for x in test_data
             if x['seconds'] > _max_seconds
             and not x['result']]
    color = s.colors.red if failures or slows else s.colors.green
    name = test_data[0]['path'].split(':')[0]
    val = color(name)
    for fail in failures + slows:
        val += '\n' + s.strings.indent(fail, 2)
    return val


def _write_to_conns(test_datas=None):
    test_datas = test_datas or []
    if any(y['result'] for x in test_datas for y in x):
        message = 'red'
    else:
        message = 'green'
    for c in _conns:
        c.write_message(message)


def _print(terminal, text):
    print(terminal.clear)
    print(terminal.move(0, 0))
    print(text)
    print(terminal.move(0, 0)) # hide_cursor broken in multi-term in emacs


def _app(terminal, pytest):
    last = None
    for test_datas in s.test.run_tests_auto(pytest):
        _write_to_conns(test_datas)
        text = '\n'.join(map(_view, test_datas)) or s.colors.green('tests passed')
        if text != last:
            _print(terminal, text)
            last = text


def auto(pytest=False):
    s.log.setup()
    assert s.net.port_free(_port), 'something already running on port: {}'.format(_port)
    s.thread.new(_server)
    terminal = blessed.Terminal()
    with terminal.fullscreen():
        with terminal.hidden_cursor():
            _app(terminal, pytest)
