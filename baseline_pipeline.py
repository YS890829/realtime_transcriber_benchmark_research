#!/usr/bin/env python3
"""
ベースラインパイプライン: 従来処理（話者情報なし）

_structured.json から直接要約・トピック抽出・ファイル名生成
新パイプラインとの比較用
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

# Gemini API設定
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

genai.configure(api_key=GEMINI_API_KEY)

# 無料プランで使用可能な高速モデル
MODEL_NAME = 'gemini-2.0-flash-exp'

def summarize_segments_baseline(segments, window_size=10):
    """
    セグメントを要約（話者情報なし、基本的なプロンプトのみ）
    """
    model = genai.GenerativeModel(MODEL_NAME)
    summarized = []

    for i in range(0, len(segments), window_size):
        window = segments[i:i+window_size]

        # 話者情報を含めない会話テキスト
        conversation = "\n".join([seg['text'] for seg in window])

        # 基本的な要約プロンプト（コンテキストなし）
        prompt = f"""以下の会話を簡潔に要約してください。

会話:
{conversation}

要約:"""

        response = model.generate_content(
            prompt,
            generation_config={'temperature': 0.3}
        )

        summary_text = response.text.strip()

        summary_segment = {
            'id': i // window_size + 1,
            'original_segment_ids': [seg['id'] for seg in window],
            'text': summary_text,
            'timestamp': window[0]['timestamp'],
            'original_segments_count': len(window)
        }

        summarized.append(summary_segment)

        print(f"   Summarized segments {window[0]['id']}-{window[-1]['id']} ({len(window)} segments)")

        # Rate limit対策: 6秒待機（10 req/min）
        time.sleep(6)

    return summarized

def extract_topics_baseline(full_text):
    """
    全文からトピックを抽出（基本的な抽出のみ）
    """
    model = genai.GenerativeModel(MODEL_NAME)

    prompt = f"""以下の会話から、主要なトピックを抽出してください。

会話:
{full_text}

以下のJSON形式で回答してください:
{{
  "topics": ["トピック1", "トピック2", ...]
}}"""

    response = model.generate_content(
        prompt,
        generation_config={
            'temperature': 0.1,
            'response_mime_type': 'application/json'
        }
    )

    return json.loads(response.text)

def generate_filename_baseline(original_filename, topics):
    """
    基本的なファイル名生成（日付 + トピック）
    """
    model = genai.GenerativeModel(MODEL_NAME)

    prompt = f"""以下の情報から、適切なファイル名を生成してください。

元のファイル名: {original_filename}
トピック: {', '.join(topics[:3])}

ファイル名は以下の形式で生成してください:
MM-DD トピック1とトピック2

以下のJSON形式で回答してください:
{{
  "filename": "生成したファイル名"
}}"""

    response = model.generate_content(
        prompt,
        generation_config={
            'temperature': 0.3,
            'response_mime_type': 'application/json'
        }
    )

    result = json.loads(response.text)
    return result['filename']

def baseline_pipeline(input_file):
    """
    ベースラインパイプラインを実行
    """
    start_time = time.time()

    print("="*80)
    print("🔵 Baseline Pipeline (No Speaker Info, Basic Prompts)")
    print("="*80)

    print(f"\n📂 Loading: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    segments = data['segments']
    file_name = data['metadata']['file']['file_name']

    # Step 1: 要約生成
    print(f"\n🔍 Summarizing {len(segments)} segments (baseline method)...")
    summarized_segments = summarize_segments_baseline(segments, window_size=10)
    print(f"✅ Created {len(summarized_segments)} summary segments")

    # Step 2: トピック抽出
    print(f"\n🔍 Extracting topics (baseline method)...")
    full_text = "\n".join([seg['text'] for seg in segments])
    topics_result = extract_topics_baseline(full_text)
    topics = topics_result.get('topics', [])
    print(f"✅ Extracted {len(topics)} topics")

    # Step 3: ファイル名生成
    print(f"\n🔍 Generating filename (baseline method)...")
    generated_filename = generate_filename_baseline(file_name, topics)
    print(f"✅ Generated filename: {generated_filename}")

    # 実行時間計算
    execution_time = time.time() - start_time

    # 結果をまとめる
    result = {
        'metadata': {
            'input_file': input_file,
            'original_filename': file_name,
            'processed_at': datetime.now().isoformat(),
            'method': 'baseline',
            'model': MODEL_NAME,
            'execution_time_seconds': execution_time
        },
        'segments': segments,  # 元のセグメントを保持
        'summarized_segments': summarized_segments,
        'topics': topics,
        'generated_filename': generated_filename,
        'statistics': {
            'segment_count': len(segments),
            'summary_count': len(summarized_segments),
            'topic_count': len(topics),
            'filename_length': len(generated_filename),
            'total_chars': sum(len(seg['text']) for seg in segments),
            'summary_chars': sum(len(seg['text']) for seg in summarized_segments)
        }
    }

    # 出力ファイル
    output_file = input_file.replace('_structured.json', '_baseline_result.json')

    print(f"\n💾 Saving to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Baseline Pipeline Complete!")
    print(f"   Execution time: {execution_time:.1f} seconds")

    return output_file

def main():
    if len(sys.argv) < 2:
        print("Usage: python baseline_pipeline.py <structured.json>")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    baseline_pipeline(input_file)

if __name__ == '__main__':
    main()
