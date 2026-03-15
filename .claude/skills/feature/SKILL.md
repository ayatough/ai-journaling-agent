# 機能開発スキル

## 手順

1. プランモードで計画を提示（いきなり実装しない）
2. ユーザー承認後、Issue化 or 実装を選択
3. 実装時は以下を守る:
   - `src/ai_journaling_agent/core/` にコアロジック（LINE非依存）
   - `src/ai_journaling_agent/adapters/` にアダプター層
   - テストを `tests/` に追加
4. `uv run pytest` で全テスト通過を確認
5. `uv run ruff check src/ tests/` でlintチェック
6. `jj new` で新しい変更セットを作成してから作業開始
7. 完了したら `jj describe` でコミットメッセージを記述

## コアとアダプターの分離

- コアロジック（`core/`）は外部サービスに依存しない
- LINE固有の処理は `adapters/line/` に閉じる
- 将来のアプリ化・Rust移行時にコアロジックのみ移植可能にする
