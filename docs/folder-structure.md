# フォルダ構造ガイド

**最終更新**: 2025-10-17
**対応バージョン**: Phase 11-3最適化版

## 概要

このドキュメントは、リアルタイム文字起こしシステムの現在のフォルダ構造と、各フォルダの役割を説明します。

## プロジェクト構造

```
realtime_transcriber_benchmark_research/
├── src/                        # ソースコード
│   ├── transcription/         # 文字起こし（Phase 0）
│   ├── participants/          # 参加者管理（Phase 11-3 Steps 3-4）
│   ├── topics/                # トピック/エンティティ（Phase 11-3 Steps 5-6）
│   ├── pipeline/              # 統合パイプライン（Phase 11-3全体）
│   ├── vector_db/             # Vector DB構築（Phase 11-4）
│   ├── search/                # RAG検索・semantic search
│   ├── file_management/       # ファイル管理・削除・リネーム
│   ├── monitoring/            # Webhook・iCloud監視
│   ├── batch/                 # バッチ処理
│   └── shared/                # 共通ユーティリティ
│
├── docs/                      # ドキュメント
├── downloads/                 # 処理済みファイル
├── data/                      # データベース
├── tools/                     # ユーティリティスクリプト
└── tests/                     # テスト
```

## srcフォルダ詳細

### 1. transcription/ - 文字起こし

**役割**: Whisper APIを使用した音声文字起こし

**主要ファイル**:
- `structured_transcribe.py`: メイン文字起こしスクリプト
  - Whisper API呼び出し
  - 構造化JSON生成
  - Phase 11-3/11-4パイプライン起動

**Phase**: Phase 0（前処理）

**インポートパス例**:
```python
from src.transcription.structured_transcribe import main
```

---

### 2. participants/ - 参加者管理

**役割**: カレンダー参加者の抽出・DB管理・話者推論

**主要ファイル**:
- `participants_db.py`: 参加者データベース管理（SQLite）
- `extract_participants.py`: カレンダーから参加者抽出（LLM使用）
- `enhanced_speaker_inference.py`: 話者推論（カレンダー+エンティティ統合版）

**Phase**: Phase 11-3 Steps 3-4, 7

**インポートパス例**:
```python
from src.participants.participants_db import ParticipantsDB
from src.participants.extract_participants import extract_participants_from_description
from src.participants.enhanced_speaker_inference import infer_speakers_with_participants
```

---

### 3. topics/ - トピック/エンティティ

**役割**: トピック抽出、エンティティ抽出・解決

**主要ファイル**:
- `add_topics_entities.py`: トピック・エンティティ抽出（Gemini 2.5 Pro使用）
- `entity_resolution_llm.py`: エンティティ名寄せ（LLMベース）

**Phase**: Phase 11-3 Steps 5-6

**インポートパス例**:
```python
from src.topics.add_topics_entities import extract_topics_and_entities
from src.topics.entity_resolution_llm import EntityResolver
```

---

### 4. pipeline/ - 統合パイプライン

**役割**: Phase 11-3の10ステップ統合実行

**主要ファイル**:
- `integrated_pipeline.py`: Phase 11-3メインパイプライン
  - Step 1: JSON読み込み
  - Step 2: カレンダーマッチング
  - Step 3: 参加者抽出
  - Step 4: 参加者DB検索
  - Step 5: トピック/エンティティ抽出
  - Step 6: エンティティ解決
  - Step 7: 話者推論（エンティティ統合）
  - Step 8: 要約生成
  - Step 9: 参加者DB更新
  - Step 10: 会議情報登録

**Phase**: Phase 11-3（全体統合）

**インポートパス例**:
```python
from src.pipeline.integrated_pipeline import run_phase_11_3_pipeline
```

---

### 5. vector_db/ - Vector DB構築

**役割**: Qdrant Vector DBへのドキュメント登録

**主要ファイル**:
- `build_unified_vector_index.py`: Vector DB構築メインスクリプト
  - enhanced JSON読み込み
  - ベクトル化（text-embedding-004）
  - Qdrant登録

**Phase**: Phase 11-4

**インポートパス例**:
```python
from src.vector_db.build_unified_vector_index import main as build_vector_db
```

---

### 6. search/ - 検索機能

**役割**: RAG検索・semantic search

**主要ファイル**:
- `rag_qa.py`: RAG Q&A（Vector DB + LLM）
- `semantic_search.py`: セマンティック検索

**Phase**: 検索・取得フェーズ

**インポートパス例**:
```python
from src.search.rag_qa import answer_question
from src.search.semantic_search import semantic_search
```

---

### 7. file_management/ - ファイル管理

**役割**: ファイル削除・リネーム・レジストリ管理

**主要ファイル**:
- `cloud_file_manager.py`: Google Driveファイル削除
- `generate_smart_filename.py`: AI生成ファイル名（Gemini使用）
- `unified_registry.py`: 処理済みファイルレジストリ

**Phase**: 後処理フェーズ

**インポートパス例**:
```python
from src.file_management.cloud_file_manager import delete_gdrive_file
from src.file_management.generate_smart_filename import generate_filename_from_transcription
from src.file_management.unified_registry import is_processed
```

---

### 8. monitoring/ - 監視

**役割**: Webhook・iCloud監視による自動処理トリガー

**主要ファイル**:
- `webhook_server.py`: Google Drive Webhook受信サーバー
- `icloud_monitor.py`: iCloud音声ファイル監視

**Phase**: 自動化フェーズ

**インポートパス例**:
```python
from src.monitoring.webhook_server import app
from src.monitoring.icloud_monitor import AudioFileHandler
```

---

### 9. batch/ - バッチ処理

**役割**: 複数ファイルの一括処理

**主要ファイル**:
- `run_phase_2_6_batch.py`: Phase 2-6一括実行（レガシー）

**Phase**: バッチ処理

---

### 10. shared/ - 共通ユーティリティ

**役割**: 複数モジュールで共有される機能

**主要ファイル**:
- `calendar_integration.py`: Google Calendar API連携
- `summary_generator.py`: 要約生成（Gemini使用）

**インポートパス例**:
```python
from src.shared.calendar_integration import get_events_for_file_date
from src.shared.summary_generator import generate_summary_with_calendar
```

---

## Phase 11-3処理フロー

```
Google Drive Upload (Webhook検知)
  ↓
[src/transcription/structured_transcribe.py]
  ↓
[src/pipeline/integrated_pipeline.py]
  ↓
Step 1: JSON読み込み
Step 2: カレンダーマッチング
Step 3: 参加者抽出 ← src/participants/extract_participants.py
Step 4: 参加者DB検索 ← src/participants/participants_db.py
Step 5: トピック/エンティティ抽出 ← src/topics/add_topics_entities.py
Step 6: エンティティ解決
Step 7: 話者推論 ← src/participants/enhanced_speaker_inference.py
Step 8: 要約生成 ← src/shared/summary_generator.py
Step 9: 参加者DB更新 ← src/participants/participants_db.py
Step 10: 会議情報登録
  ↓
[src/vector_db/build_unified_vector_index.py] ← Phase 11-4
  ↓
[src/file_management/cloud_file_manager.py] ← Google Drive削除
```

## 環境変数による制御

```bash
# Phase 11-3有効化（デフォルト: true）
ENABLE_INTEGRATED_PIPELINE=true

# Phase 11-4有効化（デフォルト: true）
ENABLE_VECTOR_DB=true

# 自動ファイル名変更（デフォルト: false）
AUTO_RENAME_FILES=false

# Google Docs作成（デフォルト: false）
ENABLE_DOCS_EXPORT=false
```

## データフロー

### 1. 入力
- **音声ファイル**: `.m4a`
- **Google Drive**: Webhook通知

### 2. 中間ファイル
- **構造化JSON**: `*_structured.json`（Phase 0出力）
- **拡張JSON**: `*_structured_enhanced.json`（Phase 11-3出力）

### 3. 永続化
- **participants.db**: SQLite参加者データベース
- **Qdrant**: Vector DB（検索用）
- **unified_registry.json**: 処理済みファイルレジストリ

### 4. 出力
- **JSON**: ローカル`downloads/`フォルダ
- **Google Docs**: モバイル表示用（オプション）

## 移行履歴

**2025-10-17**: フォルダ構造リファクタリング
- `step1_transcribe` → `transcription`
- `step2_participants` → `participants`
- `step3_topics` + `step4_entities` → `topics`（統合）
- `step5_vector_db` → `vector_db`
- `step6_search` → `search`
- `step7_file_management` → `file_management`
- 新規作成: `pipeline/`（integrated_pipeline.py移動）

**理由**:
- Phase番号依存の命名を廃止
- 機能別グルーピングによる可読性向上
- Phase 11-3の10ステップとの整合性確保

## 関連ドキュメント

- [Phase 11-3アーキテクチャ](./phase-11-3-architecture.md)
- [Phase 11-3最適化](./phase-11-3-optimization.md)
- [パイプラインアーキテクチャ](./pipeline-architecture.md)
