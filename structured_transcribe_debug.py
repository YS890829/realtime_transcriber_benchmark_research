#!/usr/bin/env python3
"""
Structured Transcription with Enhanced Logging (Debug Version)
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

# .envファイルを読み込み
load_dotenv()

# Gemini API Key選択（デフォルト: 無料枠）
USE_PAID_TIER = os.getenv("USE_PAID_TIER", "false").lower() == "true"
if USE_PAID_TIER:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_PAID")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY_PAID not set but USE_PAID_TIER=true")
    print("ℹ️  Using PAID tier API key", flush=True)
else:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_FREE")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY_FREE not set")
    print("ℹ️  Using FREE tier API key", flush=True)

# Gemini API inline file size limit (20MB)
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB in bytes


def split_audio_file(file_path, chunk_duration=600):
    """
    Split large audio file into chunks using ffmpeg
    """
    file_path = Path(file_path)
    output_dir = file_path.parent / f"{file_path.stem}_chunks"
    output_dir.mkdir(exist_ok=True)

    output_pattern = str(output_dir / f"chunk_%03d{file_path.suffix}")

    cmd = [
        'ffmpeg',
        '-i', str(file_path),
        '-f', 'segment',
        '-segment_time', str(chunk_duration),
        '-c', 'copy',
        output_pattern
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"ffmpeg failed: {result.stderr}")

    chunks = sorted(output_dir.glob(f"chunk_*{file_path.suffix}"))
    return chunks


def summarize_text(text):
    """
    Gemini APIでテキストを要約（詳細ログ付き）
    """
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""以下の文字起こしテキストを要約してください。

【要約形式】
1. エグゼクティブサマリー（2-3行）
2. 主要ポイント（箇条書き、3-5項目）
3. 詳細サマリー（段落形式）

【文字起こしテキスト】
{text}
"""

    # ログ: 要約リクエスト情報
    print(f"  [要約API] テキスト長: {len(text)}文字", flush=True)
    print(f"  [要約API] プロンプト長: {len(prompt)}文字", flush=True)
    print(f"  [要約API] API呼び出し開始...", flush=True)

    try:
        response = model.generate_content(prompt)

        # ログ: レスポンス詳細
        print(f"  [要約API] API呼び出し完了", flush=True)
        print(f"  [要約API] Response type: {type(response)}", flush=True)

        if hasattr(response, 'candidates'):
            candidates_count = len(response.candidates) if response.candidates else 0
            print(f"  [要約API] Candidates count: {candidates_count}", flush=True)

            if not response.candidates or candidates_count == 0:
                print(f"  [要約API] ❌ エラー: response.candidates is empty", flush=True)

                # prompt_feedbackを確認
                if hasattr(response, 'prompt_feedback'):
                    feedback = response.prompt_feedback
                    print(f"  [要約API] prompt_feedback: {feedback}", flush=True)

                    if hasattr(feedback, 'block_reason'):
                        print(f"  [要約API] block_reason: {feedback.block_reason}", flush=True)

                    if hasattr(feedback, 'safety_ratings'):
                        print(f"  [要約API] safety_ratings:", flush=True)
                        for rating in feedback.safety_ratings:
                            print(f"    - {rating}", flush=True)

                raise ValueError(f"Response blocked: candidates is empty. prompt_feedback={feedback if hasattr(response, 'prompt_feedback') else 'N/A'}")

            # 正常な場合のログ
            candidate = response.candidates[0]
            print(f"  [要約API] finish_reason: {candidate.finish_reason if hasattr(candidate, 'finish_reason') else 'N/A'}", flush=True)

            if hasattr(candidate, 'safety_ratings'):
                print(f"  [要約API] safety_ratings:", flush=True)
                for rating in candidate.safety_ratings:
                    print(f"    - {rating}", flush=True)

            print(f"  [要約API] ✅ 要約生成成功 (長さ: {len(response.text)}文字)", flush=True)

        return response.text

    except Exception as e:
        print(f"  [要約API] ❌ Exception: {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise


# 元のstructured_transcribe.pyからmain()をコピー
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python structured_transcribe_debug.py <音声ファイルパス>")
        sys.exit(1)

    audio_path = sys.argv[1]
    print(f"🔍 DEBUG MODE: Enhanced logging enabled", flush=True)
    print(f"🎙️ File: {audio_path}", flush=True)

    # 要約テストのみ実行（文字起こしはスキップ）
    test_text = "これはテスト用の短いテキストです。要約APIのレスポンスをデバッグします。"
    print(f"\n[テスト] 短いテキストで要約API動作確認...", flush=True)
    try:
        summary = summarize_text(test_text)
        print(f"\n✅ テスト成功: 要約生成完了", flush=True)
        print(f"要約: {summary[:100]}...", flush=True)
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}", flush=True)
