# jj (Jujutsu) ワークフロー

## 基本コマンド

```bash
jj status                  # 状態確認
jj diff                    # 差分表示
jj new                     # 新しい変更セットを作成
jj describe -m "message"   # 変更セットにメッセージを付与
jj log                     # 履歴表示
jj bookmark create <name>  # ブックマーク作成
jj git push                # リモートにプッシュ
```

## 注意

- `git` コマンドは直接使わない。`jj` 経由で操作する
- `jj new` で作業を始め、`jj describe` で完了を記録
- outputs/ はjj管理外（.gitignoreで除外済み）
