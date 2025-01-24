import psutil
import time
from datetime import datetime

def get_chrome_memory_usage():
    """
    Get memory usage of all Chrome processes.
    
    Returns:
        dict: Dictionary containing various memory metrics in MB
    """
    chrome_processes = []
    total_memory = 0
    
    # Iterate through all running processes
    for proc in psutil.process_iter(['name', 'memory_info']):
        try:
            # Check if process name contains 'chrome'
            if 'chrome' in proc.info['name'].lower():
                memory = proc.info['memory_info'].rss / (1024 * 1024)  # Convert to MB
                chrome_processes.append({
                    'pid': proc.pid,
                    'memory_mb': round(memory, 2)
                })
                total_memory += memory
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_memory_mb': round(total_memory, 2),
        'process_count': len(chrome_processes),
        'processes': chrome_processes
    }

