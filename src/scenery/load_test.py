# load_test_framework.py
import time
import threading
import requests
import http
from collections import defaultdict
import logging



class LoadTester:
    def __init__(self, base_url):
        self.base_url = base_url
        # self.request_results = defaultdict(list)
        # self.request_errors = defaultdict(list)
        self.data = defaultdict(list)
        self.lock = threading.Lock()  # Thread synchronization

    def make_request(self, endpoint, method='GET', data=None, headers=None):
        """Execute a single request and return response time and status"""
        url = self.base_url + endpoint
        start_time = time.time()
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            # elif method == 'PUT':
            #     response = requests.put(url, json=data, headers=headers)
            # elif method == 'DELETE':
            #     response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            elapsed_time = time.time() - start_time
            return {
                'elapsed_time': elapsed_time,
                'status_code': response.status_code,
                'success': 200 <= response.status_code < 300
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            return {
                'elapsed_time': elapsed_time,
                'error': str(e),
                'success': False
            }

    def _worker_task(self, endpoint, method, data, headers, num_requests):
        """Worker function executed by each thread"""
        for _ in range(num_requests):
            result = self.make_request(endpoint, method, data, headers)
            
            with self.lock:
                if result.get('success', False):
                    self.data[endpoint].append(result)
                else:
                    self.data[endpoint].append(result)

    def run_load_test(self, endpoint, method='GET', data=None, headers=None, users=10, requests_per_user=10, ramp_up=2):
        """Execute concurrent load test using threading"""
        threads = []

        logging.info(f"Load test with {users=}")
        
        # Create threads for each simulated user
        for i in range(users):
            thread = threading.Thread(
                target=self._worker_task,
                args=(endpoint, method, data, headers, requests_per_user)
            )
            threads.append(thread)
            
            # Optional: implement ramp-up by staggering thread starts
            thread.start()
            # if ramp_up > 0 and users > 1:
            #     time.sleep(ramp_up / (users - 1))
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # return self.request_results, self.request_errors