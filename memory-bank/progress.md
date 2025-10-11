# Progress Tracking (Google Drive連携版)

## マイルストーン

### ✅ Phase 0-2: ローカルWhisper実装（アーカイブ済み）
- [x] faster-whisper実装
- [x] pyannote.audio話者分離
- [x] Unstructured風メタデータ
- [x] archive_phase1_local_whisper/へ移動

**完了日**: 2025-10-05
**場所**: `archive_phase1_local_whisper/`

### ✅ Phase 3: 超シンプル版実装（完了）
**目標**: 50行で動く文字起こしスクリプト

#### 完了タスク
- [x] transcribe_api.py実装（50行）
- [x] OpenAI Whisper API統合
- [x] requirements.txt作成
- [x] .env設定
- [x] 動作テスト完了

**完了日**: 2025-10-07

### ✅ Phase 4: 要約機能追加（完了）
**目標**: Gemini APIで要約生成

#### 完了タスク
- [x] Gemini API統合
- [x] summarize_text() 関数実装
- [x] Markdown出力機能
- [x] requirements.txt更新（google-generativeai追加）
- [x] .env.example更新（GEMINI_API_KEY追加）
- [x] 動作テスト完了

**完了日**: 2025-10-07

### ✅ Phase 5-1: Google Drive手動ダウンロード＆文字起こし（完了）
**目標**: Google Driveの`audio`フォルダから1ファイルを手動で取得して文字起こし

**前提条件**: Phase 4が動作すること

#### タスク
- [x] Google Cloud Console設定（初回のみ）
  - [x] プロジェクト作成
  - [x] Google Drive API有効化
  - [x] OAuth同意画面設定
  - [x] OAuth 2.0クライアントID作成（デスクトップアプリ）
  - [x] credentials.jsonダウンロード
- [x] requirements.txt更新
  - [x] google-api-python-client追加
  - [x] google-auth-httplib2追加
  - [x] google-auth-oauthlib追加
- [x] drive_download.py実装（実装完了: 197行）
  - [x] Google Drive認証（OAuth 2.0）
  - [x] token.json自動生成（初回実行時）
  - [x] ファイルダウンロード機能
  - [x] transcribe_api.py呼び出し
- [x] 動作テスト（完了）
  - [x] ライブラリインストール
  - [x] Google Drive認証テスト（OAuth同意画面テストユーザー追加）
  - [x] ファイルダウンロードテスト
  - [x] 文字起こし・要約テスト

**使い方**: `venv/bin/python drive_download.py <file_id>`

**完了条件**: ✅ Google Drive上の音声ファイルの文字起こし・要約が成功

**完了日**: 2025-10-09

**注意事項**:
- テストユーザーの追加が必要（OAuth同意画面で設定）
- 初回実行時はブラウザ認証が必要
- 2回目以降はtoken.jsonで自動認証

### ✅ Phase 5-2: Google Driveポーリング自動検知（完了）
**目標**: Google Driveの`audio`フォルダ（My Drive直下）に新規ファイルが追加されたら自動で文字起こし（ポーリング方式）

**前提条件**: Phase 5-1が動作すること

**監視対象フォルダ**: Google Driveの`My Drive/audio`フォルダ（今後の音声ファイル保存先）

#### 完了タスク
- [x] monitor_drive.py実装（218行）
  - [x] Google Drive認証（token.json再利用）
  - [x] My Drive/audioフォルダのID取得
  - [x] 5分間隔でaudioフォルダをチェック
  - [x] 処理済みファイルリスト管理（.processed_drive_files.txt）
  - [x] 新規ファイル検出 → ダウンロード → 文字起こし → 要約
  - [x] 25MB超過ファイル自動分割（ffmpeg使用）
- [x] 動作テスト
  - [x] ポーリング動作テスト
  - [x] 新規ファイル検出テスト（101MB大容量ファイル含む）
  - [x] 自動文字起こしテスト
  - [x] 処理済みリスト管理テスト

**検知方式**: 定期的な調査（最大5分遅延あり）

**使い方**: `python monitor_drive.py`（ターミナルで実行、Ctrl+Cで停止）

**完了条件**: ✅ Google Driveへの新規アップロードを検知し、自動文字起こし成功

**完了日**: 2025-10-11

**テスト実績**:
- Seven Eleven Soka Kitaya 1Chome-Shop 10.m4a (178KB)
- Seven Eleven Soka Kitaya 1Chome-Shop 11.m4a (206KB)
- Test Recording.m4a (101MB) - 11チャンクに分割処理成功

### ✅ Phase 5-3: FastAPI + Push通知リアルタイム検知（完了）
**目標**: Google Driveの`audio`フォルダにファイル作成時、リアルタイムで検知し即座に文字起こし（Push通知方式）

**前提条件**: Phase 5-2が動作すること

**監視対象フォルダ**: Google Driveの`My Drive/audio`フォルダ（Phase 5-2と同じ）

#### 完了タスク
- [x] requirements.txt更新
  - [x] fastapi追加
  - [x] uvicorn[standard]追加
- [x] webhook_server.py実装（280行）
  - [x] Webhookエンドポイント作成（POST /webhook）
  - [x] Google Drive認証
  - [x] changes.watch() 実装
  - [x] /setup エンドポイントでWebhook登録
  - [x] Webhook受信 → バックグラウンド処理 → 新規ファイルダウンロード → 文字起こし
- [x] ngrokセットアップ（ローカルHTTPS トンネル）
  - [x] ngrokインストール
  - [x] ngrok authtoken設定
  - [x] HTTPS URL取得
- [x] Google Drive Push通知設定
  - [x] ngrok HTTPS URLをchanges.watch()に登録
  - [x] 初回同期メッセージ受信確認
- [x] 動作テスト
  - [x] ngrokでローカルHTTPSテスト
  - [x] Webhook受信テスト（State: change）
  - [x] リアルタイム文字起こしテスト

**検知方式**: イベント駆動（数秒以内にリアルタイム検知）

**開発環境**: ngrok（HTTPS トンネル）

**本番環境**: 不要（ローカルテストのみ）

**使い方**:
1. FastAPI起動: `PYTHONPATH="venv/lib/python3.11/site-packages:$PYTHONPATH" /usr/local/opt/python@3.11/bin/python3.11 webhook_server.py`
2. 別ターミナルでngrok起動: `ngrok http 8000`
3. Webhook登録: `curl "http://localhost:8000/setup?webhook_url=<ngrok-https-url>"`

**注意事項**:
- ngrok無料版は2時間セッション制限
- URL再起動ごとに変更（webhook再登録必要）
- Webhook有効期限: 24時間（自動更新未実装）

**完了条件**: ✅ ファイルアップロード後、数秒以内に自動文字起こし開始（ngrok環境で動作）

**完了日**: 2025-10-11

**テスト実績**:
- Seven Eleven Soka Kitaya 1Chome-Shop 12.m4a (89KB)
- Webhook通知受信（State: change）
- 検知から処理完了まで: 数秒以内
- ngrok URL: https://6ca1c21ca080.ngrok-free.app
- Channel ID: channel-20251011031555

### ⬜ Phase 6: データ構造化とメタデータ付与（計画中）
**目標**: 音声データから文字起こしした情報に構造化とメタデータを付与し、要約や分析の精度を高める

**背景**: Unstructured, Plaud, Granolaの3社のベストプラクティスを分析し、最適なアプローチを設計

**詳細プラン**: [phase6-plan.md](phase6-plan.md) 参照

#### Phase 6-1: 基本メタデータ抽出（未開始）
**目標**: 文字起こしテキストに基本的なメタデータを付与し、JSON形式で構造化

**タスク**:
- [ ] ファイルメタデータの抽出（名前、サイズ、日時、長さ、形式）
- [ ] 文字起こしメタデータの生成（文字数、単語数、推定話者数、言語）
- [ ] テキストセグメント化（文単位、段落単位）
- [ ] タイムスタンプ付与（Whisper API word-level timestamps）
- [ ] JSON構造化出力

**技術スタック**: Whisper API with timestamps, Python JSON

**推定工数**: 2-3時間

**完了条件**: JSON形式での構造化データ出力、基本メタデータの完全性

#### Phase 6-2: 話者識別とトピック抽出（未開始）
**目標**: 話者を識別し、トピックごとにセグメント化

**タスク**:
- [ ] 話者識別（Speaker Diarization with pyannote.audio）
- [ ] 話者ごとの統計（発言時間、割合、ターン数）
- [ ] トピック抽出とセグメント化（Gemini API）
- [ ] トピックごとのサマリー生成
- [ ] キーワード・エンティティ抽出（人名、組織、日付、アクションアイテム）
- [ ] 会話タイプの自動判定
- [ ] JSON構造の拡張

**技術スタック**: pyannote.audio, Gemini API, spaCy (optional)

**推定工数**: 4-5時間

**完了条件**: 話者ラベル精度 > 80%, トピック分類の有用性検証

#### Phase 6-3: セマンティック検索とRAG（未開始）
**目標**: 複数の文字起こしを横断した検索・分析機能

**タスク**:
- [ ] セマンティック検索の実装（ChromaDB + embeddings）
- [ ] フォルダー/カテゴリ管理システム
- [ ] 自動カテゴリ分類とタグ付け
- [ ] クロス分析機能（複数会議を横断したトレンド分析）
- [ ] 引用付き質問応答（RAG with LangChain）
- [ ] タイムスタンプリンク機能
- [ ] 可視化機能（マインドマップ、発言時間分析、キーワードクラウド）

**技術スタック**: ChromaDB, OpenAI Embeddings, LangChain, matplotlib/plotly

**推定工数**: 6-8時間

**完了条件**: セマンティック検索実現、RAG質問応答の精度検証、複数会議の統合分析デモ

**Phase 6全体の完了条件**:
- ✅ 基本メタデータの自動抽出
- ✅ 話者識別の実装
- ✅ トピック自動抽出
- ✅ JSON形式での構造化データ出力
- ✅ セマンティック検索の実現
- ✅ 複数会議を横断した分析機能
- ✅ RAG質問応答システムの構築

**コスト分析**:
- 現状（Phase 5）: $0.72 / 2時間音声
- Phase 6完了時: $0.72054 / 2時間音声
- **追加コスト**: わずか$0.00054（約0.08円）

**リサーチ完了日**: 2025-10-11

## 完了タスク

### 2025-10-09（方針変更: Google Drive連携へ）
- ✅ Phase 6（iCloud自動監視）破棄
- ✅ コミット27795dcに戻す（Phase 4完了時点）
- ✅ 不要なログファイル・Phase 6関連ファイル削除
- ✅ Phase 5をGoogle Drive連携（3段階実装）に変更
- ✅ メモリーバンク更新

### 2025-10-07（Phase 3-4実装）
- ✅ Phase 3: OpenAI Whisper API統合
- ✅ Phase 4: Gemini要約機能追加
- ✅ transcribe_api.py実装完了

### 2025-10-05（プロジェクト再構築）
- ✅ Phase 1-2実装をアーカイブ
- ✅ メモリーバンクをアーカイブにコピー
- ✅ 超シンプル版実装プラン策定

## 削除した機能

### Phase 1-2から削除（Phase 3で除外）
- ❌ faster-whisper（ローカル処理）
- ❌ pyannote.audio（話者分離）
- ❌ JSON出力（不要）
- ❌ メタデータ（不要）
- ❌ エラーリトライ（手動再実行で十分）

### Phase 6（完全削除・方針変更）
- ❌ iCloud自動監視（Watchdog + launchd）
- ❌ macOS権限対応（フルディスクアクセス）
- ❌ .qtaファイル処理

## メトリクス

### 開発進捗
- **Phase 3**: ✅ 100% 完了
- **Phase 4**: ✅ 100% 完了
- **Phase 5-1**: ✅ 100% 完了
- **Phase 5-2**: ✅ 100% 完了
- **Phase 5-3**: ✅ 100% 完了
- **Phase 6-1**: ⬜ 0% (計画完了、実装準備中)
- **Phase 6-2**: ⬜ 0% (未開始)
- **Phase 6-3**: ⬜ 0% (未開始)

### コード統計（Phase 3目標）
- **実装総行数**: 50行（transcribe_api.py）
- **ファイル数**: 3ファイル
  - transcribe_api.py (50行)
  - requirements.txt (2行)
  - .env.example (3行)
- **依存関係**: 2つ（openai, python-dotenv）

### パフォーマンス目標（Phase 3）
| 指標 | 目標値 | 現状 |
|------|--------|------|
| 処理速度（60分音声） | 1分以内 | 未テスト |
| コスト | $0.36/60分 | 未テスト |
| コード理解時間 | 30分以内 | - |

## 既知の課題・制限事項

### 技術的課題
- OpenAI APIファイルサイズ制限（25MB）
- インターネット接続必須

### Google Drive API制限（Phase 5）
- **クォータ**: 20,000リクエスト/100秒（無料）
- **ポーリング方式**: 最大5分の検知遅延
- **Push通知**: ngrok無料版は2時間セッション制限、URL再起動ごとに変更

## 学習ログ

### 設計思想
1. **超シンプル優先**: 初学者でも理解できるコード
2. **段階的拡張**: Phase 3→4→5-1→5-2→5-3で機能追加
3. **初学者フレンドリー**: 各Phaseで明確な目標
4. **デバッグ容易**: エラー箇所が特定しやすい
5. **無料枠で完結**: Google Drive API無料枠内で動作

### Phase 5の段階的アプローチ
1. **5-1（手動）**: Google Drive認証とファイルダウンロードを学ぶ
2. **5-2（ポーリング）**: 定期的な調査で自動化を学ぶ
3. **5-3（Push通知）**: Webhook・FastAPI・リアルタイム処理を学ぶ

## 次のアクション

### 最優先（Phase 5-1実装）
1. **Google Cloud Console設定**: API有効化、OAuth認証設定
2. **requirements.txt更新**: Google Drive API関連ライブラリ追加
3. **drive_download.py実装**: 手動ダウンロード＆文字起こし
4. **動作テスト**: Google Drive認証、ファイルダウンロード、文字起こしテスト

### Phase 5-1完了後
1. **Phase 5-2実装**: ポーリング自動検知
2. **Phase 5-3実装**: FastAPI + Push通知

## 更新履歴

- **2025-10-11 13:00**: Phase 6計画完了（Unstructured/Plaud/Granolaのリサーチ、実装プラン作成）
- **2025-10-11 12:20**: Phase 5-3完了（FastAPI + Push通知リアルタイム検知）
- **2025-10-11 11:30**: Phase 5-2完了（ポーリング自動検知、大容量ファイル対応）
- **2025-10-09 13:00**: Phase 5-1完了、テスト成功（各Phase完了ごとにコミット方針）
- **2025-10-09 12:30**: Phase 5をGoogle Drive連携（3段階）に変更、メモリーバンク更新完了
- **2025-10-09 11:45**: Phase 6破棄、コミット27795dcに戻す
- **2025-10-07**: Phase 3-4実装完了
- **2025-10-05**: プロジェクト再構築、Phase 1-2アーカイブ

## 開発方針

**各Phase完了ごとにgit commit**:
- Phase 5-1完了 → コミット
- Phase 5-2完了 → コミット
- Phase 5-3完了 → コミット
