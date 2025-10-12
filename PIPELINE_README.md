# 統合パイプライン: 話者推論 → 要約 → ファイル名生成

## 概要

音声文字起こし結果に対して、以下の3ステップを順次実行する統合パイプライン:

```
_structured.json
    ↓
[Step 1] 話者推論
    ↓
_structured_with_speakers.json (話者名: Sugimoto/Other)
    ↓
[Step 2] コンテキストプロンプト付き要約
    ↓
_structured_summarized.json (要約 + トピック + エンティティ)
    ↓
[Step 3] 最適ファイル名生成
    ↓
_structured_final.json (最適ファイル名付き)
```

## 各ステップの詳細

### Step 1: 話者推論 (`infer_speakers.py`)

**目的**: 会話から話者を特定し、Sugimoto/Otherに分類

**処理内容**:
- 会話内容とプロフィールから話者を推論（Gemini 2.5 Pro）
- 判断基準:
  1. 名前の明示的言及
  2. 録音者の可能性（独白、思考整理）
  3. 会話の主導者（専門的話題を深く語る）
  4. 質問を受ける側（面談、キャリアを語る）
  5. 意思決定者の立場

**入力**: `*_structured.json`
**出力**: `*_structured_with_speakers.json`

**メタデータ追加**:
```json
{
  "speaker_inference": {
    "inferred_at": "2025-10-12T19:28:46.819958",
    "result": {
      "sugimoto_identified": true,
      "sugimoto_speaker": "Speaker 2",
      "confidence": "high",
      "reasoning": "..."
    },
    "sugimoto_segments": 351,
    "other_segments": 362
  }
}
```

**実行例**:
```bash
python infer_speakers.py "downloads/recording_structured.json"
```

**所要時間**: 約5秒

---

### Step 2: コンテキストプロンプト付き要約 (`summarize_with_context.py`)

**目的**: 話者情報を活用した高精度要約とトピック/エンティティ抽出

**処理内容**:
- System Instructionsで話者プロフィールを付与
- ウィンドウ単位（10セグメント）で要約
- 全文からトピック/エンティティを抽出（5カテゴリ）

**System Instructions**:
- Sugimotoの発言を重点的に要約（意思決定、戦略、アイデア）
- 専門用語を正確に扱う（起業、資金調達、医療、DX、AI）
- 具体的な数字、日付、固有名詞を保持

**入力**: `*_structured_with_speakers.json`
**出力**: `*_structured_summarized.json`

**メタデータ追加**:
```json
{
  "summarized_segments": [
    {
      "id": 1,
      "original_segment_ids": [1, 2, 3, ..., 10],
      "speaker": "Summary",
      "text": "要約テキスト",
      "timestamp": "01:21",
      "original_segments_count": 10
    },
    ...
  ],
  "topics_entities": {
    "topics": ["起業準備", "医療流通プラットフォーム", ...],
    "entities": {
      "people": ["杉本", ...],
      "organizations": ["スタートアップ", ...],
      "locations": ["東京", ...],
      "products_services": ["プラットフォーム", ...],
      "concepts": ["資金調達", "事業戦略", ...]
    }
  }
}
```

**実行例**:
```bash
python summarize_with_context.py "downloads/recording_structured_with_speakers.json"
```

**所要時間**:
- 713セグメント → 72回のAPI呼び出し
- 約36分（Gemini 2.5 Proのレート制限: 2 req/min）

---

### Step 3: 最適ファイル名生成 (`generate_optimal_filename.py`)

**目的**: 話者情報 + 要約 + トピック + エンティティを統合して最適なファイル名を生成

**処理内容**:
- 全情報を統合してLLMに最適化を依頼
- ファイル名要件:
  1. 日付を含める（元ファイル名から抽出）
  2. 会話の種類（面談、ミーティング、カジュアル会話など）
  3. 主要トピック2-3個
  4. 話者情報を活用
  5. 全体で50-80文字程度
  6. 検索しやすく内容が一目でわかる

**入力**: `*_structured_summarized.json`
**出力**: `*_structured_final.json`

**メタデータ追加**:
```json
{
  "optimal_filename": {
    "generated_at": "2025-10-12T19:45:00.000000",
    "filename": "09-22 意思決定ミーティング：Sugimoto-起業準備と医療流通プラットフォーム戦略の統合検討",
    "reasoning": "..."
  }
}
```

**実行例**:
```bash
python generate_optimal_filename.py "downloads/recording_structured_summarized.json"
```

**所要時間**: 約5秒

---

## 統合パイプライン実行

### 自動実行（推奨）

```bash
python run_full_pipeline.py "downloads/recording_structured.json"
```

3つのステップを自動で順次実行します。

### 手動実行

```bash
# Step 1
python infer_speakers.py "downloads/recording_structured.json"

# Step 2
python summarize_with_context.py "downloads/recording_structured_with_speakers.json"

# Step 3
python generate_optimal_filename.py "downloads/recording_structured_summarized.json"
```

---

## 技術仕様

### モデル
- **Gemini 2.5 Pro** (全ステップで統一)

### レート制限
- Gemini 2.5 Pro: **2 req/min**
- Step 2で30秒待機を実装

### ファイルフォーマット
- 入力: JSON (UTF-8, indent=2)
- 出力: JSON (UTF-8, indent=2, ensure_ascii=False)

### エラーハンドリング
- ファイル存在チェック
- API エラーハンドリング（自動リトライ）
- レート制限対応

---

## 実装の特徴

### 1. 話者情報の活用
- Step 1で特定した話者情報を後続ステップで活用
- "Sugimotoの発言では..." のように明示的に話者を参照

### 2. コンテキスト強化
- System Instructionsで話者プロフィールを付与
- 専門用語や固有名詞の正確な理解

### 3. 情報の統合
- Step 3で全情報を統合して最適化
- 検索性と可読性を両立したファイル名

### 4. メタデータの保持
- 各ステップでメタデータを追加
- 処理履歴と結果をすべて記録

---

## 今後の拡張案

1. **バッチ処理**: 複数ファイルを一括処理
2. **話者の詳細化**: Otherの具体的な名前推論
3. **要約の階層化**: 全体要約 + セクション要約
4. **ファイル名の自動リネーム**: 生成したファイル名で実際にリネーム
5. **レポート生成**: 処理結果のサマリーレポート

---

## トラブルシューティング

### レート制限エラー
```
google.api_core.exceptions.ResourceExhausted: 429 You exceeded your current quota
```

**解決策**: Step 2の`time.sleep(30)`を`time.sleep(60)`に変更

### メモリ不足
大きなファイル（1000+セグメント）の場合、メモリ不足になる可能性があります。

**解決策**: `window_size`を小さくする（デフォルト10 → 5に変更）

### 話者推論の精度が低い
`confidence: "low"`の場合、手動で話者を修正できます。

**解決策**: `_structured_with_speakers.json`を手動編集後、Step 2から再実行

---

## ライセンス

MIT License

## 貢献者

- 実装: Claude (Anthropic)
- プロジェクト: Sugimoto Yuuki
