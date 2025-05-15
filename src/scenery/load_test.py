# load_test_framework.py
import time
import threading
import requests
import http
from collections import defaultdict
import statistics

from scenery.common import colorize, show_histogram, rich_tabulate


class LoadTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.results = defaultdict(list)
        self.errors = defaultdict(list)
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
                    self.results[endpoint].append(result)
                else:
                    self.errors[endpoint].append(result)

    def run_load_test(self, endpoint, method='GET', data=None, headers=None, users=10, requests_per_user=10, ramp_up=2):
        """Execute concurrent load test using threading"""
        threads = []
        
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
            
        # return self.analyze_results(endpoint)


    def analyze_results(self):
        """Analyze test results and return statistics"""

        endpoints = list(self.results.keys())

        for ep in endpoints:
            print(colorize("cyan", ep if ep else "Base url"))
        
            success_times = [r['elapsed_time'] for r in self.results[ep]]
            error_times = [r['elapsed_time'] for r in self.errors[ep]]
            
            total_requests = len(success_times) + len(error_times)
            if total_requests == 0:
                continue
                
            error_rate = (len(error_times) / total_requests) * 100 if total_requests > 0 else 0
            
            ep_analysis = {
                'total_requests': total_requests,
                'successful_requests': len(success_times),
                'failed_requests': len(error_times),
                'error_rate': error_rate
            }
            
            if success_times:
                ep_analysis.update({
                    'avg_time': statistics.mean(success_times),
                    'min_time': min(success_times),
                    'max_time': max(success_times),
                    'median_time': statistics.median(success_times)
                })
                
                if len(success_times) > 1:
                    ep_analysis['stdev_time'] = statistics.stdev(success_times)
            

                    # Define the metrics we want to display and their format
            formatting = {
                "total_requests": ("{}", None),
                "successful_requests": ("{}", None),
                "failed_requests": ("{}", None),
                "error_rate": ("{:.2f}%", None),
                "avg_time": ("{:.4f}s", None),
                "median_time": ("{:.4f}s", None),
                "min_time": ("{:.4f}s", None),
                "max_time": ("{:.4f}s", None),
                "stdev_time": ("{:.4f}s", None),
            }
            rich_tabulate(
                ep_analysis, 
                "Metric", 
                "Value", 
                f"Load test on '{ep if ep else "Base URL"}'",
                formatting,
                )
            show_histogram(success_times)






if __name__ == "__main__":

    url = "http://localhost:8000"
    endpoint = ""
    users = 50
    requests_per_user = 20


    tester = LoadTester(url)
    
    # Run a load test against a specific endpoint
    tester.run_load_test(
        endpoint=endpoint, 
        users=users,             
        requests_per_user=requests_per_user  
    )

    # Analyze and print the results
    tester.analyze_results()