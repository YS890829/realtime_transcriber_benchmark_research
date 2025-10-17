# Voice Memo Transcription & Summarization System

iPhoneボイスメモ・Google Drive・iCloud Driveからの音声を自動文字起こし＆要約する完全自動化システム

## 特徴

- **完全自動化**: Google Drive/iCloud Drive連携で音声アップロード→文字起こし→要約→Vector DB構築まで全自動
- **参加者管理**: Google Calendar統合で会議参加者を自動抽出・DB管理
- **高精度話者推論**: カレンダー情報とエンティティ抽出を組み合わせた高精度話者識別
- **RAG検索**: 複数ファイル横断のセマンティック検索とQ&Aシステム
- **ファイル管理**: スマートファイル名自動生成・重複検知・自動削除

## アーキテクチャ

### フォルダ構造

```
src/
├── transcription/          # 文字起こし（Gemini Audio API）
├── participants/           # 参加者管理・話者推論
├── topics/                 # トピック/エンティティ抽出
├── pipeline/               # Phase 11-3統合パイプライン
├── vector_db/              # Vector DB構築（Qdrant）
├── search/                 # RAG検索・semantic search
├── file_management/        # ファイル管理・削除・リネーム
├── monitoring/             # Webhook・iCloud監視
├── batch/                  # バッチ処理
└── shared/                 # 共通ユーティリティ
```

詳細は [docs/folder-structure.md](docs/folder-structure.md) を参照。

## 必要環境

- macOS 14 (Sonoma) 以降
- Python 3.10+
- Intel Mac または Apple Silicon Mac
- RAM 8GB以上
- Gemini API Key（無料枠で利用可能）

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

### 5. 環境変数設定

`.env`ファイルを作成:

```bash
cp .env.example .env
```

`.env`の内容:
```bash
# Gemini API
GEMINI_API_KEY_FREE=your_gemini_api_key_here

# Google OAuth (Calendar/Drive)
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here

# 機能フラグ
ENABLE_INTEGRATED_PIPELINE=true      # Phase 11-3統合パイプライン
ENABLE_VECTOR_DB=true                # Vector DB自動構築
ENABLE_ICLOUD_MONITORING=true        # iCloud Drive監視
AUTO_RENAME_FILES=true               # スマートファイル名自動生成

# パス設定
ICLOUD_DRIVE_PATH=~/Library/Mobile Documents/com~apple~CloudDocs
PROCESSED_FILES_REGISTRY=.processed_files_registry.jsonl
```

### 6. Google Calendar/Drive認証

初回のみ認証が必要：

```bash
python src/shared/calendar_integration.py
```

ブラウザが開き、Google認証が求められます。許可すると`token.json`が自動生成されます。

## 使い方

### オプション1: Google Drive自動監視（推奨）

```bash
# Webhook サーバー起動
python src/monitoring/webhook_server.py

# 別ターミナルでngrok起動
ngrok http 8000

# Webhook登録（ngrokのHTTPS URLを使用）
curl "http://localhost:8000/setup?webhook_url=<ngrok-https-url>"
```

**動作**:
1. Google Driveに音声ファイルをアップロード
2. Webhook経由で即座に検知（数秒以内）
3. 自動で文字起こし→Phase 11-3パイプライン→Vector DB構築
4. Google Driveファイルを自動削除

### オプション2: iCloud Drive自動監視

```bash
python src/monitoring/icloud_monitor.py
```

**動作**:
1. iCloud Driveに音声ファイルを保存
2. リアルタイム検知（watchdog）
3. SHA-256ハッシュで重複防止
4. 自動で文字起こし→Phase 11-3パイプライン→Vector DB構築

### オプション3: 手動実行

```bash
# 単一ファイルの文字起こし
python src/transcription/structured_transcribe.py path/to/audio.m4a
```

## 処理フロー（Phase 11-3統合パイプライン）

```
音声ファイル（.m4a）
  ↓
┌─────────────────────────────────────────┐
│ Phase 0: 文字起こし（Gemini Audio API）  │
└──────────────┬──────────────────────────┘
               ↓
*_structured.json（Gemini文字起こし結果）
               ↓
┌─────────────────────────────────────────┐
│ Phase 11-3: 統合パイプライン（10ステップ）│
├─────────────────────────────────────────┤
│ Step 1: JSON読み込み                     │
│ Step 2: カレンダーイベントマッチング       │
│ Step 3: 参加者抽出（LLM）                 │
│ Step 4: 参加者DB検索                      │
│ Step 5: トピック/エンティティ抽出（LLM）   │
│ Step 6: エンティティ解決                  │
│ Step 7: 話者推論（LLM、統合版）           │
│ Step 8: 要約生成（LLM、統合版）           │
│ Step 9: 参加者DB更新（UPSERT）            │
│ Step 10: 会議情報登録                     │
└──────────────┬──────────────────────────┘
               ↓
*_structured_enhanced.json + 参加者DB更新
               ↓
┌─────────────────────────────────────────┐
│ Phase 11-4: Vector DB構築（自動）        │
│ - Qdrant登録                             │
│ - セマンティック検索準備完了              │
└─────────────────────────────────────────┘
```

詳細は [docs/phase-11-3-architecture.md](docs/phase-11-3-architecture.md) を参照。

## 主要機能

### 1. 参加者データベース管理

Google Calendarイベントのdescriptionから参加者情報を自動抽出し、SQLiteデータベースで管理：

- **UPSERT対応**: 新規登録・既存参加者更新を自動判定
- **表示名マージ**: 「田中」「田中部長」「田中さん」を統合管理
- **会議参加履歴**: 参加者ごとの会議履歴を追跡

**データベース**:
- `participants.db` - 参加者情報（canonical_name, display_names, role, organization）
- `meetings` - 会議情報（title, date, summary, event_id）
- `participant_meetings` - 中間テーブル（多対多関係）

### 2. 高精度話者推論

カレンダー参加者情報 + エンティティ抽出を組み合わせた話者識別：

- **カレンダー情報**: 参加者一覧から候補を特定
- **エンティティ抽出**: 会話内で言及された人物を抽出
- **統合推論**: 両方の情報を組み合わせて高精度識別（85-95%）

### 3. セマンティック検索・RAG

複数ファイル横断のセマンティック検索とQ&Aシステム：

```bash
# セマンティック検索
python src/search/semantic_search.py

# RAG Q&A（インタラクティブモード）
python src/search/rag_qa.py --interactive
```

### 4. スマートファイル名自動生成

文字起こし内容から最適なファイル名を自動生成：

**変更前**:
```
downloads/temp_1a2b3c4d5e.m4a
```

**変更後**:
```
downloads/20251015_営業ミーティング_Q4戦略.m4a
```

### 5. 重複検知・自動削除

- **重複検知**: SHA-256ハッシュでGoogle Drive/iCloud Drive間の重複を防止
- **自動削除**: 文字起こし完了後、Google Driveファイルを自動削除（ストレージ節約）
- **削除ログ**: `.deletion_log.jsonl`に全削除イベントを記録

## 出力ファイル

```
downloads/
├── 20251015_営業ミーティング_Q4戦略.m4a                    # 音声ファイル
├── 20251015_営業ミーティング_Q4戦略_structured.json         # 文字起こし結果
└── 20251015_営業ミーティング_Q4戦略_structured_enhanced.json # Phase 11-3拡張版
```

### JSON出力例（Phase 11-3拡張版）

```json
{
  "metadata": {
    "file_name": "20251015_営業ミーティング_Q4戦略.m4a",
    "duration": 1800.0,
    "date": "20251015"
  },
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "会議を開始します",
      "speaker": "Speaker 0",
      "speaker_name": "田中"
    }
  ],
  "full_text": "会議を開始します...",
  "summary": {
    "overview": "Q4営業戦略の議論...",
    "key_points": ["..."],
    "action_items": ["..."]
  },
  "topics": [
    {
      "name": "Q4営業戦略",
      "summary": "...",
      "keywords": ["営業", "戦略", "Q4"]
    }
  ],
  "entities": {
    "people": ["田中", "佐藤"],
    "organizations": ["営業部", "企画部"],
    "canonical_names": {
      "田中": "田中太郎",
      "佐藤": "佐藤花子"
    }
  }
}
```

## パフォーマンス

### Phase 11-3パイプライン処理時間

| 処理 | 平均時間 | LLM使用 |
|-----|---------|---------|
| Step 2: カレンダーマッチング | 3-5秒 | - |
| Step 3: 参加者抽出 | 3-5秒 | Gemini Flash |
| Step 5: トピック/エンティティ抽出 | 5-8秒 | Gemini Pro |
| Step 7: 話者推論 | 6-10秒 | Gemini Flash |
| Step 8: 要約生成 | 6-10秒 | Gemini Pro |
| **Phase 11-3 合計** | **25-30秒** | **4回のLLM呼び出し** |

### Vector DB構築

| ファイル数 | 処理時間 |
|----------|---------|
| 1ファイル | 20-30秒 |
| 10ファイル | 3-5分 |

## ドキュメント

### 技術ドキュメント (`docs/`)

- [folder-structure.md](docs/folder-structure.md) - フォルダ構造の完全ガイド
- [phase-11-3-architecture.md](docs/phase-11-3-architecture.md) - Phase 11-3アーキテクチャ設計
- [phase-11-3-optimization.md](docs/phase-11-3-optimization.md) - Phase 11-3最適化詳細

### メモリーバンク (`memory-bank/`)

- `projectbrief.md` - プロジェクト概要
- `progress.md` - 全フェーズ進捗管理

## トラブルシューティング

### Google Calendar認証エラー

```bash
# token.jsonを削除して再認証
rm token.json
python src/shared/calendar_integration.py
```

### participants.db初期化

```bash
# データベース再作成
sqlite3 participants.db < src/participants/participants_db.sql
```

### Vector DB再構築

```bash
# 全ファイルからVector DB再構築
python src/vector_db/build_unified_vector_index.py downloads/*_enhanced.json
```

### iCloud Driveパスが見つからない

```bash
# iCloud Driveパス確認
ls ~/Library/Mobile\ Documents/com~apple~CloudDocs/
```

## テスト

```bash
# Phase 11-3パイプライン単体テスト
python src/pipeline/integrated_pipeline.py downloads/test_file_structured.json

# 統合テスト
python test_pipeline_integration.py
```

## 技術スタック

- **文字起こし**: Gemini 2.0 Flash Experimental（Audio API）
- **LLM**: Gemini 2.0 Flash / 2.5 Pro
- **Vector DB**: Qdrant（セマンティック検索）
- **データベース**: SQLite（参加者管理）
- **監視**: watchdog（iCloud Drive）, FastAPI（Google Drive Webhook）
- **Python 3.10+**: 関数ベース実装

## ライセンス

MIT License

## 今後の拡張候補

- [ ] Web UI（Gradio/Streamlit）
- [ ] 音声認識の話者分離統合（Pyannote）
- [ ] リアルタイム文字起こし（WebSocket）
- [ ] マルチモーダル対応（画面共有・スライド解析）
