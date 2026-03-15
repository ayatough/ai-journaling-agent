# uv の使い方

## 基本コマンド

```bash
uv sync                    # 依存関係をインストール
uv run pytest              # テスト実行
uv run ruff check src/     # lint
uv run ruff format src/    # フォーマット
uv run mypy src/           # 型チェック
uv add <package>           # 依存追加
uv add --dev <package>     # dev依存追加
```

## 注意

- `pip install` は使わない。必ず `uv` 経由
- `pyproject.toml` で依存管理
- `.venv/` はjj管理外（.gitignoreに含まれる）
