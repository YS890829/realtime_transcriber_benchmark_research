#!/usr/bin/env python3
"""
Summary Generator Module (Phase 11-1)
予定情報を統合した高精度要約生成

使い方:
    from summary_generator import generate_summary_with_calendar

    summary = generate_summary_with_calendar(transcript_segments, matched_event)

機能:
- 文字起こし全文 + カレンダー予定情報から要約生成
- フォールバック処理（予定なし時は予定情報なしで要約生成）
"""

import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

# 環境変数読み込み
load_dotenv()


def generate_summary_with_calendar(transcript_segments: list, matched_event: dict = None, participants_context: str = "") -> dict:
    """
    予定情報と参加者DB情報を統合した要約生成（Phase 11-3対応）

    Args:
        transcript_segments: 文字起こしセグメントリスト
        matched_event: マッチした予定情報（Noneの場合は予定情報なし）
        participants_context: 参加者の過去情報（整形済みテキスト）

    Returns:
        {
            "summary": "概要",
            "topics": ["トピック1", "トピック2", ...],
            "action_items": ["アイテム1", ...],
            "keywords": ["キーワード1", ...]
        }
    """
    # Gemini API設定（既存の仕組みに合わせる）
    use_paid = os.getenv('USE_PAID_TIER', 'false').lower() == 'true'
    if use_paid:
        api_key = os.getenv('GEMINI_API_KEY_PAID')
        if not api_key:
            print("❌ GEMINI_API_KEY_PAIDが設定されていません")
            return {
                "summary": "（エラー: API KEY未設定）",
                "topics": [],
                "action_items": [],
                "keywords": []
            }
    else:
        api_key = os.getenv('GEMINI_API_KEY_FREE')
        if not api_key:
            print("❌ GEMINI_API_KEY_FREEが設定されていません")
            return {
                "summary": "（エラー: API KEY未設定）",
                "topics": [],
                "action_items": [],
                "keywords": []
            }

    genai.configure(api_key=api_key)

    # 文字起こし全文を結合
    full_text = "\n".join([seg.get('text', '') for seg in transcript_segments])

    # 予定情報のコンテキスト生成
    calendar_context = ""
    if matched_event:
        summary_title = matched_event.get('summary', '')
        start_time = matched_event.get('start', {}).get('dateTime', matched_event.get('start', {}).get('date', ''))
        end_time = matched_event.get('end', {}).get('dateTime', matched_event.get('end', {}).get('date', ''))
        description = matched_event.get('description', '')

        # 参加者リスト（attendeesフィールドから取得）
        attendees = matched_event.get('attendees', [])
        attendees_names = []
        if attendees:
            # emailからdisplayNameを優先、なければemailのユーザー名部分を使用
            for a in attendees:
                display_name = a.get('displayName', '')
                email = a.get('email', '')
                if display_name:
                    attendees_names.append(display_name)
                elif email:
                    # email の @ 前を使用
                    attendees_names.append(email.split('@')[0])

        # descriptionに参加者情報がある場合も考慮
        # 実運用では「参加者：」「出席者：」などの記載がdescriptionに含まれることが多い
        attendees_str = '、'.join(attendees_names) if attendees_names else '（attendeesフィールドには未記載）'

        # メモ（description）に参加者情報が含まれている可能性があることを明示
        description_note = ""
        if description and any(keyword in description for keyword in ['参加者', '出席者', 'メンバー', '同席']):
            description_note = "\n※ メモ内に参加者情報が記載されている可能性があります"

        calendar_context = f"""
【関連するカレンダー予定】
- タイトル: {summary_title}
- 時刻: {start_time} 〜 {end_time}
- メモ: {description if description else 'なし'}{description_note}
- 参加者（attendeesフィールド）: {attendees_str}

この音声は上記の予定に関連する内容です。予定の情報も踏まえて要約してください。
特に、メモ内に参加者や関係者の情報が記載されている場合は、それも参考にしてください。
"""
        print("📝 予定情報を要約生成に統合します")
    else:
        print("📝 予定情報なしで要約生成します")

    # 参加者DB情報を統合（Phase 11-3）
    if participants_context:
        calendar_context += f"\n{participants_context}"
        print("📝 参加者DB情報を要約生成に統合します")

    # プロンプト作成
    prompt = f"""{calendar_context}

【文字起こし全文】
{full_text}

【タスク】
以下の形式で要約を生成してください：

1. **概要**（2-3文で全体を要約。予定情報がある場合は予定タイトルや参加者も含める）
2. **主要トピック**（箇条書き、3-7個）
3. **重要な決定事項・アクションアイテム**（あれば箇条書き、なければ空配列）
4. **キーワード**（5-10個）

【出力形式（JSON）】
{{
  "summary": "概要（予定情報も含めた文脈で記述）",
  "topics": ["トピック1", "トピック2", ...],
  "action_items": ["アイテム1", "アイテム2", ...],
  "keywords": ["キーワード1", "キーワード2", ...]
}}

**重要**: 必ずJSON形式のみを出力してください。他の説明文は不要です。
"""

    try:
        # Gemini 2.5 Flash（既存の要約生成と同じモデル）
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(prompt)

        # JSONパース
        response_text = response.text.strip()

        # Markdown code blockを削除
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()

        summary_result = json.loads(response_text)

        print(f"✅ 要約生成完了")
        print(f"   概要: {summary_result.get('summary', '')[:100]}...")
        print(f"   トピック数: {len(summary_result.get('topics', []))}")
        print(f"   アクションアイテム数: {len(summary_result.get('action_items', []))}")
        print(f"   キーワード数: {len(summary_result.get('keywords', []))}")

        return summary_result

    except json.JSONDecodeError as e:
        print(f"❌ JSON解析エラー: {e}")
        print(f"レスポンス: {response.text[:500]}")
        return {
            "summary": f"（エラー: JSON解析失敗）",
            "topics": [],
            "action_items": [],
            "keywords": []
        }
    except Exception as e:
        print(f"❌ 要約生成エラー: {e}")
        return {
            "summary": f"（エラー: {str(e)}）",
            "topics": [],
            "action_items": [],
            "keywords": []
        }


if __name__ == '__main__':
    # テスト用
    print("=== Summary Generator Test ===")

    # テストデータ
    test_segments = [
        {"text": "今日は営業ミーティングです。"},
        {"text": "Q4の戦略について話し合いました。"},
        {"text": "新製品のローンチ計画を確認しました。"}
    ]

    test_event = {
        "summary": "営業ミーティング",
        "start": {"dateTime": "2025-10-16T14:00:00+09:00"},
        "end": {"dateTime": "2025-10-16T15:00:00+09:00"},
        "description": "Q4戦略レビュー",
        "attendees": [
            {"email": "tanaka@example.com", "displayName": "田中太郎"},
            {"email": "yamada@example.com", "displayName": "山田花子"}
        ]
    }

    # テスト1: 予定情報あり
    print("\n--- テスト1: 予定情報あり ---")
    summary1 = generate_summary_with_calendar(test_segments, test_event)
    print(json.dumps(summary1, ensure_ascii=False, indent=2))

    # テスト2: 予定情報なし
    print("\n--- テスト2: 予定情報なし ---")
    summary2 = generate_summary_with_calendar(test_segments, None)
    print(json.dumps(summary2, ensure_ascii=False, indent=2))
