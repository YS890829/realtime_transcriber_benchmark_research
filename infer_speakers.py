#!/usr/bin/env python3
"""
LLMによる話者推論: 会話内容から杉本さんの発言を特定
_structured.json → _structured_with_speakers.json
"""

import json
import sys
import os
from pathlib import Path
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# Gemini API設定
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

genai.configure(api_key=GEMINI_API_KEY)

def analyze_speakers(segments, file_context=""):
    """
    会話全体を分析し、どのSpeakerが杉本さんかを推論

    Args:
        segments: セグメントリスト
        file_context: ファイル名などの追加コンテキスト

    Returns:
        dict: {"sugimoto_speaker": "Speaker 1" or "Speaker 2" or None}
    """
    # 会話サンプルを抽出（最初の50セグメント程度を分析）
    sample_size = min(50, len(segments))
    sample_segments = segments[:sample_size]

    # 会話テキストを構築
    conversation_text = "\n".join([
        f"{seg['speaker']}: {seg['text']}"
        for seg in sample_segments
    ])

    # プロンプト作成
    prompt = f"""以下は録音された会話の文字起こしです。

ファイル情報: {file_context}

会話内容:
{conversation_text}

【タスク】
この会話に「杉本」という人物が参加していますか？
参加している場合、Speaker 1とSpeaker 2のどちらが杉本さんですか？

【杉本さんのプロフィール】
- 起業家・事業家
- 医療業界・ヘルスケア分野に関心
- 事業戦略、資金調達、海外展開などのビジネストピックに詳しい
- キャリアや事業の話題で主導的に話す傾向
- 録音の目的: 自身の考えや意思決定プロセスを記録

【判断基準（優先順位順）】
1. 名前の明示的言及（「杉本」「杉本さん」と呼ばれる、自己紹介する）
2. 録音者である可能性（一人語り、独白、思考の整理）
3. 会話の主導者（ビジネス戦略、起業、医療などの専門的話題を深く語る）
4. 質問を受ける側（面談やインタビューで自身のキャリアを語る）
5. 意思決定者の立場（「〜することにした」「〜を決める必要がある」など）

【重要】
- 名前が明示されていなくても、上記プロフィールと一致すれば「medium」以上の確信度で判定可能
- 独白や一人語りの場合、発言者が杉本さんである可能性が高い
- 面談やインタビュー形式で自身のキャリアを語る側が杉本さんの可能性が高い

【回答形式】
以下のJSON形式で回答してください:
{{
  "sugimoto_identified": true/false,
  "sugimoto_speaker": "Speaker 1" or "Speaker 2" or null,
  "confidence": "high" or "medium" or "low",
  "reasoning": "判断理由を簡潔に（使用した判断基準を明記）"
}}"""

    model = genai.GenerativeModel('gemini-2.5-pro')

    response = model.generate_content(
        prompt,
        generation_config={
            'temperature': 0.1,
            'response_mime_type': 'application/json'
        }
    )

    result = json.loads(response.text)
    return result

def infer_speakers(input_file):
    """
    話者推論を実行し、結果を保存
    """
    print(f"📂 Loading: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    segments = data['segments']
    file_name = data['metadata']['file']['file_name']

    print(f"🔍 Analyzing {len(segments)} segments to identify Sugimoto...")

    # 話者推論を実行
    result = analyze_speakers(segments, file_context=file_name)

    print(f"\n📊 Analysis Result:")
    print(f"   Sugimoto identified: {result['sugimoto_identified']}")
    print(f"   Sugimoto speaker: {result['sugimoto_speaker']}")
    print(f"   Confidence: {result['confidence']}")
    print(f"   Reasoning: {result['reasoning']}")

    # セグメントの話者名を更新
    if result['sugimoto_identified'] and result['sugimoto_speaker']:
        sugimoto_speaker = result['sugimoto_speaker']
        other_speaker = "Speaker 1" if sugimoto_speaker == "Speaker 2" else "Speaker 2"

        updated_segments = []
        sugimoto_count = 0
        other_count = 0

        for seg in segments:
            new_seg = seg.copy()
            if seg['speaker'] == sugimoto_speaker:
                new_seg['speaker'] = "Sugimoto"
                new_seg['original_speaker'] = seg['speaker']
                sugimoto_count += 1
            elif seg['speaker'] == other_speaker:
                new_seg['speaker'] = "Other"
                new_seg['original_speaker'] = seg['speaker']
                other_count += 1
            updated_segments.append(new_seg)

        print(f"\n✅ Updated speakers:")
        print(f"   Sugimoto: {sugimoto_count} segments")
        print(f"   Other: {other_count} segments")
    else:
        print(f"\n⚠️  Could not identify Sugimoto, keeping original speaker labels")
        updated_segments = segments

    # メタデータ更新
    data['segments'] = updated_segments
    data['metadata']['speaker_inference'] = {
        'inferred_at': datetime.now().isoformat(),
        'result': result,
        'sugimoto_segments': sugimoto_count if result['sugimoto_identified'] else 0,
        'other_segments': other_count if result['sugimoto_identified'] else 0
    }

    # 出力ファイル名
    output_file = input_file.replace('_structured.json', '_structured_with_speakers.json')

    print(f"\n💾 Saving to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Complete!")
    return output_file

def main():
    if len(sys.argv) < 2:
        print("Usage: python infer_speakers.py <structured.json>")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    infer_speakers(input_file)

if __name__ == '__main__':
    main()
