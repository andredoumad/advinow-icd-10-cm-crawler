"""
point this at a python file to call it in a thread, if the thread exits, it restarts it after some delay.
each time the thread exits it also calls a delayed function to do some work before starting the python file again.
"""

import openpyxl # noqa
import os
import threading
import time
from datetime import datetime
from standalone_tools import eventlog

dir_path = os.path.dirname(os.path.realpath(__file__))

class jobTrigger(threading.Thread):
    def __init__(self, **kwargs):
        print("thread initialized...")
        self.owner = kwargs["owner"]
        self.t_id = kwargs["t_id"]
        self.delay = kwargs["delay"]
        self.run_this_after_thread_ends = kwargs["run_this_after_thread_ends"]
        self.owner.append_thread_id(self.t_id)
        self.activate()

    def activate(self):
        target = os.path.join(dir_path, "crawler.py")
        target = "python {}".format(target)
        print("starting python file: {}".format(target))
        os.system(target)
        print("running after python file thread has exited: {}".format(self.run_this_after_thread_ends))
        self.run_this_after_thread_ends()
        self.owner.remove_thread(self.t_id)


# delayed run_this_after_thread_ends
def delayed_function():
    eventlog("crawler thread has exited, restarting...")


class Solution(object):
    def __init__(self):
        self.threads = []
        self.myLock = threading.Lock()

    def append_thread_id(self, t_id):
        self.log("appending new thread id " + str(t_id) + " to threads ")
        self.threads.append(t_id)
        self.log(str(self.threads))

    def remove_thread(self, t_id):
        self.log("removing thread id " + str(t_id) + " from threads ")
        for i in range(0, len(self.threads)):
            if self.threads[i] == t_id:
                self.threads.pop(i)

    def log(self, msg):
        self.myLock.acquire(True)
        print(str(msg))
        self.myLock.release()

    def run_forever(self, delay, run_this_after_thread_ends):
        # if delay is too short, and machine is too slow
        # it will get stuck in a restart loop.
        if delay < 60:
            delay = 60
        while True:
            thread = threading.Thread(target=jobTrigger, daemon=True, kwargs={
                "t_id": 1,
                "delay": delay,
                "run_this_after_thread_ends": run_this_after_thread_ends,
                "owner": self,
            })
            thread.start()
            time.sleep(3)
            while len(self.threads) > 0:
                time.sleep(delay)
                self.log("Waiting for thread to exit...")


if __name__ == "__main__":
    solution = Solution()
    solution.run_forever(delay=60, run_this_after_thread_ends=delayed_function)
