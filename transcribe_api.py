#!/usr/bin/env python3
"""
超シンプル文字起こしスクリプト
使い方: python transcribe_api.py <音声ファイルパス>
"""

import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

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

    # 出力ファイル名を生成（.txt）
    output_path = audio_path.rsplit(".", 1)[0] + "_transcription.txt"

    # テキスト保存
    save_text(text, output_path)

    print("🎉 完了!")

if __name__ == "__main__":
    main()
