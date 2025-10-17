#!/usr/bin/env python3
"""
統合パイプライン: 話者推論 → 要約 → ファイル名生成

_structured.json から始めて、3つのステップを順次実行
"""

import sys
import os
from pathlib import Path

# 各ステップのスクリプトをインポート
from infer_speakers import infer_speakers
from summarize_with_context import summarize_with_context
from generate_optimal_filename import main as generate_filename_main

def run_full_pipeline(input_file):
    """
    フルパイプラインを実行

    Args:
        input_file: *_structured.json ファイル
    """
    print("="*80)
    print("🚀 Starting Full Pipeline")
    print("="*80)

    # Step 1: 話者推論
    print("\n" + "="*80)
    print("📍 Step 1/3: Speaker Inference")
    print("="*80)

    speakers_file = infer_speakers(input_file)

    # Step 2: コンテキスト付き要約
    print("\n" + "="*80)
    print("📍 Step 2/3: Context-Aware Summarization")
    print("="*80)

    summarized_file = summarize_with_context(speakers_file)

    # Step 3: 最適ファイル名生成
    print("\n" + "="*80)
    print("📍 Step 3/3: Optimal Filename Generation")
    print("="*80)

    # generate_optimal_filenameを直接呼び出す
    sys.argv = ['generate_optimal_filename.py', summarized_file]
    generate_filename_main()

    print("\n" + "="*80)
    print("✅ Full Pipeline Complete!")
    print("="*80)

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_full_pipeline.py <structured.json>")
        print("\nExample:")
        print("  python run_full_pipeline.py downloads/recording_structured.json")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    if not input_file.endswith('_structured.json'):
        print(f"Warning: Input file should be *_structured.json")
        print(f"Got: {input_file}")

    run_full_pipeline(input_file)

if __name__ == '__main__':
    main()
