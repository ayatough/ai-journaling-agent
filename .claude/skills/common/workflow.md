# 開発ワークフロー

## セッションベース開発（通常）

1. セッション開始 → プランモードで計画提示
2. ユーザー承認後、Issue化 or 実装を選択
3. 実装 → テスト → jjコミット

## Issue駆動開発（Loop用）

- 仕様が明確なIssueのみ自動実装
- 曖昧なものはコメントで確認

## 記録の棲み分け

| 種類 | 場所 | jj管理 |
|------|------|--------|
| ADR | `docs/adr/` | o |
| 実験メモ | `outputs/experiments_log.md` | x |
| 実験サマリ | `docs/experiments/` | o |
| 週次/月次報告 | GitHub Discussions | - (人間専用) |
