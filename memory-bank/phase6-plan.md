# Phase 6: データ構造化とメタデータ付与

## 目標
音声データから文字起こしした情報に、構造化とメタデータを付与し、要約や分析の精度を高める。

## リサーチサマリー（Unstructured, Plaud, Granola）

### Unstructured.io
**専門分野**: ドキュメント要素の構造化
- 30種類以上のメタデータ（element type, hierarchy, xy coordinates, language等）
- セマンティックチャンキング（意味的な単位での分割）
- 要素タイプ分類（Title, NarrativeText, ListItem等）
- 階層構造の保持

### Plaud AI
**専門分野**: 会話特化のメタデータ抽出
- 話者識別（Speaker Diarization）
- カスタム語彙辞書（医療、法律、金融等10+業界）
- 3000+要約テンプレート
- マインドマップ生成
- マルチモーダル統合（音声+ノート+画像）

### Granola
**専門分野**: 文脈理解と検索可能性
- コンテキスト分析（会議タイプの自動判定）
- 参加者メタデータ（役割とコンテキスト）
- トピック分離と時系列整理
- タイムスタンプリンク（元発言箇所への直接ジャンプ）
- フォルダー組織化（プロジェクト/クライアント/チーム別）
- クロス会議分析（複数会議を横断した検索）
- 引用付きAI回答（必ず元の発言を引用）

---

## Phase 6 実装アプローチ

### 段階的実装（3ステップ）

#### **Phase 6-1: 基本メタデータの抽出と構造化**
**目標**: 文字起こしテキストに基本的なメタデータを付与し、JSON形式で構造化

**実装タスク:**
1. **ファイルメタデータの抽出**
   - ファイル名
   - ファイルサイズ
   - 録音日時（ファイル作成日時）
   - 音声長（duration）
   - ファイル形式

2. **文字起こしメタデータの生成**
   - 文字数
   - 単語数
   - 推定話者数（文体分析から推測）
   - 言語（ja固定 or 自動検出）
   - 処理日時

3. **テキストセグメント化**
   - 文単位での分割
   - 段落単位での分割
   - タイムスタンプの付与（Whisper APIのword-level timestamps利用）

4. **JSON構造化**
   ```json
   {
     "metadata": {
       "file_name": "...",
       "file_size_bytes": 123456,
       "recorded_at": "2025-10-11T12:00:00",
       "duration_seconds": 120,
       "format": "m4a",
       "transcribed_at": "2025-10-11T12:05:00",
       "language": "ja",
       "word_count": 500,
       "char_count": 1500,
       "estimated_speakers": 2
     },
     "segments": [
       {
         "id": 1,
         "start": 0.0,
         "end": 5.2,
         "text": "...",
         "words": [...]
       }
     ],
     "full_text": "...",
     "summary": "..."
   }
   ```

**技術スタック:**
- Whisper API with `timestamp_granularities=["word", "segment"]`
- Python JSON処理
- datetime, pathlib

**完了条件**:
- JSON形式での構造化データ出力
- 基本メタデータの完全性

---

#### **Phase 6-2: 話者識別とトピック抽出**
**目標**: 話者を識別し、トピックごとにセグメント化

**実装タスク:**
1. **話者識別（Speaker Diarization）**
   - pyannote.audioを使用した話者分離
   - または、Whisper API + LLMによる話者推測
   - 各セグメントに話者ラベル付与（Speaker 1, Speaker 2等）

2. **トピック抽出**
   - LLM（Gemini/Claude）を使用したトピックセグメント化
   - 各トピックに名前とサマリーを付与
   - トピック間の関連性分析

3. **キーワード・エンティティ抽出**
   - 重要な固有名詞（人名、地名、組織名）
   - 専門用語
   - アクションアイテム（TODO項目）
   - 日付・時刻の言及

4. **JSON構造の拡張**
   ```json
   {
     "metadata": {...},
     "speakers": [
       {
         "id": "speaker_1",
         "label": "Speaker 1",
         "total_duration": 60.5,
         "speaking_percentage": 50.4
       }
     ],
     "topics": [
       {
         "id": "topic_1",
         "name": "プロジェクト進捗報告",
         "summary": "...",
         "start_time": 0.0,
         "end_time": 30.0,
         "segments": [1, 2, 3]
       }
     ],
     "entities": {
       "people": ["田中さん", "佐藤さん"],
       "organizations": ["ABC社"],
       "dates": ["来週月曜日"],
       "action_items": ["見積もり作成", "資料送付"]
     },
     "segments": [
       {
         "id": 1,
         "speaker": "speaker_1",
         "topic": "topic_1",
         "start": 0.0,
         "end": 5.2,
         "text": "...",
         "keywords": ["進捗", "期限"]
       }
     ]
   }
   ```

**技術スタック:**
- pyannote.audio or Whisper + LLM
- Gemini API (トピック抽出、エンティティ認識)
- spaCy (日本語NLP、オプション)

**完了条件**:
- 話者ラベルの精度 > 80%
- トピック分類の有用性検証

---

#### **Phase 6-3: 高度な分析とナレッジベース構築**
**目標**: 複数の文字起こしを横断した検索・分析機能

**実装タスク:**
1. **セマンティック検索の実装**
   - ベクトルDB（ChromaDB or FAISS）の導入
   - セグメント単位でのembedding生成
   - 意味的な類似検索の実現

2. **フォルダー/カテゴリ管理**
   - 自動カテゴリ分類（会議タイプ、プロジェクト等）
   - タグ付け機能
   - フォルダー階層の作成

3. **クロス分析機能**
   - 複数会議を横断したトピックトレンド分析
   - 頻出キーワード・トピックの可視化
   - 時系列での変化追跡

4. **引用付き質問応答（RAG）**
   - LLM + ベクトルDB
   - 質問に対する回答を元の発言箇所を引用して生成
   - タイムスタンプリンクの提供

5. **可視化機能**
   - トピックマインドマップ
   - 話者ごとの発言時間分析
   - キーワードクラウド

**技術スタック:**
- ChromaDB or FAISS（ベクトルDB）
- OpenAI Embeddings or Gemini Embeddings
- LangChain（RAG構築）
- matplotlib/plotly（可視化）

**完了条件**:
- セマンティック検索の実現
- RAG質問応答の精度検証
- 複数会議の統合分析デモ

---

## データスキーマ設計（最終形）

```json
{
  "document_id": "uuid-xxx",
  "version": "1.0",
  "metadata": {
    "file": {
      "name": "meeting_2025-10-11.m4a",
      "size_bytes": 1048576,
      "format": "m4a",
      "source": "google_drive",
      "drive_file_id": "xxx"
    },
    "recording": {
      "recorded_at": "2025-10-11T12:00:00+09:00",
      "duration_seconds": 1800,
      "sample_rate": 44100
    },
    "processing": {
      "transcribed_at": "2025-10-11T12:30:00+09:00",
      "transcription_model": "whisper-1",
      "summary_model": "gemini-2.0-flash",
      "processing_time_seconds": 45.2
    },
    "content": {
      "language": "ja",
      "char_count": 5000,
      "word_count": 1500,
      "sentence_count": 120,
      "estimated_speakers": 3
    },
    "classification": {
      "meeting_type": "sales_call",  // auto-detected or manual
      "category": "customer_feedback",
      "tags": ["Q4", "feature_request", "pricing"],
      "folder": "/sales/2025-Q4"
    }
  },
  "speakers": [
    {
      "id": "speaker_1",
      "label": "Speaker 1",
      "name": null,  // manual annotation
      "role": null,  // manual annotation
      "total_duration_seconds": 600,
      "speaking_percentage": 33.3,
      "turn_count": 25,
      "avg_turn_duration": 24.0
    }
  ],
  "topics": [
    {
      "id": "topic_1",
      "name": "製品フィードバック",
      "summary": "顧客から新機能のリクエストがあった。特にモバイル対応が強く求められている。",
      "start_time": 120.0,
      "end_time": 450.0,
      "duration_seconds": 330.0,
      "segments": [3, 4, 5, 6],
      "keywords": ["モバイル", "新機能", "UI改善"],
      "sentiment": "positive"  // optional
    }
  ],
  "entities": {
    "people": [
      {"text": "田中さん", "count": 5, "segments": [1, 3, 7]}
    ],
    "organizations": [
      {"text": "ABC株式会社", "count": 3, "segments": [2, 4]}
    ],
    "locations": [],
    "dates": [
      {"text": "来週月曜日", "normalized": "2025-10-18", "segments": [8]}
    ],
    "action_items": [
      {"text": "見積もり作成", "assignee": null, "due_date": null, "segment": 12}
    ]
  },
  "segments": [
    {
      "id": 1,
      "speaker": "speaker_1",
      "topic": "topic_1",
      "start_time": 0.0,
      "end_time": 5.2,
      "text": "今日はよろしくお願いします。",
      "words": [
        {"word": "今日", "start": 0.0, "end": 0.8},
        {"word": "は", "start": 0.8, "end": 1.0},
        {"word": "よろしく", "start": 1.2, "end": 2.0},
        {"word": "お願い", "start": 2.1, "end": 2.8},
        {"word": "します", "start": 2.9, "end": 3.5}
      ],
      "sentence_type": "greeting",  // optional
      "keywords": ["挨拶"],
      "embedding": [0.1, 0.2, ...]  // for semantic search
    }
  ],
  "full_text": "今日はよろしくお願いします。...",
  "summary": {
    "executive_summary": "...",
    "key_points": ["...", "...", "..."],
    "detailed_summary": "...",
    "action_items_summary": "..."
  },
  "insights": {
    "key_topics": ["製品フィードバック", "価格交渉"],
    "sentiment_overall": "positive",
    "urgency_level": "medium",
    "follow_up_required": true
  }
}
```

---

## 技術選定

### コア技術
- **文字起こし**: OpenAI Whisper API (word-level timestamps対応)
- **要約**: Google Gemini API
- **話者識別**: pyannote.audio or LLM-based inference
- **トピック抽出**: Gemini API with structured prompts
- **ベクトルDB**: ChromaDB (ローカル、シンプル)
- **Embedding**: OpenAI text-embedding-3-small
- **RAG**: LangChain

### ストレージ
- **JSON**: 各文字起こしの構造化データ
- **SQLite**: メタデータ検索用インデックス（オプション）
- **ChromaDB**: セマンティック検索用

---

## 段階的実装スケジュール

| Phase | タスク | 完了条件 | 推定工数 |
|-------|--------|---------|---------|
| 6-1 | 基本メタデータ抽出 | JSON構造化出力 | 2-3時間 |
| 6-2 | 話者識別+トピック抽出 | 話者ラベル付与 | 4-5時間 |
| 6-3 | セマンティック検索+RAG | 横断検索実現 | 6-8時間 |

---

## Phase 5との統合

### Phase 5（現状）
- Google Drive監視 → 文字起こし → 要約生成

### Phase 6（追加）
- 文字起こし → **構造化+メタデータ付与** → JSON保存 → ベクトルDB登録

### ファイル構成
```
downloads/
  ├── audio.m4a
  ├── audio_transcription.txt  # Phase 5
  ├── audio_summary.md         # Phase 5
  └── audio_structured.json    # Phase 6 NEW
```

---

## 完了条件（Phase 6全体）

1. ✅ 基本メタデータの自動抽出
2. ✅ 話者識別の実装
3. ✅ トピック自動抽出
4. ✅ JSON形式での構造化データ出力
5. ✅ セマンティック検索の実現
6. ✅ 複数会議を横断した分析機能
7. ✅ RAG質問応答システムの構築

---

## 将来の拡張可能性

- **リアルタイム文字起こし**: ストリーミング処理対応
- **マルチモーダル**: 画像、ビデオとの統合
- **自動フォローアップ**: アクションアイテムの自動リマインダー
- **ダッシュボード**: 会議分析の可視化UI
- **Slack/Teams連携**: 自動通知、共有
