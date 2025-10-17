# Active Context

## 現在の作業フォーカス

### Phase 11-4: Enhanced JSON生成実装（優先度: High）

**問題**:
- Phase 11-3（integrated_pipeline.py）がenhanced JSONを生成していない
- Phase 11-4（Vector DB自動構築）がスキップされている
- Vector DBは存在するが、新規ファイルが追加されない

**根本原因**:
1. `src/pipeline/integrated_pipeline.py` がJSONを保存していない
2. `src/transcription/structured_transcribe.py:702` がenhanced JSON存在を仮定
3. `src/vector_db/build_unified_vector_index.py` がenhanced JSON必須

**必要な実装**:
```python
# src/pipeline/integrated_pipeline.py の最後に追加
# Step 11: Enhanced JSON保存（Phase 11-4用）
print("\n[Step 11] Enhanced JSON保存中...")

enhanced_data = {
    **data,  # 元の構造化JSON
    "meeting_id": meeting_id,
    "matched_event": matched_event,
    "calendar_participants": calendar_participants,
    "inference_result": inference_result,
    "summary_data": summary_data
}

enhanced_json_path = structured_file_path.replace('_structured.json', '_structured_enhanced.json')
with open(enhanced_json_path, 'w', encoding='utf-8') as f:
    json.dump(enhanced_data, f, ensure_ascii=False, indent=2)

print(f"  ✓ Enhanced JSON保存完了: {enhanced_json_path}")

return {
    ...,
    "enhanced_json_path": enhanced_json_path
}
```

**影響範囲**:
- [src/pipeline/integrated_pipeline.py](../src/pipeline/integrated_pipeline.py:289-296) - return文の更新必要
- [src/transcription/structured_transcribe.py](../src/transcription/structured_transcribe.py:702) - enhanced_json_path取得方法変更

**検証方法**:
1. iCloud Driveに音声ファイルアップロード
2. `downloads/*_structured_enhanced.json` が生成されることを確認
3. Phase 11-4が実行されることをログで確認
4. Vector DBに新規embeddingsが追加されることを確認

---

### Phase 11-5: Vector DB検索・クエリ機能（次のタスク）

**概要**:
構築されたVector DBを活用して、セマンティック検索やRAG（Retrieval-Augmented Generation）を実装。

**実装内容**:

#### 1. セマンティック検索API
```python
# src/search/semantic_search.py
def semantic_search(
    query: str,
    n_results: int = 5,
    filters: Optional[Dict] = None
) -> List[SearchResult]:
    """
    自然言語クエリで過去の会話を検索

    Args:
        query: 検索クエリ（例: "子育てについて話した会議"）
        n_results: 返す結果数
        filters: フィルタ条件
            - date_range: (start, end)
            - speakers: [name1, name2]
            - topics: [topic1, topic2]

    Returns:
        検索結果リスト（類似度スコア付き）
    """
```

#### 2. 会議検索機能
```python
# src/search/meeting_search.py
def search_by_meeting_id(meeting_id: str) -> MeetingDetail
def search_by_participant(participant_name: str) -> List[Meeting]
def search_by_topic(topic: str) -> List[Meeting]
```

#### 3. RAG統合
```python
# src/search/rag_qa.py
def answer_with_context(
    question: str,
    context_meetings: Optional[List[str]] = None
) -> Answer:
    """
    過去の会話履歴を参照した回答生成

    Args:
        question: ユーザーの質問
        context_meetings: 参照する会議ID（Noneの場合は自動検索）

    Returns:
        回答 + 参照元会議情報
    """
```

#### 4. 技術スタック
- **Vector DB**: ChromaDB（既存）
- **Embeddings**: Gemini text-embedding-004（既存）
- **API**: FastAPI（検索エンドポイント）
- **LLM**: Gemini 2.0 Flash（RAG回答生成）

#### 5. 期待される効果
- 「○○について話した会議はいつ？」のような質問に即答
- 会議の内容を踏まえた次回の文字起こし
- ナレッジベースの構築

**実装優先度**: Medium（Phase 11-4完了後）

---

## 最近の変更

### 2025-10-17: Phase 11-4検証完了
- Vector DB構築状況を徹底検証
- 7,357 embeddings稼働中を確認
- Enhanced JSON未生成問題を特定
- 検証レポート作成: [docs/phase_11_4_verification_report.md](../docs/phase_11_4_verification_report.md)

### 2025-10-17: Phase 11-3 iCloud Drive統合修正
- icloud_monitor.pyにload_dotenv()追加
- subprocess.runにenv=os.environ.copy()追加
- .envにENABLE_INTEGRATED_PIPELINE=true追加
- iCloud/Google Drive両方でPhase 11-3実行成功

### 2025-10-17: テストファイル削除
- 20251017の1分未満ファイル24個削除
- ローカル49ファイル、レジストリ16エントリ、Google Drive 27ファイル削除

### 2025-10-16: Phase 11-3最適化完了
- トピック/エンティティ抽出を1回のAPI呼び出しに統合
- エンティティ解決をLLMベースに変更
- 話者推論をentities.people活用版に強化

---

## 次のステップ

### 即座に実施
1. **Phase 11-4修正**: Enhanced JSON生成機能追加
   - integrated_pipeline.py修正
   - 動作検証（iCloud/Google Drive）
   - Vector DB自動構築確認

### 短期（1-2日）
2. **Phase 11-5実装**: Vector DB検索機能
   - semantic_search.py実装
   - FastAPI検索エンドポイント
   - 簡易UI（オプション）

### 中期（1週間）
3. **RAG統合**: コンテキスト強化型要約
4. **検索UI**: Web/モバイルインターフェース
5. **テスト自動化**: pytest導入

---

## アクティブな決定・考慮事項

### 決定1: Enhanced JSON形式
- **現在**: 未定義（未生成のため）
- **提案**: 構造化JSON + Phase 11-3結果を統合
- **含める情報**:
  - meeting_id, matched_event, calendar_participants
  - inference_result (話者推論結果)
  - summary_data (要約)
  - topics, entities（Phase 11-3 Step 5の結果）

### 決定2: Vector DB Embedding次元
- **現在**: Gemini text-embedding-004 (768次元)
- **問題**: ChromaDBデフォルト（384次元）と不一致
- **対策**: 検索時にGemini埋め込みを使用

### 決定3: Shop 1-25重複問題
- **問題**: iCloud Drive + Shop 1-25で重複検知誤検知
- **提案**: 自動削除機能（保留中）
- **ユーザー判断**: 一旦保留

### 考慮事項1: Gemini RPD制限
- **現状**: 1,500 requests/日
- **対策**: バッチ処理時のレート制限監視
- **Phase 11-5影響**: 検索時の埋め込み生成でRPD消費

### 考慮事項2: Vector DB容量
- **現在**: 43.7 MB (13,908 embeddings)
- **成長率**: 1ファイル → 約500 embeddings
- **1年後推定**: 約2GB（1日10ファイル処理想定）

---

## ブロッカー・課題

### ブロッカー1: Enhanced JSON未生成
- **状態**: 特定済み
- **対応**: 実装待ち
- **影響**: Phase 11-4自動実行不可

### 課題1: cloud_file_manager未実装
- **状態**: ModuleNotFoundError
- **優先度**: Low
- **対応**: Google Drive削除機能は手動で代替可能

### 課題2: Phase 11-5検索機能なし
- **状態**: 未実装
- **優先度**: Medium
- **対応**: Phase 11-4完了後に着手
