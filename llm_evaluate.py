#!/usr/bin/env python3
"""
LLM評価: ベースラインと新パイプラインの品質比較

LLMを使って2つの出力を比較評価
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

# Gemini 2.5 Pro
MODEL_NAME = 'gemini-2.5-pro'

def llm_compare_summaries(original_segments, baseline_summary, new_pipeline_summary):
    """
    LLMを使って2つの要約を比較評価
    """
    model = genai.GenerativeModel(MODEL_NAME)

    # 元の会話（最初の50セグメント）
    sample_size = min(50, len(original_segments))
    original_sample = "\n".join([
        f"{seg.get('speaker', 'Speaker')}: {seg['text']}"
        for seg in original_segments[:sample_size]
    ])

    # 要約サンプル（最初の5セグメント）
    baseline_sample = "\n".join([seg['text'] for seg in baseline_summary[:5]])
    new_pipeline_sample = "\n".join([seg['text'] for seg in new_pipeline_summary[:5]])

    prompt = f"""以下の2つの要約を比較評価してください。

【元の会話（冒頭部分）】
{original_sample}

【要約A（従来処理: 話者情報なし）】
{baseline_sample}

【要約B（新パイプライン: 話者情報あり、コンテキスト強化）】
{new_pipeline_sample}

以下の基準で1-5点で評価してください：
1. 情報の正確性: 重要な情報を正確に保持しているか
2. 文脈理解度: 話者の意図や意思決定プロセスが明確か
3. 有用性: 後で見返したときに有用か
4. 簡潔性: 冗長性を排除し、簡潔にまとまっているか

また、どちらの要約が優れているか、その理由も説明してください。

以下のJSON形式で回答してください:
{{
  "baseline_scores": {{
    "accuracy": 1-5,
    "context_understanding": 1-5,
    "usefulness": 1-5,
    "conciseness": 1-5
  }},
  "new_pipeline_scores": {{
    "accuracy": 1-5,
    "context_understanding": 1-5,
    "usefulness": 1-5,
    "conciseness": 1-5
  }},
  "winner": "baseline" or "new_pipeline" or "tie",
  "reasoning": "判断理由を詳しく説明"
}}"""

    response = model.generate_content(
        prompt,
        generation_config={
            'temperature': 0.1,
            'response_mime_type': 'application/json'
        }
    )

    return json.loads(response.text)

def llm_compare_filenames(original_filename, baseline_filename, new_pipeline_filename, topics_baseline, topics_new):
    """
    LLMを使って2つのファイル名を比較評価
    """
    model = genai.GenerativeModel(MODEL_NAME)

    prompt = f"""以下の2つのファイル名を比較評価してください。

【元のファイル名】
{original_filename}

【要約に使用されたトピック】
従来処理: {', '.join(topics_baseline[:5])}
新パイプライン: {', '.join(topics_new[:5])}

【ファイル名A（従来処理）】
{baseline_filename}

【ファイル名B（新パイプライン）】
{new_pipeline_filename}

以下の基準で1-5点で評価してください：
1. 情報量: 有用な情報がどれだけ含まれているか
2. 検索性: 後で検索しやすいか
3. 可読性: 読みやすく理解しやすいか
4. 適切性: 元の内容を適切に表現しているか

また、どちらのファイル名が優れているか、その理由も説明してください。

以下のJSON形式で回答してください:
{{
  "baseline_scores": {{
    "information_richness": 1-5,
    "searchability": 1-5,
    "readability": 1-5,
    "appropriateness": 1-5
  }},
  "new_pipeline_scores": {{
    "information_richness": 1-5,
    "searchability": 1-5,
    "readability": 1-5,
    "appropriateness": 1-5
  }},
  "winner": "baseline" or "new_pipeline" or "tie",
  "reasoning": "判断理由を詳しく説明"
}}"""

    response = model.generate_content(
        prompt,
        generation_config={
            'temperature': 0.1,
            'response_mime_type': 'application/json'
        }
    )

    return json.loads(response.text)

def calculate_overall_scores(summary_eval, filename_eval):
    """
    総合スコアを計算
    """
    # 要約スコアの平均
    baseline_summary_avg = sum(summary_eval['baseline_scores'].values()) / len(summary_eval['baseline_scores'])
    new_pipeline_summary_avg = sum(summary_eval['new_pipeline_scores'].values()) / len(summary_eval['new_pipeline_scores'])

    # ファイル名スコアの平均
    baseline_filename_avg = sum(filename_eval['baseline_scores'].values()) / len(filename_eval['baseline_scores'])
    new_pipeline_filename_avg = sum(filename_eval['new_pipeline_scores'].values()) / len(filename_eval['new_pipeline_scores'])

    # 総合スコア（要約70%、ファイル名30%の重み付け）
    baseline_overall = baseline_summary_avg * 0.7 + baseline_filename_avg * 0.3
    new_pipeline_overall = new_pipeline_summary_avg * 0.7 + new_pipeline_filename_avg * 0.3

    improvement = new_pipeline_overall - baseline_overall

    return {
        'baseline_overall': baseline_overall,
        'new_pipeline_overall': new_pipeline_overall,
        'improvement': improvement,
        'improvement_percentage': (improvement / baseline_overall * 100) if baseline_overall > 0 else 0
    }

def main():
    if len(sys.argv) < 3:
        print("Usage: python llm_evaluate.py <baseline_result.json> <new_pipeline_result.json>")
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
    print("🤖 LLM Evaluation: Baseline vs New Pipeline")
    print("="*80)

    # ファイル読み込み
    print("\n📂 Loading files...")
    with open(baseline_file, 'r', encoding='utf-8') as f:
        baseline = json.load(f)

    with open(new_pipeline_file, 'r', encoding='utf-8') as f:
        new_pipeline = json.load(f)

    # 要約の比較
    print("\n🔍 Evaluating summaries with LLM...")
    summary_eval = llm_compare_summaries(
        baseline['segments'],
        baseline['summarized_segments'],
        new_pipeline['summarized_segments']
    )

    print(f"✅ Summary evaluation complete")
    print(f"   Winner: {summary_eval['winner']}")

    # ファイル名の比較
    print("\n🔍 Evaluating filenames with LLM...")
    filename_eval = llm_compare_filenames(
        baseline['metadata']['original_filename'],
        baseline['generated_filename'],
        new_pipeline['metadata']['optimal_filename']['filename'],
        baseline.get('topics', []),
        new_pipeline.get('topics_entities', {}).get('topics', [])
    )

    print(f"✅ Filename evaluation complete")
    print(f"   Winner: {filename_eval['winner']}")

    # 総合スコア計算
    print("\n🔍 Calculating overall scores...")
    overall_scores = calculate_overall_scores(summary_eval, filename_eval)

    # レポート作成
    report = {
        'metadata': {
            'evaluation_date': datetime.now().isoformat(),
            'evaluation_method': 'llm_comparison',
            'model': MODEL_NAME
        },
        'summary_evaluation': summary_eval,
        'filename_evaluation': filename_eval,
        'overall_scores': overall_scores,
        'conclusion': {
            'winner': 'new_pipeline' if overall_scores['improvement'] > 0.5 else 'baseline' if overall_scores['improvement'] < -0.5 else 'tie',
            'improvement_summary': f"新パイプラインは総合スコアで{overall_scores['improvement']:.2f}点（{overall_scores['improvement_percentage']:.1f}%）の改善"
        }
    }

    # レポート保存
    output_file = "evaluation_report_llm.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📊 LLM Evaluation Report saved to: {output_file}")

    # サマリー表示
    print("\n" + "="*80)
    print("📈 LLM Evaluation Summary")
    print("="*80)

    print(f"\n【要約の比較】")
    print(f"  ベースライン平均: {sum(summary_eval['baseline_scores'].values()) / len(summary_eval['baseline_scores']):.2f}/5.00")
    print(f"  新パイプライン平均: {sum(summary_eval['new_pipeline_scores'].values()) / len(summary_eval['new_pipeline_scores']):.2f}/5.00")
    print(f"  Winner: {summary_eval['winner']}")

    print(f"\n【ファイル名の比較】")
    print(f"  ベースライン平均: {sum(filename_eval['baseline_scores'].values()) / len(filename_eval['baseline_scores']):.2f}/5.00")
    print(f"  新パイプライン平均: {sum(filename_eval['new_pipeline_scores'].values()) / len(filename_eval['new_pipeline_scores']):.2f}/5.00")
    print(f"  Winner: {filename_eval['winner']}")

    print(f"\n【総合評価】")
    print(f"  ベースライン総合: {overall_scores['baseline_overall']:.2f}/5.00")
    print(f"  新パイプライン総合: {overall_scores['new_pipeline_overall']:.2f}/5.00")
    print(f"  改善: {overall_scores['improvement']:+.2f}点 ({overall_scores['improvement_percentage']:+.1f}%)")
    print(f"  Winner: {report['conclusion']['winner']}")

    print("\n✅ LLM evaluation complete!")

if __name__ == '__main__':
    main()
