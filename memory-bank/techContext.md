# Technical Context

## 技術スタック

### コア技術
- **言語**: Python 3.11
- **パッケージ管理**: venv (仮想環境)
- **依存管理**: requirements.txt

### 主要ライブラリ

#### AI/ML
```
openai==1.58.1              # Whisper API
google-generativeai==0.8.3  # Gemini API
chromadb==0.5.23            # Vector DB
sentence-transformers       # Embeddings (未使用)
```

#### Google API
```
google-api-python-client==2.154.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.1
```

#### Web/監視
```
fastapi==0.115.6           # Webhook server
uvicorn==0.34.0            # ASGI server
watchdog==6.0.0            # iCloud file monitoring
pyngrok==7.2.2             # Tunnel for webhooks
```

#### ユーティリティ
```
python-dotenv==1.0.1       # .env管理
requests==2.32.3           # HTTP client
ffmpeg-python==0.2.0       # 音声分割
```

## 開発環境

### ディレクトリ構造
```
realtime_transcriber_benchmark_research/
├── src/                   # ソースコード
│   ├── transcription/    # 文字起こし
│   ├── participants/     # 参加者管理
│   ├── topics/           # トピック/エンティティ
│   ├── pipeline/         # 統合パイプライン
│   ├── vector_db/        # Vector DB
│   ├── file_management/  # ファイル管理
│   ├── monitoring/       # 監視
│   └── shared/           # 共通
├── data/                 # データベース
│   └── participants.db   # SQLite
├── downloads/            # 処理済みファイル
├── chroma_db/           # Vector DB
├── docs/                # ドキュメント
├── memory-bank/         # AI記憶
├── tools/               # ユーティリティ
├── venv/                # 仮想環境
├── .env                 # 環境変数
└── requirements.txt     # 依存関係
```

### 環境変数 (.env)
```bash
# OpenAI
OPENAI_API_KEY=sk-proj-xxx

# Gemini
GEMINI_API_KEY=AIzaSyxxx
GEMINI_MODEL=gemini-2.0-flash-exp

# Google Calendar/Drive
# (credentials.json, token.json使用)

# Phase制御
ENABLE_INTEGRATED_PIPELINE=true
ENABLE_VECTOR_DB=true
AUTO_RENAME_FILES=false
ENABLE_DOCS_EXPORT=false

# その他
ENABLE_ICLOUD_MONITORING=true
```

## 技術的制約

### API制限

#### Whisper API
- **ファイルサイズ**: 25 MB上限
- **対応形式**: mp3, mp4, mpeg, mpga, m4a, wav, webm
- **コスト**: $0.006/分
- **対策**: 25MB超過時はffmpegで分割

#### Gemini API
- **RPD (Requests Per Day)**: 1,500
- **RPM (Requests Per Minute)**: 15
- **Tokens/分**: 1,000,000
- **コスト**: $0.00001875/1000 tokens (input)
- **対策**: レート制限監視、Tier管理

#### Google Calendar/Drive API
- **クォータ**: 1,000,000 requests/日
- **認証**: OAuth 2.0
- **スコープ**:
  - calendar.readonly
  - drive.readonly
  - drive.file (削除用)

### ChromaDB制限
- **埋め込み次元**: 768 (Gemini text-embedding-004)
- **デフォルトモデル**: all-MiniLM-L6-v2 (384次元) → 使用不可
- **ストレージ**: SQLiteベース (chroma.sqlite3)
- **現在のサイズ**: 43.7 MB (13,908 embeddings)

### SQLite制約
- **同時書き込み**: 制限あり
- **ファイルロック**: 必要
- **トランザクション**: 手動管理必要
- **対策**: 書き込み時はlockを取得

## 開発ワークフロー

### セットアップ
```bash
# 1. 仮想環境作成
python3 -m venv venv

# 2. 依存インストール
venv/bin/pip install -r requirements.txt

# 3. 環境変数設定
cp .env.example .env
# .envを編集

# 4. Google認証
# credentials.jsonをプロジェクトルートに配置
# 初回実行時にブラウザ認証 → token.json生成
```

### 実行方法

#### 文字起こし（単体）
```bash
venv/bin/python src/transcription/structured_transcribe.py <audio_file>
```

#### Google Drive監視
```bash
venv/bin/python src/monitoring/webhook_server.py
# 別ターミナルでngrok起動
ngrok http 8000
```

#### iCloud Drive監視
```bash
venv/bin/python src/monitoring/icloud_monitor.py
```

#### Vector DB構築（手動）
```bash
venv/bin/python src/vector_db/build_unified_vector_index.py downloads/*_enhanced.json
```

### テスト
```bash
# 単体テスト（未実装）
pytest tests/

# 統合テスト（手動）
1. iCloud Driveに音声ファイルアップロード
2. ログ確認: tail -f icloud_monitor.log
3. 結果確認: ls downloads/*_structured.json
4. DB確認: sqlite3 data/participants.db
```

## 外部依存

### 必須サービス
1. **OpenAI API**: Whisper文字起こし
2. **Google Gemini API**: LLM処理（参加者抽出、要約、話者推論）
3. **Google Calendar API**: カレンダー情報取得
4. **Google Drive API**: ファイル検知・削除

### オプションサービス
1. **ngrok**: Webhook受信用トンネル
2. **Google Docs API**: モバイル表示用（ENABLE_DOCS_EXPORT=true）

### ローカル依存
1. **ffmpeg**: 25MB超過ファイルの分割
   ```bash
   brew install ffmpeg  # macOS
   ```

2. **iCloud Drive**: ローカルファイル監視
   - パス: `~/Library/Mobile Documents/com~apple~CloudDocs/transcriptions/`

## パフォーマンス特性

### 処理時間
- **文字起こし**: 1分音声 → 約10秒
- **Phase 11-3**: 構造化JSON → 約30秒
- **Vector DB構築**: enhanced JSON → 約10秒
- **合計**: 1分音声 → 約50秒で完了

### メモリ使用量
- **Whisper API**: サーバー側処理（ローカル不要）
- **Gemini API**: 軽量（Flashモデル）
- **ChromaDB**: 約50MB（7,357 embeddings）
- **SQLite**: 約1MB（participants.db）

### ディスク使用量
```
downloads/               # 約500MB（処理済みファイル）
├── *.m4a               # 音声ファイル
├── *_structured.json   # 構造化JSON（数KB〜数MB）
└── *_enhanced.json     # 拡張JSON（未生成）

chroma_db/              # 約44MB
└── chroma.sqlite3     # Vector DB

data/                   # 約1MB
└── participants.db    # 参加者DB
```

## 既知の技術的課題

### 課題1: Enhanced JSON未生成
- **問題**: Phase 11-3がenhanced JSONを保存しない
- **影響**: Phase 11-4（Vector DB自動構築）がスキップされる
- **優先度**: High
- **解決策**: integrated_pipeline.pyにJSON保存処理追加

### 課題2: Gemini RPD制限
- **問題**: 1,500 requests/日の制限
- **影響**: 大量バッチ処理時に制限に到達
- **優先度**: Medium
- **解決策**: Tier管理、バッチサイズ調整

### 課題3: cloud_file_manager未実装
- **問題**: ModuleNotFoundError
- **影響**: Google Drive自動削除が動作しない
- **優先度**: Low
- **解決策**: 実装完了または削除

### 課題4: Vector DB検索機能なし
- **問題**: Phase 11-5未実装
- **影響**: Vector DBが構築されても検索できない
- **優先度**: Medium
- **解決策**: Phase 11-5実装（FastAPI検索エンドポイント）

## デプロイ情報

### 現在のデプロイ
- **環境**: ローカルマシン（macOS）
- **実行方法**: CLI
- **監視**: バックグラウンドプロセス
- **ログ**: ファイル出力（icloud_monitor.log, webhook_server.log）

### 将来のデプロイ構想
- **環境**: AWS/GCP
- **アーキテクチャ**: サーバーレス（Lambda/Cloud Functions）
- **トリガー**: イベント駆動（S3/Cloud Storage）
- **DB**: Managed PostgreSQL（参加者DB）
- **Vector DB**: Managed Qdrant/Pinecone
