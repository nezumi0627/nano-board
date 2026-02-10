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

# Tailscale Funnelの有効化
echo "Starting Tailscale Funnel on port 5000..." | tee -a "$LOG_FILE"
# Funnelをバックグラウンドで実行
sudo tailscale funnel 5000 > /dev/null 2>&1 &
TAILSCALE_PID=$!

# スクリプト終了時にTailscale Funnelも終了させる
cleanup() {
    echo "Stopping Tailscale Funnel..." | tee -a "$LOG_FILE"
    if ps -p $TAILSCALE_PID > /dev/null; then
        sudo kill $TAILSCALE_PID
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
python3 -u app.py 2>&1 | tee -a "$LOG_FILE"
