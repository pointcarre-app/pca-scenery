# load_test_framework.py
import time
import threading

import http
from collections import defaultdict

from scenery import logger
import os


# TODO: lancer avec gunicorn plutot que django


class LoadTester:
    def __init__(self, manifest, mode):

        self.manifest = manifest
        self.mode = mode
        self.data = defaultdict(list)
        self.lock = threading.Lock()  # Thread synchronization


    @property
    def base_url(self):
        return os.environ[f"SCENERY_{self.mode.upper()}_URL"]

    def make_request(self, session, take, headers):
        """Execute a single request and return response time and status"""

        start_time = time.time()

        if take.method == http.HTTPMethod.GET:
            response = session.get(
                self.base_url + take.url,
                data=take.data,
                headers=headers,
            )
        elif take.method == http.HTTPMethod.POST:
            response = session.post(
                self.base_url + take.url,
                take.data,
                headers=headers,
            )
        else:
            raise NotImplementedError(take.method)

                
        elapsed_time = time.time() - start_time

        # print(response.status_code)


        if not (200 <= response.status_code < 300):
        #     ...
            logger.warning(f"{response.status_code=}")
            logger.debug(f"{response.content.decode("utf8")=}")
        return {
            'elapsed_time': elapsed_time,
            'status_code': response.status_code,
            'success': 200 <= response.status_code < 300
        }


    def _worker_task(self, django_testcase, take, num_requests):
        """Worker function executed by each thread"""


        for _ in range(num_requests):
            result = self.make_request(django_testcase.session, take, django_testcase.headers)
            
            with self.lock:
                self.data[take.url].append(result)
