#!/usr/bin/env python3
"""
Structured Transcription with Metadata (Phase 7 Stage 7-1)
使い方: python structured_transcribe.py <音声ファイルパス>
機能: Gemini Audio API (話者識別付き) + JSON構造化
注意: Word-level/Segment-level timestampsは非対応（Geminiの制約）
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
    print("ℹ️  Using PAID tier API key")
else:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_FREE")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY_FREE not set")
    print("ℹ️  Using FREE tier API key")

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


def transcribe_audio_with_gemini(file_path):
    """
    Gemini Audio APIで音声ファイルを文字起こし（話者識別付き）

    戻り値:
        dict: {
            "text": 全文,
            "segments": [セグメントリスト with speaker],
            "words": None,  # Geminiは非対応
            "speakers": [話者リスト]
        }
    """
    genai.configure(api_key=GEMINI_API_KEY)
    # Use Gemini 2.5 Flash
    model = genai.GenerativeModel("gemini-2.5-flash")

    file_size = os.path.getsize(file_path)
    file_path_obj = Path(file_path)
    mime_type = f"audio/{file_path_obj.suffix[1:]}" if file_path_obj.suffix else "audio/mpeg"

    # ファイルサイズチェック（20MB超過の場合は分割）
    if file_size > MAX_FILE_SIZE:
        print(f"  File size: {file_size / 1024 / 1024:.1f}MB (exceeds 20MB limit)")
        print(f"  Splitting into chunks...")

        chunks = split_audio_file(file_path)
        print(f"  Created {len(chunks)} chunks")

        # 各チャンクを文字起こし
        all_segments = []
        all_speakers = {}
        full_text_parts = []
        segment_id_offset = 0

        for i, chunk_path in enumerate(chunks, 1):
            print(f"  Transcribing chunk {i}/{len(chunks)}...", end='\r')

            # Rate limiting: 2 RPM = 30 seconds per request
            if i > 1:
                time.sleep(30)

            with open(chunk_path, "rb") as audio_file:
                audio_bytes = audio_file.read()

            prompt = """この音声ファイルを文字起こしし、JSON形式で出力してください。

【出力形式】
{
  "segments": [
    {
      "speaker": "Speaker 1",
      "text": "発言内容",
      "timestamp": "MM:SS"
    }
  ]
}

【要件】
1. 話者を識別し、Speaker 1, Speaker 2などのラベルを付与
2. セグメントごとに話者とテキストを記載
3. タイムスタンプはMM:SS形式で推定
4. 日本語の文字起こし"""

            response = model.generate_content(
                [prompt, {"mime_type": mime_type, "data": audio_bytes}],
                generation_config={
                    "response_mime_type": "application/json"
                }
            )

            # JSONパース
            try:
                chunk_data = json.loads(response.text)

                # セグメント追加（ID調整）
                for seg in chunk_data.get("segments", []):
                    segment = {
                        "id": len(all_segments) + 1,
                        "speaker": seg.get("speaker", "Unknown"),
                        "text": seg.get("text", ""),
                        "timestamp": seg.get("timestamp", "00:00")
                    }
                    all_segments.append(segment)

                    # 話者カウント
                    speaker = segment["speaker"]
                    if speaker not in all_speakers:
                        all_speakers[speaker] = 0
                    all_speakers[speaker] += 1

                # テキスト追加
                full_text_parts.append(" ".join([s.get("text", "") for s in chunk_data.get("segments", [])]))

            except json.JSONDecodeError as e:
                print(f"\n  Warning: JSON parse error in chunk {i}: {e}")
                print(f"  Attempting to repair...")

                # JSON修復試行
                try:
                    text = response.text
                    last_complete = text.rfind('},')
                    if last_complete > 0:
                        repaired = text[:last_complete + 1] + '\n  ]\n}'
                        chunk_data = json.loads(repaired)

                        for seg in chunk_data.get("segments", []):
                            segment = {
                                "id": len(all_segments) + 1,
                                "speaker": seg.get("speaker", "Unknown"),
                                "text": seg.get("text", ""),
                                "timestamp": seg.get("timestamp", "00:00")
                            }
                            all_segments.append(segment)

                            speaker = segment["speaker"]
                            if speaker not in all_speakers:
                                all_speakers[speaker] = 0
                            all_speakers[speaker] += 1

                        full_text_parts.append(" ".join([s.get("text", "") for s in chunk_data.get("segments", [])]))
                        print(f"  ✓ Chunk {i} JSON repaired successfully.")
                    else:
                        raise ValueError("Cannot repair")
                except Exception:
                    # 修復失敗時は生テキストを使用
                    full_text_parts.append(response.text)

        print()  # 改行

        # チャンクを削除
        for chunk in chunks:
            chunk.unlink()
        chunks[0].parent.rmdir()

        # 話者リスト生成
        speakers = [
            {"id": speaker, "segment_count": count}
            for speaker, count in all_speakers.items()
        ]

        return {
            "text": "\n\n".join(full_text_parts),
            "segments": all_segments,
            "words": None,  # Geminiは非対応
            "speakers": speakers
        }

    else:
        # ファイルサイズが20MB以下の場合は通常処理
        with open(file_path, "rb") as audio_file:
            audio_bytes = audio_file.read()

        prompt = """この音声ファイルを文字起こしし、JSON形式で出力してください。

【出力形式】
{
  "segments": [
    {
      "speaker": "Speaker 1",
      "text": "発言内容",
      "timestamp": "MM:SS"
    }
  ]
}

【要件】
1. 話者を識別し、Speaker 1, Speaker 2などのラベルを付与
2. セグメントごとに話者とテキストを記載
3. タイムスタンプはMM:SS形式で推定
4. 日本語の文字起こし"""

        response = model.generate_content(
            [prompt, {"mime_type": mime_type, "data": audio_bytes}],
            generation_config={
                "response_mime_type": "application/json"
            }
        )

        # JSONパース
        try:
            # エラーハンドリング：finish_reasonをチェック
            if not response.text:
                print(f"⚠️ Gemini API response error: finish_reason={response.candidates[0].finish_reason}")
                print(f"Safety ratings: {response.candidates[0].safety_ratings}")
                raise ValueError(f"Gemini blocked response: finish_reason={response.candidates[0].finish_reason}")

            data = json.loads(response.text)

            segments = []
            speakers_dict = {}

            for i, seg in enumerate(data.get("segments", []), 1):
                speaker = seg.get("speaker", "Unknown")
                segment = {
                    "id": i,
                    "speaker": speaker,
                    "text": seg.get("text", ""),
                    "timestamp": seg.get("timestamp", "00:00")
                }
                segments.append(segment)

                # 話者カウント
                if speaker not in speakers_dict:
                    speakers_dict[speaker] = 0
                speakers_dict[speaker] += 1

            # 話者リスト生成
            speakers = [
                {"id": speaker, "segment_count": count}
                for speaker, count in speakers_dict.items()
            ]

            # 全文テキスト生成
            full_text = " ".join([s.get("text", "") for s in data.get("segments", [])])

            return {
                "text": full_text,
                "segments": segments,
                "words": None,  # Geminiは非対応
                "speakers": speakers
            }

        except json.JSONDecodeError as e:
            print(f"  Warning: JSON parse error: {e}")
            print(f"  Attempting to repair truncated JSON...")

            # JSON修復試行: 最後のセグメントが不完全な場合、それを削除して閉じる
            try:
                text = response.text
                # 最後の完全なセグメントを見つける
                last_complete = text.rfind('},')
                if last_complete > 0:
                    # そこまでを取り、配列とオブジェクトを閉じる
                    repaired = text[:last_complete + 1] + '\n  ]\n}'
                    data = json.loads(repaired)

                    segments = []
                    speakers_dict = {}

                    for i, seg in enumerate(data.get("segments", []), 1):
                        speaker = seg.get("speaker", "Unknown")
                        segment = {
                            "id": i,
                            "speaker": speaker,
                            "text": seg.get("text", ""),
                            "timestamp": seg.get("timestamp", "00:00")
                        }
                        segments.append(segment)

                        if speaker not in speakers_dict:
                            speakers_dict[speaker] = 0
                        speakers_dict[speaker] += 1

                    speakers = [
                        {"id": speaker, "segment_count": count}
                        for speaker, count in speakers_dict.items()
                    ]

                    full_text = " ".join([s.get("text", "") for s in data.get("segments", [])])

                    print(f"  ✓ JSON repaired successfully. Recovered {len(segments)} segments.")

                    return {
                        "text": full_text,
                        "segments": segments,
                        "words": None,
                        "speakers": speakers
                    }
                else:
                    raise ValueError("Cannot find valid segment boundary")

            except Exception as repair_error:
                print(f"  Warning: JSON repair failed: {repair_error}")
                print(f"  Response preview: {response.text[:200]}...")
                # エラー時はフォールバック
                return {
                    "text": response.text,
                    "segments": [],
                    "words": None,
                    "speakers": []
                }


def summarize_text(text):
    """
    Gemini APIでテキストを要約（詳細ログ付き）
    失敗時はNoneを返す（例外を上げない）
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

                print(f"  [要約API] ⚠️  要約生成失敗（フォールバック: summary=null）", flush=True)
                return None

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
        print(f"  [要約API] ⚠️  要約生成失敗（フォールバック: summary=null）", flush=True)
        import traceback
        traceback.print_exc()
        return None



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

    try:
        print(f"🎙️ 構造化文字起こし開始: {audio_path}")
        print("[1/3] 文字起こし中（Gemini Audio API + 話者識別）...")

        # 文字起こし実行（Gemini Audio API）
        transcription_result = transcribe_audio_with_gemini(audio_path)

        # セグメントが取得できなかった場合はエラー
        if not transcription_result.get("segments"):
            print(f"❌ エラー: 文字起こしに失敗しました（セグメントが空です）", file=sys.stderr)
            sys.exit(1)

        print("[2/3] 要約生成中...")

        # 要約生成（失敗時はNone）
        summary = summarize_text(transcription_result["text"])

        if summary is None:
            print("  ⚠️  要約生成に失敗しましたが、文字起こし結果は保存されます（summary: null）", flush=True)

        print("[3/3] JSON構造化中...")

        # 構造化JSON生成（summaryがNoneでも問題なし）
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

        # 要約状態表示
        if structured_data['summary']:
            print(f"  要約: 生成済み ({len(structured_data['summary'])}文字)")
        else:
            print(f"  要約: null（生成失敗）")

        # 話者情報表示
        if 'speakers' in structured_data and structured_data['speakers']:
            print(f"  話者数: {len(structured_data['speakers'])}")
            for speaker in structured_data['speakers']:
                print(f"    - {speaker['id']}: {speaker['segment_count']}セグメント")

        # Note: Word-level timestampsは非対応（Geminiの制約）
        if structured_data['words']:
            print(f"  単語タイムスタンプ数: {len(structured_data['words'])}")
        else:
            print(f"  単語タイムスタンプ: 非対応（Gemini API制約）")

        if structured_data['metadata']['file']['duration_seconds']:
            duration = structured_data['metadata']['file']['duration_seconds']
            print(f"  音声長: {duration:.1f}秒 ({duration/60:.1f}分)")

        # [Phase 10-1] 自動ファイル名変更
        if os.getenv('AUTO_RENAME_FILES', 'false').lower() == 'true':
            try:
                from generate_smart_filename import (
                    generate_filename_from_transcription,
                    rename_local_files
                )

                print("\n📝 最適なファイル名を生成中...")
                new_name = generate_filename_from_transcription(json_path)
                print(f"✨ 提案ファイル名: {new_name}")

                # ローカルファイルリネーム
                rename_map = rename_local_files(audio_path, new_name)

                # パス更新（統計表示後なので不要だが、将来の拡張のため）
                audio_path = str(rename_map[Path(audio_path)])
                json_path = str(rename_map[Path(json_path)])

            except Exception as e:
                print(f"⚠️  自動リネーム失敗: {e}")
                print("  文字起こし結果は保存されています")

        print("\n🎉 完了!")

    except Exception as e:
        print(f"\n❌ エラー: 処理中に例外が発生しました: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
