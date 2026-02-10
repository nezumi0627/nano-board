# NanoBoard

Tailscale認証を使用したNanobot管理コンソールです。

## 機能

- **モニタリング**: Nanobotプロセスの状態監視（PID, Uptime, Memory, CPU）
- **詳細情報**: 設定情報（Gateway, Model, Channels）やセッション詳細の表示
- **ネットワーク**: Tailscaleの状態とFunnel URLの表示
- **ジョブ管理**: Cronジョブの状態確認（スケジュールを読みやすい形式で表示）
- **チャットテスト**: モデルとの対話テスト機能（`<think>`タグの折りたたみ表示に対応）
- **UI/UX**: 長いモデル名の適切な表示、チャットの自動スクロール、操作時のフィードバック改善
- **PWA対応**: iOS/Androidでのアプリ化と更新機能（Service Worker）
- **セキュリティ**: Tailscale認証によるアクセス制御

## クイックスタート

### 1. セットアップ

```bash
cd /home/nezumi0627/nano-board
./install.sh
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

Nanobotを起動すると、コンソールも自動的に起動します:

```bash
./start-nanobot.sh
```

これにより、Nanobot Gatewayとコンソールの両方がtmuxセッションで起動します。

### 手動起動

```bash
cd /home/nezumi0627/nano-board
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
nano-board/
├── app/                # アプリケーションパッケージ
│   ├── __init__.py     # アプリケーションファクトリ
│   ├── services/       # バックグラウンドサービス
│   └── utils/          # ユーティリティ
├── run.py              # エントリーポイント
├── requirements.txt    # 依存ライブラリ
├── static/             # 静的ファイル (CSS, JS, Images)
└── templates/          # HTMLテンプレート
```

## 注意事項

- Tailscale認証が有効な場合、Tailscaleネットワーク経由でアクセスする必要があります
- nanobotの設定ファイル（`~/.nanobot/config.json`）への読み取りアクセスが必要です
- プロセス情報の取得には`psutil`ライブラリが必要です
- Tailscale Funnelを使用する場合、sudo権限が必要です
