#!/usr/bin/env python3
"""
Structured Transcription with Metadata (Phase 6-1)
使い方: python structured_transcribe.py <音声ファイルパス>
機能: OpenAI Whisper API (word-level timestamps) + Gemini API要約 + JSON構造化
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
import google.generativeai as genai

# .envファイルを読み込み
load_dotenv()

# OpenAI Whisper API file size limit (25MB)
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB in bytes


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


def transcribe_audio_with_timestamps(file_path):
    """
    OpenAI Whisper APIで音声ファイルを文字起こし（word-level timestamps付き）

    戻り値:
        dict: {
            "text": 全文,
            "segments": [セグメントリスト],
            "words": [単語リスト] or None
        }
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    file_size = os.path.getsize(file_path)

    # ファイルサイズチェック（25MB超過の場合は分割）
    if file_size > MAX_FILE_SIZE:
        print(f"  File size: {file_size / 1024 / 1024:.1f}MB (exceeds 25MB limit)")
        print(f"  Splitting into chunks...")

        chunks = split_audio_file(file_path)
        print(f"  Created {len(chunks)} chunks")

        # 各チャンクを文字起こし
        all_segments = []
        all_words = []
        full_text_parts = []
        time_offset = 0.0

        for i, chunk_path in enumerate(chunks, 1):
            print(f"  Transcribing chunk {i}/{len(chunks)}...", end='\r')

            with open(chunk_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja",
                    response_format="verbose_json",
                    timestamp_granularities=["word", "segment"]
                )

            # テキスト追加
            full_text_parts.append(response.text)

            # セグメント追加（時刻オフセット調整）
            if hasattr(response, 'segments') and response.segments:
                for seg in response.segments:
                    segment = {
                        "id": len(all_segments) + 1,
                        "start": seg.start + time_offset,
                        "end": seg.end + time_offset,
                        "text": seg.text
                    }
                    all_segments.append(segment)

            # 単語追加（時刻オフセット調整）
            if hasattr(response, 'words') and response.words:
                for word in response.words:
                    word_data = {
                        "word": word.word,
                        "start": word.start + time_offset,
                        "end": word.end + time_offset
                    }
                    all_words.append(word_data)

            # 次のチャンクのオフセットを更新
            if hasattr(response, 'segments') and response.segments and len(response.segments) > 0:
                time_offset = all_segments[-1]['end']

        print()  # 改行

        # チャンクを削除
        for chunk in chunks:
            chunk.unlink()
        chunks[0].parent.rmdir()

        return {
            "text": "\n\n".join(full_text_parts),
            "segments": all_segments,
            "words": all_words if all_words else None
        }

    else:
        # ファイルサイズが25MB以下の場合は通常処理
        with open(file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ja",
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"]
            )

        # セグメント処理
        segments = []
        if hasattr(response, 'segments') and response.segments:
            for i, seg in enumerate(response.segments, 1):
                segment = {
                    "id": i,
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text
                }
                segments.append(segment)

        # 単語処理
        words = []
        if hasattr(response, 'words') and response.words:
            for word in response.words:
                word_data = {
                    "word": word.word,
                    "start": word.start,
                    "end": word.end
                }
                words.append(word_data)

        return {
            "text": response.text,
            "segments": segments,
            "words": words if words else None
        }


def summarize_text(text):
    """
    Gemini APIでテキストを要約
    """
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.0-flash")

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


def extract_file_metadata(audio_path):
    """
    音声ファイルのメタデータを抽出
    """
    path = Path(audio_path)
    stat = path.stat()

    # ffprobeで音声長を取得
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip()) if result.returncode == 0 else None
    except:
        duration = None

    return {
        "file_name": path.name,
        "file_size_bytes": stat.st_size,
        "format": path.suffix[1:] if path.suffix else None,
        "recorded_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "duration_seconds": duration
    }


def extract_transcription_metadata(text, segments):
    """
    文字起こしテキストのメタデータを生成
    """
    char_count = len(text)
    word_count = len(text.split())
    sentence_count = text.count('。') + text.count('.') + text.count('!') + text.count('？')

    return {
        "transcribed_at": datetime.now().isoformat(),
        "language": "ja",
        "char_count": char_count,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "segment_count": len(segments)
    }


def create_structured_json(audio_path, transcription_result, summary):
    """
    構造化されたJSONを生成
    """
    file_metadata = extract_file_metadata(audio_path)
    transcription_metadata = extract_transcription_metadata(
        transcription_result["text"],
        transcription_result["segments"]
    )

    structured_data = {
        "metadata": {
            "file": file_metadata,
            "transcription": transcription_metadata
        },
        "segments": transcription_result["segments"],
        "words": transcription_result["words"],
        "full_text": transcription_result["text"],
        "summary": summary
    }

    return structured_data


def save_json(data, output_path):
    """
    JSONファイルに保存
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON保存完了: {output_path}")


def main():
    # コマンドライン引数チェック
    if len(sys.argv) < 2:
        print("使い方: python structured_transcribe.py <音声ファイルパス>")
        sys.exit(1)

    audio_path = sys.argv[1]

    # ファイル存在チェック
    if not os.path.exists(audio_path):
        print(f"❌ エラー: ファイルが見つかりません: {audio_path}")
        sys.exit(1)

    print(f"🎙️ 構造化文字起こし開始: {audio_path}")
    print("[1/3] 文字起こし中（タイムスタンプ付き）...")

    # 文字起こし実行（タイムスタンプ付き）
    transcription_result = transcribe_audio_with_timestamps(audio_path)

    print("[2/3] 要約生成中...")

    # 要約生成
    summary = summarize_text(transcription_result["text"])

    print("[3/3] JSON構造化中...")

    # 構造化JSON生成
    structured_data = create_structured_json(audio_path, transcription_result, summary)

    # 出力ファイル名を生成
    base_path = audio_path.rsplit(".", 1)[0]
    json_path = base_path + "_structured.json"

    # JSON保存
    save_json(structured_data, json_path)

    # 統計情報表示
    print("\n📊 処理統計:")
    print(f"  文字数: {structured_data['metadata']['transcription']['char_count']}")
    print(f"  単語数: {structured_data['metadata']['transcription']['word_count']}")
    print(f"  セグメント数: {structured_data['metadata']['transcription']['segment_count']}")
    if structured_data['words']:
        print(f"  単語タイムスタンプ数: {len(structured_data['words'])}")

    if structured_data['metadata']['file']['duration_seconds']:
        duration = structured_data['metadata']['file']['duration_seconds']
        print(f"  音声長: {duration:.1f}秒 ({duration/60:.1f}分)")

    print("\n🎉 完了!")


if __name__ == "__main__":
    main()
