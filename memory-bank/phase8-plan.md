# Phase 8実装プラン: パイプライン最適化とVector DB統合

**作成日**: 2025-10-14
**目標**: タスク順序の再構築、話者推論精度向上、エンティティ統一、統合Vector DB構築

---

## 📋 背景と問題点

### 現在のパイプライン順序の問題

```
❌ 現在の実装順序（非効率）:
1. structured_transcribe.py → _structured.json
2. add_topics_entities.py → _enhanced.json（トピック・エンティティ抽出）
3. build_vector_index.py → ChromaDB（各ファイル独立でベクトル化）
4. entity_resolution_llm.py → 複数ファイル横断でエンティティ名寄せ
```

**問題点:**
- ベクトル化（Step 3）が名寄せ（Step 4）**より先**に実行される
- 各ファイルで「福島さん」「福島」「Fukushima」が別エンティティとしてベクトル化
- 名寄せ後もベクトルDBは古いまま（再構築されない）
- 5ファイルが独立したコレクション（横断検索に5回のクエリ必要）

**影響:**
- 検索精度低下: 「福島」で検索しても「福島さん」の発言はヒットしない
- メタデータ不整合: 同一人物が複数のIDで管理される
- 非効率な横断検索: 5コレクションを個別に検索

---

## ✅ Phase 8の改善内容

### 1. タスク順序の最適化

```
✅ 改善後のパイプライン順序:
1. structured_transcribe.py → _structured.json（音声文字起こし）
2. infer_speakers.py → _structured_with_speakers.json（話者推論）
3. add_topics_entities.py → _enhanced.json（トピック・エンティティ抽出）
4. entity_resolution_llm.py → _enhanced.json更新（エンティティ名寄せ + canonical_name付与）
5. build_unified_vector_index.py → transcripts_unified（統合Vector DB構築）
6. semantic_search.py, rag_qa.py → 5ファイル横断検索（1クエリ）
```

**改善効果:**
- エンティティ統一後にベクトル化 → 検索精度向上
- 統合Vector DB → 1クエリで5ファイル横断検索
- メタデータ一貫性 → 同一人物が同じIDで管理

---

### 2. 話者推論プロンプトの改善

#### 現在の問題点
- 「杉本さんのプロフィール」が実態と異なる（起業家・事業家、医療業界関心）
- 声質情報がない
- 呼称のバリエーション不足
- 今後の目標（起業、アメリカ転職）が反映されていない

#### 改善内容
職務経歴書（職務経歴書_杉本裕樹.pdf）の内容を反映:

**杉本裕樹さんプロフィール:**

**基本情報:**
- 性別: 男性
- 呼称: 杉本、すーさん、ゆうき、ゆうきくん、杉本さん
- 声質: 低めかつ少しこもった声

**現在の職種（2025年1月時点）:**
- 株式会社エクサウィザーズ
- 機械学習/ソフトウェアエンジニア（生成AI担当）
- 次の転職先: ビズリーチ（AIエンジニア、社内DX・AIエージェント構築）

**経歴サマリー:**
1. **リクルート住まいカンパニー (2013-2019)**: 賃貸営業、Sales Leader
   - 大手顧客の事業成長支援（民泊立ち上げ、CRM開発、新規出店提案）
   - 担当取引売上昨対183%達成（0.3億円→0.55億円）
   - MVP、特別賞多数受賞

2. **英語学習・CS学位取得 (2019-2023)**:
   - サンフランシスコ留学（3ヶ月）、TOEIC 905点
   - University of the People (アメリカオンライン大学) CS学士 GPA 3.85
   - 学習内容: Python, 機械学習, 深層学習, FastAPI, Docker, AWS

3. **アジラ (2022)**: AI Engineer
   - 画像処理プロダクト開発（防犯カメラ、違和感行動検知）
   - IoTデバイスキッティング、R&D拠点との英語での打ち合わせ

4. **エクサウィザーズ (2022-現在)**: 機械学習エンジニア
   - 大手自動車会社: クラスタリング、分類予測モデル構築
   - 大手通信会社: RAG構築による経理業務効率化
   - 自社プロダクト: アンケート添削自動化、営業向けアプリ開発

**現在の学位（進行中）:**
- University of Colorado Boulder (アメリカオンライン大学院)
- データサイエンス修士専攻
- 2025年12月卒業予定（働きながら学習）

**専門領域:**
- 営業: 顧客理解、戦略策定、PDCA実行、合意形成
- エンジニアリング: 機械学習、RAG、生成AI、Python、FastAPI、Streamlit
- 要求定義力: 顧客課題からプロダクト開発まで一気通貫

**思考性・今後の目標:**
- 起業を目指している
- アメリカ転職を目標にしている
- 営業とエンジニアリングの両方の専門性を活かした価値提供
- 「AIを効果的に活用し、複数専門領域を担える人材」を志向
- 本質的価値を追求するスタンス（中長期成長に必要なことは何か）

**話し方の特徴:**
- ビジネス戦略、起業、AI、DX、生成AI、RAGなどの話題に詳しい
- 顧客課題の本質を追求する姿勢
- 営業経験からの現場感覚を持つ
- データに基づく意思決定を重視
- 合意形成力（課題の要素分解力）が高い

---

### 3. エンティティ名寄せ結果の反映

#### 現在の問題点
- entity_resolution_llm.pyが名寄せ結果を返すだけ
- _enhanced.jsonには名寄せ結果が反映されない
- Vector DB構築時に古いエンティティ情報を使用

#### 改善内容
- 名寄せ結果を各_enhanced.jsonに反映
- canonical_name（正規化名）とentity_id付与
- モデル変更: gemini-2.0-flash-exp → gemini-2.5-pro（文脈理解精度向上）

**新しいentitiesフィールド構造:**
```json
{
  "entities": {
    "people": [
      {
        "name": "福島さん",
        "canonical_name": "福島",
        "entity_id": "person_001",
        "variants": ["福島", "福島さん"],
        "occurrences": 15
      },
      {
        "name": "杉本",
        "canonical_name": "杉本",
        "entity_id": "person_002",
        "variants": ["杉本", "すーさん", "ゆうき"],
        "occurrences": 42
      }
    ],
    "organizations": [
      {
        "name": "リクルート",
        "canonical_name": "リクルート",
        "entity_id": "org_001",
        "variants": ["リクルート", "リクルートホールディングス"],
        "occurrences": 8
      }
    ]
  }
}
```

---

### 4. 統合Vector DB構築

#### 現在の問題点
- 各ファイルが独立したコレクション（5コレクション）
- 5ファイル横断検索に5回のクエリが必要
- エンティティ統一前の情報でベクトル化

#### 改善内容
- 新規スクリプト: build_unified_vector_index.py
- 全5ファイルを1つのコレクション"transcripts_unified"に統合
- 統一されたentity_idでベクトル化
- メタデータにsource_file追加

**統合コレクションメタデータ構造:**
```python
metadata = {
    'segment_id': 'file1_seg_001',
    'source_file': '09-22 意思決定ミーティング.mp3',
    'speaker': 'Sugimoto',
    'start_time': 81.0,
    'end_time': 84.5,
    'topics': '起業準備, 資金調達',
    'people': '福島(person_001), 田中(person_002)',  # canonical_name + entity_id
    'organizations': 'ビズリーチ(org_001)',
    'dates': '2025年10月'
}
```

---

## 🎯 Phase 8の実装ステージ

### **Phase 8-1: メモリーバンク更新 + 話者推論改善**

**タスク:**
1. memory-bank/phase8-plan.md作成（本ファイル）
2. memory-bank/progress.md更新（Phase 8追加���
3. infer_speakers.py修正（杉本さんプロフィール更新）
4. 5ファイルで話者推論再実行、精度確認

**完了条件:**
- ✅ memory-bank/phase8-plan.md作成完了
- ✅ infer_speakers.py修正完了
- ✅ 5ファイル再実行で話者推論精度向上確認

**推定所要時間:** 1-2時間

---

### **Phase 8-2: エンティティ名寄せ結果の_enhanced.json反映**

**タスク:**
1. entity_resolution_llm.py修正
   - 名寄せ結果を各_enhanced.jsonに反映
   - canonical_nameとentity_id付与
   - モデル変更: gemini-2.0-flash-exp → gemini-2.5-pro
2. 全5ファイルで実行、_enhanced.json更新

**完了条件:**
- ✅ entity_resolution_llm.py修正完了
- ✅ 全5ファイルの_enhanced.json更新完了
- ✅ canonical_nameとentity_id付与完了

**推定所要時間:** 2-3時間

---

### **Phase 8-3: 統合Vector DB構築**

**タスク:**
1. build_unified_vector_index.py作成（新規スクリプト）
   - 全5ファイルを1つのコレクションに統合
   - 統一されたentity_idでベクトル化
   - メタデータにsource_file追加
2. semantic_search.py修正（統合コレクション対応）
3. rag_qa.py修正（複数ファイルにまたがる質問対応）

**完了条件:**
- ✅ build_unified_vector_index.py作成完了
- ✅ 統合Vector DB構築完了（全4,209セグメント）
- ✅ semantic_search.py, rag_qa.py修正完了
- ✅ 1クエリで5ファイル横断検索成功

**推定所要時間:** 3-4時間

---

### **Phase 8-4: 検証とドキュメント更新**

**タスク:**
1. 統合検証
   - 話者推論精度確認（杉本さん特定率）
   - エンティティ名寄せ結果確認（統一率）
   - Vector DB横断検索テスト
2. テストクエリ実行
3. README.md更新（新パイプライン順序説明）
4. memory-bank/progress.md更新（Phase 8完了記録）

**完了条件:**
- ✅ 全テスト成功
- ✅ ドキュメント更新完了

**推定所要時間:** 1-2時間

---

## 📊 Phase 8完了後の状態

### 獲得する機能

1. **高精度話者推論**
   - 杉本さんの経歴・声質・思考性を反映
   - 呼称のバリエーション対応（杉本、すーさん、ゆうき）
   - 専門領域（営業+エンジニアリング）を考慮

2. **エンティティ統一管理**
   - 「福島さん」=「福島」として統合
   - canonical_nameとentity_idで一意に管理
   - 全5ファイル横断で統一されたID

3. **統合Vector DB**
   - 1つのコレクション"transcripts_unified"
   - 4,209セグメント全て統合
   - 1クエリで5ファイル横断検索

4. **クロスミーティング分析**
   - 複数会議にまたがるトピック追跡
   - エンティティの時系列分析
   - 話者ごとの発言統計

### パフォーマンス改善

| 項目 | Before | After | 改善率 |
|-----|--------|-------|-------|
| 横断検索クエリ数 | 5回 | 1回 | 80%削減 |
| エンティティ統一 | なし | あり | - |
| 話者推論精度 | 80-90% | 90-95% | +5-15% |
| 検索精度 | 中 | 高 | - |

---

## 🚀 推定総所要時間

**Phase 8全体: 7-11時間**

- Phase 8-1: 1-2時間
- Phase 8-2: 2-3時間
- Phase 8-3: 3-4時間
- Phase 8-4: 1-2時間

---

## 📝 実装履歴

- **2025-10-14**: Phase 8プラン作成
- **2025-10-14**: Phase 8-1実装開始
