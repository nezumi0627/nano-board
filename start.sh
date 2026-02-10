#!/bin/bash
# Nanobot Dashboard起動スクリプト

cd "$(dirname "$0")"

# ログ設定
mkdir -p logs
LOG_FILE="logs/dashboard_$(date +%Y%m%d_%H%M%S).log"
LATEST_LOG="logs/latest.log"
ln -sf "$(basename "$LOG_FILE")" "$LATEST_LOG"

echo "=== Starting Nanobot Console at $(date) ===" | tee -a "$LOG_FILE"

# ユーザーにsudoパスワード入力を促す (バックグラウンド実行前に認証を済ませる)
sudo -v

# ==========================================
# 1. 既存プロセスのクリーンアップ
# ==========================================
echo "Checking for existing processes..." | tee -a "$LOG_FILE"

# Port 5000 (Dashboard) を使用しているプロセスを終了
if sudo lsof -i :5000 -t >/dev/null 2>&1; then
    echo "Killing process on port 5000..." | tee -a "$LOG_FILE"
    PID=$(sudo lsof -i :5000 -t)
    sudo kill $PID 2>/dev/null
    sleep 2
    # まだ生きていれば強制終了
    if sudo lsof -i :5000 -t >/dev/null 2>&1; then
         sudo kill -9 $PID 2>/dev/null
    fi
fi

# 既存の tailscale funnel を終了
if pgrep -f "tailscale funnel" >/dev/null; then
    echo "Killing existing tailscale funnel..." | tee -a "$LOG_FILE"
    sudo pkill -f "tailscale funnel"
fi

echo "Cleanup complete." | tee -a "$LOG_FILE"

# ==========================================
# 2. サービスの起動
# ==========================================

# Tailscale Funnelの有効化
echo "Starting Tailscale Funnel on port 5000..." | tee -a "$LOG_FILE"
# Funnelをバックグラウンドで実行
sudo tailscale funnel 5000 > /dev/null 2>&1 &
TAILSCALE_PID=$!

# スクリプト終了時にTailscale Funnelも終了させる
cleanup() {
    echo "Stopping Tailscale Funnel..." | tee -a "$LOG_FILE"
    if [ -n "$TAILSCALE_PID" ]; then
        sudo kill $TAILSCALE_PID 2>/dev/null
    fi
    # このスクリプトの子プロセスを全て終了させる
    pkill -P $$
}
trap cleanup EXIT

# アプリケーション起動
echo "Starting Flask Application..." | tee -a "$LOG_FILE"
source venv/bin/activate
# 依存関係の確認とインストール
pip install -r requirements.txt | tee -a "$LOG_FILE"
pip install setuptools | tee -a "$LOG_FILE"

# -u: Unbuffered output for real-time logging
# バックグラウンドで起動して監視できるようにする
python3 -u app.py 2>&1 | tee -a "$LOG_FILE" &
APP_PID=$!

# ==========================================
# 3. 起動時チェック
# ==========================================
echo "Waiting for application to start..." | tee -a "$LOG_FILE"

# 最大30秒待機
MAX_RETRIES=30
for ((i=1; i<=MAX_RETRIES; i++)); do
    if curl -s http://localhost:5000 >/dev/null; then
        echo "" | tee -a "$LOG_FILE"
        echo "✅ Dashboard is up and running!" | tee -a "$LOG_FILE"
        echo "   Local: http://localhost:5000" | tee -a "$LOG_FILE"
        break
    fi
    
    # プロセスが終了していないかチェック
    if ! kill -0 $APP_PID 2>/dev/null; then
        echo "" | tee -a "$LOG_FILE"
        echo "❌ Dashboard failed to start! Check logs." | tee -a "$LOG_FILE"
        exit 1
    fi
    
    echo -n "." | tee -a "$LOG_FILE"
    sleep 1
done

if [ $i -gt $MAX_RETRIES ]; then
    echo "" | tee -a "$LOG_FILE"
    echo "⚠️  Dashboard startup timed out, but process is still running." | tee -a "$LOG_FILE"
fi

# アプリプロセスの終了を待機（これでスクリプトは終了せず走り続ける）
wait $APP_PID