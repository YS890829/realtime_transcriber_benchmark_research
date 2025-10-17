#!/usr/bin/env python3
"""
コンテキストプロンプト付き要約 (Step 3)
_structured_with_speakers.json → _structured_summarized.json

話者情報を活用し、System Instructionsでコンテキストを与えて要約精度を向上
"""

import json
import sys
import os
import time
from pathlib import Path
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# Gemini API Key選択（デフォルト: 無料枠）
USE_PAID_TIER = os.getenv("USE_PAID_TIER", "false").lower() == "true"
if USE_PAID_TIER:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_PAID")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY_PAID not set but USE_PAID_TIER=true")
    print("ℹ️  Using PAID tier API key")
else:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_FREE")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY_FREE not set")
    print("ℹ️  Using FREE tier API key")

genai.configure(api_key=GEMINI_API_KEY)

# System Instructions（全処理で共通のコンテキスト）
SYSTEM_INSTRUCTION = """あなたは会話の文字起こしを要約する専門家です。

【話者について】
- Sugimoto: 起業家・事業家。医療業界・ヘルスケア分野に関心を持ち、事業戦略、資金調達、海外展開などのビジネストピックに詳しい。録音の目的は自身の考えや意思決定プロセスの記録。
- Other: Sugimotoの対話相手、またはSpeaker 2, 3など

【要約の方針】
1. Sugimotoの発言を重点的に要約（特に意思決定、戦略、アイデア）
2. 専門用語を正確に扱う（起業、資金調達、医療、DX、AIなど）
3. 具体的な数字、日付、固有名詞を保持
4. 会話の文脈と流れを維持
5. 冗長な相槌や繰り返しは省略

【要約品質の重視点】
- 情報の正確性
- ビジネス文脈の理解
- Sugimotoの思考プロセスの明確化
"""

def summarize_segments(segments, window_size=10):
    """
    セグメントを要約（ウィンドウ単位）

    Args:
        segments: セグメントリスト（話者情報付き）
        window_size: 要約単位のセグメント数

    Returns:
        list: 要約済みセグメント
    """
    model = genai.GenerativeModel(
        'gemini-2.5-pro',
        system_instruction=SYSTEM_INSTRUCTION
    )

    summarized = []

    for i in range(0, len(segments), window_size):
        window = segments[i:i+window_size]

        # ウィンドウ内の会話テキスト作成
        conversation = "\n".join([
            f"{seg['speaker']}: {seg['text']}"
            for seg in window
        ])

        # 要約プロンプト
        prompt = f"""以下の会話を簡潔に要約してください。

会話:
{conversation}

要約:"""

        response = model.generate_content(
            prompt,
            generation_config={'temperature': 0.3}
        )

        summary_text = response.text.strip()

        # 要約セグメント作成
        summary_segment = {
            'id': i // window_size + 1,
            'original_segment_ids': [seg['id'] for seg in window],
            'speaker': 'Summary',
            'text': summary_text,
            'timestamp': window[0]['timestamp'],
            'original_segments_count': len(window)
        }

        summarized.append(summary_segment)

        print(f"   Summarized segments {window[0]['id']}-{window[-1]['id']} ({len(window)} segments)")

        # Rate limit対策: Gemini 2.5 Proは2 req/min (30秒待機)
        time.sleep(30)

    return summarized

def extract_topics_entities(full_text):
    """
    全文からトピックとエンティティを抽出
    """
    model = genai.GenerativeModel(
        'gemini-2.5-pro',
        system_instruction=SYSTEM_INSTRUCTION
    )

    prompt = f"""以下の会話全体から、主要なトピックとエンティティを抽出してください。

会話全文:
{full_text}

以下のJSON形式で回答してください:
{{
  "topics": ["トピック1", "トピック2", ...],
  "entities": {{
    "people": ["人名1", "人名2", ...],
    "organizations": ["組織名1", "組織名2", ...],
    "locations": ["場所1", "場所2", ...],
    "products_services": ["製品/サービス1", "製品/サービス2", ...],
    "concepts": ["概念1", "概念2", ...]
  }}
}}"""

    response = model.generate_content(
        prompt,
        generation_config={
            'temperature': 0.1,
            'response_mime_type': 'application/json'
        }
    )

    return json.loads(response.text)

def summarize_with_context(input_file):
    """
    コンテキストプロンプト付き要約を実行
    """
    print(f"📂 Loading: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    segments = data['segments']
    file_name = data['metadata']['file']['file_name']

    print(f"🔍 Summarizing {len(segments)} segments with context...")

    # 要約実行
    summarized_segments = summarize_segments(segments, window_size=10)

    print(f"\n✅ Created {len(summarized_segments)} summary segments")

    # トピック/エンティティ抽出
    print(f"\n🔍 Extracting topics and entities...")
    full_text = "\n".join([f"{seg['speaker']}: {seg['text']}" for seg in segments])
    topics_entities = extract_topics_entities(full_text)

    print(f"✅ Topics: {len(topics_entities['topics'])}")
    print(f"✅ Entities: {sum(len(v) for v in topics_entities['entities'].values())}")

    # メタデータ更新
    data['segments'] = segments  # 元のセグメントは保持
    data['summarized_segments'] = summarized_segments
    data['topics_entities'] = topics_entities
    data['metadata']['summarization'] = {
        'summarized_at': datetime.now().isoformat(),
        'summary_count': len(summarized_segments),
        'window_size': 10,
        'method': 'context_aware_with_system_instruction'
    }

    # 出力ファイル名
    output_file = input_file.replace('_structured_with_speakers.json', '_structured_summarized.json')

    print(f"\n💾 Saving to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Complete!")
    return output_file

def main():
    if len(sys.argv) < 2:
        print("Usage: python summarize_with_context.py <structured_with_speakers.json>")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    summarize_with_context(input_file)

if __name__ == '__main__':
    main()
