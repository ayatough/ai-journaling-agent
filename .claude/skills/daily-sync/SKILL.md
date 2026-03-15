# 定期同期スキル（Loop用）

`/loop 10m /daily-sync` で10分間隔で実行される。

## 実行内容

### 1. インボックス処理（最優先）

1. `uv run inbox list` で未処理メッセージを確認
2. 未処理メッセージがあれば、各メッセージについて:
   a. `uv run journal-history --days 3` で直近の文脈を取得
   b. 文脈を踏まえて、温かく共感的な返信を生成
   c. `uv run push-line --text "{response}"` で送信
   d. `uv run inbox mark-read {id}` で処理済みに

### 2. チェックイン確認

1. `uv run checkin status` で確認
2. チェックインが必要なら:
   a. 朝（6-10時JST）: モーニングチェックイン送信
   b. 夜（18-22時JST）: イブニングチェックイン送信
   c. `uv run push-line --text "{prompt}"`
   d. `uv run checkin record --kind morning|evening`

### 3. 従来タスク

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
