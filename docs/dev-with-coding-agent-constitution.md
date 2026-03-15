# AI エージェントと人間の協働開発におけるワークフロー設計

## 議論の背景

**目的**: AIエージェント（Claude Code）と人間が協働で研究開発を行うための、長期運用可能なワークフロー設計

**核心的な課題**:
- VibeCoding（その場限りの対話）では、セッションを跨いだ文脈が失われる
- 過去の設計判断が共有されず、矛盾した実装が生まれる
- 長期開発で人間とAIの間で目標・タスク・進捗が共有されていない

---

## 参考資料

### 1. OpenAI公式ブログ
**Harness engineering: leveraging Codex in an agent-first world**
https://openai.com/index/harness-engineering/

**主要な知見**:
- OpenAIが2025年8月に空のリポジトリから数週間で100万行規模のコードをCodexエージェント主体で開発
- エンジニアの役割が「コードを書くこと」から「環境を設計し、エージェントが確実に動作できるフィードバックループを構築すること」に変化
- カスタムリンターや構造テストでルールを強制し、エージェントが認識・実行できる形で制約を実装
- AGENTS.mdは百科事典ではなく目次として機能させ、リポジトリの知識ベースは構造化されたdocs/ディレクトリに配置
- **重要**: 何かが失敗したとき、解決策は「もっと頑張る」ではなく「どの能力が欠けているか、エージェントが認識・実行できる形でそれをどう実装するか」を問うこと

### 2. 論文
**Evaluating AGENTS.md (ETH Zurich, 2026年2月)**
https://arxiv.org/pdf/2602.11988

**主要な知見**:
- LLM生成のAGENTS.mdはタスク成功率を平均3%低下させる
- 人間が書いたAGENTS.mdは平均4%改善するが、推論コストは20%以上増加
- 不要な要件がタスクを難しくしている
- **結論**: 人間が書くAGENTS.mdは最小限の要件のみを記述すべき

### 3. 実践記事
**お前らが書いてるCLAUDE.md全部間違えてるから正解を言う**
https://note.com/kepoorz/n/n41f2654e3227

**核心的な主張**:
- AGENTS.mdは「説明書」ではなく「ルーティングテーブル」
- タスク3〜5個と簡単なディレクトリ構造だけ書く
- 詳細はスキル（`.claude/skills/`）に書く
- スキルは呼ばれたときだけ読み込まれる（20個あっても普段は2,000トークン、ベタ書きだと40,000トークン）
- **余白が大事**: AIは遊びが大きいほうが力を発揮する

---

## 設計の核心原則

### 1. AGENTS.mdは最小限（50行以内）

**書くべきもの**:
- タスクのエントリーポイント（3〜5個）
- 最小限のディレクトリ構造
- 絶対に守るべき制約（3つまで）

**書かないもの（スキルへ移動）**:
- 詳細な手順
- ツールの使い方
- コーディング規約
- テスト戦略

### 2. ハイブリッド開発フロー

**セッションベース（80%）**:
- 仕様が曖昧・探索的開発
- プランモード強制（いきなり実装しない）
- 計画承認後、Issue化 or セッション継続を選択

**Issue駆動（20%）**:
- 仕様が明確・定型作業
- Loopによる非同期実行（1日1〜2回）
- 人間不在でも進められる作業

### 3. 記録の棲み分け

| 記録の種類 | 配置場所 | 管理方法 | 更新頻度 |
|-----------|---------|---------|---------|
| **ADR** | `docs/adr/` | jj管理 | 必要時のみ（月1〜2個） |
| **実験ログ（雑メモ）** | `outputs/experiments_log.md` | jj管理外 | 毎日 |
| **実験サマリ** | `docs/experiments/YYYY-Wxx-summary.md` | jj管理 | 週次 |
| **週次報告** | GitHub Discussions | 自動（編集履歴） | 週1回 |
| **月次報告** | GitHub Discussions | 自動（編集履歴） | 月1回 |
| **Development Journal** | GitHub Discussions | 自動（編集履歴） | 随時 |

**重要な取り決め**: Discussionはエージェントから書き込まない（人間専用）

---

## ディレクトリ構造

```
project/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── feature.md
│   │   └── bug.md
│   └── workflows/
│       └── ci.yml
├── .claude/
│   └── skills/
│       ├── feature/SKILL.md
│       ├── refactor/SKILL.md
│       ├── issue/SKILL.md
│       ├── daily-sync/SKILL.md
│       └── common/
│           ├── uv-usage.md
│           ├── jj-workflow.md
│           ├── test-strategy.md
│           └── workflow.md
├── docs/
│   ├── adr/                          ← jj管理
│   │   ├── 0001-example.md
│   │   └── template.md
│   └── experiments/                   ← jj管理（週次サマリのみ）
│       ├── 2026-W10-summary.md
│       └── 2026-W11-summary.md
├── outputs/                           ← jj管理外
│   ├── multirun/                      ← TensorBoardログ等
│   └── experiments_log.md             ← 日々の実験メモ
├── src/
├── tests/
│   └── fixtures/
├── AGENTS.md
└── pyproject.toml

GitHub Discussions:
├── Weekly Reports
├── Monthly Reviews
└── Development Journal
```

---

## ADRの運用（厳格な基準）

### ADRを書くタイミング

**書くべき◯**:
- 複数の選択肢があり、トレードオフを検討して一つを選んだ
- プロジェクト全体に影響する技術選定
- 「なぜこうしたか」を6ヶ月後に思い出す必要がある

**書かない×**:
- 通常の機能実装
- バグ修正
- リファクタリング
- 一時的な判断・実験

### ADRの数の目安
- 初期（1ヶ月）: 5〜10個
- 成長期（2〜6ヶ月）: 月1〜2個
- 安定期（6ヶ月〜）: 四半期1〜2個

---

## 実験管理のフロー

### 日常（月〜木）
```
実験実行
  ↓
outputs/experiments_log.md に雑メモ（jj管理外）
  例: "exp001: alpha=0.1 → 82%（低い）"
```

### 週次定例（金曜日）
```
1. 人間: 週次報告をDiscussionに投稿
   - 今週の成果
   - 学んだこと
   - 来週の方針

2. AI（Loopまたはセッション）:
   - outputs/experiments_log.md を読む
   - docs/experiments/2026-Wxx-summary.md を作成（jj管理）
   - ADR化すべきものを提案

3. 人間: 確認・承認 → jjコミット
```

### 本番採用決定時
```
成功した実験を採用
  ↓
ADR作成（docs/adr/）
  - 決定内容
  - 理由
  - 実験ID（TensorBoardログへの参照）
  ↓
jjコミット
```

---

## Loopによる定期同期

**daily-sync/SKILL.mdの役割**（1日1〜2回実行）:

1. アサイン済みIssueの確認・処理
2. 週次報告Discussionの確認
3. Development Journalの確認（人間の状態把握）
4. 外部ツール同期（Asana・Google Drive等、MCP経由）
5. ADR/実験ログ更新判断
6. 進捗報告

**重要**: Loopはセッションを跨いだ継続性を実現するが、Discussionには書き込まない

---

## 外部ツール連携

### MCP Serverによる自動取得（推奨）

**推奨構成**:
- Asana MCP → タスク一覧取得
- Google Drive MCP → 月次報告スライド取得

**運用**:
- 人間が転記するのではなく、AIが自動取得
- ただし読み取り後「この理解で合ってますか？」と確認
- 齟齬があればDiscussionやIssueで報告

---

## TensorBoardログ・チェックポイントの扱い

### 管理方針

| 種類 | 配置 | jj管理 | 保持期間 |
|------|------|--------|---------|
| tfevents（TensorBoardログ） | `outputs/multirun/` | ❌ | 1ヶ月（ローカル） |
| checkpoint（モデルの重み） | `outputs/` | ❌ | 1ヶ月（ローカル） |
| 実験メモ | `outputs/experiments_log.md` | ❌ | 永続（ローカル） |
| 実験サマリ | `docs/experiments/` | ✅ | 永続 |
| 設定ファイル | `docs/experiments/` | ✅ | 永続 |
| 結果グラフ画像 | `docs/experiments/` | ✅ | 永続 |

**理由**:
- バイナリファイルは大容量（リポジトリ肥大化）
- 再現性は設定ファイルとコミットハッシュで担保
- 実験IDをADRに記載することで紐付け

---

## セッションベース開発のフロー（プランモード強制）

```
1. セッション開始
   ↓
2. 人間: タスク依頼
   ↓
3. AI: [プランモード] 計画を提示（実装しない）
   ↓
4. 人間: 承認 or 修正指示
   ↓
5. AI: 「Issue化して非同期実行？ or このまま実装？」
   ↓
   ├─ Issue化 → Issue起票してセッション終了
   │            （Loopが後で実装）
   └─ 実装 → そのまま実装開始
      ↓
6. 実装・テスト・jj操作
   ↓
7. セッション終了時: 自動でIssue化（記録）
```

---

## 実装の優先順位

### Phase 1: 基本構造（Week 1）
- AGENTS.md最小化（50行以内）
- スキル分離（`.claude/skills/common/`）
- `docs/adr/` 作成・テンプレート配置
- GitHub Discussions カテゴリ設定

### Phase 2: Loop運用開始（Week 2）
- `daily-sync/SKILL.md` 作成
- `/loop daily-sync` を1日1回実行
- 実際のIssueで試運用

### Phase 3: 外部ツール連携（Week 3）
- Asana MCP・Google Drive MCP設定
- daily-syncに外部ツール同期追加

### Phase 4: 週次・月次統合（Week 4以降）
- 週次報告ルーチン確立
- 実験ログの週次サマリ作成の定着

---

## 主要な設計判断の記録

### 1. AGENTS.mdの配置
- **決定**: 50行以内、詳細はスキルへ
- **理由**: コンテキスト節約（OpenAI・論文・記事の知見）

### 2. journalの配置
- **決定**: GitHub Discussions（ローカルファイルではない）
- **理由**: 非同期アクセス・検索性・バージョン管理の煩雑さ回避

### 3. ADRの配置
- **決定**: `docs/adr/` でjj管理
- **理由**: コードと同期してバージョン管理すべき、不変性

### 4. 実験ログの配置
- **決定**: 日々は `outputs/experiments_log.md`（jj管理外）、週次で `docs/experiments/` にサマリ（jj管理）
- **理由**: 五月雨式の実験を全部管理すると煩雑、成功例と知見のみ残す

### 5. TensorBoardログ
- **決定**: jj管理しない、実験IDで紐付け
- **理由**: バイナリで大容量、再現性は設定とコミットで担保

### 6. DiscussionとIssueの使い分け
- **決定**: Issueはタスク管理、Discussionは定例報告・Journal
- **理由**: エージェントからDiscussionに書き込まないことで棲み分け

### 7. ハイブリッド開発
- **決定**: セッション80%、Issue駆動20%
- **理由**: 速度と記録の両立

---

## 運用上の注意点

1. **最初から完璧を目指さない**: ミニマムから始めて育てる
2. **ADRは厳選**: 毎週増えているなら書きすぎ
3. **Loopの過信は禁物**: 曖昧なIssueは自動実装させない
4. **余白を保つ**: AIの探索力を最大化する
