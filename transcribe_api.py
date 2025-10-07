#!/usr/bin/env python3
"""
超シンプル文字起こし＆要約スクリプト（Phase 4）
使い方: python transcribe_api.py <音声ファイルパス>
機能: OpenAI Whisper API文字起こし + Gemini API要約
"""

import os
import sys
from openai import OpenAI
from dotenv import load_dotenv
import google.generativeai as genai

# .envファイルを読み込み
load_dotenv()

def transcribe_audio(file_path):
    """
    OpenAI Whisper APIで音声ファイルを文字起こし

    引数:
        file_path: 音声ファイルのパス（.m4a, .mp3, .wav等）

    戻り値:
        文字起こしされたテキスト（文字列）
    """
    # OpenAIクライアント初期化
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # 音声ファイルを開く
    with open(file_path, "rb") as audio_file:
        # Whisper APIで文字起こし
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ja"  # 日本語指定
        )

    return response.text

def summarize_text(text):
    """
    Gemini APIでテキストを要約

    引数:
        text: 要約するテキスト

    戻り値:
        要約されたテキスト（文字列）
    """
    # Gemini API初期化
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-1.5-flash")

    # 要約プロンプト
    prompt = f"""以下の文字起こしテキストを要約してください。

【要約形式】
1. エグゼクティブサマリー（2-3行）
2. 主要ポイント（箇条書き、3-5項目）
3. 詳細サマリー（段落形式）

【文字起こしテキスト】
{text}
"""

    response = model.generate_content(prompt)
    return response.text

def save_text(text, output_path):
    """
    テキストをファイルに保存

    引数:
        text: 保存するテキスト
        output_path: 出力ファイルパス
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"✅ 保存完了: {output_path}")

def save_markdown(transcription, summary, output_path):
    """
    文字起こしと要約をMarkdown形式で保存

    引数:
        transcription: 文字起こしテキスト
        summary: 要約テキスト
        output_path: 出力ファイルパス
    """
    # Markdownフォーマット
    markdown_content = f"""# 文字起こし結果

## 要約

{summary}

---

## 全文

{transcription}
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"✅ Markdown保存完了: {output_path}")

def main():
    # コマンドライン引数チェック
    if len(sys.argv) < 2:
        print("使い方: python transcribe_api.py <音声ファイルパス>")
        sys.exit(1)

    # 音声ファイルパス取得
    audio_path = sys.argv[1]

    # ファイル存在チェック
    if not os.path.exists(audio_path):
        print(f"❌ エラー: ファイルが見つかりません: {audio_path}")
        sys.exit(1)

    print(f"🎙️ 文字起こし開始: {audio_path}")

    # 文字起こし実行
    text = transcribe_audio(audio_path)

    # 出力ファイル名を生成
    base_path = audio_path.rsplit(".", 1)[0]
    txt_path = base_path + "_transcription.txt"
    md_path = base_path + "_summary.md"

    # テキスト保存
    save_text(text, txt_path)

    print("📝 要約生成中...")

    # 要約生成
    summary = summarize_text(text)

    # Markdown保存
    save_markdown(text, summary, md_path)

    print("🎉 完了!")

if __name__ == "__main__":
    main()
