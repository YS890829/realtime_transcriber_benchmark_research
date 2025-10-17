#!/usr/bin/env python3
"""
Phase 6-2: トピック抽出とエンティティ抽出
既存の構造化JSONにトピック・エンティティ・構造化要約を追加するスクリプト
Phase 6-1の結果（_structured.json）を入力として、トピック抽出とエンティティ抽出のみを実行
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Gemini APIキー選択（FREE/PAID tier）
use_paid_tier = os.getenv("USE_PAID_TIER", "").lower() == "true"
api_key = os.getenv("GEMINI_API_KEY_PAID") if use_paid_tier else os.getenv("GEMINI_API_KEY_FREE")

if not api_key:
    print("❌ Error: GEMINI_API_KEY_FREE not found in environment variables")
    sys.exit(1)

genai.configure(api_key=api_key)
print(f"✅ Using Gemini API: {'PAID' if use_paid_tier else 'FREE'} tier")


def extract_topics_and_entities(full_text):
    """
    Gemini APIを使用してトピック抽出とエンティティ抽出

    Args:
        full_text: 全文テキスト

    Returns:
        dict: {
            "topics": [トピックリスト],
            "entities": {people, organizations, dates, action_items}
        }
    """
    print(f"[1/3] トピック・エンティティ抽出中...")

    model = genai.GenerativeModel("gemini-2.0-flash-exp")

    prompt = f"""
以下の文字起こしテキストを分析し、以下のJSON形式で出力してください：

{{
  "topics": [
    {{
      "id": "topic_1",
      "name": "トピック名",
      "summary": "トピックの要約（1-2文）",
      "keywords": ["キーワード1", "キーワード2"]
    }}
  ],
  "entities": {{
    "people": ["人名1", "人名2"],
    "organizations": ["組織名1", "組織名2"],
    "dates": ["日付表現1", "日付表現2"],
    "action_items": ["アクション1", "アクション2"]
  }}
}}

文字起こしテキスト:
{full_text}
"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # JSONを抽出（```jsonブロックを除去）
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        result = json.loads(response_text)

        print(f"  Extracted {len(result.get('topics', []))} topics")
        print(f"  Found {len(result.get('entities', {}).get('people', []))} people")

        return result

    except Exception as e:
        print(f"  Error: {e}")
        return {
            "topics": [],
            "entities": {"people": [], "organizations": [], "dates": [], "action_items": []}
        }


def assign_topics_to_segments(segments, topics):
    """セグメントにトピック割り当て（キーワードマッチング）"""
    segments_enhanced = []

    for seg in segments:
        seg_text = seg["text"]
        assigned_topics = []

        # 各トピックのキーワードがセグメントに含まれるかチェック
        for topic in topics:
            keywords = topic.get("keywords", [])
            if any(keyword in seg_text for keyword in keywords):
                assigned_topics.append(topic["id"])

        seg_copy = seg.copy()
        seg_copy["topics"] = assigned_topics if assigned_topics else []
        segments_enhanced.append(seg_copy)

    return segments_enhanced


def generate_enhanced_summary(full_text, topics, entities):
    """構造化データを活用した要約生成"""
    print(f"[2/3] 構造化要約生成中...")

    # API key is already configured at the top of the script
    model = genai.GenerativeModel("gemini-2.0-flash-exp")

    # トピック情報を文字列化
    topics_info = "\n".join([
        f"- {t['name']}: {t['summary']}"
        for t in topics
    ])

    # エンティティ情報を文字列化
    entities_info = f"""
- 人物: {', '.join(entities.get('people', []))}
- 組織: {', '.join(entities.get('organizations', []))}
- 日付: {', '.join(entities.get('dates', []))}
- アクション: {', '.join(entities.get('action_items', []))}
"""

    prompt = f"""
以下の情報を元に、会話の要約を作成してください。

【トピック】
{topics_info}

【抽出されたエンティティ】
{entities_info}

【全文テキスト】
{full_text[:5000]}...

以下の形式で要約を作成してください：

# エグゼクティブサマリー
（2-3文で全体の概要）

# 主要ポイント
- ポイント1
- ポイント2
- ポイント3

# 詳細サマリー
（各トピックについて詳細に説明）
"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"  Error: {e}")
        return "要約生成に失敗しました"


def main():
    if len(sys.argv) < 2:
        print("Usage: python add_topics_entities.py <structured_json>")
        sys.exit(1)

    json_path = sys.argv[1]

    if not os.path.exists(json_path):
        print(f"Error: JSON file not found: {json_path}")
        sys.exit(1)

    print(f"🎙️ Phase 6-2処理開始（トピック・エンティティ抽出）")
    print(f"  入力JSON: {json_path}")

    # 既存のJSONを読み込み
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # トピック・エンティティ抽出
    topics_result = extract_topics_and_entities(data["full_text"])

    # セグメントにトピック割り当て
    print(f"[3/3] セグメントにトピック割り当て中...")
    segments_enhanced = assign_topics_to_segments(
        data["segments"],
        topics_result["topics"]
    )

    # 構造化要約生成
    summary = generate_enhanced_summary(
        data["full_text"],
        topics_result["topics"],
        topics_result["entities"]
    )

    # 拡張JSONを作成
    enhanced_data = data.copy()
    enhanced_data["topics"] = topics_result["topics"]
    enhanced_data["entities"] = topics_result["entities"]
    enhanced_data["segments"] = segments_enhanced
    enhanced_data["summary"] = summary

    # 出力
    output_path = Path(json_path).stem + "_enhanced.json"
    output_dir = Path(json_path).parent
    output_file = output_dir / output_path

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(enhanced_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ JSON保存完了: {output_file}")

    print(f"\n📊 処理統計:")
    print(f"  トピック数: {len(enhanced_data['topics'])}")
    print(f"  エンティティ: 人物{len(enhanced_data['entities'].get('people', []))}名")
    print(f"  組織: {len(enhanced_data['entities'].get('organizations', []))}個")

    print(f"\n🎉 完了!")


if __name__ == "__main__":
    main()
