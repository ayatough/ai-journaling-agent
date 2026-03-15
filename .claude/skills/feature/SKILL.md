# 機能開発スキル

## 手順

1. プランモードで計画を提示（いきなり実装しない）
2. ユーザー承認後、Issue化 or 実装を選択
3. 実装時は以下を守る:
   - `src/ai_journaling_agent/core/` にコアロジック（配信チャネル非依存）
   - `src/ai_journaling_agent/adapters/` にアダプター層
   - テストを `tests/` に追加
4. アーキテクチャ変更を伴う場合、既存ADRとの整合を確認し、必要に応じてADR更新を含める
5. `uv run pytest` で全テスト通過を確認
6. `uv run ruff check src/ tests/` でlintチェック
7. `jj new` で新しい変更セットを作成してから作業開始
8. 完了したら `jj describe` でコミットメッセージを記述

## コアとアダプターの分離

- コアロジック（`core/`）は配信チャネル（LINE等）に依存しない。AI SDK依存は許容
- LINE固有の処理は `adapters/line/` に閉じる
- 将来のアプリ化・Rust移行時にコアロジックのみ移植可能にする
