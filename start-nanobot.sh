#!/bin/bash

# tmuxセッションが既に存在したら何もしない
tmux has-session -t nanobot-gateway 2>/dev/null && exit 0

# 新しいtmuxセッションを作成してデタッチ（画面なし）
tmux new-session -d -s nanobot-gateway

# セッション内でnanobot gateway起動
tmux send-keys -t nanobot-gateway "nanobot gateway" C-m

echo "nanobot gateway started in tmux session 'nanobot-gateway'"

# ダッシュボードも起動
DASHBOARD_DIR="$(dirname "$0")"
if [ -d "$DASHBOARD_DIR" ] && ! tmux has-session -t nano-board 2>/dev/null; then
    tmux new-session -d -s nano-board
    # Use ./start.sh instead of direct python command to handle cleanup and checks
    tmux send-keys -t nano-board "cd $DASHBOARD_DIR && ./start.sh" C-m
    echo "nanobot dashboard started in tmux session 'nano-board'"
fi

