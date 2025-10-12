#!/usr/bin/env python3
"""
小規模サンプルファイルを作成（最初の100セグメント）

APIクォータ制限を考慮した検証用
"""

import json
import sys

def create_small_sample(input_file, num_segments=100):
    """
    最初のN個のセグメントを抽出してサンプルファイルを作成
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 最初のN個のセグメントを抽出
    sample_data = data.copy()
    sample_data['segments'] = data['segments'][:num_segments]

    # メタデータ更新
    sample_data['metadata']['sample_info'] = {
        'is_sample': True,
        'original_segment_count': len(data['segments']),
        'sample_segment_count': num_segments,
        'sample_percentage': num_segments / len(data['segments']) * 100
    }

    # 出力ファイル名
    output_file = input_file.replace('_structured.json', f'_structured_sample{num_segments}.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Created sample file: {output_file}")
    print(f"   Original segments: {len(data['segments'])}")
    print(f"   Sample segments: {num_segments} ({num_segments / len(data['segments']) * 100:.1f}%)")

    return output_file

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python create_small_sample.py <structured.json> [num_segments]")
        sys.exit(1)

    input_file = sys.argv[1]
    num_segments = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    create_small_sample(input_file, num_segments)
