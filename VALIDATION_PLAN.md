# 精度改善検証計画

## 目的
新パイプライン（話者推論→コンテキスト付き要約→最適ファイル名生成）が従来の処理と比較してどれだけ精度が改善されたかを定量的に検証する。

## 検証対象

### 比較する2つのアプローチ

#### 1. 従来処理 (ベースライン)
- `_structured.json` から直接要約・ファイル名生成
- 話者情報なし、コンテキストなし
- 基本的なプロンプトのみ

#### 2. 新パイプライン
- **Step 1**: 話者推論（Sugimoto/Other識別）
- **Step 2**: 話者情報活用 + System Instructions + トピック/エンティティ抽出
- **Step 3**: 全情報統合による最適ファイル名生成

## 検証指標

### 1. 話者識別精度
- **正解率**: 手動で確認したSugimotoセグメントとの一致率
- **信頼度**: LLMが出力する信頼度 (high/medium/low)
- **新パイプラインのみで測定**（ベースラインには話者識別なし）

### 2. 要約品質
- **情報保持率**: 重要キーワード（固有名詞、数字、専門用語）の保持率
- **文脈理解度**: 話者の意図や意思決定プロセスの明確さ
- **冗長性削減**: 相槌や繰り返しの削除率
- **要約の簡潔性**: 同じ情報量をより短く表現

### 3. トピック/エンティティ抽出精度
- **カバレッジ**: トピック・エンティティの網羅率
- **正確性**: 誤抽出（無関係なトピック）の割合
- **カテゴリ分類精度**: 5カテゴリ（人、組織、場所、製品/サービス、概念）への分類精度

### 4. ファイル名品質
- **情報量**: ファイル名に含まれる有用情報の数
- **検索性**: 主要キーワードの含有率
- **可読性**: 文字数と構造の適切さ（50-80文字が理想）
- **日付・形式の正確性**: 日付、会話種類の適切な表現

## 検証方法

### Phase 1: 自動評価（無料プラン - Gemini 2.0 Flash Exp）

#### 1.1 従来処理を実行
- 話者情報なしで要約生成
- 基本的なトピック抽出
- シンプルなファイル名生成

#### 1.2 新パイプラインを実行
- 完全な3ステップパイプライン実行
- 既存の話者情報ファイル活用可能

#### 1.3 自動評価指標の計算
```python
metrics = {
    'keyword_retention': count_important_keywords() / total_keywords,
    'topic_count': len(topics),
    'entity_count': sum(len(entities[category]) for category in entities),
    'filename_info_density': count_info_units(filename) / len(filename),
    'summary_compression': original_length / summary_length,
}
```

### Phase 2: LLM評価（無料プラン - Gemini 2.0 Flash Exp）

#### 評価プロンプト
```
以下の2つの要約を比較評価してください：

【元の会話】
{original_text}

【要約A（従来処理）】
{baseline_summary}

【要約B（新パイプライン）】
{new_pipeline_summary}

以下の基準で1-5点で評価してください：
1. 情報の正確性: 重要な情報を正確に保持しているか
2. 文脈理解度: 話者の意図や意思決定プロセスが明確か
3. 有用性: 後で見返したときに有用か
4. 簡潔性: 冗長性を排除し、簡潔にまとまっているか
5. 総合評価: 全体的な品質
```

#### 評価指標
- 各項目 1-5点（5点満点）
- 総合スコア
- 改善点の提案

### Phase 3: 詳細評価（容量制限後、有料プラン）
- Gemini 2.5 Pro での詳細評価
- 複数サンプルでの統計分析
- 改善提案の生成
- セグメント単位の詳細比較

## 実装ファイル構成

### 1. `baseline_pipeline.py`
従来処理（話者情報なし）を実装
- 入力: `_structured.json`
- 出力: `_baseline_result.json`
- 処理:
  - 基本的な要約（System Instructionsなし）
  - シンプルなトピック抽出
  - 基本的なファイル名生成

### 2. `evaluate_accuracy.py`
自動評価指標を計算
- 2つの出力ファイルを読み込み
- 自動評価指標を計算
- 統計データを生成

### 3. `llm_evaluate.py`
LLMを使った品質評価
- 2つの出力をLLMに提示
- 比較評価を実行
- スコアと改善提案を生成

### 4. `run_validation.py`
全検証プロセスを自動実行
- ベースライン実行
- 新パイプライン実行（既存結果も利用可）
- 自動評価
- LLM評価
- レポート生成

## レート制限戦略

### 無料プラン (Gemini 2.0 Flash Exp)
- **レート制限**: 10 req/min（15 req/min in some cases）
- **待機時間**: 6秒/リクエスト
- **使用用途**:
  - ベースライン処理
  - 自動評価
  - LLM評価

### 有料プラン（必要時のみ）
- **Gemini 2.5 Pro**
- **使用用途**:
  - 詳細分析
  - 複数サンプル評価
  - より高精度な比較

## 検証サンプル

### 優先度1（最初のテスト）
**ファイル**: `09-22 意思決定ミーティング：起業準備と医療流通プラットフォーム戦略の統合検討.mp3`
- **理由**:
  - 既にStep 1完了済み（`_structured_with_speakers.json`存在）
  - 話者情報が明確
  - ビジネス専門用語が豊富
  - 意思決定プロセスが含まれる
- **セグメント数**: 713
- **所要時間**: 約40分（ベースライン20分 + 評価20分）

### 優先度2（容量許せば）
1. `10-07 面談：キャリア変遷と今後の事業展望.mp3`
   - 面談形式、キャリアの詳細

2. `08-07 カジュアル会話_ 起業計画・資金調達・AI活用...mp3`
   - カジュアルな会話、多様なトピック

## 出力形式

### 評価レポート (`evaluation_report.json`)
```json
{
  "metadata": {
    "test_file": "09-22 意思決定ミーティング...",
    "evaluation_date": "2025-10-12T20:00:00",
    "model_used": "gemini-2.0-flash-exp"
  },
  "baseline": {
    "execution_time_seconds": 120,
    "summary_length_chars": 1000,
    "topics_count": 5,
    "entities_count": 15,
    "filename": "09-22 会議録音.mp3",
    "filename_length": 12
  },
  "new_pipeline": {
    "speaker_identification": {
      "sugimoto_segments": 351,
      "other_segments": 362,
      "confidence": "high"
    },
    "execution_time_seconds": 150,
    "summary_length_chars": 800,
    "topics_count": 8,
    "entities_count": 25,
    "entities_by_category": {
      "people": 5,
      "organizations": 8,
      "locations": 3,
      "products_services": 6,
      "concepts": 3
    },
    "filename": "09-22 意思決定ミーティング：Sugimoto-起業準備と医療流通プラットフォーム戦略",
    "filename_length": 48
  },
  "automatic_metrics": {
    "keyword_retention_improvement": 0.35,
    "topic_coverage_improvement": 0.60,
    "entity_extraction_improvement": 0.67,
    "summary_compression_ratio": 0.80,
    "filename_info_density_improvement": 4.0
  },
  "llm_evaluation": {
    "accuracy_score": 4.5,
    "context_understanding_score": 4.8,
    "usefulness_score": 4.7,
    "conciseness_score": 4.6,
    "overall_score": 4.65,
    "baseline_overall_score": 3.2,
    "improvement": 1.45,
    "detailed_feedback": "新パイプラインは..."
  },
  "conclusion": {
    "summary": "新パイプラインは従来処理と比較して...",
    "key_improvements": [
      "話者識別により文脈理解が大幅向上",
      "トピック抽出が60%改善",
      "ファイル名の情報密度が4倍向上"
    ],
    "remaining_issues": [
      "処理時間が25%増加",
      "レート制限による待機時間"
    ]
  }
}
```

### 可視化レポート (`evaluation_report.md`)
- Markdown形式で読みやすいレポート
- 比較表
- スコアのグラフ（テキストベース）
- 具体例の提示

## タイムライン

1. ✅ **実装計画作成**: 5分
2. 🔄 **メモリーバンク更新**: 2分
3. ⏳ **ベースライン実装**: 10分
4. ⏳ **評価スクリプト実装**: 15分
5. ⏳ **検証実行（無料プラン）**: 20-40分
   - ベースライン実行: 10-20分
   - 評価実行: 10-20分
6. ⏳ **結果分析**: 10分
7. ⏳ **レポート作成 & コミット**: 5分

**合計**: 約1-1.5時間

## 成功基準

以下の条件を満たせば、新パイプラインは「成功」と判断:

1. **自動評価**: 主要指標で30%以上の改善
2. **LLM評価**: 総合スコアで1点以上の改善（5点満点）
3. **話者識別**: 信頼度 "high" または "medium" 以上
4. **ファイル名**: 情報密度が2倍以上向上

## リスクと対応

### リスク1: レート制限による中断
**対応**: Gemini 2.0 Flash Expを優先使用（10 req/min）

### リスク2: 無料プラン容量不足
**対応**: 有料プランに切り替え（ユーザー承認済み）

### リスク3: 評価の主観性
**対応**: 自動評価指標を中心に、LLM評価は補助的に使用
