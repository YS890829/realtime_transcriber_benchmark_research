# System Patterns (MVP)

## MVPアーキテクチャ（シンプル化）

```
┌─────────────────┐
│  iPhone 17      │
│  ボイスメモ App │
└────────┬────────┘
         │ iCloud Sync
         ↓
┌─────────────────────────────────────────────┐
│  Intel MacBook Pro                           │
│                                              │
│  ┌────────────────────────────────────┐    │
│  │  transcribe.py (単一スクリプト)     │    │
│  │                                     │    │
│  │  1. 新規ファイル検出                │    │
│  │     ↓                               │    │
│  │  2. faster-whisper 文字起こし        │    │
│  │     ↓                               │    │
│  │  3. Gemini API 要約                 │    │
│  │     ↓                               │    │
│  │  4. TXT + Markdown 保存             │    │
│  │     ↓                               │    │
│  │  5. .processed_files.txt 更新       │    │
│  └────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

**MVPで削除した複雑さ**:
- ❌ watchdog自動監視 → 手動実行
- ❌ Whisper API fallback → faster-whisperのみ
- ❌ Claude API → Gemini APIのみ
- ❌ Strategy Pattern → 単純な関数
- ❌ 複雑なエラーハンドリング → ログ出力のみ

## MVP実装（シンプルな関数構成）

### 1. ファイル検出（find_new_files）
**責務**: 新規ボイスメモファイルを検出

**実装**:
```python
def find_new_files():
    voice_memos_path = Path.home() / "Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings"

    # 処理済みリスト読み込み
    processed = set()
    if Path(".processed_files.txt").exists():
        processed = set(Path(".processed_files.txt").read_text().splitlines())

    # 新規ファイル検出
    all_files = list(voice_memos_path.glob("*.m4a"))
    new_files = [f for f in all_files if f.name not in processed]

    return new_files
```

**MVPで削除**:
- ❌ watchdog監視（手動実行で十分）
- ❌ メタデータ抽出（最小限）
- ❌ DB管理（テキストファイルで十分）

### 2. 文字起こし（transcribe_audio）
**責務**: faster-whisperで音声をテキスト化

**実装**:
```python
def transcribe_audio(audio_path):
    from faster_whisper import WhisperModel

    model = WhisperModel("medium", device="cpu")
    segments, info = model.transcribe(
        str(audio_path),
        language="ja",
        vad_filter=True
    )

    transcript = " ".join([seg.text for seg in segments])
    return transcript
```

**MVPで削除**:
- ❌ Whisper API fallback（faster-whisperのみ）
- ❌ Strategy Pattern（単純な関数）
- ❌ JSON出力（文字列のみ）
- ❌ セグメント情報（全文のみ）

### 3. 要約（summarize_text）
**責務**: Gemini APIでテキスト要約

**実装**:
```python
def summarize_text(transcript):
    import google.generativeai as genai
    import os

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""以下の文字起こしテキストを要約してください。

【要約形式】
1. エグゼクティブサマリー（2-3行）
2. 主要ポイント（箇条書き、3-5項目）
3. 詳細サマリー（段落形式）

【文字起こしテキスト】
{transcript}
"""

    response = model.generate_content(prompt)
    return response.text
```

**MVPで削除**:
- ❌ Claude API（Gemini APIのみ）
- ❌ Chain of Responsibility（単純な関数）
- ❌ 複数プロンプトテンプレート（1つのみ）

### 4. 保存（save_output）
**責務**: TXTとMarkdownで結果を保存

**実装**:
```python
def save_output(filename, transcript, summary):
    output_dir = Path.home() / "Documents/VoiceMemoTranscripts"
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = Path(filename).stem

    # TXT: 文字起こし全文
    txt_path = output_dir / f"{base_name}.txt"
    txt_path.write_text(transcript)

    # Markdown: 要約
    md_path = output_dir / f"{base_name}_summary.md"
    md_path.write_text(f"# {base_name}\n\n{summary}")

    return txt_path, md_path
```

**MVPで削除**:
- ❌ JSON出力（TXT + Markdownのみ）
- ❌ シンボリックリンク（不要）
- ❌ 日付別ディレクトリ（フラット構造）

## MVPデータフロー（シンプル化）

### 処理フロー
1. **検出**: 新規.m4aファイル検出（.processed_files.txtと比較）
2. **文字起こし**: faster-whisperで処理（60分→約4分）
3. **要約**: Gemini APIで要約生成（～10秒）
4. **保存**: TXT + Markdown保存
5. **記録**: .processed_files.txtに追記

### MVPエラーハンドリング（最小限）
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    transcript = transcribe_audio(audio_file)
    summary = summarize_text(transcript)
    save_output(audio_file.name, transcript, summary)

    # 処理済みリストに追加
    with open(".processed_files.txt", "a") as f:
        f.write(f"{audio_file.name}\n")

    logger.info(f"✅ 処理完了: {audio_file.name}")
except Exception as e:
    logger.error(f"❌ 処理失敗: {audio_file.name} - {e}")
```

**MVPで削除**:
- ❌ Whisper API fallback（エラーログのみ）
- ❌ リトライロジック（手動再実行）
- ❌ macOS通知（ログ出力のみ）

## 技術的決定事項

### 1. faster-whisper選択
**決定**: whisper.cppではなくfaster-whisperを採用

**理由**:
- Intel CPUでwhisper.cppより**5倍高速**（CTranslate2エンジン）
- セットアップが簡単（`pip install faster-whisper`のみ）
- デフォルト設定（量子化なし）で十分高速
- VADフィルタ内蔵で精度向上
- large-v3-turbo対応（より高速な最新モデル）

**量子化について**:
- 量子化なし（デフォルト）を推奨
- 理由: バグ修正が容易、デバッグしやすい、精度最高
- それでもwhisper.cppより圧倒的に高速

**比較**:
| 項目 | faster-whisper | whisper.cpp |
|------|----------------|-------------|
| Intel CPU速度 | ⚡⚡⚡⚡⚡ | ⚡ |
| セットアップ | pip install | ビルド必要 |
| 実装言語 | Python | C++ |
| デバッグ容易性 | ⭐⭐⭐⭐⭐ | ⭐⭐ |

**トレードオフ**:
- モデルファイルが大容量（medium: ~3GB, large-v3: ~6GB、量子化なし）
- 初回実行時にモデルダウンロードが必要

### 2. LLM要約にGemini API選択（MVPではGeminiのみ）
**決定**: Gemini APIのみ使用

**理由**:
- 無料枠（60リクエスト/日）で十分
- 日本語対応が良好
- セットアップが簡単

**MVPで削除**:
- ❌ Claude API fallback（Gemini APIのみ）

### 3. 手動実行（watchdog不使用）
**決定**: スクリプト手動実行

**理由**:
- MVPではシンプルさ優先
- `python transcribe.py`で実行
- 自動監視は将来拡張

**MVPで削除**:
- ❌ watchdog自動監視
- ❌ launchd/cron設定

### 4. テキストファイル管理（DB不使用）
**決定**: .processed_files.txtで処理済み管理

**理由**:
- MVPではファイル数が少ない
- grep/検索が容易
- シンプル

**MVPで削除**:
- ❌ SQLite/DB
- ❌ JSON管理ファイル

## MVPパフォーマンス（シンプル設定）

### faster-whisper設定（デフォルト）
```python
# MVP推奨: デフォルト設定（量子化なし）
model = WhisperModel("medium", device="cpu")
segments, info = model.transcribe(
    str(audio_path),
    language="ja",
    vad_filter=True  # 無音除去で高速化
)
```

**MVPで削除**:
- ❌ スレッド数調整（デフォルトで十分）
- ❌ バッチ処理最適化（単純なループ）

### メモリ使用量（量子化なし）
| モデル | メモリ | RAM推奨 |
|--------|--------|---------|
| medium | ~3GB | 8GB+ |

**注**: mediumモデル推奨（精度と速度のバランス）

### 処理時間目安（Intel Mac、mediumモデル）
| 音声長 | 処理時間 |
|--------|----------|
| 10分 | ~40秒 |
| 30分 | ~2分 |
| 60分 | ~4分 |

## セキュリティとプライバシー

### データ保護
- **ローカル処理優先**: 音声データは可能な限りローカルで処理
- **API通信暗号化**: HTTPS/TLS必須
- **APIキー管理**: 環境変数または暗号化された設定ファイル

### ファイルアクセス
- macOSセキュリティ許可が必要
- Full Disk Access権限（ボイスメモフォルダアクセス用）
