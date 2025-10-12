# クリーンアップ計画

## 保持すべきファイル（現在の実装に必要）

### コアパイプライン
- ✅ `structured_transcribe.py` - OpenAI Whisper API文字起こし
- ✅ `infer_speakers.py` - 話者推論（新パイプライン Step 1）
- ✅ `summarize_with_context.py` - コンテキスト付き要約（新パイプライン Step 2）
- ✅ `generate_optimal_filename.py` - 最適ファイル名生成（新パイプライン Step 3）
- ✅ `run_full_pipeline.py` - 統合パイプライン

### 検証システム
- ✅ `baseline_pipeline.py` - ベースライン処理
- ✅ `evaluate_accuracy.py` - 自動評価
- ✅ `llm_evaluate.py` - LLM評価
- ✅ `run_validation.py` - 統合検証

### ユーティリティ
- ✅ `create_small_sample.py` - サンプル作成
- ✅ `.env` - API キー
- ✅ `requirements.txt` - 依存関係

### ドキュメント（最新）
- ✅ `README.md` - プロジェクト概要
- ✅ `PIPELINE_README.md` - パイプライン技術ドキュメント
- ✅ `VALIDATION_PLAN.md` - 検証計画
- ✅ `VALIDATION_PROGRESS_REPORT.md` - 進捗レポート
- ✅ `FINAL_EVALUATION_REPORT.md` - 最終評価レポート
- ✅ `MEMORY_BANK_UPDATE.md` - メモリーバンク更新

### メモリーバンク（必要最小限）
- ✅ `memory-bank/projectbrief.md`
- ✅ `memory-bank/progress.md`
- ✅ `memory-bank/phase7-complete-summary.md`

---

## 削除対象ファイル

### 1. 旧実装・重複ファイル（削除）
- ❌ `add_topics_entities.py` - 旧実装（summarize_with_context.pyに統合済み）
- ❌ `add_topics_entities_v2.py` - 旧バージョン
- ❌ `action_item_structuring.py` - 未使用
- ❌ `build_vector_index.py` - 未使用
- ❌ `cross_analysis.py` - 未使用
- ❌ `entity_resolution_llm.py` - 未使用
- ❌ `topic_clustering_llm.py` - 未使用
- ❌ `topic_clustering.py` - 未使用

### 2. 古い機能（削除）
- ❌ `drive_download.py` - Google Drive連携（現在未使用）
- ❌ `monitor_drive.py` - Google Drive監視（現在未使用）
- ❌ `webhook_server.py` - Webhook（現在未使用）
- ❌ `transcribe_api.py` - 旧API（structured_transcribe.pyを使用）
- ❌ `rag_qa.py` - RAG機能（現在未使用）
- ❌ `semantic_search.py` - セマンティック検索（現在未使用）

### 3. 一時ファイル・ログ（削除）
- ❌ `baseline_execution.log`
- ❌ `test_recording_transcribe.log`
- ❌ `transcribe_10-07.log`
- ❌ `transcribe_test.log`
- ❌ `.processed_drive_files.txt`
- ❌ `.start_page_token.txt`

### 4. 古いレポート・ドキュメント（削除）
- ❌ `action_items_report.md`
- ❌ `classical_ml_analysis.txt`
- ❌ `cross_meeting_analysis_report.md`
- ❌ `entity_resolution_report.md`
- ❌ `gemini_migration_plan.md` - 既に完了
- ❌ `stage4_improvement_report.md`
- ❌ `topic_clustering_llm_report.md`
- ❌ `topic_clustering_report.md`
- ❌ `topic_clustering_report_0.75.md`
- ❌ `topic_clustering_report_final.md`

### 5. 一時スクリプト（削除）
- ❌ `check_transcriptions.py` - 一時スクリプト
- ❌ `monitor_progress.sh` - 一時スクリプト
- ❌ `wait_for_transcriptions.sh` - 一時スクリプト

### 6. 古いメモリーバンク（削除）
- ❌ `memory-bank/activeContext.md` - 古いコンテキスト
- ❌ `memory-bank/phase6-plan.md` - 古いフェーズ
- ❌ `memory-bank/phase6-status.md` - 古いフェーズ
- ❌ `memory-bank/phase7-stage7-2-handoff.md` - 既に完了
- ❌ `memory-bank/productContext.md` - 未使用
- ❌ `memory-bank/systemPatterns.md` - 未使用
- ❌ `memory-bank/techContext.md` - 未使用

---

## 削除の優先順位

### Phase 1: 一時ファイル・ログ（即座に削除可能）
- ログファイル（.log）
- 一時テキストファイル（.txt）
- 一時シェルスクリプト（.sh）

### Phase 2: 旧実装・重複ファイル（削除後テスト）
- 旧Pythonスクリプト
- テスト実行して依存関係を確認

### Phase 3: 古いドキュメント（削除可能）
- 古いレポート
- 古いメモリーバンク

---

## 削除後のディレクトリ構造（理想）

```
.
├── .env
├── requirements.txt
├── README.md
├── PIPELINE_README.md
├── VALIDATION_PLAN.md
├── VALIDATION_PROGRESS_REPORT.md
├── FINAL_EVALUATION_REPORT.md
├── MEMORY_BANK_UPDATE.md
├── memory-bank/
│   ├── projectbrief.md
│   ├── progress.md
│   └── phase7-complete-summary.md
├── structured_transcribe.py
├── infer_speakers.py
├── summarize_with_context.py
├── generate_optimal_filename.py
├── run_full_pipeline.py
├── baseline_pipeline.py
├── evaluate_accuracy.py
├── llm_evaluate.py
├── run_validation.py
├── create_small_sample.py
├── archive_phase1_local_whisper/ (保持)
├── downloads/ (保持)
└── venv/ (保持)
```

**削減予定**:
- Pythonファイル: 26個 → 10個（-16個）
- ドキュメント: 40個以上 → 9個（-30個以上）
- 合計: 約50%削減
