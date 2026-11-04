"""Spawnable invented transports without market/replay/numerical imports.

The parent tests exercise actual deadlines and byte/request caps. Importing the
entire replay test graph in each child can consume those deadlines before the
fixture sends its first byte, obscuring the behaviour the test measures.
"""
import time


def fixture_trickle_worker(url, pipe, limit, timeout):
    pipe.send(('status', 200))
    pipe.send(('chunk', b'{"partial":'))
    time.sleep(5)


def fixture_cap_worker(url, pipe, limit, timeout):
    pipe.send(('status', 200))
    pipe.send(('chunk', b'x' * limit))
    pipe.send(('done', None))


def fixture_complete_worker(url, pipe, limit, timeout):
    pipe.send(('status', 200))
    pipe.send(('chunk', b'{}'))
    pipe.send(('done', None))
