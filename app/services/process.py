import subprocess
import os

class ProcessService:
    def __init__(self):
        self.session_name = "nanobot-gateway"
        # ユーザーは nanobot gateway の制御を求めている
        # start-nanobot.sh のロジックを参照
        # ただし、ここではダッシュボードとは別のtmuxセッション(nanobot)を操作する前提

    def _run_cmd(self, cmd):
        try:
            subprocess.run(cmd, shell=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def is_running(self):
        # check tmux session
        cmd = f"tmux has-session -t {self.session_name} 2>/dev/null"
        return self._run_cmd(cmd)

    def start(self):
        if self.is_running():
            return False, "Already running"
        
        # start-nanobot.shのロジックを模倣または呼び出し
        # ここでは直接tmuxコマンドを発行する
        # ※ 実際の起動コマンドはユーザー環境に依存するが、
        # start-nanobot.sh があると仮定してそれを呼び出すのが安全
        script_path = os.path.expanduser("~/nano-board/start-nanobot.sh")
        if os.path.exists(script_path):
             # バックグラウンドで実行
            return self._run_cmd(f"bash {script_path}"), "Started via script"
        else:
            return False, "Startup script not found"

    def stop(self):
        if not self.is_running():
            return False, "Not running"
        return self._run_cmd(f"tmux kill-session -t {self.session_name}"), "Stopped"

    def restart(self):
        self.stop()
        import time
        time.sleep(1)
        return self.start()

process_service = ProcessService()
