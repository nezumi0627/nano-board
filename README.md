# Nanobot Status Dashboard

Tailscale認証を使用したnanobotステータスダッシュボードです。

## 機能

- nanobotプロセスの状態監視（実行中/停止中、PID、稼働時間、メモリ使用量、CPU使用率）
- nanobot設定情報の表示（Gateway、モデル、チャネル設定）
- セッション情報の表示（セッション数、メッセージ数、最新アクティビティ）
- Cronジョブの状態表示
- Tailscale認証によるアクセス制御
- 手動更新（自動更新なし）
- nanobot起動時に自動起動

## クイックスタート

### 1. セットアップ

```bash
cd /home/nezumi0627/nanobot-dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 起動

```bash
./start.sh
```

### 3. Tailscale Funnelで公開（推奨）

```bash
./setup-funnel.sh
```

または手動で:
```bash
sudo tailscale funnel 5000
tailscale funnel status  # URLを確認
```

## 使用方法

### 自動起動（推奨）

nanobotを起動すると、ダッシュボードも自動的に起動します:

```bash
./start-nanobot.sh
```

これにより、nanobot gatewayとダッシュボードの両方がtmuxセッションで起動します。

### 手動起動

```bash
cd /home/nezumi0627/nanobot-dashboard
./start.sh
```

### アクセス方法

1. **Tailscale Funnel使用時**（推奨）
   - `tailscale funnel status`で表示されるURLにアクセス
   - 例: `https://xxxxx-xxxxx.ts.net`

2. **Tailscaleネットワーク経由**
   - `http://<tailscale-ip>:5000`
   - Tailscale IP確認: `tailscale ip -4`

3. **ローカル開発時**（認証無効化）
   ```bash
   export REQUIRE_TAILSCALE_AUTH=false
   ./start.sh
   ```
   - `http://localhost:5000`

### Tailscale Funnel管理

- **有効化**: `sudo tailscale funnel 5000`
- **状態確認**: `tailscale funnel status`
- **停止**: `sudo tailscale funnel reset`

## 環境変数

```bash
export PORT=5000                    # ポート番号（デフォルト: 5000）
export HOST=0.0.0.0                 # ホスト（デフォルト: 0.0.0.0）
export REQUIRE_TAILSCALE_AUTH=true  # Tailscale認証（デフォルト: true）
```

## API エンドポイント

- `GET /` - ダッシュボードUI
- `GET /api/status` - nanobotステータス情報（JSON）
- `GET /api/health` - ヘルスチェック

## ファイル構成

```
nanobot-dashboard/
├── app.py              # Flaskアプリケーション
├── start.sh            # 起動スクリプト
├── setup-funnel.sh     # Tailscale Funnel設定スクリプト
├── requirements.txt    # Python依存関係
├── README.md           # このファイル
├── .gitignore          # Git除外設定
└── templates/
    └── dashboard.html  # ダッシュボードUI
```

## 注意事項

- Tailscale認証が有効な場合、Tailscaleネットワーク経由でアクセスする必要があります
- nanobotの設定ファイル（`~/.nanobot/config.json`）への読み取りアクセスが必要です
- プロセス情報の取得には`psutil`ライブラリが必要です
- Tailscale Funnelを使用する場合、sudo権限が必要です
