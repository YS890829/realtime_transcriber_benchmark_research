#!/usr/bin/env python3
"""
Phase 6-3 Stage 4-2: LLM-Based Entity Resolution
エンティティ名寄せ（Gemini 2.0 Flash使用）

同一人物・同一組織の異なる表記を統合する
- 「福島さん」「福島」→ 同一人物
- 「リクルート」「リクルートホールディングス」→ 同一組織
- 文脈を考慮してLLMが判断
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EntityResolver:
    """LLMベースのエンティティ解決システム"""

    def __init__(self):
        """初期化"""
        # Gemini API setup
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

        print("=" * 70)
        print("Phase 6-3 Stage 4-2: LLM-Based Entity Resolution")
        print("=" * 70)
        print("✅ Entity Resolver initialized")
        print(f"   Model: gemini-2.0-flash-exp\n")

    def load_entities_from_json(self, json_files: List[str]) -> Tuple[List[Dict], List[Dict]]:
        """
        JSONファイルから人物・組織エンティティを抽出

        Args:
            json_files: JSONファイルパスのリスト

        Returns:
            (people_list, organizations_list)
        """
        people_dict = defaultdict(lambda: {
            'name': '',
            'occurrences': 0,
            'contexts': []
        })

        orgs_dict = defaultdict(lambda: {
            'name': '',
            'occurrences': 0,
            'contexts': []
        })

        for json_file in json_files:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            meeting_name = Path(json_file).stem.replace('_structured_enhanced', '')
            entities = data.get('entities', {})
            segments = data.get('segments', [])

            # 人物エンティティ（文字列のリスト）
            for person in entities.get('people', []):
                # personは文字列
                if isinstance(person, str):
                    name = person.strip()
                else:
                    # 辞書形式の場合も対応
                    name = person.get('name', '').strip()

                if not name:
                    continue

                # 文脈を取得（セグメントテキストから）
                contexts = []
                for segment in segments:
                    if name in segment.get('text', ''):
                        # 前後50文字を文脈として取得
                        text = segment.get('text', '')
                        idx = text.find(name)
                        start = max(0, idx - 50)
                        end = min(len(text), idx + len(name) + 50)
                        context_text = text[start:end]

                        contexts.append({
                            'meeting': meeting_name,
                            'text': context_text,
                            'timestamp': f"{segment.get('start', 0):.1f}s",
                            'full_text': text
                        })

                        # 最大3つの文脈まで
                        if len(contexts) >= 3:
                            break

                people_dict[name]['name'] = name
                people_dict[name]['occurrences'] += 1
                people_dict[name]['contexts'].extend(contexts)

            # 組織エンティティ（文字列のリスト）
            for org in entities.get('organizations', []):
                # orgは文字列
                if isinstance(org, str):
                    name = org.strip()
                else:
                    # 辞書形式の場合も対応
                    name = org.get('name', '').strip()

                if not name:
                    continue

                # 文脈を取得
                contexts = []
                for segment in segments:
                    if name in segment.get('text', ''):
                        text = segment.get('text', '')
                        idx = text.find(name)
                        start = max(0, idx - 50)
                        end = min(len(text), idx + len(name) + 50)
                        context_text = text[start:end]

                        contexts.append({
                            'meeting': meeting_name,
                            'text': context_text,
                            'timestamp': f"{segment.get('start', 0):.1f}s",
                            'full_text': text
                        })

                        if len(contexts) >= 3:
                            break

                orgs_dict[name]['name'] = name
                orgs_dict[name]['occurrences'] += 1
                orgs_dict[name]['contexts'].extend(contexts)

        people_list = list(people_dict.values())
        orgs_list = list(orgs_dict.values())

        print(f"📂 Loaded entities from {len(json_files)} files")
        print(f"   People: {len(people_list)}")
        print(f"   Organizations: {len(orgs_list)}\n")

        return people_list, orgs_list

    def resolve_people_with_llm(self, people: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        LLMを使用して人物エンティティを解決

        Args:
            people: 人物エンティティのリスト

        Returns:
            解決結果の辞書
        """
        print(f"🤖 Resolving {len(people)} people with Gemini...\n")

        # 人物情報を整形
        people_info = []
        for i, person in enumerate(people, 1):
            info = f"{i}. {person['name']}"
            info += f"\n   出現回数: {person['occurrences']}回"

            if person['contexts']:
                info += "\n   文脈例:"
                for j, ctx in enumerate(person['contexts'][:2], 1):
                    meeting = ctx['meeting'][:30]
                    text = ctx['text'].replace('\n', ' ')[:80]
                    info += f"\n     - [{meeting}] {text}..."

            people_info.append(info)

        people_text = "\n\n".join(people_info)

        # プロンプト作成
        prompt = f"""以下は複数のミーティングから抽出された{len(people)}名の人物エンティティです。
同一人物と思われるものをグループ化してください。

【重要な判断基準】
1. 敬称の有無（「福島さん」「福島」）は無視して同一人物と判断
2. 姓のみの場合、文脈から同一人物か別人かを判断
3. 異なるミーティングで全く異なる文脈の同姓は別人の可能性
4. 文脈が不十分で判断できない場合は「判断不可」とする
5. 自信がない場合は confidence を "low" にする

【人物リスト】（{len(people)}名）
{people_text}

【出力形式】JSON形式で出力（コードブロック不要、JSONのみ）
{{
  "people_groups": [
    {{
      "canonical_name": "正規化された名前（敬称なし）",
      "variants": ["表記バリエーション1", "表記バリエーション2"],
      "entity_ids": [元のリストの番号],
      "is_same_person": true,
      "confidence": "high" | "medium" | "low",
      "reason": "グループ化の理由（1-2文）"
    }}
  ],
  "separate_entities": [
    {{
      "name": "人物名",
      "entity_id": 番号,
      "reason": "別人と判断した理由 or 判断不可の理由"
    }}
  ]
}}
"""

        try:
            # Gemini API呼び出し
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # JSON抽出
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result = json.loads(response_text)

            print("✅ People resolution completed")
            print(f"   Groups found: {len(result.get('people_groups', []))}")
            print(f"   Separate entities: {len(result.get('separate_entities', []))}\n")

            return result

        except Exception as e:
            print(f"❌ Error resolving people: {e}")
            return {"people_groups": [], "separate_entities": []}

    def resolve_organizations_with_llm(self, organizations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        LLMを使用して組織エンティティを解決

        Args:
            organizations: 組織エンティティのリスト

        Returns:
            解決結果の辞書
        """
        print(f"🤖 Resolving {len(organizations)} organizations with Gemini...\n")

        # 組織情報を整形
        org_info = []
        for i, org in enumerate(organizations, 1):
            info = f"{i}. {org['name']}"
            info += f"\n   出現回数: {org['occurrences']}回"

            if org['contexts']:
                info += "\n   文脈例:"
                for j, ctx in enumerate(org['contexts'][:2], 1):
                    meeting = ctx['meeting'][:30]
                    text = ctx['text'].replace('\n', ' ')[:80]
                    info += f"\n     - [{meeting}] {text}..."

            org_info.append(info)

        org_text = "\n\n".join(org_info)

        # プロンプト作成
        prompt = f"""以下は複数のミーティングから抽出された{len(organizations)}組織のエンティティです。
同一組織と思われるものをグループ化してください。

【重要な判断基準】
1. 略称と正式名称を統合（「リクルート」「リクルートホールディングス」）
2. 親会社と子会社の関係（実質同一とみなすか、別組織とするか文脈で判断）
3. 英語表記とカタカナ表記（「Apple」「アップル」）
4. 文脈が不十分で判断できない場合は「判断不可」とする
5. 自信がない場合は confidence を "low" にする

【組織リスト】（{len(organizations)}組織）
{org_text}

【出力形式】JSON形式で出力（コードブロック不要、JSONのみ）
{{
  "org_groups": [
    {{
      "canonical_name": "正規化された名前",
      "variants": ["表記バリエーション1", "表記バリエーション2"],
      "entity_ids": [元のリストの番号],
      "is_same_org": true,
      "confidence": "high" | "medium" | "low",
      "reason": "グループ化の理由（1-2文）"
    }}
  ],
  "separate_entities": [
    {{
      "name": "組織名",
      "entity_id": 番号,
      "reason": "別組織と判断した理由 or 判断不可の理由"
    }}
  ]
}}
"""

        try:
            # Gemini API呼び出し
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # JSON抽出
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result = json.loads(response_text)

            print("✅ Organization resolution completed")
            print(f"   Groups found: {len(result.get('org_groups', []))}")
            print(f"   Separate entities: {len(result.get('separate_entities', []))}\n")

            return result

        except Exception as e:
            print(f"❌ Error resolving organizations: {e}")
            return {"org_groups": [], "separate_entities": []}

    def generate_report(self,
                       people: List[Dict],
                       people_result: Dict,
                       organizations: List[Dict],
                       org_result: Dict,
                       output_file: str = "entity_resolution_report.md"):
        """
        エンティティ解決レポートを生成

        Args:
            people: 元の人物リスト
            people_result: 人物解決結果
            organizations: 元の組織リスト
            org_result: 組織解決結果
            output_file: 出力ファイル名
        """
        print(f"💾 Generating entity resolution report: {output_file}")

        # 統合後のエンティティ数を計算
        people_merged = len(people_result.get('people_groups', []))
        people_separate = len(people_result.get('separate_entities', []))
        people_after = people_merged + people_separate

        org_merged = len(org_result.get('org_groups', []))
        org_separate = len(org_result.get('separate_entities', []))
        org_after = org_merged + org_separate

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Entity Resolution Report\n\n")
            f.write("**Method:** LLM-based (Gemini 2.0 Flash)\n\n")

            # サマリー
            f.write("## Summary\n\n")
            f.write("| Entity Type | Before | After | Reduction |\n")
            f.write("|-------------|--------|-------|----------|\n")
            f.write(f"| People | {len(people)} | {people_after} | {len(people) - people_after} ({(len(people) - people_after) / len(people) * 100:.1f}%) |\n")
            f.write(f"| Organizations | {len(organizations)} | {org_after} | {len(organizations) - org_after} ({(len(organizations) - org_after) / len(organizations) * 100:.1f}%) |\n")
            f.write(f"| **Total** | **{len(people) + len(organizations)}** | **{people_after + org_after}** | **{(len(people) + len(organizations)) - (people_after + org_after)}** |\n\n")

            # 人物グループ
            f.write("## People Resolution\n\n")
            f.write(f"### Merged Groups ({people_merged} groups)\n\n")

            for i, group in enumerate(people_result.get('people_groups', []), 1):
                f.write(f"#### {i}. {group['canonical_name']}\n\n")
                f.write(f"**Variants:** {', '.join(group['variants'])}\n\n")
                f.write(f"**Confidence:** {group['confidence']}\n\n")
                f.write(f"**Reason:** {group['reason']}\n\n")

            if people_result.get('separate_entities'):
                f.write(f"\n### Separate People ({people_separate} entities)\n\n")
                for entity in people_result.get('separate_entities', []):
                    f.write(f"- **{entity['name']}**: {entity['reason']}\n")
                f.write("\n")

            # 組織グループ
            f.write("## Organization Resolution\n\n")
            f.write(f"### Merged Groups ({org_merged} groups)\n\n")

            for i, group in enumerate(org_result.get('org_groups', []), 1):
                f.write(f"#### {i}. {group['canonical_name']}\n\n")
                f.write(f"**Variants:** {', '.join(group['variants'])}\n\n")
                f.write(f"**Confidence:** {group['confidence']}\n\n")
                f.write(f"**Reason:** {group['reason']}\n\n")

            if org_result.get('separate_entities'):
                f.write(f"\n### Separate Organizations ({org_separate} entities)\n\n")
                for entity in org_result.get('separate_entities', []):
                    f.write(f"- **{entity['name']}**: {entity['reason']}\n")
                f.write("\n")

        print(f"✅ Report saved: {output_file}\n")


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("Usage: python entity_resolution_llm.py <json_file1> <json_file2> ...")
        sys.exit(1)

    json_files = sys.argv[1:]

    # EntityResolver初期化
    resolver = EntityResolver()

    # エンティティ抽出
    people, organizations = resolver.load_entities_from_json(json_files)

    # 人物解決
    people_result = resolver.resolve_people_with_llm(people)

    # 組織解決
    org_result = resolver.resolve_organizations_with_llm(organizations)

    # レポート生成
    resolver.generate_report(people, people_result, organizations, org_result)

    print("=" * 70)
    print("✅ Entity resolution completed!")
    print("   Cost: Free (Gemini 2.0 Flash)")
    print("=" * 70)


if __name__ == "__main__":
    main()
