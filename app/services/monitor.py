import time
import psutil
import threading
import json
import subprocess
import os

class MonitorService:
    def __init__(self):
        self.lock = threading.Lock()
        self._cpu_usage = 0.0
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def _monitor_loop(self):
        while self._running:
            # WSLでのCPU取得を安定させるためにintervalを設ける
            try:
                # interval=1.0 blocks for 1 second, giving accurate result
                cpu = psutil.cpu_percent(interval=1.0)
                with self.lock:
                    self._cpu_usage = cpu
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                time.sleep(1)

    def get_system_stats(self):
        with self.lock:
            cpu = self._cpu_usage
        
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        try:
            p = psutil.Process(os.getpid())
            uptime = time.time() - p.create_time()
            pid = p.pid
        except:
            uptime = 0
            pid = 0

        return {
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "memory_used": mem.used / (1024 * 1024),
            "memory_total": mem.total / (1024 * 1024),
            "disk_percent": disk.percent,
            "uptime_seconds": uptime,
            "pid": pid
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
