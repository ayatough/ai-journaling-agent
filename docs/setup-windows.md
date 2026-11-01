# 自分用に立てる手順（Windows）

このボットは **1 人 1 インスタンス** で使う。自分の LINE チャネル・自分の Claude サブスクリプション・自分の PC で動かし、
`OWNER_USER_ID` に設定した本人のメッセージにだけ応答する。他人に自分のボットを使わせる（自分の Claude 枠で他人に返事をする）構成にはしないこと。

構成の全体像は [architecture.md](architecture.md) を参照。

## 1. 必要なもの

| もの | 用途 | 入れ方 |
|---|---|---|
| Claude Pro / Max | AI 応答（サブスクリプション枠で動く。API キー不要） | — |
| [uv](https://docs.astral.sh/uv/) | Python と依存関係 | `winget install astral-sh.uv` |
| Claude Code (`claude`) | 長期トークンの発行 | <https://claude.com/claude-code> |
| ngrok アカウント（無料） | LINE から届く固定 HTTPS URL | <https://dashboard.ngrok.com> |
| ngrok 3.28 以上 | トンネル | 下記「4. ngrok」参照（winget 版は古い） |
| LINE Developers のチャネル | Messaging API | <https://developers.line.biz/console/> |

## 2. リポジトリと依存関係

```powershell
git clone https://github.com/ayatough/ai-journaling-agent.git
cd ai-journaling-agent
uv sync
```

## 3. LINE チャネル

1. LINE Developers でプロバイダーと **Messaging API チャネル** を作る。
2. 「チャネル基本設定」から **チャネルシークレット** と、一番下の **あなたのユーザーID**（`U` で始まる 33 文字）を控える。
3. 「Messaging API設定」で **チャネルアクセストークン（長期）** を発行する。
4. 同じ画面で「応答メッセージ」を無効、「Webhookの利用」を有効にする（URL は 5 で設定）。
5. 同じ画面の QR コードから自分のスマホでボットを友だち追加する。

## 4. ngrok

1. ngrok にログインし、左メニュー「Your Authtoken」をコピーして登録する。
   ```powershell
   ngrok config add-authtoken <トークン>
   ```
2. 左メニュー「Domains」で無料の固定ドメイン（`xxxx.ngrok-free.dev` など）を確認する。
3. ngrok が古い・入っていない場合は公式の zip を `%LOCALAPPDATA%\Programs\ngrok\` に展開する。
   Windows Defender が ngrok を検出して削除することがある。その場合は自分の判断で、管理者 PowerShell から
   そのフォルダだけを除外に追加する：
   `Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\Programs\ngrok"`

## 5. Claude の長期トークン

```powershell
claude setup-token
```

ブラウザでログインすると `sk-ant-oat01-...` が表示される（有効期間 1 年）。チャットや Git に貼らないこと。

## 6. `.env`

`.env.example` をコピーして `.env` を作り、値を入れる。

```dotenv
LINE_CHANNEL_SECRET=...
LINE_CHANNEL_ACCESS_TOKEN=...
OWNER_USER_ID=U...                 # 3-2 で控えた自分のユーザーID。未設定だと誰にも応答しない
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
NGROK_DOMAIN=xxxx.ngrok-free.dev
```

## 7. 動作確認

```powershell
# webhook とトンネルを一度だけ手動で起動して確認する場合
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-webhook.ps1   # 別ウィンドウで
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-tunnel.ps1    # 別ウィンドウで
curl.exe http://127.0.0.1:8000/health    # {"status":"ok"}
```

LINE Developers の「Webhook URL」に `https://<NGROK_DOMAIN>/callback` を設定し、「検証」で成功すること、
スマホから送ったメッセージに返事が来ることを確認したら、手動起動したウィンドウを閉じる。

## 8. 自動起動（再起動後も復帰）

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\register-tasks.ps1
```

タスクスケジューラに次の 3 つが登録される（窓は出ない）。

| タスク | タイミング | 内容 |
|---|---|---|
| `AIJournaling-Webhook` | ログオン時 | webhook（落ちたら再起動） |
| `AIJournaling-Tunnel` | ログオン時 | ngrok（落ちたら再起動） |
| `AIJournaling-Checkin` | 30 分ごと | 必要ならチェックインを送信 |

解除は `register-tasks.ps1 -Unregister`。ログは `%USERPROFILE%\.ai-journaling-agent\logs\` に月ごと。

## 注意

- PC がスリープ中・ログオン前は応答しない。
- コードを更新したら webhook を再起動する（`AIJournaling-Webhook` タスクを終了 → 実行、または python プロセスを終了すると自動で再起動）。
- `.env` とデータフォルダには個人情報・秘密情報が入る。共有しないこと。
