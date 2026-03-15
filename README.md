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
| `OWNER_USER_ID` | No | push送信時のデフォルトユーザーID |
| `STORAGE_DIR` | No | データ保存先 (デフォルト: `~/.ai-journaling-agent/data`) |
| `PORT` | No | Webhookサーバーのポート (デフォルト: `8000`) |

## 起動方法

### 1. Webhookサーバー

LINEからのメッセージを受信するFastAPIサーバーです。

```bash
uv run python -m ai_journaling_agent.main
```

- エントリーポイント: [src/ai_journaling_agent/main.py](src/ai_journaling_agent/main.py)
- エンドポイント: `POST /callback`
- デフォルトポート: 8000

### 2. AI応答ループ (Claude Code)

別プロセスでClaude Codeを起動し、定期的にインボックスを処理します。

```bash
claude code /loop 10m /daily-sync
```

このループが行うこと:
- 未処理メッセージの読み取りとAI応答の生成・送信
- 朝 (6-10時 JST) / 夜 (18-22時 JST) のチェックイン促進

## CLIツール

Claude Code `/loop` から使用されるCLIツール群です。

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

詳細は [ADR-0003](docs/adr/0003-operational-architecture.md) を参照。
