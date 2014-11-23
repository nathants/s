from __future__ import print_function, absolute_import
import s
import time
import s.sock


_async_kw = {'timeout': 1000}
_sync_kw = s.dicts.merge(_async_kw, {'async': False})


def test_push_pull_device_middleware_coroutine():
    upstream_route = s.sock.new_ipc_route()
    downstream_route = s.sock.new_ipc_route()
    @s.async.coroutine
    def pusher():
        yield s.sock.connect('push', upstream_route, **_async_kw).send_string('job1')
    @s.async.coroutine
    def streamer():
        msg = yield s.sock.bind('pull', upstream_route, **_async_kw).recv_string()
        yield s.sock.bind('push', downstream_route, **_async_kw).send_string(msg + ' [streamer]')
    @s.async.coroutine
    def main():
        msg = yield s.sock.connect('pull', downstream_route, **_async_kw).recv_string()
        assert msg == 'job1 [streamer]'
    pusher()
    streamer()
    s.async.run_sync(main)


def test_push_pull_coroutine():
    route = s.sock.new_ipc_route()
    @s.async.coroutine
    def pusher():
        yield s.sock.bind('push', route, **_async_kw).send_string('asdf')
    @s.async.coroutine
    def puller():
        msg = yield s.sock.connect('pull', route, **_async_kw).recv_string()
        assert msg == 'asdf'
    pusher()
    s.async.run_sync(puller)


def test_push_pull_coroutine_multipart_string():
    route = s.sock.new_ipc_route()
    @s.async.coroutine
    def pusher():
        yield s.sock.bind('push', route, **_async_kw).send_multipart_string(('a', 'b'))
    @s.async.coroutine
    def puller():
        msg = yield s.sock.connect('pull', route, **_async_kw).recv_multipart_string()
        assert msg == ('a', 'b')
    pusher()
    s.async.run_sync(puller)


def test_push_pull_coroutine_json():
    route = s.sock.new_ipc_route()
    @s.async.coroutine
    def pusher():
        yield s.sock.bind('push', route, **_async_kw).send_json([1, 2])
    @s.async.coroutine
    def puller():
        msg = yield s.sock.connect('pull', route, **_async_kw).recv_json()
        assert msg == (1, 2)
    pusher()
    s.async.run_sync(puller)


def test_req_rep_coroutine():
    route = s.sock.new_ipc_route()
    @s.async.coroutine
    def requestor():
        req = s.sock.bind('req', route, **_async_kw)
        yield req.send_string('asdf')
        msg = yield req.recv_string()
        assert msg == 'asdf!!'
    @s.async.coroutine
    def replier():
        rep = s.sock.connect('rep', route, **_async_kw)
        msg = yield rep.recv_string()
        yield rep.send_string(msg + '!!')
    requestor()
    s.async.run_sync(replier)


def test_push_pull_tcp():
    route = 'tcp://localhost:{}'.format(s.net.free_port())
    s.thread.new(lambda: s.sock.bind('push', route.replace('localhost', '*'), **_sync_kw).send_string('asdf'))
    assert s.sock.connect('pull', route, **_sync_kw).recv_string() == 'asdf'


def test_push_pull_reverse_connect_bind_order():
    route = s.sock.new_ipc_route()
    s.thread.new(lambda: s.sock.connect('push', route, **_sync_kw).send_string('asdf'))
    assert s.sock.bind('pull', route, **_sync_kw).recv_string() == 'asdf'


def test_push_pull():
    route = s.sock.new_ipc_route()
    s.thread.new(lambda: s.sock.bind('push', route, **_sync_kw).send_string('asdf'))
    assert s.sock.connect('pull', route, **_sync_kw).recv_string() == 'asdf'


def test_req_rep():
    route = s.sock.new_ipc_route()
    def replier():
        rep = s.sock.bind('rep', route, **_sync_kw)
        msg = rep.recv_string()
        rep.send_string('thanks for: ' + msg)
    s.thread.new(replier)
    req = s.sock.connect('req', route, **_sync_kw)
    req.send_string('asdf')
    assert 'thanks for: asdf' == req.recv_string()


def test_pub_sub():
    route = s.sock.new_ipc_route()
    state = {'send': True}
    def pubber():
        pub = s.sock.bind('pub', route, **_sync_kw)
        while state['send']:
            pub.send_string('asdf')
            time.sleep(.001)
    s.thread.new(pubber)
    assert s.sock.connect('sub', route, **_sync_kw).recv_string() == 'asdf'
    state['send'] = False


def test_pub_sub_multipart():
    route = s.sock.new_ipc_route()
    state = {'send': True}
    def pubber():
        pub = s.sock.bind('pub', route, **_sync_kw)
        while state['send']:
            pub.send_multipart_string(['', 'asdf'])
            time.sleep(.001)
    s.thread.new(pubber)
    assert s.sock.connect('sub', route, **_sync_kw).recv_multipart_string() == ['', 'asdf']
    state['send'] = False


def test_pub_sub_subscriptions():
    route = s.sock.new_ipc_route()
    state = {'send': True}
    def pubber():
        pub = s.sock.bind('pub', route, **_sync_kw)
        while state['send']:
            pub.send_string('topic1 asdf')
            pub.send_string('topic2 123')
            time.sleep(.001)
    s.thread.new(pubber)
    sub = s.sock.connect('sub', route, subscriptions=['topic1'], **_sync_kw)
    assert sub.recv_string() == 'topic1 asdf'
    assert sub.recv_string() == 'topic1 asdf'
    state['send'] = False


def test_pub_sub_subscriptions_multipart():
    route = s.sock.new_ipc_route()
    state = {'send': True}
    def pubber():
        pub = s.sock.bind('pub', route, **_sync_kw)
        while state['send']:
            pub.send_multipart_string(['topic1', 'asdf'])
            pub.send_multipart_string(['topic2', '123'])
            time.sleep(.001)
    s.thread.new(pubber)
    sub = s.sock.connect('sub', route, subscriptions=['topic1'], **_sync_kw)
    assert sub.recv_multipart_string() == ['topic1', 'asdf']
    assert sub.recv_multipart_string() == ['topic1', 'asdf']
    state['send'] = False


def test_req_rep_device():
    req_route = s.sock.new_ipc_route()
    rep_route = s.sock.new_ipc_route()
    def replier(x):
        rep = s.sock.connect('rep', rep_route, **_sync_kw)
        msg = rep.recv_string()
        rep.send_string('thanks for: {msg}, from rep{x}'.format(**locals()))
    s.thread.new(replier, 1)
    s.thread.new(replier, 2)
    s.thread.new(s.sock.device, 'QUEUE', req_route, rep_route, **_sync_kw)
    req = s.sock.connect('req', req_route, **_sync_kw)
    responses = set()
    for _ in range(2):
        req.send_string('asdf')
        responses.add(req.recv_string())
    assert responses == {'thanks for: asdf, from rep1',
                         'thanks for: asdf, from rep2'}


def test_req_rep_device_middleware():
    req_route = s.sock.new_ipc_route()
    rep_route = s.sock.new_ipc_route()
    def replier():
        rep = s.sock.connect('rep', rep_route, **_sync_kw)
        msg = rep.recv_string()
        rep.send_string('thanks for: ' + msg)
    def queue():
        router = s.sock.bind('router', req_route, **_async_kw)
        dealer = s.sock.bind('dealer', rep_route, **_async_kw)
        @router.on_recv
        def router_on_recv(msg):
            msg[-1] = msg[-1] + b' [router.on_recv]'
            dealer.send_multipart(msg)
        @dealer.on_recv
        def dealer_on_recv(msg):
            msg[-1] = msg[-1] + b' [dealer.on_recv]'
            router.send_multipart(msg)
        s.sock.ioloop().start()
    s.thread.new(replier)
    s.thread.new(queue)
    req = s.sock.connect('req', req_route, **_sync_kw)
    req.send_string('asdf')
    assert req.recv_string() == 'thanks for: asdf [router.on_recv] [dealer.on_recv]'
    s.sock.ioloop().stop()


def test_pub_sub_device():
    sub_route = s.sock.new_ipc_route()
    pub_route = s.sock.new_ipc_route()
    state = {'send': True}
    def pubber(x):
        pub = s.sock.connect('pub', sub_route, **_sync_kw)
        while state['send']:
            pub.send_multipart_string(['topic{}'.format(x), 'asdf'])
            time.sleep(.01)
    s.thread.new(pubber, 1)
    s.thread.new(pubber, 2)
    s.thread.new(s.sock.device, 'forwarder', sub_route, pub_route, **_sync_kw)
    sub = s.sock.connect('sub', pub_route, **_sync_kw)
    responses = {tuple(sub.recv_multipart_string()) for _ in range(100)}
    assert responses == {('topic1', 'asdf'),
                         ('topic2', 'asdf')}
    state['send'] = False


def test_pub_sub_device_middleware():
    sub_route = s.sock.new_ipc_route()
    pub_route = s.sock.new_ipc_route()
    state = {'send': True}
    def pubber():
        pub = s.sock.connect('pub', sub_route, **_sync_kw)
        while state['send']:
            pub.send_multipart_string(['topic1', 'asdf'])
            time.sleep(.01)
    def forwarder():
        sub = s.sock.bind('sub', sub_route, **_async_kw)
        pub = s.sock.bind('pub', pub_route, **_async_kw)
        @sub.on_recv
        def sub_on_recv(msg):
            msg[-1] = msg[-1] + b' [sub.on_recv]'
            pub.send_multipart(msg)
        s.sock.ioloop().start()
    s.thread.new(pubber)
    s.thread.new(forwarder)
    sub = s.sock.connect('sub', pub_route, **_sync_kw)
    assert sub.recv_multipart_string() == ['topic1', 'asdf [sub.on_recv]']
    state['send'] = False
    s.sock.ioloop().stop()


def test_push_pull_device():
    pull_route = s.sock.new_ipc_route()
    push_route = s.sock.new_ipc_route()
    def pusher(x):
        s.sock.connect('push', pull_route, **_sync_kw).send_string('job{}'.format(x))
    s.thread.new(pusher, 1)
    s.thread.new(pusher, 2)
    s.thread.new(s.sock.device, 'streamer', pull_route, push_route, **_sync_kw)
    pull = s.sock.connect('pull', push_route, **_sync_kw)
    responses = {pull.recv_string() for _ in range(2)}
    assert responses == {'job1', 'job2'}


def test_push_pull_device_middleware():
    pull_route = s.sock.new_ipc_route()
    push_route = s.sock.new_ipc_route()
    def pusher():
        s.sock.connect('push', pull_route, **_sync_kw).send_string('job1')
    def streamer():
        pull = s.sock.bind('pull', pull_route, **_async_kw)
        push = s.sock.bind('push', push_route, **_async_kw)
        @pull.on_recv
        def pull_on_recv(msg):
            push.send(msg[0] + b' [pull.on_recv]')
        s.sock.ioloop().start()
    s.thread.new(pusher)
    s.thread.new(streamer)
    assert s.sock.connect('pull', push_route, **_sync_kw).recv_string() == 'job1 [pull.on_recv]'
    s.sock.ioloop().stop()
