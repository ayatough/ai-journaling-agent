# AI Journaling Agent

AIエージェントベースのジャーナリングアプリ。LINE経由でユーザーと対話し、日々の記録を通じて充実感を育てる。

## タスク

| やりたいこと | スキル |
|------------|--------|
| 新機能を追加 | `.claude/skills/feature/SKILL.md` |
| コードを改善 | `.claude/skills/refactor/SKILL.md` |
| Issueを管理 | `.claude/skills/issue/SKILL.md` |
| 定期同期（Loop用） | `.claude/skills/daily-sync/SKILL.md` |

## ディレクトリ構造

```
src/ai_journaling_agent/core/     ← コアロジック（LINE非依存）
src/ai_journaling_agent/adapters/ ← 外部サービス連携（LINE等）
docs/adr/                    ← 設計判断記録
docs/experiments/            ← 週次実験サマリ
outputs/                     ← 実験ログ・TBログ（jj管理外）
```

## 共通ナレッジ

- 開発ワークフロー: `.claude/skills/common/workflow.md`
- uv の使い方: `.claude/skills/common/uv-usage.md`
- jj の使い方: `.claude/skills/common/jj-workflow.md`
- テスト方針: `.claude/skills/common/test-strategy.md`

## 絶対に守る制約

1. **jj を使う**（gitコマンド直接実行禁止）
2. **プランモード強制**（セッション開始時、いきなり実装しない）
3. **GitHub Discussions に書き込まない**（人間専用）
