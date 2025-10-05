#!/usr/bin/env python3
"""
Voice Memo Transcription & Summarization Tool (MVP)

iPhoneのボイスメモを文字起こし＆要約するシンプルなスクリプト
"""

import os
import logging
from pathlib import Path
from typing import List, Tuple

from faster_whisper import WhisperModel
import google.generativeai as genai
from dotenv import load_dotenv

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数読み込み
load_dotenv()

# 定数
VOICE_MEMOS_PATH = Path.home() / "Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings"
OUTPUT_DIR = Path.home() / "Documents/VoiceMemoTranscripts"
PROCESSED_FILES_LIST = Path(".processed_files.txt")


def find_new_files() -> List[Path]:
    """
    新規ボイスメモファイルを検出

    Returns:
        List[Path]: 未処理の.m4aファイルのリスト
    """
    logger.info("新規ファイルを検索中...")

    # ボイスメモフォルダの存在確認
    if not VOICE_MEMOS_PATH.exists():
        logger.error(f"ボイスメモフォルダが見つかりません: {VOICE_MEMOS_PATH}")
        logger.error("macOS Sonoma以降であることを確認してください")
        return []

    # 処理済みリスト読み込み
    processed = set()
    if PROCESSED_FILES_LIST.exists():
        processed = set(PROCESSED_FILES_LIST.read_text().splitlines())

    # 全.m4aファイル取得
    all_files = list(VOICE_MEMOS_PATH.glob("*.m4a"))

    # 新規ファイルのみ抽出
    new_files = [f for f in all_files if f.name not in processed]

    logger.info(f"新規ファイル: {len(new_files)}件")
    return new_files


def transcribe_audio(audio_path: Path) -> str:
    """
    faster-whisperで音声をテキスト化

    Args:
        audio_path: 音声ファイルのパス

    Returns:
        str: 文字起こしテキスト
    """
    logger.info(f"文字起こし中: {audio_path.name}")

    # モデル初期化（デフォルト設定、量子化なし）
    model = WhisperModel("medium", device="cpu")

    # 文字起こし実行
    segments, info = model.transcribe(
        str(audio_path),
        language="ja",
        vad_filter=True  # 無音除去
    )

    # セグメントを結合
    transcript = " ".join([seg.text for seg in segments])

    logger.info(f"文字起こし完了: {len(transcript)}文字")
    return transcript


def summarize_text(transcript: str) -> str:
    """
    Gemini APIでテキスト要約

    Args:
        transcript: 文字起こしテキスト

    Returns:
        str: 要約テキスト
    """
    logger.info("要約生成中...")

    # Gemini API初期化
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEYが設定されていません。.envファイルを確認してください")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # 要約プロンプト
    prompt = f"""以下の文字起こしテキストを要約してください。

【要約形式】
1. エグゼクティブサマリー（2-3行）
2. 主要ポイント（箇条書き、3-5項目）
3. 詳細サマリー（段落形式）

【文字起こしテキスト】
{transcript}
"""

    # 要約生成
    response = model.generate_content(prompt)
    summary = response.text

    logger.info("要約生成完了")
    return summary


def save_output(filename: str, transcript: str, summary: str) -> Tuple[Path, Path]:
    """
    TXTとMarkdownで結果を保存

    Args:
        filename: 元ファイル名
        transcript: 文字起こしテキスト
        summary: 要約テキスト

    Returns:
        Tuple[Path, Path]: (txtパス, mdパス)
    """
    logger.info("ファイル保存中...")

    # 出力ディレクトリ作成
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ファイル名（拡張子なし）
    base_name = Path(filename).stem

    # TXT: 文字起こし全文
    txt_path = OUTPUT_DIR / f"{base_name}.txt"
    txt_path.write_text(transcript, encoding="utf-8")
    logger.info(f"保存: {txt_path}")

    # Markdown: 要約
    md_path = OUTPUT_DIR / f"{base_name}_summary.md"
    md_content = f"# {base_name}\n\n{summary}"
    md_path.write_text(md_content, encoding="utf-8")
    logger.info(f"保存: {md_path}")

    return txt_path, md_path


def mark_as_processed(filename: str) -> None:
    """
    処理済みリストに追加

    Args:
        filename: ファイル名
    """
    with open(PROCESSED_FILES_LIST, "a", encoding="utf-8") as f:
        f.write(f"{filename}\n")


def main():
    """メイン処理"""
    logger.info("=== Voice Memo Transcriber (MVP) ===")

    # 新規ファイル検出
    new_files = find_new_files()

    if not new_files:
        logger.info("新規ファイルはありません")
        return

    # 各ファイルを処理
    for audio_file in new_files:
        try:
            logger.info(f"\n処理開始: {audio_file.name}")

            # 文字起こし
            transcript = transcribe_audio(audio_file)

            # 要約生成
            summary = summarize_text(transcript)

            # 保存
            save_output(audio_file.name, transcript, summary)

            # 処理済みリストに追加
            mark_as_processed(audio_file.name)

            logger.info(f"✅ 処理完了: {audio_file.name}\n")

        except Exception as e:
            logger.error(f"❌ 処理失敗: {audio_file.name} - {e}\n")
            continue

    logger.info("=== 全処理完了 ===")


if __name__ == "__main__":
    main()
