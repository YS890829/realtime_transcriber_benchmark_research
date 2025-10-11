# Phase 6 実装状況

## ✅ Phase 6-1: 基本メタデータの抽出と構造化（完了）

### 目標
文字起こしテキストに基本的なメタデータを付与し、JSON形式で構造化

### 完了タスク
- [x] ファイルメタデータの抽出（名前、サイズ、日時、長さ、形式）
- [x] 文字起こしメタデータの生成（文字数、単語数、言語、処理時刻）
- [x] テキストセグメント化（セグメント単位）
- [x] タイムスタンプ付与（Whisper API word-level timestamps）
- [x] JSON構造化出力
- [x] 25MB超ファイルの自動チャンク処理

### 実装ファイル
- `structured_transcribe.py` (349行)

### 技術スタック
- Whisper API with `timestamp_granularities=["word", "segment"]`
- Python JSON
- ffmpeg (チャンク分割)

### テスト結果
- ✅ Test Recording.m4a (101MB, 108.3分)
- ✅ 1,976セグメント、13,665単語タイムスタンプ抽出成功
- ✅ 処理時間: 24分（4.5倍速処理）
- ✅ 出力: `Test Recording_structured.json` (1.6MB)

### JSON構造
```json
{
  "metadata": {
    "file": {...},
    "transcription": {...}
  },
  "segments": [...],
  "words": [...],
  "full_text": "...",
  "summary": "..."
}
```

### 完了日
2025-10-11

---

## ⚠️ Phase 6-2: 話者識別とトピック抽出（部分完了・課題あり）

### 目標
話者を識別し、トピックごとにセグメント化

### 完了タスク ✅
- [x] pyannote.audioインストール
- [x] HuggingFace Token設定 (`[REDACTED]`)
- [x] トピック抽出とセグメント化（Gemini API）
- [x] キーワード・エンティティ抽出（人名、組織、日付、アクションアイテム）
- [x] 構造化データを活用した要約生成
- [x] JSON構造の拡張

### 未完了タスク（残課題）❌
- [ ] **話者識別（Speaker Diarization with pyannote.audio）**
  - **問題**: scipy/numpy互換性エラー
  - **エラー1**: `expected np.ndarray (got numpy.ndarray)`
    - 発生環境: numpy 2.3.3
    - 対応: numpy 1.26.4にダウングレード → エラー2に遭遇
  - **エラー2**: `All ufuncs must have type numpy.ufunc. Received (<ufunc 'sph_legendre_p'>, ...)`
    - 発生環境: numpy 1.26.4 + scipy
    - 原因: scipyとnumpyのバージョン不整合
  - **現状**: フォールバック機能で単一話者として処理

- [ ] 話者ごとの統計（発言時間、割合、ターン数）
  - 話者識別が完了次第実装可能

### 実装ファイル
- `enhanced_transcribe.py` (568行) - フル版（音声ファイルから全処理）
- `add_speaker_diarization.py` (349行) - 軽量版（Phase 6-1のJSONを入力として使用）

### 技術スタック
- pyannote.audio 3.4.0
- Gemini 2.0 Flash (トピック抽出、エンティティ抽出、要約)
- HuggingFace Hub (pyannote/speaker-diarization-3.1)

### テスト結果（部分成功）
#### 成功項目
- ✅ トピック抽出: **6トピック検出**
  1. キャリア戦略/今後の方向性
  2. AI技術の活用と営業の未来
  3. 人間関係と幸せ
  4. 投資と株
  5. (その他2トピック)

- ✅ エンティティ抽出: **6名の人名検出**
  - 大竹、岡崎、スー、山瀬たかし、等

- ✅ 組織名抽出: リステック、セールステップ、等

- ✅ 構造化要約: 成功
  - 話者情報を含む要約生成
  - トピック別サマリー
  - エンティティ情報の統合

#### 失敗項目
- ❌ 話者識別: scipy/numpy互換性問題により失敗
  - 検出話者数: 1（フォールバック）
  - 実際の話者数: 不明（複数話者の可能性あり）

### 拡張JSON構造
```json
{
  "metadata": {...},
  "speakers": [
    {
      "id": "SPEAKER_00",
      "label": "Speaker 1",
      "total_duration": 3272.98,
      "speaking_percentage": 100.0
    }
  ],
  "topics": [
    {
      "id": "topic_1",
      "name": "...",
      "summary": "...",
      "keywords": [...]
    }
  ],
  "entities": {
    "people": [...],
    "organizations": [...],
    "dates": [...],
    "action_items": [...]
  },
  "segments": [
    {
      "id": 1,
      "speaker": "SPEAKER_00",
      "topics": [],
      "start": 0.0,
      "end": 5.2,
      "text": "..."
    }
  ],
  "words": [...],
  "full_text": "...",
  "summary": "..."
}
```

### 決定事項（2025-10-11 15:35）
**話者識別（Speaker Diarization）は保留**

**理由:**
- pyannote.audioの処理時間が非常に長い（108分音声で2時間以上実行中）
- 複数の互換性問題（numpy/scipy、m4aフォーマット）
- 実用性を考慮し、優先度を下げる

**対応:**
- Phase 6-2は「トピック抽出・エンティティ抽出」の実装で完了とする
- 話者識別は将来の改善課題として記録
- **Phase 6-3（セマンティック検索とRAG）に進む**

### 試行した解決策
1. ✅ numpy 2.3.3 → 1.26.4にダウングレード
   - 結果: scipy互換性エラー発生
2. ✅ scipy 1.16.2 → 1.11.4にダウングレード
   - 結果: ufuncエラー発生
3. ✅ FFmpegでm4a→WAV変換を実装
   - 結果: フォーマットエラーは解決、処理時間問題が発覚（2時間以上）

### 今後の対応（保留）
話者識別が必要になった場合の選択肢:
1. 有料API（AssemblyAI: $0.00025/秒）の利用検討
2. WhisperXへの切り替え検討
3. より軽量な話者識別手法の調査
4. 短時間音声でのテスト実施

### 作業日
2025-10-11

---

## ⬜ Phase 6-3: セマンティック検索とRAG（未開始）

### 目標
複数の文字起こしを横断した検索・分析機能

### タスク
- [ ] セマンティック検索の実装（ChromaDB + embeddings）
- [ ] フォルダー/カテゴリ管理システム
- [ ] 自動カテゴリ分類とタグ付け
- [ ] クロス分析機能（複数会議を横断したトレンド分析）
- [ ] 引用付き質問応答（RAG with LangChain）
- [ ] タイムスタンプリンク機能
- [ ] 可視化機能（マインドマップ、発言時間分析、キーワードクラウド）

### 技術スタック
- ChromaDB (ローカルベクトルDB)
- OpenAI Embeddings (text-embedding-3-small)
- LangChain (RAG framework)
- matplotlib/plotly (可視化)

### 推定工数
6-8時間

---

## コスト分析

### 現状（Phase 5）
- Whisper API: $0.006/分 × 120分 = **$0.72**
- Gemini API: 無料（128k tokens/分）
- **合計: $0.72 / 2時間音声**

### Phase 6-1完了時
- Whisper API: $0.72（変更なし）
- **合計: $0.72 / 2時間音声**

### Phase 6-2完了時（予定）
- Whisper API: $0.72
- pyannote.audio: **無料**（ローカル処理）
- Gemini API: **無料**（トピック抽出、エンティティ抽出、要約）
- **合計: $0.72 / 2時間音声**

### Phase 6-3完了時（予定）
- Whisper API: $0.72
- OpenAI Embeddings: $0.00002/1k tokens × 約27k tokens = **$0.00054**
- ChromaDB: **無料**（ローカル）
- **合計: $0.72054 / 2時間音声**
- **追加コスト: $0.00054（約0.08円）**

## 環境情報

### インストール済みライブラリ
- openai
- google-generativeai
- python-dotenv
- pyannote.audio 3.4.0
- torch 2.2.2
- torchaudio 2.2.2
- numpy 1.26.4
- scipy 1.16.2

### 設定済みトークン
- OPENAI_API_KEY: 設定済み
- GEMINI_API_KEY: 設定済み
- HUGGINGFACE_TOKEN: 設定済み（[REDACTED]）

### テストファイル
**メインテストファイル:** `downloads/Test Recording_20min.m4a` (18MB, 20分)
- **Phase 6-1, 6-2, 6-3のすべてのテストで使用**
- Test Recording.m4aの最初の20分を抽出（ffmpeg使用）
- 処理時間が短く、実用的なテストが可能
- Phase 6-1テスト結果: 4,035文字、489セグメント、2,656単語タイムスタンプ
- Phase 6-2テスト結果: 4トピック、2名の人物、12組織

**元ファイル（参考）:** `downloads/Test Recording.m4a` (101MB, 108.3分)
- 長時間処理テスト用（必要な場合のみ使用）
