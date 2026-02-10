#!/bin/bash
# Tailscale Funnel設定スクリプト

echo "🐈 Nanobot Dashboard - Tailscale Funnel設定"
echo ""

# ダッシュボードが起動しているか確認
if ! curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
    echo "⚠️  ダッシュボードが起動していません。まず起動してください:"
    echo "   ./start.sh"
    echo ""
    exit 1
fi

echo "✅ ダッシュボードは実行中です"
echo ""
echo "Tailscale Funnelを有効化します..."
echo "（sudoのパスワード入力が必要な場合があります）"
echo ""

# Tailscale Funnelを有効化
sudo tailscale funnel 5000

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Tailscale Funnelが有効化されました！"
echo ""
echo "📋 公開URLを確認するには:"
echo "   tailscale funnel status"
echo ""
echo "🌐 ダッシュボードにアクセス:"
echo "   上記のURLを使用してください"
echo ""
echo "🛑 Funnelを停止するには:"
echo "   sudo tailscale funnel reset"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
