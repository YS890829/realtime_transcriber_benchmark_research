#!/usr/bin/env python3
"""
Phase 11-3: 統合パイプライン
作成日: 2025-10-16

Phase 11-3の8ステップを統合したメインパイプライン:
Step 1: 構造化JSON読み込み
Step 2: カレンダーイベントマッチング
Step 3: 参加者抽出
Step 4: 参加者DB検索
Step 5: 話者推論
Step 6: 要約生成
Step 7: 参加者DB更新
Step 8: 会議情報登録
"""

import os
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional

from participants_db import ParticipantsDB
from extract_participants import extract_participants_from_description
from enhanced_speaker_inference import infer_speakers_with_participants, apply_speaker_inference_to_structured_json
from calendar_integration import get_events_for_file_date, match_event_with_transcript


def run_phase_11_3_pipeline(structured_file_path: str) -> Dict:
    """
    Phase 11-3 統合パイプライン

    処理フロー:
    1. 構造化JSONファイル読み込み
    2. カレンダーイベントマッチング
    3. 参加者情報抽出（description）
    4. 参加者DB検索（過去情報取得）
    5. 話者推論（参加者情報統合版）
    6. 要約生成（参加者DB情報統合）※ 現在は省略、M4完成後に実装
    7. 参加者DB更新（UPSERT）
    8. 会議情報登録

    Args:
        structured_file_path: 構造化JSONファイルパス（Phase 1出力）

    Returns:
        {
            "meeting_id": str,
            "matched_event": dict or None,
            "calendar_participants": list,
            "inference_result": dict,
            "success": bool
        }
    """
    print(f"\n{'='*60}")
    print(f"[Phase 11-3] パイプライン開始: {os.path.basename(structured_file_path)}")
    print(f"{'='*60}\n")

    # ========================
    # Step 1: 構造化JSON読み込み
    # ========================
    print("[Step 1] 構造化JSON読み込み中...")
    with open(structured_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    segments = data.get("segments", [])
    metadata = data.get("metadata", {})
    file_date = metadata.get("date", "")

    print(f"  ✓ ファイル読み込み完了: {len(segments)} セグメント")
    print(f"  ✓ 会議日: {file_date}")

    # ========================
    # Step 2: カレンダーイベントマッチング
    # ========================
    print("\n[Step 2] カレンダーイベントマッチング中...")
    matched_event = None
    try:
        events = get_events_for_file_date(file_date)
        if events:
            # 会話の最初の部分を使ってマッチング
            transcript_text = "\n".join([seg["text"] for seg in segments[:20]])
            matched_event = match_event_with_transcript(transcript_text, events)
            if matched_event:
                print(f"  ✓ マッチ成功: {matched_event.get('summary', '無題')}")
            else:
                print("  ⚠ マッチング失敗: 該当するイベントなし")
        else:
            print("  ⚠ カレンダーイベントが見つかりません")
    except Exception as e:
        print(f"  ⚠ カレンダーAPI エラー: {e}")

    # ========================
    # Step 3: 参加者情報抽出
    # ========================
    print("\n[Step 3] 参加者情報抽出中...")
    calendar_participants = []
    if matched_event:
        description = matched_event.get('description', '')
        if description:
            calendar_participants = extract_participants_from_description(description)
            print(f"  ✓ 参加者抽出完了: {len(calendar_participants)} 名")
            for p in calendar_participants:
                role_org = []
                if p.get('role'):
                    role_org.append(p['role'])
                if p.get('organization'):
                    role_org.append(p['organization'])
                role_org_str = f" ({', '.join(role_org)})" if role_org else ""
                print(f"    - {p.get('canonical_name', '不明')}{role_org_str}")
        else:
            print("  ⚠ description フィールドが空")
    else:
        print("  ⏭ スキップ（イベントマッチングなし）")

    # ========================
    # Step 4: 参加者DB検索（過去情報取得）
    # ========================
    print("\n[Step 4] 参加者DB検索中...")
    db = ParticipantsDB()
    participants_past_info = {}

    if calendar_participants:
        for p in calendar_participants:
            canonical_name = p.get("canonical_name", "")
            past_info = db.get_participant_info(canonical_name)
            if past_info:
                participants_past_info[canonical_name] = past_info
                print(f"  ✓ {canonical_name}: 過去 {past_info['meeting_count']} 回の会議参加")
            else:
                print(f"  ℹ {canonical_name}: 初登場")
    else:
        print("  ⏭ スキップ（参加者情報なし）")

    # ========================
    # Step 5: 話者推論（参加者情報統合版）
    # ========================
    print("\n[Step 5] 話者推論実行中...")
    inference_result = infer_speakers_with_participants(
        segments=segments,
        calendar_participants=calendar_participants,
        file_context=os.path.basename(structured_file_path)
    )

    print(f"  ✓ 話者推論完了")
    print(f"    杉本: {inference_result['sugimoto_speaker']}")
    print(f"    信頼度: {inference_result['confidence']}")
    if inference_result.get('participants_mapping'):
        print(f"    マッピング: {inference_result['participants_mapping']}")

    # 構造化JSONに話者推論結果を適用
    apply_speaker_inference_to_structured_json(structured_file_path, inference_result)
    print(f"  ✓ 構造化JSONに speaker_name 追加完了")

    # ========================
    # Step 6: 要約生成（参加者DB情報統合）
    # ========================
    print("\n[Step 6] 要約生成")
    print("  ⏭ スキップ（M4完成後に実装予定）")
    # TODO: M4完成後にsummary_generator.pyを修正して実装

    # ========================
    # Step 7: 参加者DB更新（UPSERT）
    # ========================
    print("\n[Step 7] 参加者DB更新中...")

    participant_canonical_names = []
    if calendar_participants:
        for p in calendar_participants:
            canonical_name = p.get("canonical_name", "")
            if not canonical_name:
                continue

            display_names = p.get("display_names", [])
            organization = p.get("organization")
            role = p.get("role")

            # 要約から抽出した追加情報をnotesに追加（オプション）
            notes = f"会議: {matched_event.get('summary', '無題') if matched_event else 'イベントなし'}"

            participant_id = db.upsert_participant(
                canonical_name=canonical_name,
                display_names=display_names,
                organization=organization,
                role=role,
                notes=notes
            )
            participant_canonical_names.append(canonical_name)
            print(f"  ✓ {canonical_name}: DB更新完了")
    else:
        print("  ⏭ スキップ（参加者情報なし）")

    # ========================
    # Step 8: 会議情報登録
    # ========================
    print("\n[Step 8] 会議情報登録中...")

    meeting_id = db.register_meeting(
        structured_file_path=structured_file_path,
        meeting_date=file_date,
        meeting_title=matched_event.get('summary', '無題') if matched_event else 'カレンダーイベントなし',
        calendar_event_id=matched_event.get('id') if matched_event else None,
        participants=participant_canonical_names if participant_canonical_names else None
    )

    print(f"  ✓ 会議登録完了: meeting_id={meeting_id[:8]}...")

    # ========================
    # 完了
    # ========================
    print(f"\n{'='*60}")
    print(f"[Phase 11-3] パイプライン完了")
    print(f"{'='*60}\n")

    return {
        "meeting_id": meeting_id,
        "matched_event": matched_event,
        "calendar_participants": calendar_participants,
        "inference_result": inference_result,
        "success": True
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python3 integrated_pipeline.py <structured_file_path>")
        print("例: python3 integrated_pipeline.py downloads/Shop_20250115_structured.json")
        sys.exit(1)

    structured_file_path = sys.argv[1]

    if not os.path.exists(structured_file_path):
        print(f"エラー: ファイルが見つかりません: {structured_file_path}")
        sys.exit(1)

    try:
        result = run_phase_11_3_pipeline(structured_file_path)
        print("\n✅ パイプライン実行成功")
        print(f"Meeting ID: {result['meeting_id']}")
        if result['matched_event']:
            print(f"イベント: {result['matched_event']['summary']}")
        print(f"参加者: {len(result['calendar_participants'])}名")
    except Exception as e:
        print(f"\n❌ パイプライン実行エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
