#!/usr/bin/env python3
"""
Phase 6-3 Stage 4-3: 2-Stage Action Item Structuring
アクションアイテムの構造化（Gemini 2.0 Flash使用）

2段階アプローチ:
1. Stage 1: Natural Language でアクションアイテムを抽出（推論能力維持）
2. Stage 2: Structured Output で構造化（100%スキーマ準拠）
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ActionItemStructurer:
    """2段階アクションアイテム構造化システム"""

    def __init__(self):
        """初期化"""
        # Gemini API setup
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

        print("=" * 70)
        print("Phase 6-3 Stage 4-3: 2-Stage Action Item Structuring")
        print("=" * 70)
        print("✅ Action Item Structurer initialized")
        print(f"   Model: gemini-2.0-flash-exp")
        print(f"   Method: 2-stage (Extract → Structure)\n")

    def load_meeting_content(self, json_file: str) -> Dict[str, Any]:
        """
        JSONファイルからミーティング内容を読み込み

        Args:
            json_file: JSONファイルパス

        Returns:
            ミーティングデータ
        """
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        meeting_name = Path(json_file).stem.replace('_structured_enhanced', '')

        return {
            'name': meeting_name,
            'file': json_file,
            'full_text': data.get('full_text', ''),
            'segments': data.get('segments', []),
            'topics': data.get('topics', []),
            'entities': data.get('entities', {}),
            'existing_action_items': data.get('entities', {}).get('action_items', [])
        }

    def stage1_extract_action_items(self, meeting: Dict[str, Any]) -> str:
        """
        Stage 1: Natural Language でアクションアイテムを抽出
        推論能力を最大化するため、構造化しない

        Args:
            meeting: ミーティングデータ

        Returns:
            抽出されたアクションアイテム（テキスト形式）
        """
        print(f"📝 Stage 1: Extracting action items from [{meeting['name']}]...")

        # 既存のアクションアイテムを参考情報として追加
        existing_items = meeting.get('existing_action_items', [])
        existing_text = ""
        if existing_items:
            existing_text = "\n\n【参考：既存抽出されたアクションアイテム】\n"
            for item in existing_items[:5]:
                existing_text += f"- {item}\n"

        # トピック情報を追加
        topics_text = ""
        if meeting.get('topics'):
            topics_text = "\n\n【ミーティングのトピック】\n"
            for topic in meeting['topics'][:3]:
                topics_text += f"- {topic.get('name', '')}\n"

        # プロンプト作成（Natural Language）
        prompt = f"""以下のミーティング文字起こしから、アクションアイテム（実行すべきタスク）を抽出してください。

【抽出基準】
1. 明示的なアクション
   - 「〜する」「〜しよう」「〜してください」などの行動を示す表現
   - 「検討する」「調べる」「連絡する」「送る」「確認する」などの動詞

2. 暗黙的なアクション
   - 「〜が必要」「〜したい」「〜すべき」などの表現
   - 「〜しないと」「〜までに」などの期限を示す表現

3. 担当者の推測
   - 発言者が自分自身のタスクとして述べている場合
   - 「私が〜」「僕が〜」「こちらで〜」などの表現
   - 特定の人物に依頼している場合

4. 期限の推測
   - 「今週中」「来週」「月末」「来月」などの期限表現
   - 「早めに」「急いで」などの緊急性を示す表現
   - 日付や曜日の言及

5. 優先度の推測
   - 「重要」「緊急」「優先的に」→ high
   - 「できれば」「余裕があれば」→ low
   - その他 → medium

【抽出フォーマット】
各アクションアイテムを以下の形式で列挙してください：

アクション: [具体的なタスク内容]
担当者: [推測される担当者、不明な場合は「未定」]
期限: [推測される期限、不明な場合は「未定」]
優先度: [high/medium/low、不明な場合は「medium」]
根拠: [このアクションアイテムを抽出した元の発言やセグメント]

---
{existing_text}{topics_text}

【ミーティング文字起こし（抜粋）】
{meeting['full_text'][:8000]}

上記の文字起こしからアクションアイテムを抽出してください。
"""

        try:
            # Gemini API呼び出し（Natural Language）
            response = self.model.generate_content(prompt)
            extracted_text = response.text.strip()

            print(f"   ✅ Extracted action items (text format)")
            return extracted_text

        except Exception as e:
            print(f"   ❌ Error extracting action items: {e}")
            return ""

    def stage2_structure_action_items(self, extracted_text: str, meeting_name: str) -> List[Dict[str, Any]]:
        """
        Stage 2: Structured Output で構造化
        100%スキーマ準拠を保証

        Args:
            extracted_text: Stage 1で抽出されたテキスト
            meeting_name: ミーティング名

        Returns:
            構造化されたアクションアイテムのリスト
        """
        print(f"🔧 Stage 2: Structuring action items for [{meeting_name}]...")

        # JSON Schema定義
        schema = {
            "type": "object",
            "properties": {
                "action_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "具体的なタスク内容"
                            },
                            "assignee": {
                                "type": "string",
                                "description": "担当者名（不明な場合は'未定'）"
                            },
                            "deadline": {
                                "type": "string",
                                "description": "期限（不明な場合は'未定'）"
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "優先度"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["todo", "in_progress", "done"],
                                "description": "ステータス（デフォルト: todo）"
                            },
                            "context": {
                                "type": "string",
                                "description": "根拠となる発言や文脈"
                            }
                        },
                        "required": ["action", "assignee", "deadline", "priority", "status"]
                    }
                }
            },
            "required": ["action_items"]
        }

        # プロンプト作成（Structured Output）
        prompt = f"""以下のアクションアイテム抽出結果を、指定されたJSON形式に構造化してください。

【重要な指示】
1. すべてのアクションアイテムを漏れなく含める
2. 担当者が不明な場合は「未定」
3. 期限が不明な場合は「未定」
4. 優先度が不明な場合は「medium」
5. ステータスは基本的に「todo」（完了済みの場合のみ「done」）
6. context には根拠となる発言を簡潔に記載

【抽出結果】
{extracted_text}

上記を指定されたJSON形式に構造化してください。
"""

        try:
            # Gemini API呼び出し（Structured Output）
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": schema
                }
            )

            # JSON解析
            result = json.loads(response.text)
            action_items = result.get('action_items', [])

            print(f"   ✅ Structured {len(action_items)} action items")
            return action_items

        except Exception as e:
            print(f"   ❌ Error structuring action items: {e}")
            return []

    def update_json_file(self, json_file: str, action_items: List[Dict[str, Any]]):
        """
        JSONファイルにアクションアイテムを追加

        Args:
            json_file: JSONファイルパス
            action_items: 構造化されたアクションアイテム
        """
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # structured_action_items フィールドを追加
        data['structured_action_items'] = action_items

        # ファイルに書き戻し
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"   💾 Updated: {json_file}\n")

    def process_file(self, json_file: str) -> Dict[str, Any]:
        """
        1つのファイルを処理（2段階）

        Args:
            json_file: JSONファイルパス

        Returns:
            処理結果
        """
        # ミーティング内容読み込み
        meeting = self.load_meeting_content(json_file)

        # Stage 1: 抽出（Natural Language）
        extracted_text = self.stage1_extract_action_items(meeting)

        if not extracted_text:
            return {
                'file': json_file,
                'status': 'failed',
                'action_items': []
            }

        # Stage 2: 構造化（Structured Output）
        action_items = self.stage2_structure_action_items(extracted_text, meeting['name'])

        # JSONファイル更新
        self.update_json_file(json_file, action_items)

        return {
            'file': json_file,
            'status': 'success',
            'action_items': action_items,
            'count': len(action_items)
        }

    def generate_report(self, results: List[Dict[str, Any]], output_file: str = "action_items_report.md"):
        """
        アクションアイテムレポート生成

        Args:
            results: 各ファイルの処理結果
            output_file: 出力ファイル名
        """
        print(f"📊 Generating action items report: {output_file}")

        total_items = sum(r.get('count', 0) for r in results)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Action Items Structuring Report\n\n")
            f.write("**Method:** 2-Stage LLM Processing (Gemini 2.0 Flash)\n")
            f.write("- Stage 1: Natural Language Extraction (推論能力維持)\n")
            f.write("- Stage 2: Structured Output (100%スキーマ準拠)\n\n")

            # サマリー
            f.write("## Summary\n\n")
            f.write(f"- Total meetings processed: {len(results)}\n")
            f.write(f"- Total action items extracted: {total_items}\n")
            f.write(f"- Average per meeting: {total_items / len(results):.1f}\n\n")

            # 各ミーティングのアクションアイテム
            for result in results:
                meeting_name = Path(result['file']).stem.replace('_structured_enhanced', '')
                action_items = result.get('action_items', [])

                f.write(f"## {meeting_name}\n\n")
                f.write(f"**Action Items: {len(action_items)}**\n\n")

                if action_items:
                    for i, item in enumerate(action_items, 1):
                        f.write(f"### {i}. {item['action']}\n\n")
                        f.write(f"- **担当者:** {item['assignee']}\n")
                        f.write(f"- **期限:** {item['deadline']}\n")
                        f.write(f"- **優先度:** {item['priority']}\n")
                        f.write(f"- **ステータス:** {item['status']}\n")
                        if item.get('context'):
                            f.write(f"- **根拠:** {item['context']}\n")
                        f.write("\n")
                else:
                    f.write("No action items found.\n\n")

        print(f"✅ Report saved: {output_file}\n")


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("Usage: python action_item_structuring.py <json_file1> <json_file2> ...")
        sys.exit(1)

    json_files = sys.argv[1:]

    # ActionItemStructurer初期化
    structurer = ActionItemStructurer()

    # 各ファイルを処理
    results = []
    for json_file in json_files:
        print(f"{'=' * 70}")
        print(f"Processing: {Path(json_file).name}")
        print(f"{'=' * 70}\n")

        result = structurer.process_file(json_file)
        results.append(result)

    # レポート生成
    structurer.generate_report(results)

    print("=" * 70)
    print("✅ Action item structuring completed!")
    print(f"   Total files: {len(results)}")
    print(f"   Total action items: {sum(r.get('count', 0) for r in results)}")
    print(f"   Cost: Free (Gemini 2.0 Flash)")
    print("=" * 70)


if __name__ == "__main__":
    main()
