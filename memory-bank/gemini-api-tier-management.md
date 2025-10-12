# Gemini API Tier管理機能

**実装日**: 2025-10-13
**目的**: 無料枠と有料枠のGemini APIキーを柔軟に切り替え可能にする

---

## 📋 実装概要

### 背景

Gemini APIには無料枠（5 RPM / 25 RPD制限）と有料枠（より高いレート制限）があり、開発時には有料枠を使いたいが、通常時はコスト削減のため無料枠を使いたいという要件があった。

### 解決策

`.env`ファイルに両方のAPIキーを保存し、環境変数`USE_PAID_TIER`のコメントアウトで簡単に切り替えられる仕組みを実装。

---

## 🔧 実装内容

### 変更ファイル（9ファイル）

1. **`.env`** - APIキー設定
   - `GEMINI_API_KEY_FREE`: 無料枠用APIキー
   - `GEMINI_API_KEY_PAID`: 有料枠用APIキー
   - `USE_PAID_TIER`: 切り替えフラグ（デフォルト: コメントアウト）

2. **`.env.example`** - サンプル更新
   - 新しい環境変数の説明
   - 使い方のコメント

3-9. **Pythonスクリプト（7ファイル）** - APIキー選択ロジック追加
   - `structured_transcribe.py`
   - `infer_speakers.py`
   - `summarize_with_context.py`
   - `generate_optimal_filename.py`
   - `llm_evaluate.py`
   - `baseline_pipeline.py`
   - `test_gemini_tier.py`

### APIキー選択ロジック（全ファイル共通）

```python
# Gemini API Key選択（デフォルト: 無料枠）
USE_PAID_TIER = os.getenv("USE_PAID_TIER", "false").lower() == "true"
if USE_PAID_TIER:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_PAID")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY_PAID not set but USE_PAID_TIER=true")
    print("ℹ️  Using PAID tier API key")
else:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_FREE")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY_FREE not set")
    print("ℹ️  Using FREE tier API key")

genai.configure(api_key=GEMINI_API_KEY)
```

---

## 📖 使い方

### 通常時（無料枠）- デフォルト

```bash
# .envファイル
# USE_PAID_TIER=true  ← コメントアウト状態

# スクリプト実行
python structured_transcribe.py audio.mp3
# 出力: ℹ️  Using FREE tier API key
```

### 開発時など（有料枠）

```bash
# .envファイルを編集
USE_PAID_TIER=true  ← コメントを外す

# スクリプト実行
python structured_transcribe.py audio.mp3
# 出力: ℹ️  Using PAID tier API key
```

---

## ✅ テスト結果

### 無料枠テスト

```
============================================================
Gemini API Tier テスト (FREE tier)
============================================================

📊 6回のリクエストを連続送信中...
  ⚠️  リクエスト 1/6 レート制限エラー
  ⚠️  リクエスト 2/6 レート制限エラー
  ...

判定: 無料枠の可能性が高い
→ レート制限エラーが発生（5 RPM制限）
```

**結果**: ✅ 無料枠として正常動作（レート制限を正しく検出）

### 有料枠テスト

```
============================================================
Gemini API Tier テスト (PAID tier)
============================================================

📊 6回のリクエストを連続送信中...
  ✅ リクエスト 1/6 成功 (経過時間: 0.7秒)
  ✅ リクエスト 2/6 成功 (経過時間: 2.2秒)
  ...
  ✅ リクエスト 6/6 成功 (経過時間: 8.0秒)

成功: 6/6
エラー: 0/6
総実行時間: 8.0秒

判定: 有料枠の可能性が高い
→ 短時間（1分未満）で6回のリクエストが全て成功
```

**結果**: ✅ 有料枠として正常動作（全リクエスト成功）

---

## 📊 無料枠 vs 有料枠の比較

| 項目 | 無料枠（FREE） | 有料枠（PAID） |
|------|---------------|---------------|
| **レート制限** | 5 RPM / 25 RPD | より高い制限 |
| **コスト** | $0 | 従量課金 |
| **用途** | 通常の運用 | 開発・テスト時 |
| **6回連続リクエスト** | 全てエラー | 全て成功（8秒） |
| **Google Cloud Billing** | 不要 | 必要 |

---

## 🔒 セキュリティ

- 両方のAPIキーを`.env`ファイルに保存
- `.gitignore`で除外されているため安全
- コード内にAPIキーをハードコードしない
- 環境変数で管理

---

## 💡 運用方針

1. **デフォルトは無料枠を使用**
   - 通常の運用ではコストゼロ
   - 日常的な文字起こし処理に十分

2. **必要時のみ有料枠に切り替え**
   - 開発時（高速なイテレーション）
   - 大量の音声ファイル処理
   - レート制限が問題になる場合

3. **切り替えは簡単**
   - `.env`ファイルの1行のコメントアウトを外すだけ
   - スクリプト実行時にTierが表示される

---

## 🎯 今後の拡張

### オプション案

1. **コマンドライン引数での切り替え**
   ```bash
   python structured_transcribe.py audio.mp3 --paid-tier
   ```

2. **自動切り替え**
   - レート制限エラー発生時に自動的に有料枠にフォールバック
   - 日次リクエスト数を監視して自動切り替え

3. **使用量トラッキング**
   - 無料枠・有料枠それぞれの使用量を記録
   - 月次レポート生成

---

## 📝 関連ファイル

- `.env` - APIキー設定
- `.env.example` - 設定サンプル
- `test_gemini_tier.py` - Tierテストスクリプト
- 全7つのPythonスクリプト - APIキー選択ロジック実装

---

## 📚 参考情報

### Gemini API無料枠・有料枠の違い

- **無料枠**: Google AI Studio（ai.google.dev）で取得、Google Cloud Billing不要
- **有料枠**: Google Cloud Consoleで課金設定を有効化
- **APIキー**: 同じキーを無料枠・有料枠で使用可能（プロジェクトの課金設定で決まる）

### 実装完了日

**2025-10-13**: Gemini API無料枠・有料枠切り替え機能実装完了
