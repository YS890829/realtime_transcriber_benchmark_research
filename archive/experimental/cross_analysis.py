#!/usr/bin/env python3
"""
Phase 6-3 Stage 3-1: Cross-Meeting Analysis
複数の文字起こしファイルを横断して分析

機能:
- 複数のenhanced JSONファイルを読み込み
- 共通トピック抽出（複数ミーティングで繰り返されるテーマ）
- エンティティ追跡（人物・組織が複数ミーティングでどう言及されるか）
- トピックの時系列変化分析
- アクションアイテムの進捗追跡
- 統合サマリーの生成
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
from collections import Counter, defaultdict
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


class CrossMeetingAnalyzer:
    """複数ミーティング横断分析クラス"""

    def __init__(self):
        """初期化"""
        self.llm = genai.GenerativeModel("gemini-2.0-flash-exp")

        print("✅ Cross-Meeting Analyzer initialized")
        print("   LLM: gemini-2.0-flash-exp")

    def load_transcripts(self, json_paths: List[str]) -> List[Dict[str, Any]]:
        """
        複数のenhanced JSONファイルを読み込み

        Args:
            json_paths: JSONファイルパスのリスト

        Returns:
            読み込んだデータのリスト
        """
        print(f"\n📂 Loading {len(json_paths)} transcript files...")

        transcripts = []
        for path in json_paths:
            if not os.path.exists(path):
                print(f"   ⚠️  File not found: {path}")
                continue

            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # ファイル名とメタデータを追加
            data['_file_path'] = path
            data['_file_name'] = Path(path).name

            transcripts.append(data)

            # 簡単な統計を表示
            file_name = data.get('metadata', {}).get('file', {}).get('file_name', Path(path).name)
            num_segments = len(data.get('segments', []))
            num_topics = len(data.get('topics', []))
            print(f"   ✅ {file_name}: {num_segments} segments, {num_topics} topics")

        print(f"\n✅ Loaded {len(transcripts)} transcripts")
        return transcripts

    def extract_common_topics(self, transcripts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        共通トピックを抽出

        Args:
            transcripts: 文字起こしデータのリスト

        Returns:
            共通トピック分析結果
        """
        print(f"\n🔍 Extracting common topics across {len(transcripts)} meetings...")

        # すべてのトピックを収集
        all_topics = []
        topic_by_file = {}

        for transcript in transcripts:
            file_name = transcript.get('_file_name', 'Unknown')
            topics = transcript.get('topics', [])

            topic_by_file[file_name] = [t.get('name', '') for t in topics]
            all_topics.extend(topics)

        # トピック名の出現頻度をカウント
        topic_names = [t.get('name', '') for t in all_topics if t.get('name')]
        topic_counts = Counter(topic_names)

        # 共通トピック（2回以上出現）
        common_topics = {name: count for name, count in topic_counts.items() if count >= 2}

        print(f"   Total topics: {len(all_topics)}")
        print(f"   Unique topics: {len(topic_counts)}")
        print(f"   Common topics (appearing 2+ times): {len(common_topics)}")

        if common_topics:
            print(f"\n   Top common topics:")
            for name, count in sorted(common_topics.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   - {name}: {count} occurrences")

        return {
            "all_topics": all_topics,
            "topic_counts": dict(topic_counts),
            "common_topics": common_topics,
            "topics_by_file": topic_by_file
        }

    def track_entities(self, transcripts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        エンティティ追跡（人物・組織・日付）

        Args:
            transcripts: 文字起こしデータのリスト

        Returns:
            エンティティ追跡結果
        """
        print(f"\n👥 Tracking entities across {len(transcripts)} meetings...")

        # エンティティを収集
        people_by_file = {}
        organizations_by_file = {}
        dates_by_file = {}

        all_people = []
        all_organizations = []
        all_dates = []

        for transcript in transcripts:
            file_name = transcript.get('_file_name', 'Unknown')
            entities = transcript.get('entities', {})

            people = entities.get('people', [])
            orgs = entities.get('organizations', [])
            dates = entities.get('dates', [])

            people_by_file[file_name] = people
            organizations_by_file[file_name] = orgs
            dates_by_file[file_name] = dates

            all_people.extend(people)
            all_organizations.extend(orgs)
            all_dates.extend(dates)

        # 出現頻度をカウント
        people_counts = Counter(all_people)
        org_counts = Counter(all_organizations)
        date_counts = Counter(all_dates)

        # 複数回出現するエンティティ
        recurring_people = {name: count for name, count in people_counts.items() if count >= 2}
        recurring_orgs = {name: count for name, count in org_counts.items() if count >= 2}

        print(f"   Total people mentioned: {len(people_counts)}")
        print(f"   Recurring people (2+ meetings): {len(recurring_people)}")
        print(f"   Total organizations: {len(org_counts)}")
        print(f"   Recurring organizations (2+ meetings): {len(recurring_orgs)}")

        if recurring_people:
            print(f"\n   Recurring people:")
            for name, count in sorted(recurring_people.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   - {name}: {count} occurrences")

        if recurring_orgs:
            print(f"\n   Recurring organizations:")
            for name, count in sorted(recurring_orgs.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   - {name}: {count} occurrences")

        return {
            "people_counts": dict(people_counts),
            "org_counts": dict(org_counts),
            "date_counts": dict(date_counts),
            "recurring_people": recurring_people,
            "recurring_orgs": recurring_orgs,
            "people_by_file": people_by_file,
            "organizations_by_file": organizations_by_file,
            "dates_by_file": dates_by_file
        }

    def analyze_action_items(self, transcripts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        アクションアイテムを抽出して分析

        Args:
            transcripts: 文字起こしデータのリスト

        Returns:
            アクションアイテム分析結果
        """
        print(f"\n📋 Analyzing action items across {len(transcripts)} meetings...")

        action_items_by_file = {}
        all_action_items = []

        for transcript in transcripts:
            file_name = transcript.get('_file_name', 'Unknown')
            entities = transcript.get('entities', {})
            action_items = entities.get('action_items', [])

            action_items_by_file[file_name] = action_items
            all_action_items.extend(action_items)

        print(f"   Total action items: {len(all_action_items)}")
        print(f"   Files with action items: {len([f for f, items in action_items_by_file.items() if items])}")

        return {
            "all_action_items": all_action_items,
            "action_items_by_file": action_items_by_file
        }

    def generate_integrated_summary(
        self,
        transcripts: List[Dict[str, Any]],
        topic_analysis: Dict[str, Any],
        entity_analysis: Dict[str, Any],
        action_analysis: Dict[str, Any]
    ) -> str:
        """
        Gemini APIを使用して統合サマリーを生成

        Args:
            transcripts: 文字起こしデータのリスト
            topic_analysis: トピック分析結果
            entity_analysis: エンティティ分析結果
            action_analysis: アクションアイテム分析結果

        Returns:
            統合サマリー
        """
        print(f"\n🤖 Generating integrated summary with Gemini...")

        # プロンプト作成
        file_summaries = []
        for transcript in transcripts:
            file_name = transcript.get('_file_name', 'Unknown')
            summary = transcript.get('summary', '要約なし')
            topics = [t.get('name', '') for t in transcript.get('topics', [])]

            file_summaries.append(f"""
## {file_name}
トピック: {', '.join(topics)}
要約: {summary}
""")

        prompt = f"""以下は複数のミーティングの文字起こしデータです。これらを統合して分析し、総合的なサマリーを生成してください。

【ミーティング数】
{len(transcripts)}件

【各ミーティングの要約】
{''.join(file_summaries)}

【共通トピック】
{', '.join(list(topic_analysis.get('common_topics', {}).keys())[:10])}

【繰り返し登場する人物】
{', '.join(list(entity_analysis.get('recurring_people', {}).keys())[:10])}

【繰り返し登場する組織】
{', '.join(list(entity_analysis.get('recurring_orgs', {}).keys())[:10])}

【アクションアイテム総数】
{len(action_analysis.get('all_action_items', []))}件

【出力形式】
以下の形式でMarkdownで出力してください：

# 統合サマリー

## 1. 全体概要
複数ミーティング全体を通じた主要なテーマと目的

## 2. 共通トピックの分析
複数回登場する重要なトピックとその変遷

## 3. キーパーソンと組織
繰り返し登場する人物・組織とその役割

## 4. 時系列での変化
ミーティングを通じた議論の進展や変化

## 5. アクションアイテムのまとめ
今後取るべきアクションの統合リスト

## 6. 結論と次のステップ
全体を通じた結論と推奨される次のアクション
"""

        response = self.llm.generate_content(prompt)
        summary = response.text.strip()

        print(f"   Summary generated ({len(summary)} characters)")

        return summary

    def analyze(self, json_paths: List[str]) -> Dict[str, Any]:
        """
        メイン分析処理

        Args:
            json_paths: JSONファイルパスのリスト

        Returns:
            分析結果
        """
        print("=" * 70)
        print("Phase 6-3 Stage 3-1: Cross-Meeting Analysis")
        print("=" * 70)

        # 1. ファイル読み込み
        transcripts = self.load_transcripts(json_paths)

        if len(transcripts) < 2:
            print("\n⚠️  Warning: At least 2 transcripts are recommended for cross-meeting analysis")
            if len(transcripts) == 0:
                print("❌ No valid transcripts found. Exiting.")
                return {}

        # 2. トピック分析
        topic_analysis = self.extract_common_topics(transcripts)

        # 3. エンティティ追跡
        entity_analysis = self.track_entities(transcripts)

        # 4. アクションアイテム分析
        action_analysis = self.analyze_action_items(transcripts)

        # 5. 統合サマリー生成
        integrated_summary = self.generate_integrated_summary(
            transcripts,
            topic_analysis,
            entity_analysis,
            action_analysis
        )

        # 結果をまとめる
        result = {
            "num_transcripts": len(transcripts),
            "transcripts": transcripts,
            "topic_analysis": topic_analysis,
            "entity_analysis": entity_analysis,
            "action_analysis": action_analysis,
            "integrated_summary": integrated_summary
        }

        return result

    def save_report(self, result: Dict[str, Any], output_path: str) -> None:
        """
        分析結果をMarkdownレポートとして保存

        Args:
            result: 分析結果
            output_path: 出力ファイルパス
        """
        print(f"\n💾 Saving analysis report to: {output_path}")

        with open(output_path, 'w', encoding='utf-8') as f:
            # ヘッダー
            f.write("# Cross-Meeting Analysis Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Number of Meetings:** {result['num_transcripts']}\n\n")

            # ファイル一覧
            f.write("## Analyzed Files\n\n")
            for i, transcript in enumerate(result['transcripts'], 1):
                file_name = transcript.get('_file_name', 'Unknown')
                num_segments = len(transcript.get('segments', []))
                num_topics = len(transcript.get('topics', []))
                f.write(f"{i}. `{file_name}` - {num_segments} segments, {num_topics} topics\n")

            f.write("\n---\n\n")

            # 統合サマリー
            f.write(result['integrated_summary'])

            f.write("\n\n---\n\n")

            # 統計情報
            f.write("## Detailed Statistics\n\n")

            # トピック統計
            f.write("### Topics\n\n")
            topic_counts = result['topic_analysis']['topic_counts']
            f.write(f"- Total topics: {len(topic_counts)}\n")
            f.write(f"- Common topics (2+ occurrences): {len(result['topic_analysis']['common_topics'])}\n\n")

            if topic_counts:
                f.write("**Top 10 Topics:**\n\n")
                for name, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                    f.write(f"- {name}: {count} occurrences\n")

            # エンティティ統計
            f.write("\n### Entities\n\n")
            people_counts = result['entity_analysis']['people_counts']
            org_counts = result['entity_analysis']['org_counts']

            f.write(f"- Total people: {len(people_counts)}\n")
            f.write(f"- Recurring people: {len(result['entity_analysis']['recurring_people'])}\n")
            f.write(f"- Total organizations: {len(org_counts)}\n")
            f.write(f"- Recurring organizations: {len(result['entity_analysis']['recurring_orgs'])}\n\n")

            if people_counts:
                f.write("**Top 10 People:**\n\n")
                for name, count in sorted(people_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                    f.write(f"- {name}: {count} occurrences\n")

            if org_counts:
                f.write("\n**Top 10 Organizations:**\n\n")
                for name, count in sorted(org_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                    f.write(f"- {name}: {count} occurrences\n")

            # アクションアイテム
            f.write("\n### Action Items\n\n")
            all_action_items = result['action_analysis']['all_action_items']
            f.write(f"- Total action items: {len(all_action_items)}\n\n")

            if all_action_items:
                f.write("**All Action Items:**\n\n")
                for i, item in enumerate(all_action_items, 1):
                    f.write(f"{i}. {item}\n")

        print(f"✅ Report saved: {output_path}")


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("Usage: python cross_analysis.py <json_file1> <json_file2> [json_file3 ...]")
        print("Example: python cross_analysis.py 'downloads/*_structured_enhanced.json'")
        sys.exit(1)

    # コマンドライン引数からファイルパスを取得
    json_paths = sys.argv[1:]

    # グロブパターン展開（ワイルドカード対応）
    expanded_paths = []
    for pattern in json_paths:
        from glob import glob
        matches = glob(pattern)
        if matches:
            expanded_paths.extend(matches)
        else:
            expanded_paths.append(pattern)  # パターンにマッチしない場合はそのまま追加

    # 重複削除
    json_paths = list(set(expanded_paths))

    # 分析実行
    analyzer = CrossMeetingAnalyzer()
    result = analyzer.analyze(json_paths)

    if not result:
        sys.exit(1)

    # 結果表示
    print("\n" + "=" * 70)
    print("Analysis Complete!")
    print("=" * 70)
    print(f"\n📊 Summary Statistics:")
    print(f"   Meetings analyzed: {result['num_transcripts']}")
    print(f"   Total topics: {len(result['topic_analysis']['topic_counts'])}")
    print(f"   Common topics: {len(result['topic_analysis']['common_topics'])}")
    print(f"   Recurring people: {len(result['entity_analysis']['recurring_people'])}")
    print(f"   Recurring organizations: {len(result['entity_analysis']['recurring_orgs'])}")
    print(f"   Total action items: {len(result['action_analysis']['all_action_items'])}")

    # レポート保存
    output_path = "cross_meeting_analysis_report.md"
    analyzer.save_report(result, output_path)

    print("\n" + "=" * 70)
    print(f"✅ Cross-meeting analysis completed!")
    print(f"   Report: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
