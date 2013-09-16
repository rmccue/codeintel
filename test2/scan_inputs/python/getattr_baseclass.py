# Test the case where the Python 'compiler' module's AST yields a
# class base that is not just a simple Name() node.

import queue


class MyQueue(queue.Queue):
    pass
