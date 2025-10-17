# System Patterns

## システムアーキテクチャ

### 全体構成
```
[入力] Google Drive / iCloud Drive
  ↓
[監視] Webhook Server / File Monitor
  ↓
[文字起こし] Whisper API
  ↓
[統合パイプライン] Phase 11-3 (10 Steps)
  ├── Step 1: JSON読み込み
  ├── Step 2: カレンダーマッチング
  ├── Step 3: 参加者抽出
  ├── Step 4: 参加者DB検索
  ├── Step 5: トピック/エンティティ抽出
  ├── Step 6: エンティティ解決
  ├── Step 7: 話者推論
  ├── Step 8: 要約生成
  ├── Step 9: 参加者DB更新
  └── Step 10: 会議情報登録
  ↓
[Vector DB構築] Phase 11-4
  ↓
[出力] JSON / Google Docs / Vector DB
```

## コンポーネント関係

### 1. 監視システム
- **Google Drive Webhook** (`src/monitoring/webhook_server.py`)
  - FastAPIサーバー
  - Google Drive変更通知を受信
  - ngrokでトンネリング

- **iCloud Monitor** (`src/monitoring/icloud_monitor.py`)
  - watchdogによるファイル監視
  - 新規ファイル検知 → 文字起こし起動

### 2. 文字起こしエンジン
- **structured_transcribe.py** (`src/transcription/`)
  - Whisper API呼び出し
  - 25MB超過時の自動分割
  - 構造化JSON生成
  - Phase 11-3/11-4パイプライン起動

### 3. 統合パイプライン (Phase 11-3)
- **integrated_pipeline.py** (`src/pipeline/`)
  - 10ステップの統合実行
  - カレンダー統合 → 参加者抽出 → 話者推論 → DB更新
  - モジュラー設計（各ステップ独立）

### 4. データベース層
- **参加者DB** (`data/participants.db`)
  - SQLite
  - participants, meetings テーブル
  - canonical_name, display_names, organization, role

- **Vector DB** (`chroma_db/`)
  - ChromaDB (PersistentClient)
  - Gemini text-embedding-004 (768次元)
  - transcripts_unified コレクション

### 5. ファイル管理
- **重複管理** (`.processed_files_registry.jsonl`)
  - JSONL形式
  - file_id, source, processed_at記録

- **ファイル名生成** (`src/file_management/generate_smart_filename.py`)
  - Gemini APIで内容解析
  - YYYYMMDD_概要.m4a形式

## デザインパターン

### 1. パイプラインパターン
```python
# 各ステップが独立した関数
Step 1 → Step 2 → Step 3 → ... → Step 10
```
- 利点: モジュラー性、テスト容易性
- 実装: `integrated_pipeline.py`

### 2. レジストリパターン
```python
# 処理済みファイルの管理
if is_processed(file_id):
    skip()
else:
    process()
    register(file_id)
```
- 利点: 重複処理防止
- 実装: `unified_registry.py`

### 3. 環境変数制御パターン
```python
if os.getenv('ENABLE_INTEGRATED_PIPELINE', 'true').lower() == 'true':
    run_pipeline()
```
- 利点: 機能ON/OFF切り替え
- 実装: 全パイプライン

### 4. LLM抽出パターン
```python
# JSONスキーマでLLM出力を構造化
response_schema = {
    "type": "object",
    "properties": {...}
}
result = model.generate_content(
    prompt,
    generation_config={"response_schema": response_schema}
)
```
- 利点: 構造化された確実な出力
- 実装: 参加者抽出、エンティティ抽出

## 主要な技術的決定

### 決定1: ChromaDB採用（QdrantからChromaへ移行）
- **理由**: 軽量、Pythonネイティブ、セットアップ簡単
- **トレードオフ**: Qdrantほどの高度な機能はない
- **影響**: ローカル開発が容易に

### 決定2: Gemini 2.0 Flash採用
- **理由**: コスト効率（GPT-4の1/10）、日本語性能、JSON mode
- **トレードオフ**: RPD制限（1,500リクエスト/日）
- **影響**: バッチ処理時のレート制限考慮が必要

### 決定3: SQLite参加者DB
- **理由**: サーバーレス、ファイルベース、十分な性能
- **トレードオフ**: 大規模スケーリング困難
- **影響**: 個人〜中小規模での運用に最適

### 決定4: 統合パイプライン（Phase 11-3）
- **理由**: ステップごとのバラバラな実行を統合
- **トレードオフ**: 各ステップの独立実行が困難
- **影響**: 処理の一貫性向上、メンテナンス性向上

### 決定5: Enhanced JSON生成（Phase 11-4前提）
- **現状**: 未実装 → Phase 11-4がスキップされる
- **必要性**: Vector DB自動構築に必須
- **優先度**: High

## データフロー

### 入力データ
```
音声ファイル (.m4a)
  → ファイル名（例: "Shop 123.m4a"）
  → ファイルサイズ（25MB上限、超過時分割）
  → 作成日時（カレンダーマッチングに使用）
```

### 中間データ
```
構造化JSON (*_structured.json)
{
  "metadata": {...},
  "segments": [
    {"start": 0.0, "end": 5.2, "text": "..."},
    ...
  ]
}

Enhanced JSON (*_structured_enhanced.json) ← 未実装
{
  ...構造化JSON,
  "meeting_id": "uuid",
  "matched_event": {...},
  "calendar_participants": [...],
  "inference_result": {...},
  "summary_data": {...},
  "topics": [...],
  "entities": {...}
}
```

### 永続化データ
```
participants.db (SQLite)
├── participants
│   ├── id (PRIMARY KEY)
│   ├── canonical_name
│   ├── display_names (JSON)
│   ├── organization
│   ├── role
│   └── notes
└── meetings
    ├── id (PRIMARY KEY)
    ├── meeting_id (UUID)
    ├── structured_file_path
    ├── meeting_date
    ├── meeting_title
    └── participants (JSON)

chroma_db/ (Vector DB)
├── chroma.sqlite3 (43.7 MB)
└── [collections]
    └── transcripts_unified (7,357 embeddings)

.processed_files_registry.jsonl
{"file_id": "...", "source": "gdrive", "processed_at": "..."}
{"file_id": "...", "source": "icloud", "processed_at": "..."}
```

## コンポーネント依存関係

### モジュール構成
```
src/
├── transcription/          # 依存: なし
├── participants/          # 依存: shared/calendar_integration
├── topics/                # 依存: なし
├── pipeline/              # 依存: participants, topics, shared
├── vector_db/             # 依存: なし（独立）
├── file_management/       # 依存: なし
├── monitoring/            # 依存: transcription
└── shared/                # 依存: なし（共通）
```

### 実行順序
```
1. monitoring/ → ファイル検知
2. transcription/ → 文字起こし
3. pipeline/ → 10ステップ実行
   ├── shared/calendar_integration
   ├── participants/extract_participants
   ├── participants/participants_db
   ├── topics/add_topics_entities
   ├── participants/enhanced_speaker_inference
   └── shared/summary_generator
4. vector_db/ → Vector DB構築（enhanced JSON必要）
5. file_management/ → ファイル整理
```

## セキュリティとエラーハンドリング

### 認証
- Google OAuth2（token.json自動更新）
- API Key管理（.env）
- スコープ管理（必要最小限）

### エラーハンドリング
```python
# 全API呼び出しでtry-except
try:
    result = api_call()
except Exception as e:
    print(f"⚠️ エラー: {e}")
    # 処理は続行（部分的成功を許容）
```

### ログ記録
- 各ステップの開始・完了をログ出力
- エラー発生時のスタックトレース
- 処理時間の記録
