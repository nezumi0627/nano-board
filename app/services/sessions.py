import glob
import json
import os
import time
from cachetools import TTLCache

from datetime import datetime

class SessionService:
    def __init__(self, session_dir):
        self.session_dir = session_dir
        self.cache = TTLCache(maxsize=1, ttl=2)

    def get_sessions(self):
        if 'data' in self.cache:
            return self.cache['data']

        count = 0
        total_messages = 0
        thinking_sessions = 0
        status = "idle"
        latest_activity = 0
        details = []

        try:
            if not os.path.exists(self.session_dir):
                return {"count": 0, "messages": 0, "status": "idle", "details": []}

            files = glob.glob(os.path.join(self.session_dir, "*.jsonl"))
            files.sort(key=os.path.getmtime, reverse=True)
            
            count = len(files)
            
            # Limit to recent 10 for detailed view
            recent_files = files[:10]
            
            now = time.time()
            
            for f in recent_files:
                try:
                    msg_count = 0
                    last_ts = 0
                    is_thinking = False
                    
                    # Read file to get stats
                    with open(f, 'r', encoding='utf-8') as fp:
                        for line in fp:
                            if not line.strip(): continue
                            msg_count += 1
                            try:
                                record = json.loads(line)
                                # Check timestamp
                                ts = record.get("timestamp", 0)
                                if isinstance(ts, str):
                                    try:
                                        # Try parsing ISO format (assuming UTC if no tz)
                                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                        current_ts = dt.timestamp()
                                        if current_ts > last_ts:
                                            last_ts = current_ts
                                    except:
                                        pass
                                elif isinstance(ts, (int, float)):
                                    if ts > last_ts:
                                        last_ts = ts
                                
                                # Check status if available
                                if record.get("status") == "thinking":
                                    is_thinking = True
                                else:
                                    is_thinking = False
                            except:
                                pass
                    
                    total_messages += msg_count
                    if last_ts > latest_activity:
                        latest_activity = last_ts
                    
                    if is_thinking and (now - last_ts < 300): # Thinking within last 5 mins
                        thinking_sessions += 1

                    details.append({
                        "id": os.path.basename(f).replace('.jsonl', ''),
                        "latest": last_ts * 1000 if last_ts < 1e11 else last_ts, # Ensure ms
                        "messages": msg_count
                    })
                except Exception as e:
                    # print(f"Error reading {f}: {e}")
                    pass
            
            # Determine overall status
            if thinking_sessions > 0:
                status = "thinking"
            elif latest_activity > 0 and (now - latest_activity < 60):
                status = "active"
            else:
                status = "idle"

        except Exception as e:
            print(f"Session read error: {e}")

        data = {
            "count": count,
            "messages": total_messages,
            "status": status,
            "thinking_sessions": thinking_sessions,
            "latest": latest_activity * 1000 if latest_activity < 1e11 else latest_activity,
            "details": details
        }
        self.cache['data'] = data
        return data

session_service = SessionService(os.path.expanduser("~/.nanobot/sessions"))
