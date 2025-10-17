#!/usr/bin/env python3
"""
Phase 11-3: カレンダー参加者情報を統合した話者推論
作成日: 2025-10-16

既存のinfer_speakers.pyをベースに、カレンダー参加者情報を活用することで
話者推論の精度を向上させます。
"""

import json
import sys
import os
import re
from pathlib import Path
from typing import List, Dict, Optional
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
    print("ℹ️  Using FREE tier API key (enhanced_speaker_inference)")

genai.configure(api_key=GEMINI_API_KEY)


def infer_speakers_with_participants(
    segments: List[Dict],
    calendar_participants: List[Dict] = None,
    file_context: str = ""
) -> Dict:
    """
    カレンダー参加者情報を統合した話者推論

    Args:
        segments: 文字起こしセグメント（speaker, text, start, endを含む）
        calendar_participants: extract_participants_from_description()の出力
        file_context: ファイル名などの追加コンテキスト

    Returns:
        {
            "sugimoto_speaker": "Speaker 0" or "Speaker 1",
            "participants_mapping": {"Speaker 0": "杉本", "Speaker 1": "田中"},
            "confidence": "high/medium/low",
            "reasoning": "推論理由"
        }
    """
    # 会話サンプルを抽出（最初の50セグメント）
    sample_size = min(50, len(segments))
    sample_segments = segments[:sample_size]

    # 会話テキストを構築
    conversation_text = "\n".join([
        f"{seg['speaker']}: {seg['text']}"
        for seg in sample_segments
    ])

    # カレンダー参加者情報の整形
    participants_info = ""
    if calendar_participants:
        participants_info = "\n【カレンダー参加者情報】\n"
        for p in calendar_participants:
            name = p.get("canonical_name", "不明")
            role = p.get("role", "")
            org = p.get("organization", "")
            display_names = p.get("display_names", [])

            participants_info += f"- {name}"
            if role:
                participants_info += f"（{role}）"
            if org:
                participants_info += f" - {org}"
            if display_names:
                participants_info += f"\n  呼称例: {', '.join(display_names)}"
            participants_info += "\n"

    # プロンプト作成（既存のinfer_speakers.pyをベース）
    prompt = f"""以下は録音された会話の文字起こしです。

ファイル情報: {file_context}
{participants_info}

会話内容:
{conversation_text}

【タスク】
この会話には必ず「杉本」が参加しています。
各Speakerが誰であるかを推論してください。

【杉本さんのプロフィール】
- 性別: 男性
- 呼称: 杉本、すーさん、ゆうき、ゆうきくん、杉本さん
- 声質: 低めかつ少しこもった声

【現在の職種（2025年1月時点）】
- AIエンジニア / 機械学習エンジニア（生成AI担当）
- 所属: 株式会社エクサウィザーズ
- 次の転職先: ビズリーチ（AIエンジニア、社内DX・AIエージェント構築）

【経歴サマリー】
- リクルート出身（営業、Sales Leader 2013-2019）
  * 大手顧客の事業成長支援（民泊立ち上げ、CRM開発、新規出店提案）
  * 担当取引売上昨対183%達成（0.3億円→0.55億円）
- アメリカ留学・CS学位取得（2019-2023）
  * サンフランシスコ留学、TOEIC 905点
  * University of the People（CS学士 GPA 3.85）
- AI/機械学習エンジニア（2022-現在）
  * 画像処理プロダクト開発
  * クラスタリング、分類予測モデル構築
  * RAG構築、生成AI活用
  * 自社プロダクト開発（要求定義から開発まで一気通貫）

【専門領域】
- 営業: 顧客理解、戦略策定、PDCA実行、合意形成
- エンジニアリング: 機械学習、RAG、生成AI、Python、FastAPI
- 要求定義力: 顧客課題からプロダクト開発まで

【思考性・今後の目標】
- 起業を目指している
- アメリカ転職を目標にしている
- 営業とエンジニアリングの両方の専門性を活かした価値提供
- 「AIを効果的に活用し、複数専門領域を担える人材」を志向
- 本質的価値を追求するスタンス（中長期成長に必要なことは何か）
- 録音の目的: 自身の考えや意思決定プロセスを記録

【話し方の特徴】
- ビジネス戦略、起業、AI、DX、生成AI、RAGなどの話題に詳しい
- 顧客課題の本質を追求する姿勢
- 営業経験からの現場感覚を持つ
- データに基づく意思決定を重視
- 合意形成力（課題の要素分解力）が高い

【判断基準（優先順位順）】
1. 名前の明示的言及（「杉本」「すーさん」「ゆうき」「ゆうきくん」「杉本さん」と呼ばれる、自己紹介する）
2. カレンダー参加者情報との照合（上記【カレンダー参加者情報】を参照）
3. 録音者である可能性（一人語り、独白、思考の整理）
4. 会話の主導者（ビジネス戦略、起業、AI、DX、RAG、生成AIなどの専門的話題を深く語る）
5. 質問を受ける側（面談やインタビューで自身のキャリア・経歴を語る）
6. 意思決定者の立場（「〜することにした」「〜を決める必要がある」など）
7. 声質: 低めかつ少しこもった声
8. 専門用語の使用: 機械学習、RAG、クラスタリング、分類予測、FastAPI、Pythonなどの技術用語を自然に使う

【重要】
- **この録音は杉本さん自身が録音したものであり、必ず杉本さんが話者として含まれています**
- **独白（一人語り）の場合、その話者は100%杉本さんです**
- カレンダー参加者情報がある場合、その情報を参考に各Speakerを参加者名にマッピングしてください
- 名前が明示されていなくても、上記プロフィールと一致すれば「medium」以上の確信度で判定可能
- 面談やインタビュー形式で自身のキャリアを語る側が杉本さんの可能性が高い

【回答形式】
以下のJSON形式で回答してください:
{{
  "sugimoto_speaker": "Speaker 0" or "Speaker 1",
  "participants_mapping": {{
    "Speaker 0": "杉本",
    "Speaker 1": "田中"
  }},
  "confidence": "high" or "medium" or "low",
  "reasoning": "判断理由を簡潔に（使用した判断基準を明記）"
}}

注意:
- sugimoto_speakerは必須です。nullは許可されません。
- participants_mappingは可能な範囲で埋めてください。不明な場合は "Other" としてください。
- カレンダー参加者情報がある場合は、それを最優先で活用してください。"""

    model = genai.GenerativeModel('gemini-2.5-pro')

    response = model.generate_content(
        prompt,
        generation_config={
            'temperature': 0.1,
            'response_mime_type': 'application/json'
        }
    )

    result = json.loads(response.text)

    # sugimoto_speakerがnullまたは存在しない場合のエラーハンドリング
    if not result.get('sugimoto_speaker'):
        raise ValueError(
            f"❌ LLMが杉本さんを特定できませんでした。\n"
            f"Reasoning: {result.get('reasoning', 'N/A')}\n"
            f"この録音には必ず杉本さんが含まれているはずです。\n"
            f"プロンプトを見直すか、サンプルサイズを増やしてください。"
        )

    # デフォルト値の設定
    if "participants_mapping" not in result:
        result["participants_mapping"] = {}

    return result


def apply_speaker_inference_to_structured_json(
    structured_file_path: str,
    inference_result: Dict,
    output_path: str = None
):
    """
    話者推論結果を構造化JSONに適用

    Args:
        structured_file_path: 構造化JSONファイルパス
        inference_result: infer_speakers_with_participants()の出力
        output_path: 出力先（Noneの場合は上書き）
    """
    with open(structured_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # segmentsにspeaker_nameを追加
    participants_mapping = inference_result.get("participants_mapping", {})
    sugimoto_speaker = inference_result.get("sugimoto_speaker", "")

    for seg in data.get("segments", []):
        speaker_id = seg.get("speaker", "")

        if speaker_id == sugimoto_speaker:
            seg["speaker_name"] = "杉本"
        elif speaker_id in participants_mapping:
            seg["speaker_name"] = participants_mapping[speaker_id]
        else:
            seg["speaker_name"] = "Other"

    # メタデータに推論結果を追加
    if "metadata" not in data:
        data["metadata"] = {}

    data["metadata"]["speaker_inference"] = {
        "sugimoto_speaker": sugimoto_speaker,
        "participants_mapping": participants_mapping,
        "confidence": inference_result.get("confidence", "unknown"),
        "reasoning": inference_result.get("reasoning", "")
    }

    # 保存
    output_path = output_path or structured_file_path
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✓ 話者推論結果を適用: {output_path}")


if __name__ == "__main__":
    # テスト用サンプル
    print("=== enhanced_speaker_inference.py テスト ===\n")

    # テスト用セグメント（簡略版）
    test_segments = [
        {"speaker": "Speaker 0", "text": "今日は予算について話したいと思います", "start": 0.0, "end": 3.0},
        {"speaker": "Speaker 1", "text": "はい、よろしくお願いします", "start": 3.0, "end": 5.0},
        {"speaker": "Speaker 0", "text": "前回の会議で田中さんから提案があった件ですが", "start": 5.0, "end": 8.0},
        {"speaker": "Speaker 1", "text": "あの件、承認されました", "start": 8.0, "end": 10.0},
        {"speaker": "Speaker 0", "text": "それは良かったです。私としては、このプロジェクトを進めるにあたって", "start": 10.0, "end": 15.0},
    ] * 10  # 50セグメント相当にするため10倍

    # テストケース1: カレンダー参加者情報なし
    print("テストケース1: カレンダー参加者情報なし")
    result1 = infer_speakers_with_participants(
        segments=test_segments,
        file_context="test_meeting.m4a"
    )
    print(f"sugimoto_speaker: {result1['sugimoto_speaker']}")
    print(f"confidence: {result1['confidence']}")
    print(f"participants_mapping: {result1.get('participants_mapping', {})}")
    print(f"reasoning: {result1['reasoning'][:100]}...")
    print()

    # テストケース2: カレンダー参加者情報あり
    print("テストケース2: カレンダー参加者情報あり")
    test_participants = [
        {
            "canonical_name": "田中",
            "display_names": ["田中", "田中部長"],
            "role": "部長",
            "organization": "営業部"
        }
    ]
    result2 = infer_speakers_with_participants(
        segments=test_segments,
        calendar_participants=test_participants,
        file_context="test_meeting.m4a"
    )
    print(f"sugimoto_speaker: {result2['sugimoto_speaker']}")
    print(f"confidence: {result2['confidence']}")
    print(f"participants_mapping: {result2.get('participants_mapping', {})}")
    print(f"reasoning: {result2['reasoning'][:100]}...")
    print()

    print("=== テスト完了 ===")
