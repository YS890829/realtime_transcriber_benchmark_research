#!/usr/bin/env python3
"""
統合検証スクリプト: 全検証プロセスを自動実行

1. ベースライン処理実行
2. 新パイプライン実行（既存結果も利用可能）
3. 自動評価
4. LLM評価
5. 統合レポート生成
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# 各スクリプトをインポート
from baseline_pipeline import baseline_pipeline
from evaluate_accuracy import evaluate_baseline, evaluate_new_pipeline, compare_metrics, generate_report as generate_auto_report
from llm_evaluate import llm_compare_summaries, llm_compare_filenames, calculate_overall_scores

def check_new_pipeline_result(structured_file):
    """
    新パイプラインの結果ファイルが存在するかチェック
    """
    # _structured_final.json を探す
    final_file = structured_file.replace('_structured.json', '_structured_final.json')

    if os.path.exists(final_file):
        return final_file
    else:
        return None

def generate_markdown_report(auto_report, llm_report, output_file):
    """
    統合レポートをMarkdown形式で生成
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 精度改善検証レポート\n\n")

        # メタデータ
        f.write(f"**検証日時**: {auto_report['metadata']['evaluation_date']}\n\n")

        # エグゼクティブサマリー
        f.write("## エグゼクティブサマリー\n\n")
        f.write("新パイプライン（話者推論 → コンテキスト付き要約 → 最適ファイル名生成）と従来処理を比較した結果:\n\n")

        for improvement in auto_report['summary']['key_improvements']:
            f.write(f"- ✅ {improvement}\n")

        f.write(f"\n**LLM総合評価**: ")
        improvement = llm_report['overall_scores']['improvement']
        if improvement > 0.5:
            f.write(f"新パイプラインが明確に優れている（+{improvement:.2f}点）\n\n")
        elif improvement > 0:
            f.write(f"新パイプラインがやや優れている（+{improvement:.2f}点）\n\n")
        else:
            f.write(f"ほぼ同等\n\n")

        # 自動評価結果
        f.write("## 自動評価結果\n\n")
        f.write("### ベースライン（従来処理）\n\n")
        f.write(f"- トピック数: {auto_report['baseline']['topic_count']}\n")
        f.write(f"- キーワード保持率: {auto_report['baseline']['keyword_retention_rate']*100:.1f}%\n")
        f.write(f"- ファイル名: {auto_report['baseline']['filename']}\n")
        f.write(f"- 情報密度: {auto_report['baseline']['filename_info_density']}\n\n")

        f.write("### 新パイプライン\n\n")
        f.write(f"- 話者識別信頼度: {auto_report['new_pipeline']['speaker_identification']['confidence']}\n")
        f.write(f"- トピック数: {auto_report['new_pipeline']['topic_count']}\n")
        f.write(f"- エンティティ数: {auto_report['new_pipeline']['entity_count']}\n")
        f.write(f"- キーワード保持率: {auto_report['new_pipeline']['keyword_retention_rate']*100:.1f}%\n")
        f.write(f"- ファイル名: {auto_report['new_pipeline']['filename']}\n")
        f.write(f"- 情報密度: {auto_report['new_pipeline']['filename_info_density']}\n\n")

        f.write("### 改善率\n\n")
        f.write(f"- キーワード保持率改善: {auto_report['comparison']['keyword_retention_improvement']*100:+.1f}%\n")
        f.write(f"- トピック抽出改善: {auto_report['comparison']['topic_coverage_improvement']*100:+.1f}%\n")
        f.write(f"- ファイル名情報密度: {auto_report['comparison']['filename_info_density_improvement']:.2f}倍\n\n")

        # LLM評価結果
        f.write("## LLM評価結果\n\n")

        f.write("### 要約品質の比較\n\n")
        f.write("| 評価項目 | ベースライン | 新パイプライン |\n")
        f.write("|---------|-------------|---------------|\n")

        summary_eval = llm_report['summary_evaluation']
        for key in summary_eval['baseline_scores'].keys():
            baseline_score = summary_eval['baseline_scores'][key]
            new_score = summary_eval['new_pipeline_scores'][key]
            f.write(f"| {key} | {baseline_score:.1f}/5.0 | {new_score:.1f}/5.0 |\n")

        baseline_avg = sum(summary_eval['baseline_scores'].values()) / len(summary_eval['baseline_scores'])
        new_avg = sum(summary_eval['new_pipeline_scores'].values()) / len(summary_eval['new_pipeline_scores'])
        f.write(f"| **平均** | **{baseline_avg:.2f}/5.0** | **{new_avg:.2f}/5.0** |\n\n")

        f.write(f"**Winner**: {summary_eval['winner']}\n\n")
        f.write(f"**理由**: {summary_eval['reasoning']}\n\n")

        f.write("### ファイル名品質の比較\n\n")
        f.write("| 評価項目 | ベースライン | 新パイプライン |\n")
        f.write("|---------|-------------|---------------|\n")

        filename_eval = llm_report['filename_evaluation']
        for key in filename_eval['baseline_scores'].keys():
            baseline_score = filename_eval['baseline_scores'][key]
            new_score = filename_eval['new_pipeline_scores'][key]
            f.write(f"| {key} | {baseline_score:.1f}/5.0 | {new_score:.1f}/5.0 |\n")

        baseline_avg = sum(filename_eval['baseline_scores'].values()) / len(filename_eval['baseline_scores'])
        new_avg = sum(filename_eval['new_pipeline_scores'].values()) / len(filename_eval['new_pipeline_scores'])
        f.write(f"| **平均** | **{baseline_avg:.2f}/5.0** | **{new_avg:.2f}/5.0** |\n\n")

        f.write(f"**Winner**: {filename_eval['winner']}\n\n")
        f.write(f"**理由**: {filename_eval['reasoning']}\n\n")

        # 総合評価
        f.write("## 総合評価\n\n")
        overall = llm_report['overall_scores']
        f.write(f"- ベースライン総合スコア: **{overall['baseline_overall']:.2f}/5.00**\n")
        f.write(f"- 新パイプライン総合スコア: **{overall['new_pipeline_overall']:.2f}/5.00**\n")
        f.write(f"- 改善: **{overall['improvement']:+.2f}点** ({overall['improvement_percentage']:+.1f}%)\n\n")

        # 結論
        f.write("## 結論\n\n")
        f.write(llm_report['conclusion']['improvement_summary'] + "\n\n")

        # 具体例
        f.write("## 具体例\n\n")
        f.write("### トピック比較\n\n")
        f.write("**ベースライン**:\n")
        for topic in auto_report['baseline']['topics'][:5]:
            f.write(f"- {topic}\n")

        f.write("\n**新パイプライン**:\n")
        for topic in auto_report['new_pipeline']['topics'][:5]:
            f.write(f"- {topic}\n")

        f.write("\n### ファイル名比較\n\n")
        f.write(f"**ベースライン**: {auto_report['baseline']['filename']}\n\n")
        f.write(f"**新パイプライン**: {auto_report['new_pipeline']['filename']}\n\n")

    print(f"📊 Markdown report saved to: {output_file}")

def run_validation(input_file, skip_baseline=False, skip_new_pipeline=False):
    """
    全検証プロセスを実行
    """
    print("="*80)
    print("🚀 Starting Full Validation Process")
    print("="*80)

    # Step 1: ベースライン実行
    if not skip_baseline:
        print("\n" + "="*80)
        print("📍 Step 1/4: Running Baseline Pipeline")
        print("="*80)
        baseline_file = baseline_pipeline(input_file)
    else:
        baseline_file = input_file.replace('_structured.json', '_baseline_result.json')
        if not os.path.exists(baseline_file):
            print(f"Error: Baseline file not found: {baseline_file}")
            sys.exit(1)
        print(f"\n⏭️  Skipping baseline execution, using existing: {baseline_file}")

    # Step 2: 新パイプライン結果の確認
    print("\n" + "="*80)
    print("📍 Step 2/4: Checking New Pipeline Results")
    print("="*80)

    new_pipeline_file = check_new_pipeline_result(input_file)

    if new_pipeline_file:
        print(f"✅ Found existing new pipeline result: {new_pipeline_file}")
    elif skip_new_pipeline:
        print("⚠️  New pipeline file not found and skip_new_pipeline=True")
        print("Please run the new pipeline first:")
        print(f"  python run_full_pipeline.py \"{input_file}\"")
        sys.exit(1)
    else:
        print("❌ New pipeline result not found!")
        print("Please run the new pipeline first:")
        print(f"  python run_full_pipeline.py \"{input_file}\"")
        sys.exit(1)

    # Step 3: 自動評価
    print("\n" + "="*80)
    print("📍 Step 3/4: Automatic Evaluation")
    print("="*80)

    baseline_metrics = evaluate_baseline(baseline_file)
    new_metrics = evaluate_new_pipeline(new_pipeline_file)
    comparison = compare_metrics(baseline_metrics, new_metrics)

    auto_report = generate_auto_report(
        baseline_metrics,
        new_metrics,
        comparison,
        "evaluation_report_automatic.json"
    )

    # Step 4: LLM評価
    print("\n" + "="*80)
    print("📍 Step 4/4: LLM Evaluation")
    print("="*80)

    with open(baseline_file, 'r', encoding='utf-8') as f:
        baseline = json.load(f)

    with open(new_pipeline_file, 'r', encoding='utf-8') as f:
        new_pipeline = json.load(f)

    print("🔍 Evaluating summaries with LLM...")
    summary_eval = llm_compare_summaries(
        baseline['segments'],
        baseline['summarized_segments'],
        new_pipeline['summarized_segments']
    )

    print("🔍 Evaluating filenames with LLM...")
    filename_eval = llm_compare_filenames(
        baseline['metadata']['original_filename'],
        baseline['generated_filename'],
        new_pipeline['metadata']['optimal_filename']['filename'],
        baseline.get('topics', []),
        new_pipeline.get('topics_entities', {}).get('topics', [])
    )

    overall_scores = calculate_overall_scores(summary_eval, filename_eval)

    llm_report = {
        'metadata': {
            'evaluation_date': datetime.now().isoformat(),
            'evaluation_method': 'llm_comparison',
            'model': 'gemini-2.0-flash-exp'
        },
        'summary_evaluation': summary_eval,
        'filename_evaluation': filename_eval,
        'overall_scores': overall_scores,
        'conclusion': {
            'winner': 'new_pipeline' if overall_scores['improvement'] > 0.5 else 'baseline' if overall_scores['improvement'] < -0.5 else 'tie',
            'improvement_summary': f"新パイプラインは総合スコアで{overall_scores['improvement']:.2f}点（{overall_scores['improvement_percentage']:.1f}%）の改善"
        }
    }

    # LLMレポート保存
    with open("evaluation_report_llm.json", 'w', encoding='utf-8') as f:
        json.dump(llm_report, f, ensure_ascii=False, indent=2)

    # Step 5: 統合レポート生成
    print("\n" + "="*80)
    print("📍 Generating Integrated Report")
    print("="*80)

    generate_markdown_report(auto_report, llm_report, "evaluation_report.md")

    print("\n" + "="*80)
    print("✅ Validation Complete!")
    print("="*80)

    print("\n📊 Generated Reports:")
    print("  - evaluation_report_automatic.json (自動評価)")
    print("  - evaluation_report_llm.json (LLM評価)")
    print("  - evaluation_report.md (統合レポート)")

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_validation.py <structured.json> [--skip-baseline] [--skip-new-pipeline]")
        print("\nExample:")
        print("  python run_validation.py \"downloads/recording_structured.json\"")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    skip_baseline = '--skip-baseline' in sys.argv
    skip_new_pipeline = '--skip-new-pipeline' in sys.argv

    run_validation(input_file, skip_baseline, skip_new_pipeline)

if __name__ == '__main__':
    main()
