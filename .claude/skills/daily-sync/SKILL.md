# 定期同期スキル（Loop用）

`/loop 10m /daily-sync` で10分間隔で実行される。

## 実行内容

### 1. チェックイン確認

1. `uv run checkin status` で確認
2. チェックインが必要なら:
   a. `uv run journal-history --days 3` で直近の文脈を取得
   b. 文脈を踏まえてチェックインプロンプトを生成（時間帯別の方針は下記参照）
   c. `uv run push-line --text "{contextual prompt}"`
   d. `uv run checkin record --kind morning|midday|evening|night_summary --text "{contextual prompt}"`

### 時間帯別プロンプト方針

| 時間帯 (JST) | kind | 方針 |
|---------------|------|------|
| 06:00–09:59 | morning | 今日の気分・予定を聞く |
| 12:00–12:59 | midday | 午前の振り返り・午後の予定 |
| 18:00–20:59 | evening | 今日の振り返りを促す |
| 21:00–22:59 | night_summary | `uv run journal-today` で当日記録を確認し、まとめを送信。記録がなければ優しくリマインド |

### night_summary の手順

1. `uv run journal-today` で当日エントリを取得
2. エントリがあれば → 内容を要約して「今日はこんな一日でしたね」と送信
3. エントリがなければ → 「今日は記録がないみたいですが、何かあれば聞かせてください」と優しく促す
4. まとめは事実ベース（評価・判定はしない）

### 2. 従来タスク

- **Issue確認**: アサイン済みIssueがあれば処理（仕様明確なもののみ）
- **実験ログ確認**: `outputs/experiments_log.md` に新しいエントリがあれば確認
- **ADR判断**: 重要な設計判断があればADR化を提案（人間の承認待ち）

## 応答のトーン

- 温かく、共感的
- 押し付けない
- ユーザーの感情を反映する
- 短くても丁寧に

## 禁止事項

- GitHub Discussionsへの書き込み（人間専用）
- 仕様が曖昧なIssueの自動実装
- テストが通らない状態でのコミット

## 注意

インボックス処理・AI応答生成はWebhook BackgroundTask が担当するため、
/loop では行わない。
