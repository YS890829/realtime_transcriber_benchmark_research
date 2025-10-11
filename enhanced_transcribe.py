#!/usr/bin/env python3
"""
Phase 6-2: 話者識別とトピック抽出
音声ファイルから構造化データ + 話者識別 + トピック抽出 + エンティティ抽出を実行
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai as genai

# 環境変数読み込み
load_dotenv()

def transcribe_audio_with_timestamps(file_path):
    """
    OpenAI Whisper APIで音声ファイルを文字起こし（word-level timestamps付き）

    Args:
        file_path: 音声ファイルのパス

    Returns:
        dict: {
            "text": 全文,
            "segments": [セグメントリスト],
            "words": [単語リスト] or None
        }
    """
    print(f"[1/5] 文字起こし中（タイムスタンプ付き）...")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # ファイルサイズチェック（25MB制限）
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

    if file_size_mb <= 25:
        # 通常処理
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
            "words": words
        }

    else:
        # 25MB超のファイルはチャンク分割
        print(f"  File size: {file_size_mb:.1f}MB (exceeds 25MB limit)")
        print(f"  Splitting into chunks...")

        # チャンク処理（既存のロジックを使用）
        return transcribe_large_file_chunked(file_path, client)


def transcribe_large_file_chunked(file_path, client):
    """25MB超のファイルをチャンク分割して文字起こし"""
    chunk_duration = 600  # 10分ごとに分割
    chunks_dir = Path("chunks")
    chunks_dir.mkdir(exist_ok=True)

    # ffmpegでチャンク作成
    subprocess.run([
        "ffmpeg", "-i", file_path,
        "-f", "segment",
        "-segment_time", str(chunk_duration),
        "-c", "copy",
        str(chunks_dir / "chunk_%03d.m4a")
    ], check=True, capture_output=True)

    chunk_files = sorted(chunks_dir.glob("chunk_*.m4a"))
    print(f"  Created {len(chunk_files)} chunks")

    all_segments = []
    all_words = []
    full_text_parts = []
    time_offset = 0.0

    for i, chunk_file in enumerate(chunk_files, 1):
        print(f"  Transcribing chunk {i}/{len(chunk_files)}...", end=" ")

        with open(chunk_file, "rb") as audio_file:
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

        # チャンクファイル削除
        chunk_file.unlink()

    # chunksディレクトリ削除
    chunks_dir.rmdir()

    return {
        "text": " ".join(full_text_parts),
        "segments": all_segments,
        "words": all_words
    }


def perform_speaker_diarization(audio_path, transcription_segments):
    """
    話者識別（Speaker Diarization）
    pyannote.audioを使用してセグメントごとに話者ラベルを付与

    Args:
        audio_path: 音声ファイルパス
        transcription_segments: 文字起こしセグメントリスト

    Returns:
        dict: {
            "speakers": [話者情報リスト],
            "segments_with_speaker": [話者ラベル付きセグメント]
        }
    """
    print(f"[2/5] 話者識別中...")

    try:
        from pyannote.audio import Pipeline

        # HuggingFace tokenが必要
        hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not hf_token:
            print("  Warning: HUGGINGFACE_TOKEN not found. Skipping speaker diarization.")
            return fallback_speaker_assignment(transcription_segments)

        # pyannote.audio diarizationパイプライン
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token
        )

        # 話者識別実行
        diarization = pipeline(audio_path)

        # 話者ごとの情報を集計
        speakers_info = {}
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            if speaker not in speakers_info:
                speakers_info[speaker] = {
                    "id": speaker,
                    "label": f"Speaker {len(speakers_info) + 1}",
                    "total_duration": 0.0,
                    "segments": []
                }
            speakers_info[speaker]["total_duration"] += turn.duration

        # 各セグメントに話者ラベルを割り当て
        segments_with_speaker = []
        for seg in transcription_segments:
            seg_start = seg["start"]
            seg_end = seg["end"]

            # このセグメントと最も重複する話者を探す
            max_overlap = 0.0
            assigned_speaker = "SPEAKER_00"  # デフォルト

            for turn, _, speaker in diarization.itertracks(yield_label=True):
                overlap_start = max(seg_start, turn.start)
                overlap_end = min(seg_end, turn.end)
                overlap = max(0, overlap_end - overlap_start)

                if overlap > max_overlap:
                    max_overlap = overlap
                    assigned_speaker = speaker

            seg_copy = seg.copy()
            seg_copy["speaker"] = assigned_speaker
            segments_with_speaker.append(seg_copy)

        # 話者リスト作成
        speakers_list = []
        total_duration = sum(s["total_duration"] for s in speakers_info.values())

        for speaker_id, info in speakers_info.items():
            speakers_list.append({
                "id": speaker_id,
                "label": info["label"],
                "total_duration": round(info["total_duration"], 2),
                "speaking_percentage": round((info["total_duration"] / total_duration) * 100, 1) if total_duration > 0 else 0
            })

        print(f"  Detected {len(speakers_list)} speakers")

        return {
            "speakers": speakers_list,
            "segments_with_speaker": segments_with_speaker
        }

    except Exception as e:
        print(f"  Error in speaker diarization: {e}")
        print(f"  Falling back to single speaker assumption")
        return fallback_speaker_assignment(transcription_segments)


def fallback_speaker_assignment(transcription_segments):
    """話者識別失敗時のフォールバック: 全セグメントを単一話者として扱う"""
    total_duration = sum(seg["end"] - seg["start"] for seg in transcription_segments)

    segments_with_speaker = []
    for seg in transcription_segments:
        seg_copy = seg.copy()
        seg_copy["speaker"] = "SPEAKER_00"
        segments_with_speaker.append(seg_copy)

    return {
        "speakers": [{
            "id": "SPEAKER_00",
            "label": "Speaker 1",
            "total_duration": round(total_duration, 2),
            "speaking_percentage": 100.0
        }],
        "segments_with_speaker": segments_with_speaker
    }


def extract_topics_and_entities(full_text, segments_with_speaker):
    """
    Gemini APIを使用してトピック抽出とエンティティ抽出

    Args:
        full_text: 全文テキスト
        segments_with_speaker: 話者ラベル付きセグメント

    Returns:
        dict: {
            "topics": [トピックリスト],
            "entities": {people, organizations, dates, action_items},
            "segments_enhanced": [トピックラベル付きセグメント]
        }
    """
    print(f"[3/5] トピック抽出中...")

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.0-flash-exp")

    # プロンプト作成
    prompt = f"""
以下の文字起こしテキストを分析し、以下のJSON形式で出力してください：

{{
  "topics": [
    {{
      "id": "topic_1",
      "name": "トピック名",
      "summary": "トピックの要約（1-2文）",
      "keywords": ["キーワード1", "キーワード2"]
    }}
  ],
  "entities": {{
    "people": ["人名1", "人名2"],
    "organizations": ["組織名1", "組織名2"],
    "dates": ["日付表現1", "日付表現2"],
    "action_items": ["アクション1", "アクション2"]
  }}
}}

文字起こしテキスト:
{full_text}
"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # JSONを抽出（```jsonブロックを除去）
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        result = json.loads(response_text)

        print(f"  Extracted {len(result.get('topics', []))} topics")
        print(f"  Found {len(result.get('entities', {}).get('people', []))} people")

        # セグメントにトピックを割り当て（簡易実装：キーワードマッチング）
        segments_enhanced = assign_topics_to_segments(
            segments_with_speaker,
            result.get("topics", [])
        )

        return {
            "topics": result.get("topics", []),
            "entities": result.get("entities", {}),
            "segments_enhanced": segments_enhanced
        }

    except Exception as e:
        print(f"  Error in topic extraction: {e}")
        return {
            "topics": [],
            "entities": {"people": [], "organizations": [], "dates": [], "action_items": []},
            "segments_enhanced": segments_with_speaker
        }


def assign_topics_to_segments(segments, topics):
    """セグメントにトピックラベルを割り当て（キーワードマッチング）"""
    segments_enhanced = []

    for seg in segments:
        seg_text = seg["text"]
        assigned_topics = []

        # 各トピックのキーワードがセグメントに含まれるかチェック
        for topic in topics:
            keywords = topic.get("keywords", [])
            if any(keyword in seg_text for keyword in keywords):
                assigned_topics.append(topic["id"])

        seg_copy = seg.copy()
        seg_copy["topics"] = assigned_topics if assigned_topics else []
        seg_copy["keywords"] = []  # 後で実装
        segments_enhanced.append(seg_copy)

    return segments_enhanced


def generate_enhanced_summary(full_text, topics, entities, speakers):
    """構造化データを活用した高精度要約生成"""
    print(f"[4/5] 要約生成中（構造化データ活用）...")

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.0-flash-exp")

    # 話者情報を文字列化
    speakers_info = "\n".join([
        f"- {s['label']}: {s['speaking_percentage']}% ({s['total_duration']}秒)"
        for s in speakers
    ])

    # トピック情報を文字列化
    topics_info = "\n".join([
        f"- {t['name']}: {t['summary']}"
        for t in topics
    ])

    # エンティティ情報を文字列化
    entities_info = f"""
- 人物: {', '.join(entities.get('people', []))}
- 組織: {', '.join(entities.get('organizations', []))}
- 日付: {', '.join(entities.get('dates', []))}
- アクション: {', '.join(entities.get('action_items', []))}
"""

    prompt = f"""
以下の情報を元に、会話の要約を作成してください。

【話者情報】
{speakers_info}

【トピック】
{topics_info}

【抽出されたエンティティ】
{entities_info}

【全文テキスト】
{full_text[:5000]}...  # 最初の5000文字のみ

以下の形式で要約を作成してください：

# エグゼクティブサマリー
（2-3文で全体の概要）

# 主要ポイント
- ポイント1
- ポイント2
- ポイント3

# 詳細サマリー
（各トピックについて詳細に説明）
"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"  Error in summary generation: {e}")
        return "要約生成に失敗しました"


def get_file_metadata(audio_path):
    """ファイルメタデータを抽出"""
    audio_path = Path(audio_path)

    # ファイル基本情報
    file_size = audio_path.stat().st_size
    file_mtime = datetime.fromtimestamp(audio_path.stat().st_mtime)

    # ffprobeで音声長を取得
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True,
            text=True,
            check=True
        )
        duration = float(result.stdout.strip())
    except:
        duration = 0.0

    return {
        "file_name": audio_path.name,
        "file_size_bytes": file_size,
        "format": audio_path.suffix.lstrip('.'),
        "recorded_at": file_mtime.isoformat(),
        "duration_seconds": duration
    }


def create_enhanced_json(audio_path, transcription_result, diarization_result, topics_result, summary):
    """Phase 6-2の拡張JSON構造を生成"""
    print(f"[5/5] JSON構造化中...")

    file_metadata = get_file_metadata(audio_path)

    # 文字起こしメタデータ
    full_text = transcription_result["text"]
    segments = topics_result["segments_enhanced"]
    words = transcription_result["words"]

    transcription_metadata = {
        "transcribed_at": datetime.now().isoformat(),
        "language": "ja",
        "char_count": len(full_text),
        "word_count": len(full_text.split()),
        "sentence_count": full_text.count("。") + full_text.count("？") + full_text.count("！"),
        "segment_count": len(segments)
    }

    # 統合JSON作成
    enhanced_data = {
        "metadata": {
            "file": file_metadata,
            "transcription": transcription_metadata
        },
        "speakers": diarization_result["speakers"],
        "topics": topics_result["topics"],
        "entities": topics_result["entities"],
        "segments": segments,
        "words": words,
        "full_text": full_text,
        "summary": summary
    }

    return enhanced_data


def main():
    if len(sys.argv) < 2:
        print("Usage: python enhanced_transcribe.py <audio_file>")
        sys.exit(1)

    audio_path = sys.argv[1]

    if not os.path.exists(audio_path):
        print(f"Error: File not found: {audio_path}")
        sys.exit(1)

    print(f"🎙️ 拡張文字起こし開始: {audio_path}")

    # Phase 6-1: 文字起こし
    transcription_result = transcribe_audio_with_timestamps(audio_path)

    # Phase 6-2: 話者識別
    diarization_result = perform_speaker_diarization(audio_path, transcription_result["segments"])

    # Phase 6-2: トピック抽出
    topics_result = extract_topics_and_entities(
        transcription_result["text"],
        diarization_result["segments_with_speaker"]
    )

    # Phase 6-2: 構造化データを活用した要約
    summary = generate_enhanced_summary(
        transcription_result["text"],
        topics_result["topics"],
        topics_result["entities"],
        diarization_result["speakers"]
    )

    # Phase 6-2: 拡張JSON作成
    enhanced_data = create_enhanced_json(
        audio_path,
        transcription_result,
        diarization_result,
        topics_result,
        summary
    )

    # 出力
    output_path = Path(audio_path).with_suffix('').name + "_enhanced.json"
    output_dir = Path(audio_path).parent
    output_file = output_dir / output_path

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(enhanced_data, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON保存完了: {output_file}")

    # 統計情報表示
    print(f"\n📊 処理統計:")
    print(f"  文字数: {enhanced_data['metadata']['transcription']['char_count']}")
    print(f"  単語数: {enhanced_data['metadata']['transcription']['word_count']}")
    print(f"  セグメント数: {enhanced_data['metadata']['transcription']['segment_count']}")
    print(f"  話者数: {len(enhanced_data['speakers'])}")
    print(f"  トピック数: {len(enhanced_data['topics'])}")
    print(f"  単語タイムスタンプ数: {len(enhanced_data['words']) if enhanced_data['words'] else 0}")
    print(f"  音声長: {enhanced_data['metadata']['file']['duration_seconds']:.1f}秒 ({enhanced_data['metadata']['file']['duration_seconds']/60:.1f}分)")

    print(f"\n🎉 完了!")


if __name__ == "__main__":
    main()
