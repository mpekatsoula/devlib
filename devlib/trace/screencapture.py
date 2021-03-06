#    Copyright 2018 ARM Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
import os
import sys
import threading
import time

from devlib.trace import TraceCollector
from devlib.exception import WorkerThreadError


class ScreenCapturePoller(threading.Thread):

    def __init__(self, target, period, output_path=None, timeout=30):
        super(ScreenCapturePoller, self).__init__()
        self.target = target
        self.logger = logging.getLogger('screencapture')
        self.period = period
        self.timeout = timeout
        self.stop_signal = threading.Event()
        self.lock = threading.Lock()
        self.last_poll = 0
        self.daemon = True
        self.exc = None
        self.output_path = output_path

    def run(self):
        self.logger.debug('Starting screen capture polling')
        try:
            while True:
                if self.stop_signal.is_set():
                    break
                with self.lock:
                    current_time = time.time()
                    if (current_time - self.last_poll) >= self.period:
                        self.poll()
                time.sleep(0.5)
        except Exception:  # pylint: disable=W0703
            self.exc = WorkerThreadError(self.name, sys.exc_info())

    def stop(self):
        self.logger.debug('Stopping screen capture polling')
        self.stop_signal.set()
        self.join(self.timeout)
        if self.is_alive():
            self.logger.error('Could not join screen capture poller thread.')
        if self.exc:
            raise self.exc  # pylint: disable=E0702

    def poll(self):
        self.last_poll = time.time()
        self.target.capture_screen(os.path.join(self.output_path, "screencap_{ts}.png"))


class ScreenCaptureCollector(TraceCollector):

    def __init__(self, target, output_path=None, period=None):
        super(ScreenCaptureCollector, self).__init__(target)
        self._collecting = False
        self.output_path = output_path
        self.period = period
        self.target = target
        self._poller = ScreenCapturePoller(self.target, self.period,
                                           self.output_path)

    def reset(self):
        pass

    def start(self):
        """
        Start collecting the screenshots
        """
        self._poller.start()
        self._collecting = True

    def stop(self):
        """
        Stop collecting the screenshots
        """
        if not self._collecting:
            raise RuntimeError('Screen capture collector is not running, nothing to stop')

        self._poller.stop()
        self._collecting = False
