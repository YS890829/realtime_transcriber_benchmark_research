# Progress Tracking

## 現在のステータス

### ✅ 完了済み Phase

#### Phase 0-10: 基盤構築（完了）
- [x] Whisper API文字起こし
- [x] Google Drive/iCloud Drive監視
- [x] 重複ファイル検知
- [x] 自動ファイル名変更
- [x] カレンダー統合

#### Phase 11-3: 統合パイプライン（完了 - 2025-10-17）
- [x] Step 1: 構造化JSON読み込み
- [x] Step 2: カレンダーイベントマッチング
- [x] Step 3: 参加者抽出（LLM）
- [x] Step 4: 参加者DB検索
- [x] Step 5: トピック/エンティティ抽出（最適化版）
- [x] Step 6: エンティティ解決（LLMベース）
- [x] Step 7: 話者推論（エンティティ統合版）
- [x] Step 8: 要約生成
- [x] Step 9: 参加者DB更新
- [x] Step 10: 会議情報登録
- [x] iCloud Drive統合修正（環境変数継承問題解決）
- [x] Google Drive Webhook統合

**最適化内容**:
- トピック/エンティティ抽出を1回のAPI呼び出しに統合（RPD節約）
- エンティティ解決をLLMベースに変更（精度向上）
- 話者推論でentities.people活用（カレンダー参加者+エンティティ統合）

**動作確認**:
- ✅ iCloud Drive: Shop 12, 120, 123で動作確認
- ✅ Google Drive: Shop 123で動作確認
- ✅ OAuth2自動再認証動作確認

---

### 🔄 進行中 Phase

#### Phase 11-4: Vector DB自動構築（部分完了）

**完了**:
- [x] Vector DB実装（build_unified_vector_index.py）
- [x] ChromaDB統合（text-embedding-004）
- [x] transcripts_unifiedコレクション作成
- [x] Vector DB検証完了（7,357 embeddings稼働中）

**未完了**:
- [ ] Enhanced JSON生成機能（**ブロッカー**）
- [ ] Phase 11-3からのenhanced JSON自動保存
- [ ] Phase 11-4自動実行フロー

**現状**:
- Vector DBは存在（43.7 MB, 13,908 embeddings）
- 過去のenhanced JSON（12ファイル）からは構築済み
- Phase 11-3経由の新規ファイルは追加されない（enhanced JSON未生成）

**次のアクション**:
1. integrated_pipeline.pyにStep 11追加（enhanced JSON保存）
2. structured_transcribe.pyのenhanced_json_path取得方法修正
3. 動作検証（iCloud/Google Drive）

**参考ドキュメント**:
- [Phase 11-4検証レポート](../docs/phase_11_4_verification_report.md)

---

### 📋 予定 Phase

#### Phase 11-5: Vector DB検索・クエリ機能（次のタスク）

**概要**:
構築されたVector DBを活用して、セマンティック検索やRAG（Retrieval-Augmented Generation）を実装。

**実装内容**:

##### 1. セマンティック検索API
- [ ] semantic_search.py実装
  - 自然言語クエリで過去の会話を検索
  - 類似度スコアによるランキング
  - 時間範囲フィルタ
  - 話者フィルタ
  - トピックフィルタ

##### 2. 会議検索機能
- [ ] meeting_search.py実装
  - Meeting IDベース検索
  - 参加者ベース検索
  - トピックベース検索
  - 日付範囲検索

##### 3. RAG統合
- [ ] rag_qa.py実装
  - 過去の会話履歴を参照した文字起こし
  - コンテキスト強化型要約生成
  - 質問応答システム

##### 4. FastAPI検索エンドポイント
- [ ] /api/search - セマンティック検索
- [ ] /api/meetings/{meeting_id} - 会議詳細取得
- [ ] /api/participants/{name} - 参加者の会議履歴
- [ ] /api/qa - RAG質問応答

##### 5. 簡易UI（オプション）
- [ ] Web検索インターフェース
- [ ] 検索結果表示
- [ ] 会議詳細ビュー

**技術スタック**:
- ChromaDB（既存）
- Gemini text-embedding-004（既存）
- FastAPI（検索API）
- Gemini 2.0 Flash（RAG回答生成）

**期待される効果**:
- 「○○について話した会議はいつ？」のような質問に即答
- 会議の内容を踏まえた次回の文字起こし
- ナレッジベースの構築

**前提条件**:
- Phase 11-4完了（Enhanced JSON生成実装）

---

#### Phase 12: Shop 1-25レジストリ自動削除（保留）

**問題**:
- Shop 1-25（ホーム録音）は定期的にiPhoneから削除される
- 同じファイル名が別内容で再利用される
- 重複検知が誤検知し、新規ファイルが処理されない

**提案**:
- iCloud Drive + Shop 1-25の組み合わせでレジストリを自動削除
- Google Drive経由は削除しない（保守的アプローチ）

**ユーザー判断**:
- **保留**（2025-10-17）
- 再テスト後に再検討

---

#### Phase 13: 参加者DB管理UI（未定）

**概要**:
- 参加者情報の閲覧・編集UI
- 会議履歴の可視化
- 統計情報ダッシュボード

**優先度**: Medium

---

#### Phase 14: モバイルアプリ統合（未定）

**概要**:
- スマホから直接録音 → 文字起こし
- リアルタイム文字起こし表示
- 音声ファイルアップロード

**優先度**: Low

---

#### Phase 15: リアルタイム文字起こし（未定）

**概要**:
- ストリーミング音声の文字起こし
- リアルタイム話者推論
- ライブ要約生成

**優先度**: Low

---

## 現在動作している機能

### ✅ 自動文字起こしフロー

#### Google Drive経由
1. Google Driveに音声ファイルアップロード
2. Webhook通知 → webhook_server.pyで検知
3. Whisper API文字起こし → 構造化JSON生成
4. Phase 11-3統合パイプライン実行
5. ~~Phase 11-4 Vector DB構築~~（enhanced JSON未生成のためスキップ）
6. ファイル整理・リネーム（オプション）

#### iCloud Drive経由
1. iCloud Driveに音声ファイルアップロード
2. icloud_monitor.pyがwatchdogで検知
3. Whisper API文字起こし → 構造化JSON生成
4. Phase 11-3統合パイプライン実行
5. ~~Phase 11-4 Vector DB構築~~（enhanced JSON未生成のためスキップ）
6. ファイル整理・リネーム（オプション）

### ✅ データベース

#### 参加者DB (SQLite)
- **場所**: data/participants.db
- **テーブル**: participants, meetings
- **レコード数**:
  - participants: 複数
  - meetings: 15件（Shop 12, 123など）

#### Vector DB (ChromaDB)
- **場所**: chroma_db/chroma.sqlite3
- **サイズ**: 43.7 MB
- **Embeddings**: 13,908
- **transcripts_unified**: 7,357 embeddings
- **埋め込みモデル**: Gemini text-embedding-004 (768次元)

#### 重複管理レジストリ
- **場所**: .processed_files_registry.jsonl
- **形式**: JSONL
- **エントリ数**: 15
- **内容**: file_id, source (gdrive/icloud), processed_at

---

## 既知の問題

### 🔴 高優先度

#### 1. Enhanced JSON未生成（Phase 11-4ブロッカー）
- **問題**: integrated_pipeline.pyがenhanced JSONを保存しない
- **影響**: Phase 11-4が実行されない
- **状態**: 特定済み、実装待ち
- **解決策**: Step 11追加（JSON保存処理）

### 🟡 中優先度

#### 2. Phase 11-5未実装
- **問題**: Vector DB検索機能がない
- **影響**: Vector DBが活用されない
- **状態**: Phase 11-4完了待ち
- **解決策**: FastAPI検索エンドポイント実装

#### 3. Gemini RPD制限
- **問題**: 1,500 requests/日の制限
- **影響**: 大量バッチ処理時に制限到達
- **対策**: レート制限監視、バッチサイズ調整

### 🟢 低優先度

#### 4. cloud_file_manager未実装
- **問題**: ModuleNotFoundError
- **影響**: Google Drive自動削除が動作しない
- **対策**: 手動削除で代替可能

#### 5. OAuth2スコープ不足エラー（解決済み）
- **問題**: calendar.readonly スコープ不足
- **対策**: 自動再認証機構が動作
- **状態**: 解決済み（Shop 123で確認）

---

## 成果物

### ドキュメント
- [x] [フォルダ構造ガイド](../docs/folder-structure.md)
- [x] [Phase 11-4検証レポート](../docs/phase_11_4_verification_report.md)
- [x] [Memory Bank](.) - Clineスタイル

### コード
- [x] 文字起こし: src/transcription/structured_transcribe.py
- [x] 統合パイプライン: src/pipeline/integrated_pipeline.py
- [x] 参加者管理: src/participants/*
- [x] トピック/エンティティ: src/topics/*
- [x] Vector DB構築: src/vector_db/build_unified_vector_index.py
- [x] 監視: src/monitoring/webhook_server.py, icloud_monitor.py
- [x] ファイル管理: src/file_management/*

### データベース
- [x] participants.db (SQLite)
- [x] chroma_db/ (Vector DB)
- [x] .processed_files_registry.jsonl (重複管理)

---

## メトリクス

### 処理実績
- **文字起こし完了**: 15+ ファイル
- **Vector DB登録**: 12ファイル（7,357 embeddings）
- **参加者DB登録**: 15会議

### パフォーマンス
- **文字起こし**: 1分音声 → 約10秒
- **Phase 11-3**: 構造化JSON → 約30秒
- **Vector DB構築**: enhanced JSON → 約10秒
- **合計処理時間**: 1分音声 → 約50秒

### コスト（推定）
- **Whisper API**: $0.006/分
- **Gemini API**: $0.00001875/1000 tokens
- **月間コスト**: 約$5（100ファイル/月想定）

---

## 次回セッションのクイックスタート

1. **Phase 11-4修正を開始する場合**:
   ```bash
   # integrated_pipeline.py にStep 11追加
   # enhanced JSON保存処理実装
   # テスト実行
   ```

2. **Phase 11-5を開始する場合**:
   ```bash
   # Phase 11-4完了確認
   # src/search/semantic_search.py作成
   # FastAPIエンドポイント実装
   ```

3. **現状確認を行う場合**:
   ```bash
   # Vector DB確認
   ls -lh chroma_db/

   # 参加者DB確認
   sqlite3 data/participants.db "SELECT COUNT(*) FROM meetings;"

   # レジストリ確認
   wc -l .processed_files_registry.jsonl
   ```

**重要**: Phase 11-4のenhanced JSON生成実装が最優先タスクです。
