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

## Phase 8: 統合パイプライン（2025-10-14完了）

Phase 8では、パイプライン最適化、話者推論精度向上、エンティティ統一、統合Vector DBを実装しました。

### パイプライン処理順序

**最適化後のパイプライン:**

```
1. structured_transcribe.py
   ↓ _structured.json（音声文字起こし）

2. infer_speakers.py
   ↓ _structured_with_speakers.json（話者推論）

3. add_topics_entities.py
   ↓ _enhanced.json（トピック・エンティティ抽出）

4. entity_resolution_llm.py
   ↓ _enhanced.json更新（エンティティ名寄せ + canonical_name付与）

5. build_unified_vector_index.py
   ↓ ChromaDB: transcripts_unified（統合Vector DB構築）

6. semantic_search.py / rag_qa.py
   → 5ファイル横断検索（1クエリ）
```

### 主な改善内容

#### 1. 話者推論精度向上
- 杉本さんのプロフィールを職務経歴書ベースに更新
- 経歴・声質・思考性を反映（営業+エンジニア、起業目標、アメリカ転職目標）
- 判定根拠の明確化

#### 2. エンティティ統一管理
- canonical_name（正規化名）とentity_id付与
- 全5ファイル横断で統一されたID管理
- 例: "マチックモーメンツ" + "マジックモーメント" → "Magic Moment" (entity_id: org_002)

#### 3. 統合Vector DB
- 6,551セグメント（5ファイル）を1つのコレクション"transcripts_unified"に統合
- 横断検索クエリ数: 5回 → 1回（80%削減）
- メタデータにsource_file追加（クロスファイル追跡）
- エンティティ統一による検索精度向上

#### 4. Vector DB & RAGスクリプト

```
├── build_vector_index.py              # 個別ファイルVector DB構築（旧版）
├── build_unified_vector_index.py      # 統合Vector DB構築（Phase 8）
├── semantic_search.py                 # セマンティック検索
├── rag_qa.py                          # RAG Q&Aシステム
├── add_topics_entities.py             # トピック・エンティティ抽出
└── entity_resolution_llm.py           # エンティティ名寄せ
```

### テスト結果

```
✅ Test 1 PASSED: Speaker Inference (5ファイル話者特定)
✅ Test 2 PASSED: Entity Unification (19人物、41組織統一)
✅ Test 3 PASSED: Cross-File Search (横断検索成功)
✅ Test 4 PASSED: RAG Q&A System (4/4クエリ成功)
```

### 使い方

```bash
# 統合Vector DB構築
python build_unified_vector_index.py

# セマンティック検索
python semantic_search.py transcripts_unified

# RAG Q&A（インタラクティブモード）
python rag_qa.py transcripts_unified --interactive

# Phase 8総合テスト
python test_phase8_comprehensive.py
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

## Google Drive連携（Phase 5復元版）

Google Driveのマイドライブ（ルート）に音声ファイルをアップロードすると自動で文字起こしを実行します。

### セットアップ

#### 1. Google Cloud Console設定

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成
3. Google Drive APIを有効化
4. OAuth 2.0クライアントIDを作成（デスクトップアプリ）
5. `credentials.json`をダウンロードし、プロジェクトルートに配置

#### 2. 初回認証

```bash
# drive_download.pyで初回認証（token.json生成）
python drive_download.py <file_id>
```

初回実行時にブラウザが開き、Google認証が求められます。許可すると`token.json`が自動生成されます。

### 使い方

#### オプション1: ポーリング方式（5分間隔）

```bash
# マイドライブのルートを5分間隔で監視
python monitor_drive.py
```

**動作:**
- マイドライブのルートに音声ファイル（.m4a, .mp3, .wav）をアップロード
- 5分以内に自動検知
- `structured_transcribe.py`で文字起こし（Gemini Audio API）
- `*_structured.json`ファイルを生成

**監視対象:**
- マイドライブのルート（`root`）
- 音声ファイルのみ（MIME type: audio/*, 拡張子: .m4a, .mp3, .wav）

**処理済み管理:**
- `.processed_drive_files.txt`に処理済みファイルIDを記録
- 同じファイルを二重処理しない

#### オプション2: Webhook方式（リアルタイム検知）

```bash
# 1. FastAPIサーバー起動
python webhook_server.py

# 2. 別ターミナルでngrok起動
ngrok http 8000

# 3. Webhook登録
curl "http://localhost:8000/setup?webhook_url=<ngrok-https-url>"
```

**動作:**
- ファイルアップロード後、数秒以内に検知（Push通知）
- ngrok経由でローカルにWebhook通知を受信
- 自動で文字起こし実行

**注意事項:**
- ngrok無料版は2時間セッション制限あり
- URL再起動ごとに変更（webhook再登録必要）
- Webhook有効期限: 24時間

### トラブルシューティング

#### `credentials.json not found`
- Google Cloud ConsoleでOAuth 2.0クライアントIDを作成
- ダウンロードした`credentials.json`をプロジェクトルートに配置

#### `Invalid credentials`
- `drive_download.py`で初回認証を実行
- `token.json`が生成されることを確認

#### ファイルが検知されない
- マイドライブの**ルート**にファイルをアップロードしているか確認
- 音声ファイル形式（.m4a, .mp3, .wav）か確認
- `.processed_drive_files.txt`に既にファイルIDが記録されていないか確認

## Phase 10-1: 自動ファイル名変更機能（NEW）

文字起こし内容に基づき、Gemini APIで最適なファイル名を自動生成します。

### 機能概要

- **自動ファイル名生成**: 要約・全文から会話のトピックを抽出
- **日本語対応**: macOS/Windows互換の日本語ファイル名
- **日付付与**: YYYYMMDD形式で日付を自動追加
- **一括リネーム**: 音声ファイル + JSON等の関連ファイルを同時にリネーム
- **Google Drive同期**: ローカル＋クラウド両方でリネーム

### セットアップ

```bash
# .env に以下を追加
GEMINI_API_KEY_FREE=your_api_key_here
AUTO_RENAME_FILES=true  # true で有効化
```

### リネーム例

**変更前**:
```
downloads/temp_1a2b3c4d5e.m4a
downloads/temp_1a2b3c4d5e_structured.json
```

**変更後**:
```
downloads/20251015_営業ミーティング_Q4戦略.m4a
downloads/20251015_営業ミーティング_Q4戦略_structured.json
```

Google Drive上のファイル名も同じ名前に変更されます。

### スタンドアロン使用

既存の音声ファイルを手動でリネームする場合:

```bash
python generate_smart_filename.py downloads/your_file.m4a
```

**前提条件**: `your_file_structured.json` が既に存在すること

### 環境変数

| 変数 | デフォルト | 説明 |
|------|----------|------|
| `AUTO_RENAME_FILES` | `false` | `true`で自動リネーム有効化 |
| `GEMINI_API_KEY_FREE` | - | Gemini API無料枠キー（必須） |

### 注意事項

- ファイル名は20-30文字に制限されます
- 特殊文字（`/\:*?"<>|`）は自動除去されます
- 同名ファイルが存在する場合はタイムスタンプが追加されます
- リネーム失敗時も文字起こし結果は保存されます

## Phase 10-2: クラウドファイル自動削除機能（NEW）

文字起こし完了後、Google Driveの音声ファイルを自動削除してストレージを節約します。

### 機能概要

- **自動削除**: 文字起こし完了後、Google Driveファイルを自動削除
- **安全検証**: 5項目のJSON完全性チェックで誤削除を防止
- **ローカル保持**: ローカルファイルは削除せず保持
- **削除ログ**: 全削除イベントを`.deletion_log.jsonl`に記録
- **非致命的エラー**: 削除失敗時も処理は続行

### 削除前検証（5項目）

削除前に以下をチェックし、全て合格した場合のみ削除実行：

1. ✅ JSONファイルが存在する
2. ✅ ファイルサイズ > 0バイト
3. ✅ JSONがパース可能
4. ✅ `segments`配列が存在し、要素数 > 0
5. ✅ `full_text`フィールドが存在し、長さ > 10文字
6. ✅ `metadata`フィールドが存在

### 処理フロー

```
1. Google Driveファイル検知
2. ダウンロード
3. 文字起こし（Gemini Audio API）
4. ローカルファイルリネーム（Gemini 2.0 Flash）
5. JSON検証（5項目チェック）
   ✅ 検証合格 → Google Driveファイル削除 + ログ記録
   ❌ 検証失敗 → Google Driveファイル保持 + エラーログ記録
```

### 削除ログ形式

`.deletion_log.jsonl`（JSONL形式、1行=1イベント）:

```json
{
  "timestamp": "2025-10-15T07:31:46+00:00",
  "file_id": "1K5RZwauhMSb_jHdhkYaIPsA-6WbkQA41",
  "file_name": "Kitaya 1-Chōme 4.m4a",
  "json_path": "downloads/20251015_まなちゃん発話速度の指摘と前向きな受容_structured.json",
  "validation_passed": true,
  "validation_details": {
    "segments_count": 33,
    "full_text_length": 530,
    "file_size_bytes": 9538
  },
  "deleted": true,
  "error": null
}
```

### 環境変数

| 変数 | デフォルト | 説明 |
|------|----------|------|
| `DELETION_LOG_FILE` | `.deletion_log.jsonl` | 削除ログファイルのパス |

### スタンドアロンテスト

既存のJSONファイルの検証テスト:

```bash
python cloud_file_manager.py downloads/your_file_structured.json
```

**出力例**:
```
✅ Validation PASSED
{
  "file_exists": true,
  "segments_count": 33,
  "full_text_length": 530,
  ...
}
```

### 注意事項

- **常に削除**: 文字起こし完了後は常にGoogle Driveファイルを削除します
- **ローカル保持**: ローカルファイル（音声+JSON）は削除されません
- **検証失敗時**: JSON検証が失敗した場合、安全のため削除しません
- **復元**: 削除後の復元は不可（ログから削除履歴のみ確認可能）
- **Google Drive権限**: `drive`スコープ（全ファイルアクセス）が必要

### Phase 10-1との連携

Phase 10-1（自動リネーム）とPhase 10-2（自動削除）は同時に動作します：

1. 文字起こし完了
2. **Phase 10-1**: ローカルファイルをリネーム（Google Driveはリネームしない）
3. **Phase 10-2**: JSON検証後、Google Driveファイルを削除

**理由**: どうせ削除するので、Google Drive上のファイル名変更は不要

## Phase 10-3: iCloud Drive統合（NEW）

iCloud Driveへの音声ファイル保存を自動検知し、Google Driveとの重複を防止して文字起こしします。

### 機能概要

- **リアルタイム検知**: watchdogライブラリでiCloud Driveを監視（ポーリング不要）
- **重複防止**: SHA-256ハッシュで同一ファイルを検知し、二重処理を防止
- **統合レジストリ**: Google Drive + iCloud Driveの処理履歴を一元管理
- **ファイル安定待機**: iCloud同期完了を確認してから処理開始
- **file_id ↔ ファイル名マッピング**: Phase 10-1でリネーム後も追跡可能

### セットアップ

#### 1. watchdogパッケージインストール

```bash
pip install -r requirements.txt  # watchdog>=4.0.0が含まれます
```

#### 2. 環境変数設定

`.env`に以下を追加:

```bash
# Phase 10-3: iCloud Drive統合
ENABLE_ICLOUD_MONITORING=true
ICLOUD_DRIVE_PATH=~/Library/Mobile Documents/com~apple~CloudDocs
PROCESSED_FILES_REGISTRY=.processed_files_registry.jsonl
```

### 使い方

#### iCloud監視モード起動

```bash
python icloud_monitor.py
```

**出力例**:
```
============================================================
🚀 iCloud Drive Monitor Started (Phase 10-3)
============================================================
📁 Monitoring path: /Users/test/Library/Mobile Documents/com~apple~CloudDocs
🎵 Audio extensions: .m4a, .mp3, .wav, .aac, .flac, .ogg
⏱️  File stability wait: 5s
📊 Registry stats: {'total': 5, 'google_drive': 3, 'icloud_drive': 2}
============================================================
Press Ctrl+C to stop monitoring

✅ Monitoring active...
```

#### 動作フロー

1. iCloud Driveに音声ファイルを保存
2. watchdogが即座に検知（FSEvents）
3. ファイルサイズが安定するまで待機（iCloud同期完了確認）
4. SHA-256ハッシュを計算
5. 統合レジストリで重複チェック
   - **重複なし** → 文字起こし実行 → レジストリ登録
   - **重複あり** → スキップ（Google Driveで処理済み）
6. Phase 10-1でリネーム → レジストリ更新

### 重複検知の仕組み

**シナリオ**: iCloud同期が遅いため、手動でGoogle Driveにアップロードした場合

```
1. [13:00] Google Driveに手動アップロード
   → 文字起こし実行
   → ハッシュ "a1b2c3..." をレジストリ登録

2. [13:30] 同じファイルがiCloud Driveに同期
   → ハッシュ計算 → "a1b2c3..."
   → レジストリで重複検知
   → スキップ（二重処理防止）
```

### 統合レジストリ形式

`.processed_files_registry.jsonl`（JSONL形式、1行=1エントリ）:

```jsonl
{"source":"google_drive","file_id":"16BNBa773...","hash":"a1b2c3d4...","original_name":"recording.m4a","renamed_to":"20251015_会議.m4a","local_path":"downloads/20251015_会議.m4a","processed_at":"2025-10-15T16:30:00Z"}
{"source":"icloud_drive","file_id":null,"hash":"e5f6g7h8...","original_name":"memo.m4a","renamed_to":"20251015_メモ.m4a","local_path":"~/Library/Mobile Documents/.../memo.m4a","processed_at":"2025-10-15T16:35:00Z"}
```

### スタンドアロンテスト

既存の音声ファイルのハッシュ計算と重複チェック:

```bash
python unified_registry.py path/to/your_file.m4a
```

**出力例**:
```
Calculating hash for: your_file.m4a
  Hash: a1b2c3d4e5f6g7h8...

✅ Already processed:
  Source: google_drive
  Original: recording.m4a
  Renamed: 20251015_会議.m4a
  Processed at: 2025-10-15T16:30:00Z

Registry stats:
  Total: 10
  Google Drive: 6
  iCloud Drive: 4
```

### 環境変数

| 変数 | デフォルト | 説明 |
|------|----------|------|
| `ENABLE_ICLOUD_MONITORING` | `false` | `true`でiCloud監視を有効化 |
| `ICLOUD_DRIVE_PATH` | `~/Library/Mobile Documents/com~apple~CloudDocs` | iCloud Driveのパス |
| `PROCESSED_FILES_REGISTRY` | `.processed_files_registry.jsonl` | 統合レジストリのパス |

### Google Drive Webhookとの併用

**推奨運用方法**:

1. **iCloud Driveをメイン**: `icloud_monitor.py`を常時起動
2. **Google Driveはバックアップ**: iCloud同期が遅い時のみ手動アップロード

**併用時の動作**:

```bash
# ターミナル1: Google Drive Webhook
python webhook_server.py

# ターミナル2: iCloud監視
python icloud_monitor.py
```

同一ファイルが両方に存在しても、ハッシュベースの重複検知により**1回だけ**処理されます。

### トラブルシューティング

#### iCloud Driveパスが見つからない

```bash
# iCloud Driveのパス確認
ls ~/Library/Mobile\ Documents/com~apple~CloudDocs/
```

- iCloud Driveが有効化されているか確認
- macOS設定でiCloud Driveの同期が有効か確認

#### ファイルが検知されない

- `ENABLE_ICLOUD_MONITORING=true`に設定されているか確認
- 監視対象の拡張子か確認（.m4a, .mp3, .wav, .aac, .flac, .ogg）
- `.processed_files_registry.jsonl`に既にハッシュが記録されていないか確認

#### 重複検知が動作しない

```bash
# レジストリの内容確認
cat .processed_files_registry.jsonl | grep "hash"
```

- ハッシュが正しく計算されているか確認
- ファイル内容が完全に同一か確認（1バイトでも違えば別ファイル）

### Phase 10-1/10-2との連携

Phase 10-3は既存のPhase 10-1（自動リネーム）とPhase 10-2（自動削除）と完全統合されています：

1. **iCloud Driveファイル検知** → Phase 10-3
2. **文字起こし実行** → `structured_transcribe.py`
3. **ローカルファイルリネーム** → Phase 10-1
4. **レジストリ更新**（リネーム後のファイル名） → Phase 10-3
5. （Google Driveファイルの場合のみ）**クラウドファイル削除** → Phase 10-2

### 注意事項

- **ファイル安定待機**: iCloud同期中のファイルは最大5分待機します
- **ハッシュ計算**: 大容量ファイル（>1GB）は数秒かかる場合があります
- **レジストリは削除不可**: `.gitignore`でGit管理外ですが、手動削除は非推奨
- **macOS専用**: watchdogはクロスプラットフォームですが、iCloud DriveパスはmacOS専用

## 今後の拡張候補

MVPで不便を感じた場合のみ追加:

- [ ] watchdog自動監視
- [ ] モデルサイズ選択（medium/large）
- [ ] バッチ処理最適化
- [ ] Web UI
- [ ] Whisper API fallback
- [ ] Claude API対応
