# load_test_framework.py
import time
import threading
import requests
import http
from collections import defaultdict
import logging
import json

import bs4

# TODO: lancer avec gunicorn plutot que django

class LoadTester:
    def __init__(self, base_url):

        # TODO: could probably take the Take as argument directly
        
        self.base_url = base_url
        self.data = defaultdict(list)
        self.lock = threading.Lock()  # Thread synchronization


    def get_csrf_token_prod(self, session: requests.Session):
        response = session.get(self.base_url)
        # Extract CSRF token from cookies
        # csrf_token = session.cookies.get('csrftoken')
        # logging.debug(f"method 1: {csrf_token=}")

        # logging.info(f"{dir(response)=}")


        # NOTE: dans pca tjrs dans le body, attribute hx-header
        # and this not the same as in the session !!
        # TODO: this should prbably go into a setup_worker function  
        soup = bs4.BeautifulSoup(response.content, "html.parser")
        body = soup.find("body")
        # logging.info(f"{body.attrs=}")
        hx_headers = json.loads(body.get("hx-headers"))

        csrf_token = hx_headers['X-CSRFToken']
        logging.debug(f"{csrf_token=}")

        return csrf_token
        

    def get_csrf_token_local(self, session: requests.Session):
        """Get a CSRF token by making a GET request first"""
        session.get(self.base_url)
        # Extract CSRF token from cookies
        csrf_token = session.cookies.get('csrftoken')
        logging.debug(f"{csrf_token=}")

        return csrf_token
    
    def make_request(self, session: requests.Session, endpoint, method, data=None, headers=None):
        """Execute a single request and return response time and status"""
        url = self.base_url + endpoint

        logging.debug(f"{headers=}")

        
        start_time = time.time()
        try:
            if method == http.HTTPMethod.GET:
                response = session.get(url, headers=headers)
            elif method == http.HTTPMethod.POST:
                response = session.post(url, json=data, headers=headers)
            # elif method == 'PUT':
            #     response = requests.put(url, json=data, headers=headers)
            # elif method == 'DELETE':
            #     response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            elapsed_time = time.time() - start_time


            if not (200 <= response.status_code < 300):
                logging.warning(f"{response=}")
            return {
                'elapsed_time': elapsed_time,
                'status_code': response.status_code,
                'success': 200 <= response.status_code < 300
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            logging.error(e)
            return {
                'elapsed_time': elapsed_time,
                'error': str(e),
                'success': False
            }

    def _worker_task(self, endpoint, method, data, headers, num_requests):
        """Worker function executed by each thread"""


        session = requests.Session()
        if headers is None:
            headers = {}
        # headers['X-CSRFToken'] = self.get_csrf_token_local(session)
        headers['X-CSRFToken'] = self.get_csrf_token_prod(session)


        for _ in range(num_requests):
            result = self.make_request(session, endpoint, method, data, headers)
            
            with self.lock:
                if result.get('success', False):
                    self.data[endpoint].append(result)
                else:
                    self.data[endpoint].append(result)

    def run_load_test(self, endpoint, method, data=None, headers=None, users=10, requests_per_user=10, ramp_up=2):
        """Execute concurrent load test using threading"""
        threads = []

        # logging.info(f"{ramp_up=}")
        logging.info(f"{endpoint=}")
        logging.info(f"{method=}")
        logging.info(f"{users=}")
        logging.info(f"{requests_per_user=}")

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