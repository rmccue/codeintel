# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import sys
import time
import _thread


def counting(name, duration=10):
    for i in range(duration):
        print("%s i=%d" % (name, i))
        time.sleep(1)


if __name__ == "__main__":
    _thread.start_new_thread(counting, ('thread',))

    counting('main', 20)

    print("done")
