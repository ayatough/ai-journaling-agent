# Issue管理スキル

## Issue起票

セッションで計画したタスクをIssue化する場合:

1. タイトル: 簡潔に（日本語OK）
2. 本文:
   - 背景（なぜ必要か）
   - やること（チェックリスト形式）
   - 完了条件
3. ラベル: `feature`, `bug`, `refactor`, `experiment` から選択

## Issue実装（Loop用）

1. アサインされたIssueを確認
2. 仕様が明確なもののみ着手（曖昧ならコメントで確認）
3. 実装 → テスト → `jj describe` に `fixes #N` を含める
