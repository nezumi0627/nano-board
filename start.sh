#!/bin/bash
# Nanobot Dashboard 起動スクリプト（Tailscale + jq 自動対応）

set -Eeuo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

# ==========================================
# ログ設定
# ==========================================
mkdir -p logs
LOG_FILE="logs/dashboard_$(date +%Y%m%d_%H%M%S).log"
ln -sf "$(basename "$LOG_FILE")" logs/latest.log

log() {
    echo "[$(date '+%F %T')] $*" | tee -a "$LOG_FILE"
}

log "=== Starting Nanobot Console ==="

# sudo 認証
sudo -v

# ==========================================
# 0. jq 自動インストール
# ==========================================
if ! command -v jq >/dev/null 2>&1; then
    log "jq not found, installing..."

    if command -v apt >/dev/null 2>&1; then
        sudo apt update >>"$LOG_FILE" 2>&1
        sudo apt install -y jq >>"$LOG_FILE" 2>&1
        log "jq installed successfully"
    else
        log "❌ jq not found and apt is unavailable. Please install jq manually."
        exit 1
    fi
else
    log "jq already installed"
fi

# ==========================================
# 1. Tailscale 準備
# ==========================================
log "Checking tailscaled service..."

if ! systemctl is-active --quiet tailscaled; then
    log "Starting tailscaled"
    sudo systemctl enable --now tailscaled
fi

if ! tailscale status >/dev/null 2>&1; then
    log "Running tailscale up"
    sudo tailscale up
fi

# serve（旧CLI互換）
if ! pgrep -f "tailscale serve.*localhost:5000" >/dev/null; then
    log "Starting Tailscale Serve (bg -> localhost:5000)"
    sudo tailscale serve --bg localhost:5000
else
    log "Tailscale Serve already running"
fi

# funnel
if ! tailscale funnel status 2>/dev/null | grep -qi "on"; then
    log "Enabling Tailscale Funnel"
    sudo tailscale funnel on
else
    log "Tailscale Funnel already enabled"
fi

# ==========================================
# 2. クリーンアップ（アプリのみ）
# ==========================================
log "Cleaning port 5000 (local app only)"

PIDS=$(lsof -ti :5000 || true)
if [[ -n "$PIDS" ]]; then
    log "Killing existing app processes: $PIDS"
    kill $PIDS || true
    sleep 1
    kill -9 $PIDS 2>/dev/null || true
fi

# ==========================================
# 3. Python アプリ起動
# ==========================================
if [[ ! -d venv ]]; then
    log "❌ venv not found"
    exit 1
fi

source venv/bin/activate

if [[ requirements.txt -nt venv/.requirements_installed ]]; then
    log "Installing Python dependencies"
    pip install --upgrade pip setuptools >>"$LOG_FILE" 2>&1
    pip install -r requirements.txt >>"$LOG_FILE" 2>&1
    touch venv/.requirements_installed
else
    log "Dependencies OK"
fi

log "Starting Flask Application"
python3 -u app.py >>"$LOG_FILE" 2>&1 &
APP_PID=$!

# ==========================================
# 4. 起動確認
# ==========================================
for i in {1..30}; do
    if curl -sf http://localhost:5000 >/dev/null; then
        DNS=$(tailscale status --json 2>/dev/null | jq -r '.Self.DNSName // empty')
        log "✅ Dashboard is running"
        log "   Local     : http://localhost:5000"
        [[ -n "$DNS" ]] && log "   Tailscale : https://$DNS"
        break
    fi

    if ! kill -0 "$APP_PID" 2>/dev/null; then
        log "❌ App crashed"
        exit 1
    fi
    sleep 1
done

# ==========================================
# 5. 終了処理
# ==========================================
cleanup() {
    log "Stopping application..."
    kill "$APP_PID" 2>/dev/null || true
}
trap cleanup EXIT

wait "$APP_PID"
