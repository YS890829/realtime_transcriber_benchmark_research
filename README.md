# Voice Memo Transcription & Summarization Tool (MVP)

iPhoneのボイスメモを文字起こし＆要約するシンプルなスクリプト

## 特徴

- **シンプル**: 単一スクリプト（310行）
- **高速**: faster-whisper（Intel CPUでwhisper.cppより5倍高速）
- **無料**: Gemini API無料枠（1日60リクエスト）
- **ローカル優先**: 音声処理はローカル、要約のみAPI
- **構造化データ**: Unstructured.ioスタイルのJSON出力

## 必要環境

- macOS 14 (Sonoma) 以降
- Python 3.10+
- Intel Mac または Apple Silicon Mac
- RAM 8GB以上
- ストレージ 3.5GB以上（モデルファイル含む）

## セットアップ

### 1. リポジトリクローン

```bash
cd ~/Desktop
git clone <repo-url>
cd realtime_transcriber_benchmark_research
```

### 2. Python仮想環境作成

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 依存関係インストール

```bash
pip install -r requirements.txt
```

### 4. FFmpegインストール

```bash
brew install ffmpeg
```

### 5. Gemini APIキー設定

1. [Google AI Studio](https://aistudio.google.com/)でAPIキーを取得
2. `.env`ファイルを作成

```bash
cp .env.example .env
# .envファイルを編集してAPIキーを設定
```

`.env`の内容:
```
GEMINI_API_KEY=your_actual_api_key_here
```

## 使い方

### 基本的な使い方

```bash
python transcribe.py
```

### 処理フロー

1. **新規ファイル検出**: `~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/`から新規.m4aファイルを検出
2. **文字起こし**: faster-whisper（mediumモデル）で文字起こし＋Unstructured風メタデータ付与
3. **要約生成**: Gemini APIで要約生成
4. **保存**: `~/Documents/VoiceMemoTranscripts/`にTXT + Markdown + JSON保存
5. **記録**: `.processed_files.txt`に処理済みファイル名を記録

### 出力ファイル

```
~/Documents/VoiceMemoTranscripts/
├── meeting_20251005.txt              # 文字起こし全文
├── meeting_20251005_summary.md       # 要約（Markdown）
└── meeting_20251005_structured.json  # Unstructured風構造化データ（NEW）
```

#### JSON出力例（Unstructured.ioスタイル）

```json
{
  "elements": [
    {
      "element_id": "a3b2c1d4...",
      "text": "会議を開始します",
      "type": "TranscriptSegment",
      "metadata": {
        "filename": "meeting.m4a",
        "segment_number": 1,
        "timestamp": {
          "start": 0.0,
          "end": 2.5,
          "duration": 2.5
        },
        "transcription": {
          "avg_logprob": -0.234,
          "no_speech_prob": 0.001,
          "model": "faster-whisper-medium",
          "vad_applied": true
        }
      }
    },
    {
      "element_id": "e5f6g7h8...",
      "text": "【要約内容】",
      "type": "Summary",
      "metadata": {
        "filename": "meeting.m4a",
        "generated_by": "gemini-1.5-flash",
        "generated_at": "2025-10-05T16:45:00"
      }
    }
  ],
  "metadata": {
    "filename": "meeting.m4a",
    "audio_info": {
      "language": "ja",
      "duration": 1800.0,
      "total_segments": 145
    },
    "element_types": {
      "TranscriptSegment": 145,
      "Summary": 1
    }
  }
}
```

## パフォーマンス

| 音声長 | 処理時間（目安） |
|--------|-----------------|
| 10分   | ~40秒          |
| 30分   | ~2分           |
| 60分   | ~4分           |

※ Intel MacBook Pro、mediumモデル使用時

## トラブルシューティング

### ボイスメモフォルダが見つからない

```bash
# macOSバージョン確認
sw_vers

# パス確認
ls ~/Library/Group\ Containers/group.com.apple.VoiceMemos.shared/Recordings/
```

macOS Sonoma以降であることを確認してください。

### Gemini APIエラー

```bash
# APIキー確認
cat .env
```

- APIキーが正しいか確認
- 1日60リクエスト制限を超えていないか確認

### メモリ不足

- mediumモデルは約3GB RAM使用
- 他のアプリを終了してメモリを確保

## ファイル構成

```
.
├── README.md                      # プロジェクト概要
├── requirements.txt               # 依存関係
├── .env.example                   # 環境変数テンプレート
├── structured_transcribe.py       # 音声文字起こし（Gemini Audio API）
├── infer_speakers.py              # 話者推論
├── summarize_with_context.py      # コンテキスト付き要約
├── generate_optimal_filename.py   # 最適ファイル名生成
├── run_full_pipeline.py           # 統合パイプライン
├── baseline_pipeline.py           # ベースラインパイプライン
├── llm_evaluate.py                # LLM評価
├── test_gemini_tier.py            # API Tierテスト
├── docs/                          # 技術ドキュメント
│   ├── pipeline-architecture.md   # パイプライン技術仕様
│   ├── validation-history.md      # 検証プロセス履歴
│   └── validation-results.md      # 話者識別精度実績
├── memory-bank/                   # プロジェクト進捗記録
│   ├── projectbrief.md            # プロジェクト概要
│   ├── progress.md                # 全フェーズ進捗管理
│   └── gemini-api-tier-management.md  # API切り替え管理
├── run_validation.py              # Phase 7統合検証スクリプト
├── evaluate_accuracy.py           # Phase 7精度評価スクリプト
├── create_small_sample.py         # Phase 7サンプル作成スクリプト
└── archive_phase1_local_whisper/  # 旧実装アーカイブ
```

## Unstructured.ioベンチマーク

このプロジェクトは[Unstructured.io](https://unstructured.io/)のメタデータ構造をベンチマークとして、音声文字起こし向けに最適化しています。

### 採用した設計

- **element_id**: SHA-256ハッシュ（テキスト+タイムスタンプ+ファイル名）
- **type**: `TranscriptSegment`, `Summary`
- **metadata構造**: タイムスタンプ、信頼度スコア、モデル情報
- **JSON出力**: Unstructured互換フォーマット

### 拡張可能性

- `Speaker`: 話者識別（将来拡張）
- `Topic`: トピック分類（将来拡張）
- `Sentiment`: 感情分析（将来拡張）

## 技術スタック

- **faster-whisper**: ローカル文字起こし（CTranslate2）
- **Google Gemini API**: 要約生成（gemini-1.5-flash）
- **Python 3.10+**: シンプルな関数ベース実装

## ライセンス

MIT License

## 開発者向け

### ドキュメント構成

#### 技術ドキュメント (`docs/`)
- `pipeline-architecture.md`: 統合パイプライン（話者推論→要約→ファイル名生成）の技術仕様
- `validation-history.md`: 精度改善検証プロセスの履歴
- `validation-results.md`: 話者識別精度95%達成の記録

#### メモリーバンク (`memory-bank/`)
- `projectbrief.md`: プロジェクト概要とMVP範囲
- `progress.md`: 全フェーズ（Phase 0-7）の進捗管理
- `gemini-api-tier-management.md`: 無料枠・有料枠API切り替え管理

### コントリビューション

1. Fork
2. Feature branch作成
3. Commit
4. Push
5. Pull Request

## 今後の拡張候補

MVPで不便を感じた場合のみ追加:

- [ ] watchdog自動監視
- [ ] モデルサイズ選択（medium/large）
- [ ] バッチ処理最適化
- [ ] Web UI
- [ ] Whisper API fallback
- [ ] Claude API対応
