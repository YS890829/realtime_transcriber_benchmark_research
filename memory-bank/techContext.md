# Technical Context (Phase 3: 超シンプル版)

## 技術スタック

### Phase 3: 超シンプル版
| 技術 | バージョン | 用途 | 理由 |
|------|-----------|------|------|
| Python | 3.11+ | 実行環境 | 標準的な選択 |
| openai | 最新 | Whisper API | 公式SDKで簡単 |
| python-dotenv | 最新 | 環境変数管理 | APIキー管理 |

### Phase 4で追加予定
| 技術 | 用途 |
|------|------|
| google-generativeai | Gemini APIで要約 |

### Phase 5で追加予定
| 技術 | 用途 |
|------|------|
| なし | 標準ライブラリのみで実装 |

## アーキテクチャ

### Phase 3: 超シンプル版（50行）

```
transcribe_api.py
  ↓
  main()                    # CLI引数処理
    ↓
    transcribe_audio()      # OpenAI API呼び出し
    ↓
    save_text()             # テキスト保存
```

**特徴**:
- 一直線の処理フロー
- 関数3つのみ
- エラーハンドリング最小限

### Phase 4: 要約機能追加（+30行）

```
transcribe_api.py
  ↓
  main()
    ↓
    transcribe_audio()      # OpenAI API
    ↓
    summarize_text()        # Gemini API（新規）
    ↓
    save_text()             # TXT保存
    ↓
    save_markdown()         # Markdown保存（新規）
```

### Phase 5: 自動検出追加（+50行）

```
transcribe_api.py
  ↓
  main()
    ↓
    find_new_files()        # iCloud監視（新規）
    ↓
    for file in new_files:
        transcribe_audio()
        summarize_text()
        save_text()
        save_markdown()
        mark_as_processed() # 処理済み記録（新規）
```

## OpenAI Whisper API仕様

### エンドポイント
```
POST https://api.openai.com/v1/audio/transcriptions
```

### リクエスト（Phase 3実装）
```python
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

with open(audio_file_path, "rb") as audio_file:
    response = client.audio.transcriptions.create(
        model="whisper-1",      # 最新モデル
        file=audio_file,        # 音声ファイル
        language="ja"           # 日本語指定
    )

text = response.text  # 文字起こし結果
```

### レスポンス形式
```python
# デフォルト（text）
"これは文字起こし結果のテキストです。"
```

### サポートファイル形式
- `.m4a` (iPhoneボイスメモ)
- `.mp3`
- `.wav`
- `.mp4`
- `.mpeg`
- `.webm`

### 制約
- **ファイルサイズ**: 最大25MB
- **レート制限**: 60リクエスト/分（デフォルト）
- **価格**: $0.006/分

## Gemini API仕様（Phase 4で実装）

### エンドポイント
```python
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

response = model.generate_content(f"""
以下の文字起こしを要約してください:

{transcription}
""")

summary = response.text
```

### 価格
- **フリーティア**: 60リクエスト/日
- **有料**: $0.00025/1000文字（入力）

## ファイルシステム

### Phase 3: 手動指定
```bash
python transcribe_api.py "Test Recording.m4a"
```

### Phase 5: iCloud自動検出
```python
VOICE_MEMO_PATH = os.path.expanduser(
    "~/Library/Mobile Documents/com~apple~CloudDocs/Documents/VoiceMemoTranscripts"
)
```

## エラーハンドリング

### Phase 3: 最小限
```python
# ファイル存在チェックのみ
if not os.path.exists(audio_path):
    print(f"❌ エラー: ファイルが見つかりません")
    sys.exit(1)
```

### Phase 4: API エラー追加
```python
try:
    response = client.audio.transcriptions.create(...)
except Exception as e:
    print(f"❌ エラー: {e}")
    sys.exit(1)
```

## 環境変数

### Phase 3
```bash
OPENAI_API_KEY=sk-...
```

### Phase 4で追加
```bash
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

## コスト分析

### Phase 3: Whisperのみ
| 音声長 | Whisper API | 合計 |
|--------|------------|------|
| 10分 | $0.06 | **$0.06** |
| 60分 | $0.36 | **$0.36** |

### Phase 4: 要約追加
| 音声長 | Whisper API | Gemini API | 合計 |
|--------|------------|-----------|------|
| 10分 | $0.06 | $0 (無料枠) | **$0.06** |
| 60分 | $0.36 | $0 (無料枠) | **$0.36** |

## パフォーマンス

### Phase 3予測
| 音声長 | 処理時間（推定） | 実測 |
|--------|----------------|------|
| 10分 | 10秒 | 未テスト |
| 60分 | 1分 | 未テスト |

## セキュリティ

### APIキー管理
```python
# .envファイルに保存（Gitignore対象）
OPENAI_API_KEY=sk-...

# .env.exampleで共有
OPENAI_API_KEY=your_openai_api_key_here
```

### .gitignore
```
.env
__pycache__/
*.pyc
```

## 開発環境

### 必須
- Python 3.11以上
- pip
- インターネット接続

### 推奨
- venv（仮想環境）
- VSCode / PyCharm

## デプロイ

### Phase 3: ローカル実行のみ
```bash
# セットアップ
pip install -r requirements.txt

# 実行
python transcribe_api.py "audio.m4a"
```

### Phase 5: 自動実行（検討中）
- launchd（macOS）
- cron

## テスト戦略

### Phase 3
1. **10分音声**: 最初のテスト
2. **エラーケース**: ファイルなし
3. **日本語音声**: 精度確認

### Phase 4
1. **要約品質**: 長文でテスト
2. **Markdown出力**: フォーマット確認

### Phase 5
1. **自動検出**: iCloudフォルダ監視
2. **処理済み管理**: 重複処理防止

## ベストプラクティス

### Phase 3設計思想
1. **KISS原則**: Keep It Simple, Stupid
2. **段階的拡張**: Phase 3→4→5
3. **テスト駆動**: 動作確認してから次へ
4. **初学者優先**: 全コードが理解可能

### コーディング規約
- 関数は1つの責務のみ
- コメントで目的を明記
- エラーメッセージは日本語
- print文でデバッグ

## 技術的負債

### Phase 3で意図的に残す
- エラーリトライなし（手動再実行）
- ログファイルなし（標準出力のみ）
- 設定ファイルなし（ハードコード）

### Phase 4-5で対応予定
- 要約機能（Phase 4）
- 自動検出（Phase 5）

## 参考リソース

### 公式ドキュメント
- [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text)
- [Gemini API](https://ai.google.dev/docs) (Phase 4)

### Phase 1-2アーカイブ
- `archive_phase1_local_whisper/memory-bank/` - 旧実装の詳細

## 更新履歴

- **2025-10-07 12:00**: Phase 3版に刷新、超シンプル構成
