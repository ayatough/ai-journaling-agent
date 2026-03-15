# ADR-0004: 即時応答 + claude-agent-sdk セッション継続アーキテクチャ

## ステータス
承認

## 背景
ADR-0003 では Claude Code `/loop` による10分間隔ポーリング方式を採用したが、以下の課題が顕在化した:

1. **レイテンシ**: ユーザーがメッセージを送ってから最大10分待つ UX は実用に耐えない
2. **会話の非連続**: 毎回単発の API 呼び出しのため、前のターンの文脈が失われる
3. **inbox の二重管理**: webhook で inbox 保存 → /loop で読み取り → mark-read という冗長なフロー

PR #16 で即時応答（BackgroundTask + Anthropic SDK）を実装し、PR #18 で claude-agent-sdk によるセッション継続に移行した。

## 選択肢
1. **/loop ポーリング方式**（ADR-0003）: webhook は inbox 保存のみ、/loop が10分間隔で応答生成。低コストだがレイテンシが大きく、会話文脈を保てない
2. **BackgroundTask + Anthropic SDK 直接呼び出し**: webhook 内の BackgroundTask で即時応答。低レイテンシだが会話履歴の自前管理が必要
3. **BackgroundTask + claude-agent-sdk セッション継続**: SDK が会話状態を内部管理し、session_id のみ永続化して会話スレッドを再開

## 決定
**選択肢3: BackgroundTask + claude-agent-sdk セッション継続**を採用。

理由:
- 即時応答（数秒）で UX が大幅に改善
- SDK がセッション管理を担うため、会話履歴の自前実装が不要
- session_id の保存のみで会話文脈が自然に継続
- /loop はチェックイン促進に特化でき、責務が明確に分離

## アーキテクチャ

```
[ユーザーがメッセージ送信]
        ↓
[Webhook POST /callback]
  ├─→ JournalEntry 保存
  ├─→ inbox 保存
  └─→ BackgroundTask 起動
        ↓
[BackgroundTask: _respond_to_user()]
  ├─→ sessions/{user_id}.txt から session_id を読み込み
  ├─→ claude-agent-sdk: query(prompt, resume=session_id, system_prompt=...)
  ├─→ AssistantMessage からテキスト抽出
  ├─→ LINE push 送信
  └─→ ResultMessage の session_id を sessions/{user_id}.txt に保存

[/loop チェックイン] ← チェックイン促進専用（応答生成は行わない）
```

## 影響
- `claude-agent-sdk` は `claude` CLI（Node.js）に依存するため、本番環境にも `claude` のインストールが必要
- セッション状態は SDK 側で管理。`sessions/{user_id}.txt` に残るのは再接続用の ID のみ
- /loop の役割がチェックイン促進に縮小（inbox ポーリングは不要に）
- 単一ユーザー前提の設計は維持（ADR-0003 と同様）
