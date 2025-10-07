#!/usr/bin/env python3
"""
単一ファイルテスト用スクリプト
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# transcribe.pyから関数をインポート
from transcribe import transcribe_audio, summarize_text, save_output, diarize_audio, logger, OUTPUT_DIR

load_dotenv()

def main():
    # テスト対象ファイル（10分版）
    audio_file = Path("Test Recording_10min.m4a")

    if not audio_file.exists():
        logger.error(f"ファイルが見つかりません: {audio_file}")
        sys.exit(1)

    # 出力ディレクトリ作成
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"=== 単一ファイルテスト開始: {audio_file.name} ===")
    logger.info(f"ファイルサイズ: {audio_file.stat().st_size / 1024 / 1024:.1f} MB")

    try:
        # 話者分離をスキップ（2時間音声のためメモリエラー回避）
        logger.info("話者分離をスキップします（2時間音声のため）")
        speaker_segments = {}

        # 文字起こし
        logger.info("文字起こしを実行中...")
        transcript, segments, audio_info = transcribe_audio(audio_file, speaker_segments)

        # 要約生成
        logger.info("要約生成中...")
        summary = summarize_text(transcript)

        # 保存
        logger.info("結果を保存中...")
        save_output(audio_file.name, transcript, summary, segments, audio_info)

        # 統計情報
        unique_speakers = len(set([s['metadata']['speaker_id'] for s in segments]))

        logger.info(f"\n✅ 処理完了!")
        logger.info(f"   - セグメント数: {len(segments)}")
        logger.info(f"   - 話者数: {unique_speakers}人")
        logger.info(f"   - 音声長: {audio_info['duration']:.1f}秒 ({audio_info['duration']/60:.1f}分)")
        logger.info(f"   - 言語: {audio_info['language']}")
        logger.info(f"\n出力先: {OUTPUT_DIR}")

    except Exception as e:
        logger.error(f"❌ 処理失敗: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
