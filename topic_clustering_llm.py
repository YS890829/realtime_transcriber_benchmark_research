#!/usr/bin/env python3
"""
Phase 6-3 Stage 4-1: LLMベースのトピッククラスタリング
Gemini 2.0 Flash を使用して、トピックを意味的にグループ化

機能:
- Gemini APIで23個のトピックを分析
- 文脈理解による高精度クラスタリング
- カテゴリ名の自動生成
- 理由付きグルーピング
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
from dotenv import load_dotenv
import google.generativeai as genai

# 環境変数の読み込み
load_dotenv()

# Gemini APIキー選択（FREE/PAID tier）
use_paid_tier = os.getenv("USE_PAID_TIER", "").lower() == "true"
api_key = os.getenv("GEMINI_API_KEY_PAID") if use_paid_tier else os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found in environment variables")
    sys.exit(1)

genai.configure(api_key=api_key)
print(f"✅ Using Gemini API: {'PAID' if use_paid_tier else 'FREE'} tier")


class LLMTopicClusterer:
    """LLMベースのトピッククラスタリングクラス"""

    def __init__(self):
        """初期化"""
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

        print("✅ LLM Topic Clusterer initialized")
        print("   Model: gemini-2.0-flash-exp")

    def load_topics_from_json(self, json_paths: List[str]) -> List[Dict[str, Any]]:
        """
        複数のJSONファイルからトピックを読み込み

        Args:
            json_paths: JSONファイルパスのリスト

        Returns:
            トピックのリスト（重複なし）
        """
        unique_topics = {}
        topic_sources = defaultdict(list)

        for path in json_paths:
            if not os.path.exists(path):
                print(f"   ⚠️  File not found: {path}")
                continue

            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            topics = data.get('topics', [])
            file_name = Path(path).stem

            for topic in topics:
                topic_name = topic.get('name', '')
                if topic_name:
                    if topic_name not in unique_topics:
                        unique_topics[topic_name] = {
                            'name': topic_name,
                            'summary': topic.get('summary', ''),
                            'keywords': topic.get('keywords', [])
                        }
                    topic_sources[topic_name].append(file_name)

        # 出現回数を追加
        for topic_name, topic_data in unique_topics.items():
            topic_data['occurrences'] = len(topic_sources[topic_name])
            topic_data['sources'] = topic_sources[topic_name]

        print(f"\n📂 Loaded topics from {len(json_paths)} files")
        print(f"   Unique topics: {len(unique_topics)}")

        return list(unique_topics.values())

    def cluster_topics_with_llm(self, topics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        LLMを使用してトピックをクラスタリング

        Args:
            topics: トピックのリスト

        Returns:
            クラスタリング結果
        """
        if len(topics) < 2:
            print("⚠️  Not enough topics to cluster (need at least 2)")
            return {"clusters": [], "metadata": {}}

        print(f"\n🤖 Clustering {len(topics)} topics with Gemini...")

        # トピック情報を整形
        topic_list = []
        for i, topic in enumerate(topics, 1):
            topic_info = f"{i}. {topic['name']}"
            if topic.get('summary'):
                topic_info += f"\n   要約: {topic['summary']}"
            if topic.get('keywords'):
                topic_info += f"\n   キーワード: {', '.join(topic['keywords'][:5])}"
            topic_info += f"\n   出現回数: {topic.get('occurrences', 1)}回"
            topic_list.append(topic_info)

        topics_text = "\n\n".join(topic_list)

        # プロンプト作成
        prompt = f"""以下は複数のミーティングから抽出された{len(topics)}個のトピックです。
これらのトピックを意味的に類似したグループに分類し、5-8個の大カテゴリにまとめてください。

【重要な指示】
1. 意味が類似しているトピックを同じカテゴリにグループ化
2. 各カテゴリに分かりやすい日本語の名前を付ける
3. なぜそのグループに分類したか理由を簡潔に説明
4. 以下のJSON形式で出力（JSONのみ、説明文は不要）

【出力形式】
{{
  "clusters": [
    {{
      "category_name": "カテゴリ名（例: キャリア開発）",
      "topics": ["トピック1", "トピック2", ...],
      "reason": "グループ化の理由（1-2文）",
      "size": トピック数
    }}
  ],
  "unclustered": ["カテゴリに含まれないトピック"],
  "total_categories": カテゴリ総数
}}

【トピック一覧】
{topics_text}

上記のトピックを分析し、JSON形式で出力してください：
"""

        # Gemini API呼び出し
        response = self.model.generate_content(prompt)
        response_text = response.text.strip()

        # JSON抽出
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Response text: {response_text[:500]}...")
            return {"clusters": [], "metadata": {"error": str(e)}}

        # 結果の検証と整形
        clusters = result.get('clusters', [])
        unclustered = result.get('unclustered', [])

        print(f"\n✅ Clustering completed")
        print(f"   Categories found: {len(clusters)}")
        print(f"   Clustered topics: {sum(c.get('size', len(c.get('topics', []))) for c in clusters)}")
        print(f"   Unclustered topics: {len(unclustered)}")

        # クラスタ詳細表示
        for i, cluster in enumerate(clusters, 1):
            print(f"\n   Category {i}: {cluster.get('category_name', 'Unknown')}")
            print(f"   Size: {cluster.get('size', len(cluster.get('topics', [])))} topics")
            print(f"   Reason: {cluster.get('reason', 'N/A')}")
            topics_in_cluster = cluster.get('topics', [])
            for topic in topics_in_cluster[:3]:  # 最初の3つを表示
                print(f"      - {topic}")
            if len(topics_in_cluster) > 3:
                print(f"      ... and {len(topics_in_cluster) - 3} more")

        return {
            'clusters': clusters,
            'unclustered': unclustered,
            'total_categories': result.get('total_categories', len(clusters)),
            'metadata': {
                'method': 'LLM-based (Gemini 2.0 Flash)',
                'total_topics': len(topics)
            }
        }

    def generate_cluster_report(
        self,
        clustering_result: Dict[str, Any],
        output_path: str = "topic_clustering_llm_report.md"
    ) -> None:
        """
        クラスタリング結果のレポートを生成

        Args:
            clustering_result: クラスタリング結果
            output_path: 出力ファイルパス
        """
        print(f"\n💾 Generating clustering report: {output_path}")

        clusters = clustering_result.get('clusters', [])
        unclustered = clustering_result.get('unclustered', [])
        metadata = clustering_result.get('metadata', {})

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# LLM-Based Topic Clustering Report\n\n")
            f.write(f"**Method:** {metadata.get('method', 'LLM-based')}\n")
            f.write(f"**Total Topics Analyzed:** {metadata.get('total_topics', 'N/A')}\n\n")

            # サマリー
            f.write(f"## Summary\n\n")
            f.write(f"- Total categories: {len(clusters)}\n")
            f.write(f"- Clustered topics: {sum(c.get('size', len(c.get('topics', []))) for c in clusters)}\n")
            f.write(f"- Unclustered topics: {len(unclustered)}\n\n")

            # カテゴリ詳細
            f.write(f"## Topic Categories\n\n")

            for i, cluster in enumerate(clusters, 1):
                category_name = cluster.get('category_name', f'Category {i}')
                topics = cluster.get('topics', [])
                reason = cluster.get('reason', 'N/A')
                size = cluster.get('size', len(topics))

                f.write(f"### {i}. {category_name}\n\n")
                f.write(f"**Size:** {size} topics\n\n")
                f.write(f"**Grouping Reason:** {reason}\n\n")
                f.write(f"**Topics:**\n")
                for topic in topics:
                    f.write(f"- {topic}\n")
                f.write("\n")

            # 未分類トピック
            if unclustered:
                f.write(f"## Unclustered Topics\n\n")
                f.write(f"These topics did not fit into any category:\n\n")
                for topic in unclustered:
                    f.write(f"- {topic}\n")

        print(f"✅ Report saved: {output_path}")


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("Usage: python topic_clustering_llm.py <json_file1> <json_file2> [json_file3 ...]")
        print("Example: python topic_clustering_llm.py downloads/*_structured_enhanced.json")
        sys.exit(1)

    # コマンドライン引数からファイルパスを取得
    json_paths = sys.argv[1:]

    # グロブパターン展開
    expanded_paths = []
    for pattern in json_paths:
        from glob import glob
        matches = glob(pattern)
        if matches:
            expanded_paths.extend(matches)
        else:
            expanded_paths.append(pattern)

    json_paths = list(set(expanded_paths))

    print("=" * 70)
    print("Phase 6-3 Stage 4-1: LLM-Based Topic Clustering")
    print("=" * 70)

    # クラスタリング実行
    clusterer = LLMTopicClusterer()

    # トピック読み込み
    topics = clusterer.load_topics_from_json(json_paths)

    if not topics:
        print("❌ No topics found")
        sys.exit(1)

    # LLMでクラスタリング
    clustering_result = clusterer.cluster_topics_with_llm(topics)

    # レポート生成
    clusterer.generate_cluster_report(clustering_result)

    print("\n" + "=" * 70)
    print("✅ LLM-based topic clustering completed!")
    print("   Cost: Free (Gemini 2.0 Flash)")
    print("=" * 70)


if __name__ == "__main__":
    main()
