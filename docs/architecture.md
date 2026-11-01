# システム構成

AI Journaling Agent の現在の構成（ADR-0004 + Windows 常駐運用）と、計画中の Obsidian / Cowork 連携をまとめる。
1 人 1 インスタンス前提：各ユーザーが自分の LINE チャネル・自分の Claude サブスクリプション・自分の PC で動かす。

## 全体図

```mermaid
flowchart TB
    user(["📱 LINE アプリ"])

    subgraph cloud["インターネット"]
        line["LINE Platform<br/>Messaging API"]
        ngrok_edge["ngrok<br/>固定ドメイン (HTTPS)"]
        anthropic["Claude<br/>サブスクリプション枠"]
    end

    subgraph pc["Windows PC ・ ログオン時にタスクスケジューラが起動"]
        tunnel["ngrok エージェント"]
        subgraph app["webhook サーバー 127.0.0.1:8000"]
            callback["POST /callback<br/>署名検証 → オーナー判定"]
            handlers["記録<br/>分類・キーワード応答"]
            responder["AiResponder<br/>claude-agent-sdk"]
        end
        checkin["チェックイン送信<br/>30 分ごと"]
        data[("data/<br/>journal・inbox・sessions<br/>profiles・checkin_log")]
    end

    user -- "メッセージ" --> line
    line -- "Webhook" --> ngrok_edge --> tunnel --> callback
    callback --> handlers --> data
    callback -. "バックグラウンド" .-> responder
    responder <-- "応答生成" --> anthropic
    responder --> data
    responder -- "push" --> line
    checkin --> data
    checkin -- "push" --> line
    line -- "返信・促し" --> user
```

## メッセージ 1 通の流れ

```mermaid
sequenceDiagram
    autonumber
    actor U as ユーザー（LINE）
    participant L as LINE Platform
    participant N as ngrok
    participant W as webhook (FastAPI)
    participant S as ストレージ (JSON)
    participant C as claude-agent-sdk
    participant A as Claude

    U->>L: メッセージ送信
    L->>N: POST /callback（X-Line-Signature）
    N->>W: 127.0.0.1:8000 へ転送
    W->>W: 署名検証・オーナー判定（オーナー以外は無視）
    W->>S: ジャーナル・inbox に保存
    W-->>L: 200 OK（即時）
    W->>C: BackgroundTask: 応答生成（session_id で会話を再開）
    C->>A: query（ツールなし・1 ターン）
    A-->>C: 応答テキスト
    C-->>W: 応答 + 新しい session_id
    W->>S: session_id・プロフィール更新
    W->>L: push メッセージ
    L->>U: 返信が届く
```

## 構成要素

| 要素 | 役割 | 実体 |
|---|---|---|
| webhook サーバー | LINE からのイベント受信、記録、AI 応答 | `src/ai_journaling_agent/adapters/line/bot.py` |
| オーナー判定 | `OWNER_USER_ID` 以外のイベントを無視。未設定なら全て無視 | `is_owner_event()` |
| AiResponder | claude-agent-sdk で応答生成。session_id で会話を継続、失効時は新規セッション | `core/ai_responder.py` |
| チェックイン | 朝・昼・夕・夜に未送信なら促しを push | `core/checkin.py`, `scripts/windows/run-checkin.ps1` |
| トンネル | LINE から届く固定 HTTPS URL を PC へ中継 | ngrok（`NGROK_DOMAIN`） |
| 常駐 | ログオン時に webhook とトンネルを起動、落ちたら再起動 | `scripts/windows/register-tasks.ps1` |
| データ | ジャーナル・inbox・セッション・プロフィール | `~/.ai-journaling-agent/data`（`STORAGE_DIR`） |
| ログ | 月ごとのファイル | `~/.ai-journaling-agent/logs` |

## 計画中：Obsidian / Cowork 連携

```mermaid
flowchart LR
    line(["LINE"]) <--> agent["journal agent<br/>（webhook・チェックイン）"]
    agent -- "読む：日記・読書の状況" --> vault
    agent -- "追記：学びメモ・frontmatter" --> inbox
    agent -- "追記" --> relay
    subgraph vault["Obsidian vault"]
        inbox["Inbox/"]
        notes["Notes/"]
        relay["Claude/LINE引き継ぎ.md"]
    end
    cowork["Cowork<br/>スケジュールタスク"] -- "未処理を読む・完了チェック" --> relay
    cowork -- "整理・移動" --> inbox
    inbox -. "移動" .-> notes
    you(["あなた（Obsidian）"]) -- "確認・編集" --> vault
```

- **journal agent（LINE）**：記録の入口。✅ 実装済み：`VAULT_DIR` を設定するとチェックインに促しを添える（夜：日記が未記入なら / 土日の朝：しばらく開いていない本。論文は会話で話題になったときだけ）。計画中：会話から学びメモを `Inbox/` に追記し、デイリーノートの frontmatter を埋める。本文はユーザーの言葉のまま。
- **引き継ぎメモ**：`Claude/LINE引き継ぎ.md` に journal agent が追記するチェックリスト。
- **Cowork**：スケジュールタスクで引き継ぎメモを処理し、Inbox → Notes の整理を行う。破壊的操作は確認待ちとしてメモに残す。
