# Phase 11-3: 参加者DB統合 + Phase 2-6自動パイプライン - アーキテクチャ設計書

**作成日**: 2025-10-16
**バージョン**: 1.0
**ステータス**: 実装完了

---

## 1. 概要

### 1.1 目的

Phase 11-3は、以下2つの主要機能を実装します：

1. **参加者データベース統合**
   - Google Calendarイベントdescriptionから参加者情報を自動抽出
   - 構造化データベースで参加者情報を管理（UPSERT対応）
   - 要約生成時に過去の参加者情報を活用

2. **Phase 2-6自動パイプライン**
   - 話者推論（Phase 2）のカレンダー統合強化
   - トピック/エンティティ抽出（Phase 3-4）の自動実行
   - Vector DB構築（Phase 5）の自動化
   - RAG検証（Phase 6）は学習データ蓄積優先のため当面スキップ

### 1.2 設計方針

- **UPSERT対応**: 新規参加者登録と既存参加者更新の両方に対応
- **統合アプローチ**: 既存の話者推論を置き換えるのではなく、カレンダー情報で強化
- **スコープ明確化**: 「会議参加者」に特化（会話内言及は将来Phase）
- **識別方法**: カレンダーdescriptionフィールド中心、attendeesフィールド不使用
- **段階的構築**: RAG機能は当面スキップし、データ蓄積を優先

---

## 2. システムアーキテクチャ

### 2.1 全体処理フロー

```
音声ファイル（.m4a）
  ↓
Phase 1: 文字起こし（Gemini API）
  ↓
*_structured.json（Gemini文字起こし結果）
  ↓
┌─────────────────────────────────────────────────┐
│ Phase 11-3: 参加者DB統合パイプライン（リアルタイム）│
├─────────────────────────────────────────────────┤
│ Step 1: JSON読み込み                              │
│ Step 2: カレンダーイベントマッチング（LLM①）         │
│ Step 3: 参加者抽出（LLM②）                        │
│ Step 4: 参加者DB検索（SQL）                       │
│ Step 5: 話者推論（LLM③、カレンダー統合版）          │
│ Step 6: 要約生成（LLM④、参加者DB情報統合）         │
│ Step 7: 参加者DB更新（UPSERT - SQL）              │
│ Step 8: 会議情報登録（SQL）                       │
└─────────────────────────────────────────────────┘
  ↓
更新された*_structured.json + 参加者DB更新完了
  ↓
┌─────────────────────────────────────────────────┐
│ Phase 2-6: バッチ処理（非同期）                     │
├─────────────────────────────────────────────────┤
│ Phase 2: 話者推論 → スキップ（Step 5で実行済み）    │
│ Phase 3: トピック/エンティティ抽出（LLM⑤）         │
│ Phase 4: エンティティ解決（LLM⑤で実行）            │
│ Phase 5: Vector DB構築                          │
│ Phase 6: RAG検証 → スキップ（学習データ蓄積優先）   │
└─────────────────────────────────────────────────┘
  ↓
*_structured_enhanced.json + Vector DB更新完了
```

### 2.2 LLM呼び出し戦略

| Phase | LLM | 用途 | 処理タイミング | 想定時間 |
|-------|-----|------|-------------|---------|
| Step 2 | Gemini 2.0 Flash | カレンダーイベントマッチング | リアルタイム | 3-5秒 |
| Step 3 | Gemini 2.0 Flash | 参加者情報抽出 | リアルタイム | 3-5秒 |
| Step 5 | Gemini 2.5 Pro | 話者推論（強化版） | リアルタイム | 6-10秒 |
| Step 6 | Gemini 2.5 Pro | 要約生成（統合版） | リアルタイム | 6-10秒 |
| Phase 3 | Gemini 2.0 Flash | トピック/エンティティ抽出 | バッチ | 5-8秒/ファイル |

**合計**: 5つのLLM呼び出し（リアルタイム4回 + バッチ1回）

---

## 3. データベース設計

### 3.1 ER図

```
┌─────────────────┐         ┌──────────────────────┐
│  participants   │         │  participant_meetings│
├─────────────────┤         ├──────────────────────┤
│ participant_id  │◄────────│ participant_id       │
│ canonical_name  │         │ meeting_id           │
│ display_names   │         │ role_in_meeting      │
│ organization    │         └──────────────────────┘
│ role            │                    │
│ email           │                    │
│ notes           │                    ▼
│ meeting_count   │         ┌──────────────────────┐
│ first_seen_at   │         │      meetings        │
│ updated_at      │         ├──────────────────────┤
│ created_at      │         │ meeting_id           │
└─────────────────┘         │ event_id             │
                            │ title                │
                            │ date                 │
                            │ summary              │
                            │ json_file_path       │
                            │ created_at           │
                            └──────────────────────┘
```

### 3.2 テーブル定義

#### participants テーブル

| カラム名 | 型 | 制約 | 説明 |
|---------|---|------|------|
| participant_id | TEXT | PRIMARY KEY | 自動生成ID（UUID） |
| canonical_name | TEXT | NOT NULL | 正規化された氏名 |
| display_names | TEXT | - | 表示名バリエーション（JSON配列） |
| organization | TEXT | - | 所属組織 |
| role | TEXT | - | 役職 |
| email | TEXT | - | メールアドレス |
| notes | TEXT | - | 追加情報（タイムスタンプ付き） |
| meeting_count | INTEGER | DEFAULT 0 | 会議参加回数 |
| first_seen_at | TIMESTAMP | - | 初回登録日時 |
| updated_at | TIMESTAMP | - | 最終更新日時 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | レコード作成日時 |

**インデックス**: canonical_name（検索高速化）

#### meetings テーブル

| カラム名 | 型 | 制約 | 説明 |
|---------|---|------|------|
| meeting_id | TEXT | PRIMARY KEY | 自動生成ID（UUID） |
| event_id | TEXT | - | Google Calendar Event ID |
| title | TEXT | NOT NULL | 会議タイトル |
| date | DATE | - | 会議日付 |
| summary | TEXT | - | 会議要約 |
| json_file_path | TEXT | - | 関連JSONファイルパス |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | レコード作成日時 |

**インデックス**: event_id（重複チェック用）

#### participant_meetings テーブル（中間テーブル）

| カラム名 | 型 | 制約 | 説明 |
|---------|---|------|------|
| participant_id | TEXT | FOREIGN KEY | 参加者ID |
| meeting_id | TEXT | FOREIGN KEY | 会議ID |
| role_in_meeting | TEXT | - | 会議内での役割 |

**PRIMARY KEY**: (participant_id, meeting_id)

### 3.3 UPSERT ロジック

```python
def upsert_participant(canonical_name, display_names, organization, role, email, notes):
    existing = search_by_canonical_name(canonical_name)

    if existing:
        # 既存参加者の更新
        merged_display_names = deduplicate(existing.display_names + display_names)
        merged_notes = existing.notes + "\n[timestamp] " + notes

        UPDATE participants SET
            display_names = merged_display_names,
            organization = COALESCE(organization, existing.organization),
            role = COALESCE(role, existing.role),
            email = COALESCE(email, existing.email),
            notes = merged_notes,
            updated_at = CURRENT_TIMESTAMP
        WHERE participant_id = existing.participant_id
    else:
        # 新規参加者の登録
        INSERT INTO participants (
            participant_id, canonical_name, display_names,
            organization, role, email, notes, first_seen_at
        ) VALUES (generate_uuid(), ...)
```

---

## 4. コンポーネント設計

### 4.1 モジュール構成

```
realtime_transcriber_benchmark_research/
├── participants_db.sql          # データベーススキーマ定義
├── participants_db.py            # CRUD API（260行）
├── extract_participants.py       # 参加者抽出（217行）
├── enhanced_speaker_inference.py # 話者推論統合版（302行）
├── integrated_pipeline.py        # Phase 11-3メインパイプライン（280行）
├── summary_generator.py          # 要約生成（参加者DB統合対応）
└── run_phase_2_6_batch.py        # バッチ処理スクリプト（204行）
```

### 4.2 participants_db.py（CRUD API）

**主要クラス**: `ParticipantsDB`

**主要メソッド**:

```python
class ParticipantsDB:
    def __init__(self, db_path="participants.db")
    def upsert_participant(canonical_name, display_names, ...)
    def search_participants(query) -> List[Dict]
    def get_participant_info(participant_id) -> Dict
    def register_meeting(title, date, summary, json_file_path, event_id)
    def link_participant_to_meeting(participant_id, meeting_id, role)
    def get_participant_meetings(participant_id) -> List[Dict]
```

**特徴**:
- UPSERT機能による重複防止
- display_names配列のマージとデュプリケーション除去
- notes追記時のタイムスタンプ自動付与
- COALESCE関数による既存値保護

### 4.3 extract_participants.py（参加者抽出）

**主要関数**: `extract_participants_from_description(description: str) -> List[Dict]`

**処理フロー**:
1. **キーワード検出**: 「参加者」「出席者」「メンバー」等のキーワード有無確認
2. **LLM抽出**: Gemini 2.0 Flashでstructured JSON出力
3. **結果検証**: 必須フィールド（canonical_name）の存在確認

**出力形式**:
```json
[
  {
    "canonical_name": "田中",
    "display_names": ["田中", "田中部長"],
    "role": "部長",
    "organization": "営業部"
  }
]
```

**エラー処理**:
- キーワード不在時: 空リスト返却（警告出力）
- LLM失敗時: エラーメッセージ出力 + 空リスト返却
- JSON解析失敗時: 例外キャッチ + 空リスト返却

### 4.4 enhanced_speaker_inference.py（話者推論統合版）

**主要関数**: `infer_speakers_with_participants(segments, calendar_participants, file_context)`

**統合アプローチ**:
```python
# プロンプトにカレンダー参加者情報を追加
if calendar_participants:
    prompt += "\n【カレンダー参加者情報】\n"
    for p in calendar_participants:
        prompt += f"- {p['canonical_name']}"
        if p.get('role'):
            prompt += f" ({p['role']})"
        prompt += "\n"
```

**出力形式**:
```json
{
  "sugimoto_speaker": "Speaker 0",
  "participants_mapping": {
    "Speaker 0": "杉本",
    "Speaker 1": "田中"
  },
  "confidence": "high",
  "reasoning": "カレンダー情報により田中部長の参加が確認されたため..."
}
```

**精度向上メカニズム**:
- カレンダー情報なし: confidence = "medium"（既存精度95%）
- カレンダー情報あり: confidence = "high"（期待精度98%以上）

### 4.5 integrated_pipeline.py（メインパイプライン）

**主要関数**: `run_phase_11_3_pipeline(structured_file_path: str) -> Dict`

**8ステップ処理**:

```python
# Step 1: JSON読み込み
with open(structured_file_path) as f:
    data = json.load(f)

# Step 2: カレンダーイベントマッチング（LLM①）
matched_event = match_calendar_event(data['metadata'])

# Step 3: 参加者抽出（LLM②）
if matched_event and matched_event.get('description'):
    calendar_participants = extract_participants_from_description(
        matched_event['description']
    )

# Step 4: 参加者DB検索
participants_past_info = {}
for p in calendar_participants:
    results = db.search_participants(p['canonical_name'])
    if results:
        participants_past_info[p['canonical_name']] = results[0]

# Step 5: 話者推論（LLM③）
speaker_result = infer_speakers_with_participants(
    segments=data['segments'],
    calendar_participants=calendar_participants,
    file_context=data.get('metadata', {}).get('file_name', '')
)

# Step 6: 要約生成（LLM④）
participants_context = format_participants_context(participants_past_info)
summary_data = generate_summary_with_calendar(
    transcript_segments=data['segments'],
    matched_event=matched_event,
    participants_context=participants_context
)

# Step 7: 参加者DB更新（UPSERT）
for p in calendar_participants:
    participant_id = db.upsert_participant(
        canonical_name=p['canonical_name'],
        display_names=p.get('display_names', []),
        organization=p.get('organization'),
        role=p.get('role')
    )

# Step 8: 会議情報登録
meeting_id = db.register_meeting(
    title=matched_event.get('summary', data['metadata'].get('file_name')),
    date=matched_event.get('start', {}).get('date'),
    summary=summary_data.get('summary'),
    json_file_path=structured_file_path,
    event_id=matched_event.get('id')
)
```

**エラーハンドリング**:
- 各ステップで try-except 実装
- エラー時は警告出力して後続処理継続
- 最終的なサマリーレポート出力

### 4.6 run_phase_2_6_batch.py（バッチ処理）

**主要関数**: `run_phase_2_6_for_all_files(downloads_dir="downloads")`

**処理フロー**:

```python
# Phase 2: スキップ（integrated_pipeline.pyで実行済み）
print("⏭ スキップ（Phase 11-3 integrated_pipeline.py で既に実行済み）")

# Phase 3: トピック/エンティティ抽出（個別ファイル処理）
for file_path in structured_files:
    subprocess.run([
        "venv/bin/python3",
        "add_topics_entities.py",
        file_path
    ])

# Phase 4: エンティティ解決（全ファイル集約処理）
enhanced_files = glob.glob("*_structured_enhanced.json")
subprocess.run([
    "venv/bin/python3",
    "entity_resolution_llm.py"
] + enhanced_files)

# Phase 5: Vector DB構築（全ファイル処理）
subprocess.run([
    "venv/bin/python3",
    "build_unified_vector_index.py"
] + enhanced_files)

# Phase 6: RAG検証（スキップ）
print("⏭ スキップ（学習データ蓄積待ち、Phase 5のVector DBは継続構築）")
```

**プロセス管理**:
- subprocess.run() でタイムアウト保護
- 各Phase毎に成功/エラーカウント
- 詳細ログ出力（最後20-30行表示）

---

## 5. データフロー

### 5.1 参加者情報の流れ

```
Google Calendar Event
  ↓ description フィールド
extract_participants.py (LLM②)
  ↓ List[Dict] (canonical_name, display_names, role, org)
participants_db.py (UPSERT)
  ↓ 検索・取得
enhanced_speaker_inference.py (LLM③)
  ↓ カレンダー統合話者推論
summary_generator.py (LLM④)
  ↓ 参加者DBコンテキスト統合要約
participants_db.py (UPSERT)
  ↓ 更新完了
meetings テーブル + participant_meetings テーブル
```

### 5.2 JSON ファイルの変遷

```
Phase 1出力:
*_structured.json
  ├─ metadata: {file_name, duration, ...}
  ├─ segments: [{start, end, text, speaker}]
  └─ full_text: "..."

Phase 11-3処理後:
*_structured.json (更新)
  ├─ metadata: (同上) + {date: "20251016"}
  ├─ segments: (同上) + speaker_name追加
  ├─ full_text: (同上)
  └─ summary: {...} (参加者DB情報統合版)

Phase 3処理後:
*_structured_enhanced.json (新規)
  ├─ metadata, segments, full_text (継承)
  ├─ summary (継承)
  ├─ topics: [{name, summary, keywords}]
  ├─ entities: {people, organizations, dates, action_items}
  └─ segments: (トピックID付き)

Phase 4処理後:
*_structured_enhanced.json (更新)
  ├─ entities: (同上) + canonical_name, entity_id追加
  └─ (その他継承)
```

---

## 6. インターフェース仕様

### 6.1 環境変数

| 変数名 | 説明 | 必須 | デフォルト |
|-------|------|------|-----------|
| GEMINI_API_KEY_FREE | Gemini API Free tierキー | ✅ | - |
| GEMINI_API_KEY_PAID | Gemini API Paid tierキー | - | - |
| USE_PAID_TIER | Paid tier使用フラグ | - | false |
| GOOGLE_CLIENT_ID | Google Calendar API Client ID | ✅ | - |
| GOOGLE_CLIENT_SECRET | Google Calendar API Secret | ✅ | - |
| PARTICIPANTS_DB_PATH | 参加者DB保存パス | - | participants.db |

### 6.2 コマンドライン使用例

#### Phase 11-3パイプライン実行

```bash
# 単一ファイル処理
python3 integrated_pipeline.py downloads/meeting_20251016_structured.json

# 出力例:
# ========================================
# Phase 11-3 統合パイプライン実行
# ========================================
#
# Step 1: JSON読み込み完了 (69 segments)
# Step 2: カレンダーイベントマッチング完了
#   イベント: "週次定例ミーティング"
#   参加者情報: 田中部長、佐藤課長
# Step 3: 参加者抽出完了 (2名)
# Step 4: 参加者DB検索完了
#   田中: 過去5回の会議参加
#   佐藤: 過去3回の会議参加
# Step 5: 話者推論完了 (confidence: high)
#   Speaker 0 → 杉本
#   Speaker 1 → 田中
# Step 6: 要約生成完了
#   トピック数: 7
#   キーワード数: 10
# Step 7: 参加者DB更新完了
# Step 8: 会議情報登録完了
#
# ✅ Phase 11-3パイプライン完了
```

#### バッチ処理実行

```bash
# downloadsディレクトリ内全ファイル処理
python3 run_phase_2_6_batch.py downloads

# 出力例:
# ======================================================================
# [Batch] Phase 2-6 バッチ処理開始
# ======================================================================
#
# 対象ディレクトリ: downloads
# 対象ファイル数: 12
#
# [Phase 3] トピック/エンティティ抽出
# [1/12] meeting_20251016_structured.json ✓ 成功
# [2/12] meeting_20251015_structured.json ✓ 成功
# ...
# [Phase 3] 完了: 成功 12件、エラー 0件
#
# [Phase 4] エンティティ解決
# ✓ 成功
#   人物: 15名, 組織: 21個
#
# [Phase 5] Vector DB構築
# ✓ 成功
#   総ドキュメント: 7357
#
# ✅ バッチ処理完了
```

---

## 7. パフォーマンス特性

### 7.1 処理時間

| 処理 | 平均時間 | 備考 |
|-----|---------|------|
| Step 2: カレンダーマッチング | 3-5秒 | LLM呼び出し1回 |
| Step 3: 参加者抽出 | 3-5秒 | LLM呼び出し1回 |
| Step 4: DB検索 | <0.1秒 | SQL SELECT |
| Step 5: 話者推論 | 6-10秒 | LLM呼び出し1回（Pro） |
| Step 6: 要約生成 | 6-10秒 | LLM呼び出し1回（Pro） |
| Step 7: DB更新 | <0.1秒 | SQL UPSERT |
| Step 8: 会議登録 | <0.1秒 | SQL INSERT |
| **Phase 11-3 合計** | **18-30秒** | **LLM呼び出し4回** |
| Phase 3: トピック/エンティティ | 5-8秒/ファイル | バッチ処理 |
| Phase 4: エンティティ解決 | 10-15秒（全体） | バッチ処理 |
| Phase 5: Vector DB構築 | 20-30秒（全体） | バッチ処理 |
| **バッチ合計（12ファイル）** | **約10分** | **非同期実行可** |

### 7.2 API呼び出し数とコスト

**Gemini API使用状況**（1ファイルあたり）:

| API | モデル | 用途 | 入力トークン | 出力トークン | コスト（Free tier） |
|-----|-------|------|------------|------------|-------------------|
| LLM① | 2.0 Flash | カレンダーマッチング | ~500 | ~100 | $0 |
| LLM② | 2.0 Flash | 参加者抽出 | ~800 | ~200 | $0 |
| LLM③ | 2.5 Pro | 話者推論 | ~2000 | ~500 | $0 |
| LLM④ | 2.5 Pro | 要約生成 | ~3000 | ~800 | $0 |
| LLM⑤ | 2.0 Flash | トピック抽出 | ~4000 | ~1000 | $0 |
| **合計** | - | - | **~10,300** | **~2,600** | **$0** |

**月間制限（Gemini API Free tier）**:
- 2.0 Flash: 1,500 RPD（1日あたりのリクエスト数）
- 2.5 Pro: 50 RPD
- **Phase 11-3想定**: 1ファイル = 4リクエスト → 最大12ファイル/日（Pro制限）

### 7.3 データベースサイズ

**想定データ量（1年運用）**:

| テーブル | レコード数 | サイズ推定 |
|---------|----------|----------|
| participants | 50-100名 | 50KB |
| meetings | 500-1000件 | 500KB |
| participant_meetings | 1500-3000件 | 200KB |
| **合計** | - | **~1MB** |

**インデックスによる高速化**:
- canonical_name検索: O(log n) → <1ms
- event_id重複チェック: O(1) → <1ms

---

## 8. エラーハンドリング

### 8.1 エラー分類と対応

| エラー種別 | 発生箇所 | 対応 |
|----------|---------|------|
| API Key不在 | 全LLM呼び出し | エラーメッセージ出力 + 終了 |
| LLM呼び出し失敗 | Step 2, 3, 5, 6 | 警告出力 + 後続処理継続 |
| JSON解析失敗 | Step 1, 3 | エラー出力 + 空データで継続 |
| DB接続失敗 | Step 4, 7, 8 | エラー出力 + 終了 |
| カレンダーAPI失敗 | Step 2 | 警告出力 + カレンダーなしで継続 |
| ファイル読み込み失敗 | Step 1 | エラー出力 + 終了 |

### 8.2 リトライ戦略

```python
def call_llm_with_retry(func, max_retries=3, backoff=2):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(backoff ** attempt)
```

**適用箇所**:
- LLM呼び出し（Step 2, 3, 5, 6, Phase 3）
- Google Calendar API（Step 2）

### 8.3 ログ出力レベル

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# INFO: 処理進捗、成功通知
# WARNING: LLM失敗、カレンダー不一致、DB検索ヒットなし
# ERROR: 致命的エラー（処理終了）
```

---

## 9. セキュリティ考慮事項

### 9.1 データ保護

- **個人情報**: participants.dbは `.gitignore` に追加
- **API Key**: 環境変数経由での管理、コードに直接記述禁止
- **Google認証**: OAuth 2.0 token保存（`token.json`）は `.gitignore` に追加

### 9.2 入力検証

```python
def validate_participant_data(data: Dict) -> bool:
    """参加者データの必須フィールドチェック"""
    if not data.get('canonical_name'):
        return False
    if data.get('display_names') and not isinstance(data['display_names'], list):
        return False
    return True
```

### 9.3 SQLインジェクション対策

```python
# ✅ Good: パラメータバインディング使用
cursor.execute(
    "SELECT * FROM participants WHERE canonical_name = ?",
    (name,)
)

# ❌ Bad: 文字列結合（使用禁止）
cursor.execute(
    f"SELECT * FROM participants WHERE canonical_name = '{name}'"
)
```

---

## 10. テスト戦略

### 10.1 単体テスト

**participants_db.py**:
```python
def test_upsert_participant():
    db = ParticipantsDB(":memory:")

    # 新規登録
    pid = db.upsert_participant("田中", ["田中", "田中部長"], "営業部", "部長")
    assert pid is not None

    # 更新（display_names追加）
    pid2 = db.upsert_participant("田中", ["田中さん"], "営業部", "部長")
    assert pid == pid2

    # 確認
    info = db.get_participant_info(pid)
    assert set(json.loads(info['display_names'])) == {"田中", "田中部長", "田中さん"}
```

**extract_participants.py**:
```python
def test_extract_participants():
    description = """
    参加者：
    - 田中部長（営業部）
    - 佐藤課長（企画部）
    """

    result = extract_participants_from_description(description)
    assert len(result) == 2
    assert result[0]['canonical_name'] == "田中"
    assert result[0]['role'] == "部長"
```

### 10.2 統合テスト

**integrated_pipeline.py**:
```bash
# 実際のJSONファイルを使った統合テスト
python3 integrated_pipeline.py downloads/test_meeting_structured.json

# 検証項目:
# - 8ステップ全て成功
# - DB内に参加者・会議情報登録確認
# - JSONファイル更新確認（speaker_name, summary）
```

### 10.3 バッチ処理テスト

```bash
# 12ファイル一括処理テスト
python3 run_phase_2_6_batch.py downloads

# 検証項目:
# - Phase 3: 12/12ファイル成功
# - Phase 4: エンティティ解決完了
# - Phase 5: Vector DB構築完了
```

---

## 11. 運用ガイドライン

### 11.1 デプロイ手順

1. **環境変数設定**
   ```bash
   export GEMINI_API_KEY_FREE="your_api_key"
   export GOOGLE_CLIENT_ID="your_client_id"
   export GOOGLE_CLIENT_SECRET="your_client_secret"
   ```

2. **データベース初期化**
   ```bash
   sqlite3 participants.db < participants_db.sql
   ```

3. **依存パッケージインストール**
   ```bash
   pip install -r requirements.txt
   ```

4. **Google Calendar認証**
   ```bash
   python3 calendar_integration.py  # 初回のみ
   ```

### 11.2 定期メンテナンス

**週次タスク**:
- participants.db のバックアップ
- display_names重複チェックと手動クリーニング

**月次タスク**:
- Vector DBの再構築（`build_unified_vector_index.py`）
- エンティティ解決精度の手動レビュー

### 11.3 トラブルシューティング

**Q: カレンダーイベントがマッチしない**
A: metadata内のdateフィールド確認。Phase 1で生成されていない場合はStep 2がスキップされる。

**Q: 参加者が抽出されない**
A: カレンダーdescriptionに「参加者」「出席者」等のキーワードが含まれているか確認。

**Q: 話者推論の精度が低い**
A: カレンダー情報があっても精度が低い場合、file_contextの情報量不足の可能性。

---

## 12. 今後の拡張方針

### 12.1 短期（Phase 11-4候補）

- **会話内言及の参加者抽出**: Phase 3のエンティティ抽出結果を活用
- **参加者プロフィール画像**: Google Contactsとの統合
- **参加者関係グラフ**: NetworkXによる共起分析

### 12.2 中期（Phase 12候補）

- **RAG機能の本格実装**: Phase 6の有効化
- **セマンティック検索UI**: Gradio/Streamlitでの検索インターフェース
- **参加者ダッシュボード**: 参加回数、トピック統計の可視化

### 12.3 長期（Phase 13以降）

- **音声認識の話者分離統合**: Pyannoteとの連携
- **リアルタイム文字起こし**: WebSocketでのストリーミング対応
- **マルチモーダル対応**: 画面共有・スライド解析

---

## 13. 参考資料

### 13.1 関連ドキュメント

- [Phase 11-1: Google Calendar統合](./phase-11-1-google-calendar-integration.md)
- [Phase 11-3: 検証レポート](./phase-11-3-validation.md)
- [パイプラインアーキテクチャ](./pipeline-architecture.md)

### 13.2 外部リンク

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Google Calendar API Reference](https://developers.google.com/calendar/api/v3/reference)
- [SQLite Documentation](https://www.sqlite.org/docs.html)

---

**End of Document**
