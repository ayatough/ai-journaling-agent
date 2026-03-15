# ADR-0003: 運用アーキテクチャ — Claude Code /loop ベースのAI応答

## ステータス
承認

## 背景
Issue #1-#5でwebhook受信・ルールベース応答が完成した。次のステップとして、AIによる自然な会話応答と能動的なチェックイン促進が必要。

## 選択肢
1. **Anthropic SDK直接呼び出し**: webhookハンドラー内でAPI呼び出し。低レイテンシだがAPI管理が必要
2. **Claude Code /loop ベース**: webhookはinbox保存のみ、Claude Code /loopがAI応答をpushで送信

## 決定
**選択肢2: Claude Code /loop ベース**を採用。

理由:
- Claude Code自体がAIの「脳」として機能し、追加のAPI管理が不要
- /loopプロセスがインボックス監視とチェックイン促進の両方を担当
- MVPではレイテンシ（最大10分）は許容範囲
- ユーザーは1人（開発者自身）のため、スケーラビリティは不要

## アーキテクチャ

```mermaid
graph TB
    subgraph "LINE Platform"
        USER["ユーザー (LINE)"]
    end

    subgraph "このマシン"
        subgraph "プロセス1: Webhook Server"
            WH["FastAPI POST /callback"]
            INBOX_W["inbox保存"]
            JOURNAL_W["JournalEntry保存"]
        end

        subgraph "プロセス2: Claude Code /loop"
            LOOP["10分間隔で実行"]
            INBOX_R["inbox読み取り"]
            HISTORY["履歴取得"]
            AI["Claude Code (AI応答生成)"]
            CHECKIN["チェックイン判定"]
        end

        subgraph "CLI ツール"
            CLI_INBOX["inbox list / mark-read"]
            CLI_PUSH["push-line"]
            CLI_HIST["journal-history"]
            CLI_CHK["checkin status / record"]
        end

        subgraph "ストレージ"
            S_INBOX["inbox/ {id}.json"]
            S_JOURNAL["{user}.jsonl"]
            S_USER["users/{user}.json"]
            S_CHECKIN["checkin_log.json"]
        end
    end

    USER -->|"メッセージ送信"| WH
    WH --> INBOX_W --> S_INBOX
    WH --> JOURNAL_W --> S_JOURNAL

    LOOP --> INBOX_R
    INBOX_R -->|"CLI"| CLI_INBOX --> S_INBOX
    LOOP --> HISTORY
    HISTORY -->|"CLI"| CLI_HIST --> S_JOURNAL
    INBOX_R --> AI
    HISTORY --> AI
    AI -->|"CLI"| CLI_PUSH -->|"push API"| USER
    CLI_PUSH -->|"mark-read"| CLI_INBOX

    LOOP --> CHECKIN
    CHECKIN -->|"CLI"| CLI_CHK --> S_CHECKIN
    CHECKIN -->|"push if needed"| CLI_PUSH
```

## シーケンス図: ジャーナル送信 → AI応答

```mermaid
sequenceDiagram
    actor U as ユーザー
    participant L as LINE Platform
    participant W as Webhook (FastAPI)
    participant FS as ファイルシステム
    participant CC as Claude Code /loop

    U->>L: 「今日は良い日だった」
    L->>W: POST /callback (webhook)
    W->>FS: inbox/{id}.json 保存
    W->>FS: {user}.jsonl にJournalEntry追記
    Note over W: HTTP 200返却のみ（LINE返信なし）

    Note over CC: 10分間隔で起動

    CC->>FS: uv run inbox list
    FS-->>CC: 未処理メッセージ一覧
    CC->>FS: uv run journal-history --days 3
    FS-->>CC: 直近ジャーナル履歴
    Note over CC: 文脈を踏まえてAI応答生成
    CC->>L: uv run push-line --text "良い日だったんですね！..."
    L->>U: 「良い日だったんですね！...」
    CC->>FS: uv run inbox mark-read {id}
```

## シーケンス図: 朝チェックイン

```mermaid
sequenceDiagram
    actor U as ユーザー
    participant L as LINE Platform
    participant FS as ファイルシステム
    participant CC as Claude Code /loop

    Note over CC: 朝7:00 の /loop サイクル

    CC->>FS: uv run checkin status
    FS-->>CC: "morning check-in needed"
    Note over CC: チェックインプロンプト生成
    CC->>L: uv run push-line --text "おはようございます！..."
    L->>U: 「おはようございます！今日の調子は...」
    CC->>FS: uv run checkin record --kind morning

    Note over U: ユーザーが返信 → ジャーナル送信フローへ
```

## 影響
- webhookは即時返信しない → ユーザーは最大10分待つ（MVP許容範囲）
- Claude Code /loopの実行にAPIクレジットを消費
- 単一ユーザー前提の設計 → 将来のスケールにはAnthropic SDK直接呼び出しへの移行が必要
