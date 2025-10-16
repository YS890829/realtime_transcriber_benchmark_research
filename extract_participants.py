#!/usr/bin/env python3
"""
Phase 11-3: カレンダーdescriptionからの参加者情報抽出
作成日: 2025-10-16

このモジュールは、Google CalendarイベントのdescriptionフィールドからLLMを使用して
参加者情報を抽出します。
"""

import google.generativeai as genai
import json
import re
import os
from typing import List, Dict
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# Gemini API設定（無料枠を使用）
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_FREE")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def extract_participants_from_description(description: str) -> List[Dict[str, str]]:
    """
    カレンダーイベントのdescriptionフィールドから参加者情報を抽出

    Args:
        description: カレンダーイベントのメモテキスト

    Returns:
        [{"canonical_name": "田中太郎", "display_names": ["田中", "田中部長"],
          "role": "部長", "organization": "営業部"}, ...]
        抽出失敗時は空リスト
    """
    if not description or not description.strip():
        return []

    # 参加者関連キーワードの存在チェック
    participant_keywords = ['参加者', '出席者', 'メンバー', '同席', '出席', '参加']
    has_participant_info = any(keyword in description for keyword in participant_keywords)

    if not has_participant_info:
        return []

    if not GEMINI_API_KEY:
        print("警告: GEMINI_API_KEYが設定されていません")
        return []

    model = genai.GenerativeModel("gemini-2.0-flash-exp")

    prompt = f"""
以下の会議メモから参加者の情報を抽出してください。

メモ:
{description}

抽出ルール:
1. 参加者の名前を可能な限り正確に抽出
2. 役職や組織が記載されていれば一緒に抽出
3. "〜さん"、"〜部長" などの敬称・役職も含める
4. 曖昧な表現（"他数名"など）は除外
5. canonical_nameは最も基本的な名前（苗字または フルネーム）を推測
6. display_namesには文中に登場する全ての呼び方を含める

出力形式（JSON）:
{{
    "participants": [
        {{
            "canonical_name": "田中",
            "display_names": ["田中", "田中部長", "田中さん"],
            "role": "部長",
            "organization": "営業部"
        }},
        {{
            "canonical_name": "佐藤",
            "display_names": ["佐藤", "佐藤さん"],
            "role": null,
            "organization": null
        }}
    ]
}}

注意:
- canonical_nameは短い形（苗字のみ）で良い
- roleやorganizationが不明な場合はnullを設定
- JSONのみを出力し、説明文は不要
"""

    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # JSONブロックを抽出（```json ... ``` の形式に対応）
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group(1)
        # ```なしのJSONにも対応
        elif result_text.startswith('{'):
            pass
        else:
            # JSON形式でない場合
            print(f"警告: JSON形式でない応答: {result_text[:100]}")
            return []

        result = json.loads(result_text)
        participants = result.get("participants", [])

        # データ検証
        validated_participants = []
        for p in participants:
            if "canonical_name" in p and p["canonical_name"]:
                # display_namesがない場合はcanonical_nameで初期化
                if "display_names" not in p or not p["display_names"]:
                    p["display_names"] = [p["canonical_name"]]
                validated_participants.append(p)

        return validated_participants

    except json.JSONDecodeError as e:
        print(f"JSON パースエラー: {e}")
        print(f"応答テキスト: {result_text[:200]}")
        return []
    except Exception as e:
        print(f"参加者抽出エラー: {e}")
        return []


def normalize_participant_name(name: str) -> str:
    """
    参加者名の正規化（敬称・役職削除）

    Args:
        name: 元の名前（例: "田中部長"）

    Returns:
        正規化された名前（例: "田中"）
    """
    # 役職・敬称のパターン
    suffixes = [
        'さん', '様', '氏', '君',
        '部長', '課長', '係長', '主任', '担当',
        '社長', '専務', '常務', '取締役', '役員',
        '室長', 'グループリーダー', 'リーダー', 'マネージャー',
        'さま'  # 「様」の別表記
    ]

    normalized = name
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]

    return normalized.strip()


if __name__ == "__main__":
    # テスト用サンプル
    print("=== extract_participants.py テスト ===\n")

    # テストケース1: 明確な参加者情報
    test_description_1 = """
【参加者】
- 田中部長（営業部）
- 佐藤さん（マーケティング）
- 鈴木（開発チーム）

【議題】
新製品の販売戦略について
"""

    print("テストケース1: 明確な参加者情報")
    print(f"Description: {test_description_1.strip()[:80]}...")
    participants_1 = extract_participants_from_description(test_description_1)
    print(f"抽出結果: {len(participants_1)}名")
    for p in participants_1:
        print(f"  - {p['canonical_name']}: {p.get('role', 'N/A')} ({p.get('organization', 'N/A')})")
        print(f"    display_names: {p['display_names']}")
    print()

    # テストケース2: 参加者情報なし
    test_description_2 = """
【議題】
予算の検討

【メモ】
来週までに資料を作成すること
"""

    print("テストケース2: 参加者情報なし")
    print(f"Description: {test_description_2.strip()[:80]}...")
    participants_2 = extract_participants_from_description(test_description_2)
    print(f"抽出結果: {len(participants_2)}名")
    print()

    # テストケース3: 簡潔な参加者情報
    test_description_3 = """
出席者: 田中、佐藤、山本
"""

    print("テストケース3: 簡潔な参加者情報")
    print(f"Description: {test_description_3.strip()}")
    participants_3 = extract_participants_from_description(test_description_3)
    print(f"抽出結果: {len(participants_3)}名")
    for p in participants_3:
        print(f"  - {p['canonical_name']}: display_names={p['display_names']}")
    print()

    # normalize_participant_name のテスト
    print("normalize_participant_name テスト:")
    test_names = ["田中部長", "佐藤さん", "鈴木様", "山本", "高橋マネージャー"]
    for name in test_names:
        normalized = normalize_participant_name(name)
        print(f"  {name} → {normalized}")

    print("\n=== テスト完了 ===")
