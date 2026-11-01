# AI Journaling Agent

AIエージェントベースのジャーナリングアプリ。LINEを通じてマインドフルネスとウェルビーイングを促進します。

## セットアップ

### 前提条件

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- LINE Messaging API のチャネル

### インストール

```bash
uv sync
```

### 環境変数

`.env` ファイルをプロジェクトルートに作成:

```dotenv
LINE_CHANNEL_SECRET=your-channel-secret
LINE_CHANNEL_ACCESS_TOKEN=your-channel-access-token
OWNER_USER_ID=your-line-user-id
```

| 変数 | 必須 | 説明 |
|------|------|------|
| `LINE_CHANNEL_SECRET` | Yes | LINE チャネルシークレット |
| `LINE_CHANNEL_ACCESS_TOKEN` | Yes | LINE チャネルアクセストークン |
| `OWNER_USER_ID` | Yes | 自分の LINE ユーザーID。**このユーザー以外のメッセージは無視**。未設定なら誰にも応答しない。チェックインの送信先 |
| `STORAGE_DIR` | No | データ保存先 (デフォルト: `~/.ai-journaling-agent/data`) |
| `HOST` | No | 待受アドレス (デフォルト: `0.0.0.0`。Windows 起動スクリプトでは `127.0.0.1`) |
| `PORT` | No | Webhookサーバーのポート (デフォルト: `8000`) |
| `CLAUDE_CODE_OAUTH_TOKEN` | Windows 運用時 | `claude setup-token` で発行した長期トークン |
| `NGROK_DOMAIN` | Windows 運用時 | ngrok の固定ドメイン |

> 1 人 1 インスタンスで使う。自分用に立てる手順（Windows）は [docs/setup-windows.md](docs/setup-windows.md)。

## 起動方法

### 1. Webhookサーバー

LINEからのメッセージを受信するFastAPIサーバーです。

```bash
uv run python -m ai_journaling_agent.main
```

- エントリーポイント: [src/ai_journaling_agent/main.py](src/ai_journaling_agent/main.py)
- エンドポイント: `POST /callback`
- デフォルトポート: 8000

### 2. チェックイン送信

朝・昼・夕・夜のチェックインを、未送信なら LINE に push します。30 分ごとに実行します。

```bash
./scripts/run-checkin.sh --loop          # Linux / Docker
```

Windows ではタスクスケジューラで常駐させます（[docs/setup-windows.md](docs/setup-windows.md)）。
AI の応答は webhook 内で即時に生成されるため（ADR-0004）、Claude Code の `/loop` は不要です。

## CLIツール

運用・デバッグ用の CLI ツール群です。

| コマンド | 説明 |
|----------|------|
| `uv run inbox list` | 未処理メッセージの一覧表示 |
| `uv run inbox mark-read <id>` | メッセージを処理済みにする |
| `uv run push-line --text "..."` | LINE pushメッセージを送信 |
| `uv run journal-history --days 3` | 直近のジャーナルエントリを表示 |
| `uv run checkin status` | チェックインが必要か確認 |
| `uv run checkin record --kind morning` | チェックイン送信を記録 |

## プロジェクト構成

```
src/ai_journaling_agent/
├── main.py                  # Webhookサーバーのエントリーポイント
├── core/                    # コアロジック（LINE非依存）
│   ├── config.py            #   設定 (環境変数)
│   ├── journal.py           #   ジャーナルエントリの分類
│   ├── repository.py        #   ジャーナル永続化
│   ├── inbox.py             #   インボックス管理
│   ├── checkin.py           #   チェックイン追跡
│   ├── user.py              #   ユーザー状態管理
│   ├── prompts.py           #   プロンプトテンプレート
│   └── scheduler.py         #   時間帯判定
├── adapters/line/           # LINE固有の処理
│   ├── bot.py               #   FastAPIアプリ + Webhook
│   └── handlers.py          #   イベントハンドラー
└── cli/                     # CLIツール
    ├── inbox_cmd.py          #   inbox list / mark-read
    ├── push_cmd.py           #   push-line
    ├── history_cmd.py        #   journal-history
    └── checkin_cmd.py        #   checkin status / record
```

## 開発

```bash
uv run pytest --ignore=tests/test_config.py   # テスト実行
uv run ruff check src/ tests/                  # リント
uv run mypy src/                               # 型チェック
```

## アーキテクチャ

システム図は [docs/architecture.md](docs/architecture.md)、設計判断は [ADR-0004](docs/adr/0004-instant-response-with-agent-sdk.md) を参照（ADR-0003 の `/loop` 方式は置き換え済み）。
