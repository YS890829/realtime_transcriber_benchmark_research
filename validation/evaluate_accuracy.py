#!/usr/bin/env python3
"""
自動評価: ベースラインと新パイプラインの定量比較

自動計算可能な指標で精度を比較
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
import re

def extract_keywords(text):
    """
    重要キーワードを抽出（固有名詞、数字、専門用語）
    簡易版: カタカナ語、数字、長い単語を抽出
    """
    keywords = set()

    # カタカナ語（3文字以上）
    katakana_words = re.findall(r'[ァ-ヴー]{3,}', text)
    keywords.update(katakana_words)

    # 数字を含む単語
    number_words = re.findall(r'\d+[年月日円万億兆%台件人社]', text)
    keywords.update(number_words)

    # 長い漢字語（4文字以上）
    kanji_words = re.findall(r'[一-龯]{4,}', text)
    keywords.update(kanji_words)

    return keywords

def calculate_keyword_retention(original_keywords, summary_keywords):
    """
    キーワード保持率を計算
    """
    if not original_keywords:
        return 0.0

    retained = original_keywords & summary_keywords
    retention_rate = len(retained) / len(original_keywords)

    return retention_rate

def calculate_info_density(filename):
    """
    ファイル名の情報密度を計算
    情報単位: 日付、会話種類、トピック、人名など
    """
    info_units = 0

    # 日付パターン
    if re.search(r'\d{1,2}[-/]\d{1,2}', filename):
        info_units += 1

    # 会話種類
    types = ['面談', 'ミーティング', '会話', '独白', 'インタビュー', '打ち合わせ']
    for t in types:
        if t in filename:
            info_units += 1
            break

    # トピック数（区切り文字で推定）
    topic_separators = filename.count('と') + filename.count('・') + filename.count('、')
    info_units += min(topic_separators + 1, 3)  # 最大3トピック

    # 人名（Sugimotoなど）
    if 'Sugimoto' in filename or '杉本' in filename:
        info_units += 1

    return info_units

def evaluate_baseline(baseline_file):
    """
    ベースラインの評価指標を計算
    """
    with open(baseline_file, 'r', encoding='utf-8') as f:
        baseline = json.load(f)

    # 元のテキストからキーワード抽出
    original_text = "\n".join([seg['text'] for seg in baseline['segments']])
    original_keywords = extract_keywords(original_text)

    # 要約からキーワード抽出
    summary_text = "\n".join([seg['text'] for seg in baseline['summarized_segments']])
    summary_keywords = extract_keywords(summary_text)

    # 指標計算
    metrics = {
        'execution_time': baseline['metadata']['execution_time_seconds'],
        'summary_length': baseline['statistics']['summary_chars'],
        'original_length': baseline['statistics']['total_chars'],
        'compression_ratio': baseline['statistics']['summary_chars'] / baseline['statistics']['total_chars'],
        'topic_count': baseline['statistics']['topic_count'],
        'topics': baseline['topics'],
        'filename': baseline['generated_filename'],
        'filename_length': baseline['statistics']['filename_length'],
        'filename_info_density': calculate_info_density(baseline['generated_filename']),
        'original_keywords_count': len(original_keywords),
        'summary_keywords_count': len(summary_keywords),
        'keyword_retention_rate': calculate_keyword_retention(original_keywords, summary_keywords)
    }

    return metrics

def evaluate_new_pipeline(new_pipeline_file):
    """
    新パイプラインの評価指標を計算

    新パイプラインのファイルは _structured_final.json を想定
    """
    with open(new_pipeline_file, 'r', encoding='utf-8') as f:
        new_data = json.load(f)

    # 元のテキストからキーワード抽出
    original_text = "\n".join([seg['text'] for seg in new_data['segments']])
    original_keywords = extract_keywords(original_text)

    # 要約からキーワード抽出
    summary_text = "\n".join([seg['text'] for seg in new_data['summarized_segments']])
    summary_keywords = extract_keywords(summary_text)

    # エンティティ数を計算
    entities = new_data.get('topics_entities', {}).get('entities', {})
    entity_count = sum(len(v) for v in entities.values())

    # 話者情報
    speaker_info = new_data['metadata'].get('speaker_inference', {})

    # ファイル名情報
    optimal_filename_info = new_data['metadata'].get('optimal_filename', {})
    generated_filename = optimal_filename_info.get('filename', 'N/A')

    # 指標計算
    metrics = {
        'speaker_identification': {
            'sugimoto_segments': speaker_info.get('sugimoto_segments', 0),
            'other_segments': speaker_info.get('other_segments', 0),
            'confidence': speaker_info.get('result', {}).get('confidence', 'unknown')
        },
        'summary_length': sum(len(seg['text']) for seg in new_data['summarized_segments']),
        'original_length': sum(len(seg['text']) for seg in new_data['segments']),
        'compression_ratio': sum(len(seg['text']) for seg in new_data['summarized_segments']) / sum(len(seg['text']) for seg in new_data['segments']),
        'topic_count': len(new_data.get('topics_entities', {}).get('topics', [])),
        'topics': new_data.get('topics_entities', {}).get('topics', []),
        'entity_count': entity_count,
        'entities_by_category': {k: len(v) for k, v in entities.items()},
        'filename': generated_filename,
        'filename_length': len(generated_filename),
        'filename_info_density': calculate_info_density(generated_filename),
        'original_keywords_count': len(original_keywords),
        'summary_keywords_count': len(summary_keywords),
        'keyword_retention_rate': calculate_keyword_retention(original_keywords, summary_keywords)
    }

    return metrics

def compare_metrics(baseline_metrics, new_metrics):
    """
    2つの指標を比較し、改善率を計算
    """
    comparison = {
        'keyword_retention_improvement': (
            new_metrics['keyword_retention_rate'] - baseline_metrics['keyword_retention_rate']
        ),
        'topic_coverage_improvement': (
            (new_metrics['topic_count'] - baseline_metrics['topic_count']) / baseline_metrics['topic_count']
            if baseline_metrics['topic_count'] > 0 else 0
        ),
        'filename_info_density_improvement': (
            new_metrics['filename_info_density'] / baseline_metrics['filename_info_density']
            if baseline_metrics['filename_info_density'] > 0 else 0
        ),
        'compression_improvement': (
            baseline_metrics['compression_ratio'] - new_metrics['compression_ratio']
        ),
        'entity_extraction_added': new_metrics['entity_count']  # ベースラインにはエンティティ抽出なし
    }

    return comparison

def generate_report(baseline_metrics, new_metrics, comparison, output_file):
    """
    評価レポートを生成
    """
    report = {
        'metadata': {
            'evaluation_date': datetime.now().isoformat(),
            'evaluation_method': 'automatic_metrics'
        },
        'baseline': baseline_metrics,
        'new_pipeline': new_metrics,
        'comparison': comparison,
        'summary': {
            'key_improvements': [],
            'metrics_summary': {}
        }
    }

    # 主要な改善点を抽出
    if comparison['keyword_retention_improvement'] > 0.1:
        report['summary']['key_improvements'].append(
            f"キーワード保持率が{comparison['keyword_retention_improvement']*100:.1f}%向上"
        )

    if comparison['topic_coverage_improvement'] > 0.3:
        report['summary']['key_improvements'].append(
            f"トピック抽出が{comparison['topic_coverage_improvement']*100:.1f}%改善"
        )

    if comparison['filename_info_density_improvement'] > 1.5:
        report['summary']['key_improvements'].append(
            f"ファイル名の情報密度が{comparison['filename_info_density_improvement']:.1f}倍向上"
        )

    report['summary']['metrics_summary'] = {
        'baseline_topics': baseline_metrics['topic_count'],
        'new_pipeline_topics': new_metrics['topic_count'],
        'new_pipeline_entities': new_metrics['entity_count'],
        'baseline_filename': baseline_metrics['filename'],
        'new_pipeline_filename': new_metrics['filename']
    }

    # JSONファイルに保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📊 Evaluation Report saved to: {output_file}")

    return report

def main():
    if len(sys.argv) < 3:
        print("Usage: python evaluate_accuracy.py <baseline_result.json> <new_pipeline_result.json>")
        sys.exit(1)

    baseline_file = sys.argv[1]
    new_pipeline_file = sys.argv[2]

    if not os.path.exists(baseline_file):
        print(f"Error: Baseline file not found: {baseline_file}")
        sys.exit(1)

    if not os.path.exists(new_pipeline_file):
        print(f"Error: New pipeline file not found: {new_pipeline_file}")
        sys.exit(1)

    print("="*80)
    print("📊 Automatic Evaluation: Baseline vs New Pipeline")
    print("="*80)

    print("\n🔍 Evaluating baseline...")
    baseline_metrics = evaluate_baseline(baseline_file)

    print("🔍 Evaluating new pipeline...")
    new_metrics = evaluate_new_pipeline(new_pipeline_file)

    print("\n🔍 Comparing metrics...")
    comparison = compare_metrics(baseline_metrics, new_metrics)

    # レポート生成
    output_file = "evaluation_report_automatic.json"
    report = generate_report(baseline_metrics, new_metrics, comparison, output_file)

    # サマリー表示
    print("\n" + "="*80)
    print("📈 Evaluation Summary")
    print("="*80)

    print(f"\n【ベースライン】")
    print(f"  トピック数: {baseline_metrics['topic_count']}")
    print(f"  キーワード保持率: {baseline_metrics['keyword_retention_rate']*100:.1f}%")
    print(f"  ファイル名: {baseline_metrics['filename']}")
    print(f"  情報密度: {baseline_metrics['filename_info_density']}")

    print(f"\n【新パイプライン】")
    print(f"  話者識別: {new_metrics['speaker_identification']['confidence']}")
    print(f"  トピック数: {new_metrics['topic_count']}")
    print(f"  エンティティ数: {new_metrics['entity_count']}")
    print(f"  キーワード保持率: {new_metrics['keyword_retention_rate']*100:.1f}%")
    print(f"  ファイル名: {new_metrics['filename']}")
    print(f"  情報密度: {new_metrics['filename_info_density']}")

    print(f"\n【改善点】")
    for improvement in report['summary']['key_improvements']:
        print(f"  ✅ {improvement}")

    print("\n✅ Automatic evaluation complete!")

if __name__ == '__main__':
    main()
