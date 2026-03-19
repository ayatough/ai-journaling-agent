# デプロイ手順書

## 前提条件

- Docker / Docker Compose が利用可能なサーバー
- LINE Messaging API チャネルが作成済み
- ローカルで `claude login` が完了済み（Pro/Max プランの OAuth 認証）

## 認証方式について

本アプリは `claude_agent_sdk` を使用しており、Anthropic API キーではなく
Claude Code の OAuth トークン（`~/.claude/.credentials.json`）で認証します。

**重要な確認事項:**
- `_bundled/claude` バイナリは Linux x86-64 ELF 形式で、一般的なサーバー・Docker 環境で動作します
- `refreshToken` によってアクセストークンが自動更新されるため、長期間の非インタラクティブ実行が可能です
- ただし `refreshToken` が revoke された場合（別端末での再ログイン等）は手動再認証が必要です

---

## クイックスタート（Docker Compose）

### 1. 認証情報をサーバーへコピー

```bash
# ローカルで実行 — claude login 済みの認証情報をサーバーへ転送
scp ~/.claude/.credentials.json your-server:~/.claude/.credentials.json
ssh your-server "chmod 600 ~/.claude/.credentials.json"
```

### 2. リポジトリをクローン

```bash
git clone https://github.com/ayatough/ai-journaling-agent.git
cd ai-journaling-agent
```

### 3. 環境変数ファイルを作成

```bash
cp .env.example .env
# 以下の値を設定
#   LINE_CHANNEL_SECRET=...
#   LINE_CHANNEL_ACCESS_TOKEN=...
#   OWNER_USER_ID=...（LINE ユーザー ID）
```

> `.env.example` の作成については「環境変数一覧」を参照。

### 4. 起動

```bash
docker compose up -d
```

### 5. LINE Webhook URL を設定

LINE Developers コンソールで Webhook URL を設定します:

```
https://your-domain.example.com/callback
```

または ngrok を使ったローカルテスト:

```bash
ngrok http 8000
```

---

## 環境変数一覧

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `LINE_CHANNEL_SECRET` | ✅ | LINE チャネルシークレット |
| `LINE_CHANNEL_ACCESS_TOKEN` | ✅ | LINE チャネルアクセストークン |
| `OWNER_USER_ID` | ✅ | チェックイン送信先の LINE ユーザー ID |
| `STORAGE_DIR` | — | データ保存先（デフォルト: `~/.ai-journaling-agent/data`） |
| `PORT` | — | サーバーポート（デフォルト: `8000`） |
| `CLAUDE_CREDENTIALS_PATH` | — | credentials ファイルのパス（デフォルト: `~/.claude/.credentials.json`） |

---

## デプロイ先の選択肢

### Railway（推奨）

- **料金**: Hobby プラン $5/月〜（常時起動）
- **メリット**: GitHub 連携で自動デプロイ、シークレット管理が簡単
- **デメリット**: credentials ファイルをシークレットとして設定する必要あり
- **credentials の設定方法**: `~/.claude/.credentials.json` の内容を環境変数 `CLAUDE_CREDENTIALS_JSON` として設定し、起動スクリプトでファイルに書き出す

### Fly.io

- **料金**: 無料枠あり（小規模なら $0〜）
- **メリット**: `fly secrets set` でシークレット管理
- **デメリット**: 設定が Railway より複雑

### VPS（さくらクラウド / Vultr 等）

- **料金**: $5〜$10/月
- **メリット**: 最も柔軟、credentials ファイルをそのまま配置可能
- **デメリット**: 運用管理が必要

---

## credentials ファイルの管理

### リスクと対策

| リスク | 対策 |
|--------|------|
| refreshToken の失効 | 定期的に `claude login` でトークンを更新（現状は手動） |
| 複数プロセスの競合 | MVP 段階では単一インスタンスのみ起動する |
| ファイルの漏洩 | パーミッション `600`、`.gitignore` に追加 |

### クラウド環境での credentials 配置

Railway / Fly.io 等でファイルをそのままマウントできない場合:

```bash
# credentials.json の内容を Base64 エンコードして環境変数として保存
CLAUDE_CREDENTIALS_B64=$(base64 -w0 ~/.claude/.credentials.json)
# → Railway / Fly.io のシークレットに CLAUDE_CREDENTIALS_B64 として設定
```

起動スクリプト（`scripts/docker-entrypoint.sh`）で復元:

```bash
#!/bin/sh
if [ -n "${CLAUDE_CREDENTIALS_B64}" ]; then
    mkdir -p ~/.claude
    echo "${CLAUDE_CREDENTIALS_B64}" | base64 -d > ~/.claude/.credentials.json
    chmod 600 ~/.claude/.credentials.json
fi
exec "$@"
```

---

## ヘルスチェック

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

## ログ確認

```bash
docker compose logs -f app      # Webhook サーバーのログ
docker compose logs -f checkin  # チェックイン送信のログ
```

## 停止・再起動

```bash
docker compose down
docker compose up -d
```

---

## 未解決の課題（TODO）

- [ ] Issue #53: マルチユーザー対応（現状はシングルユーザー）
- [ ] Issue #54: レート制限
- [ ] Issue #57: ストレージバックアップ
- [ ] Issue #58: モニタリング（Sentry 等）
