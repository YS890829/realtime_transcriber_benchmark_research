#!/usr/bin/env python3
"""
既存の構造化JSONに話者識別を追加するスクリプト
Phase 6-1の結果（_structured.json）を入力として、話者識別のみを実行
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()


def perform_speaker_diarization(audio_path, segments):
    """話者識別を実行"""
    print(f"[1/3] 話者識別中...")

    try:
        from pyannote.audio import Pipeline

        hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not hf_token:
            print("  Warning: HUGGINGFACE_TOKEN not found.")
            return fallback_speaker_assignment(segments)

        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token
        )

        diarization = pipeline(audio_path)

        # 話者情報集計
        speakers_info = {}
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            if speaker not in speakers_info:
                speakers_info[speaker] = {
                    "id": speaker,
                    "label": f"Speaker {len(speakers_info) + 1}",
                    "total_duration": 0.0
                }
            speakers_info[speaker]["total_duration"] += turn.duration

        # セグメントに話者割り当て
        segments_with_speaker = []
        for seg in segments:
            seg_start = seg["start"]
            seg_end = seg["end"]

            max_overlap = 0.0
            assigned_speaker = "SPEAKER_00"

            for turn, _, speaker in diarization.itertracks(yield_label=True):
                overlap_start = max(seg_start, turn.start)
                overlap_end = min(seg_end, turn.end)
                overlap = max(0, overlap_end - overlap_start)

                if overlap > max_overlap:
                    max_overlap = overlap
                    assigned_speaker = speaker

            seg_copy = seg.copy()
            seg_copy["speaker"] = assigned_speaker
            segments_with_speaker.append(seg_copy)

        # 話者リスト作成
        speakers_list = []
        total_duration = sum(s["total_duration"] for s in speakers_info.values())

        for speaker_id, info in speakers_info.items():
            speakers_list.append({
                "id": speaker_id,
                "label": info["label"],
                "total_duration": round(info["total_duration"], 2),
                "speaking_percentage": round((info["total_duration"] / total_duration) * 100, 1) if total_duration > 0 else 0
            })

        print(f"  Detected {len(speakers_list)} speakers")

        return {
            "speakers": speakers_list,
            "segments_with_speaker": segments_with_speaker
        }

    except Exception as e:
        print(f"  Error: {e}")
        return fallback_speaker_assignment(segments)


def fallback_speaker_assignment(segments):
    """フォールバック: 単一話者"""
    total_duration = sum(seg["end"] - seg["start"] for seg in segments)

    segments_with_speaker = []
    for seg in segments:
        seg_copy = seg.copy()
        seg_copy["speaker"] = "SPEAKER_00"
        segments_with_speaker.append(seg_copy)

    return {
        "speakers": [{
            "id": "SPEAKER_00",
            "label": "Speaker 1",
            "total_duration": round(total_duration, 2),
            "speaking_percentage": 100.0
        }],
        "segments_with_speaker": segments_with_speaker
    }


def extract_topics_and_entities(full_text):
    """トピックとエンティティ抽出"""
    print(f"[2/3] トピック・エンティティ抽出中...")

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
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
    """セグメントにトピック割り当て"""
    segments_enhanced = []

    for seg in segments:
        seg_text = seg["text"]
        assigned_topics = []

        for topic in topics:
            keywords = topic.get("keywords", [])
            if any(keyword in seg_text for keyword in keywords):
                assigned_topics.append(topic["id"])

        seg_copy = seg.copy()
        seg_copy["topics"] = assigned_topics if assigned_topics else []
        segments_enhanced.append(seg_copy)

    return segments_enhanced


def generate_enhanced_summary(full_text, topics, entities, speakers):
    """構造化データを活用した要約"""
    print(f"[3/3] 要約生成中...")

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.0-flash-exp")

    speakers_info = "\n".join([
        f"- {s['label']}: {s['speaking_percentage']}% ({s['total_duration']}秒)"
        for s in speakers
    ])

    topics_info = "\n".join([
        f"- {t['name']}: {t['summary']}"
        for t in topics
    ])

    entities_info = f"""
- 人物: {', '.join(entities.get('people', []))}
- 組織: {', '.join(entities.get('organizations', []))}
- 日付: {', '.join(entities.get('dates', []))}
- アクション: {', '.join(entities.get('action_items', []))}
"""

    prompt = f"""
以下の情報を元に、会話の要約を作成してください。

【話者情報】
{speakers_info}

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
    if len(sys.argv) < 3:
        print("Usage: python add_speaker_diarization.py <audio_file> <structured_json>")
        sys.exit(1)

    audio_path = sys.argv[1]
    json_path = sys.argv[2]

    if not os.path.exists(audio_path):
        print(f"Error: Audio file not found: {audio_path}")
        sys.exit(1)

    if not os.path.exists(json_path):
        print(f"Error: JSON file not found: {json_path}")
        sys.exit(1)

    print(f"🎙️ Phase 6-2処理開始")
    print(f"  音声ファイル: {audio_path}")
    print(f"  入力JSON: {json_path}")

    # 既存のJSONを読み込み
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 話者識別実行
    diarization_result = perform_speaker_diarization(audio_path, data["segments"])

    # トピック・エンティティ抽出
    topics_result = extract_topics_and_entities(data["full_text"])

    # セグメントにトピック割り当て
    segments_enhanced = assign_topics_to_segments(
        diarization_result["segments_with_speaker"],
        topics_result["topics"]
    )

    # 構造化要約生成
    summary = generate_enhanced_summary(
        data["full_text"],
        topics_result["topics"],
        topics_result["entities"],
        diarization_result["speakers"]
    )

    # 拡張JSONを作成
    enhanced_data = data.copy()
    enhanced_data["speakers"] = diarization_result["speakers"]
    enhanced_data["topics"] = topics_result["topics"]
    enhanced_data["entities"] = topics_result["entities"]
    enhanced_data["segments"] = segments_enhanced
    enhanced_data["summary"] = summary

    # 出力
    output_path = Path(audio_path).with_suffix('').name + "_enhanced.json"
    output_dir = Path(audio_path).parent
    output_file = output_dir / output_path

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(enhanced_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ JSON保存完了: {output_file}")

    print(f"\n📊 処理統計:")
    print(f"  話者数: {len(enhanced_data['speakers'])}")
    print(f"  トピック数: {len(enhanced_data['topics'])}")
    print(f"  エンティティ: 人物{len(enhanced_data['entities'].get('people', []))}名")

    print(f"\n🎉 完了!")


if __name__ == "__main__":
    main()
