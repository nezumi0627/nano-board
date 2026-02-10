import time
import psutil
import threading
import json
import subprocess
import os

class MonitorService:
    def __init__(self):
        self.lock = threading.Lock()
        self._gateway_process = None
        self._cpu_usage = 0.0
        self._memory_mb = 0.0
        self._memory_percent = 0.0
        self._pid = 0
        self._uptime = 0
        self._disk_percent = 0.0
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def _find_process(self):
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = p.info['cmdline']
                # cmdline is a list of strings
                if cmdline and 'gateway' in cmdline:
                    # Check if 'nanobot' is in any of the arguments (path or argument)
                    if any('nanobot' in arg for arg in cmdline):
                        return p
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return None

    def _monitor_loop(self):
        while self._running:
            try:
                # Update disk stats (system wide)
                self._disk_percent = psutil.disk_usage('/').percent

                # Manage Gateway Process
                if not self._gateway_process or not self._gateway_process.is_running():
                    self._gateway_process = self._find_process()
                
                if self._gateway_process:
                    # First call to cpu_percent with interval=None returns 0.0
                    # Subsequent calls return usage since last call
                    # We rely on the loop's sleep for the interval
                    cpu = self._gateway_process.cpu_percent(interval=None)
                    
                    # Use oneshot for efficiency
                    with self._gateway_process.oneshot():
                        mem_info = self._gateway_process.memory_info()
                        mem_percent = self._gateway_process.memory_percent()
                        create_time = self._gateway_process.create_time()
                        pid = self._gateway_process.pid
                    
                    with self.lock:
                        self._cpu_usage = cpu
                        self._memory_mb = mem_info.rss / (1024 * 1024)
                        self._memory_percent = mem_percent
                        self._pid = pid
                        self._uptime = time.time() - create_time
                else:
                    with self.lock:
                        self._cpu_usage = 0.0
                        self._memory_mb = 0.0
                        self._memory_percent = 0.0
                        self._pid = 0
                        self._uptime = 0
                        
            except Exception as e:
                # print(f"Error in monitor loop: {e}")
                self._gateway_process = None
            
            time.sleep(1)

    def get_system_stats(self):
        with self.lock:
            return {
                "cpu_percent": self._cpu_usage,
                "memory_percent": self._memory_percent,
                "memory_mb": self._memory_mb,
                "disk_percent": self._disk_percent,
                "uptime_seconds": self._uptime,
                "pid": self._pid
            }

    def get_tailscale_status(self):
        try:
            cmd = ["tailscale", "status", "--json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                # Determine status
                self_node = data.get("Self", {})
                return {
                    "online": self_node.get("Online", False),
                    "url": self_node.get("DNSName", "").rstrip('.'),
                    "backend_state": data.get("BackendState", "Unknown"),
                    "peers": len(data.get("Peer", {}))
                }
        except Exception:
            pass
        return {"online": False, "url": None, "backend_state": "Error", "peers": 0}

    def get_cron_jobs(self):
        jobs_path = os.path.expanduser("~/.nanobot/cron/jobs.json")
        jobs = []
        try:
            if os.path.exists(jobs_path):
                with open(jobs_path, 'r') as f:
                    data = json.load(f)
                    # Support both list of jobs or {"jobs": [...]} format
                    if isinstance(data, list):
                        raw_jobs = data
                    else:
                        raw_jobs = data.get("jobs", [])
                    
                    for job in raw_jobs:
                        # Extract schedule info
                        schedule = job.get("schedule", {})
                        expr = schedule.get("expr") or f"{schedule.get('everyMs', 0)//60000}m"
                        
                        # Extract payload message for command/desc
                        payload = job.get("payload", {})
                        message = payload.get("message", "")
                        
                        jobs.append({
                            "id": job.get("id", "job"),
                            "expr": expr,
                            "command": message.replace('\n', ' ')[:50], # Use message as command description
                            "enabled": job.get("enabled", True)
                        })
        except Exception as e:
            print(f"Cron file error: {e}")
            pass
        
        return {
            "count": len(jobs),
            "jobs": jobs
        }

monitor_service = MonitorService()
