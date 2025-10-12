#!/usr/bin/env python3
"""
最適ファイル名生成 (Step 3)
_structured_summarized.json → 最適なファイル名を生成

話者情報 + 要約 + トピック + エンティティを統合して最適なファイル名を生成
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

def generate_optimal_filename(data):
    """
    話者情報、要約、トピック、エンティティを統合して最適なファイル名を生成

    Args:
        data: _structured_summarized.jsonの全データ

    Returns:
        str: 最適なファイル名
    """
    # 必要な情報を抽出
    original_filename = data['metadata']['file']['file_name']
    speaker_info = data['metadata'].get('speaker_inference', {})
    topics_entities = data.get('topics_entities', {})

    # 要約を結合
    summarized_segments = data.get('summarized_segments', [])
    summary_text = "\n".join([seg['text'] for seg in summarized_segments[:5]])  # 最初の5個の要約

    # プロンプト作成
    prompt = f"""以下の会話録音について、最適なファイル名を生成してください。

【元のファイル名】
{original_filename}

【話者情報】
{json.dumps(speaker_info, ensure_ascii=False, indent=2)}

【トピック】
{json.dumps(topics_entities.get('topics', []), ensure_ascii=False, indent=2)}

【エンティティ】
{json.dumps(topics_entities.get('entities', {}), ensure_ascii=False, indent=2)}

【要約（冒頭部分）】
{summary_text}

【ファイル名の要件】
1. 日付を含める（元のファイル名から抽出、例: "09-22"）
2. 会話の種類を含める（例: 面談、ミーティング、カジュアル会話、独白など）
3. 主要なトピックを2-3個含める
4. 話者情報を活用（Sugimotoの発言が主ならその旨を示す）
5. 全体で50-80文字程度
6. 検索しやすく、内容が一目でわかる

【ファイル名の形式】
MM-DD 会話種類：主要トピック1と主要トピック2とトピック3

【回答形式】
以下のJSON形式で回答してください:
{{
  "filename": "生成したファイル名（拡張子なし）",
  "reasoning": "ファイル名の選定理由を簡潔に"
}}"""

    model = genai.GenerativeModel('gemini-2.5-pro')

    response = model.generate_content(
        prompt,
        generation_config={
            'temperature': 0.3,
            'response_mime_type': 'application/json'
        }
    )

    result = json.loads(response.text)
    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_optimal_filename.py <structured_summarized.json>")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    print(f"📂 Loading: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"🔍 Generating optimal filename...")

    # ファイル名生成
    result = generate_optimal_filename(data)

    print(f"\n📊 Generated filename:")
    print(f"   {result['filename']}")
    print(f"\n💡 Reasoning:")
    print(f"   {result['reasoning']}")

    # メタデータに追加
    data['metadata']['optimal_filename'] = {
        'generated_at': datetime.now().isoformat(),
        'filename': result['filename'],
        'reasoning': result['reasoning']
    }

    # 出力ファイル名
    output_file = input_file.replace('_structured_summarized.json', '_structured_final.json')

    print(f"\n💾 Saving to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Complete!")

    # ファイル名変更の提案を表示
    original_audio = data['metadata']['file']['file_name']
    suggested_name = result['filename']

    print(f"\n📝 Suggested file renaming:")
    print(f"   Original: {original_audio}")
    print(f"   Suggested: {suggested_name}.mp3")

if __name__ == '__main__':
    main()
