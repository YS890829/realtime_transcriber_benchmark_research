#!/usr/bin/env python3
"""
Smart Filename Generator (Phase 10-1)
文字起こし内容に基づき、LLMで最適なファイル名を自動生成

使い方: python generate_smart_filename.py <音声ファイルパス>
前提条件: *_structured.json が既に存在すること
"""

import os
import sys
import json
import re
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
    print("ℹ️  Using PAID tier API key for filename generation")
else:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_FREE")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY_FREE not set")
    print("ℹ️  Using FREE tier API key for filename generation")


def generate_filename_from_transcription(json_path):
    """
    文字起こし結果から最適なファイル名を生成

    Args:
        json_path: *_structured.json のパス

    Returns:
        最適化されたファイル名（拡張子なし）
    """
    # JSONファイル読み込み
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    full_text = data.get('full_text', '')
    summary = data.get('summary', '')

    # 日付取得（録音日時 or 現在時刻）
    recorded_at = data.get('metadata', {}).get('file', {}).get('recorded_at', '')
    if recorded_at:
        try:
            date_obj = datetime.fromisoformat(recorded_at)
            date_str = date_obj.strftime('%Y%m%d')
        except:
            date_str = datetime.now().strftime('%Y%m%d')
    else:
        date_str = datetime.now().strftime('%Y%m%d')

    # Gemini APIで最適なファイル名生成
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    # 要約が長すぎる場合は切り詰め
    summary_excerpt = summary[:500] if summary else "（要約なし）"
    full_text_excerpt = full_text[:200] if full_text else "（テキストなし）"

    prompt = f"""以下の音声文字起こし内容に基づき、最適なファイル名を生成してください。

【要件】
1. ファイル名は20-30文字以内（日本語文字数）
2. 日本語OK（macOS/Windows互換）
3. 会話の主要トピックが一目でわかる
4. **必ず日付プレフィックスを使用: {date_str}_** （この日付は録音日時なので変更しないこと）
5. 特殊文字禁止（/\\:*?"<>|）
6. スペースはアンダースコア（_）に置換
7. 簡潔で分かりやすい名前

【要約】
{summary_excerpt}

【全文サンプル（最初200文字）】
{full_text_excerpt}

【出力形式】
ファイル名のみを1行で出力（拡張子なし）
**重要**: 必ず {date_str}_ で開始すること（日付は変更しない）
例: {date_str}_営業ミーティング_Q4戦略
例: {date_str}_起業計画と資金調達の相談
例: {date_str}_キャリア相談_転職について
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.3}  # 安定した出力
        )
        suggested_name = response.text.strip()

        # ファイル名のサニタイズ
        suggested_name = sanitize_filename(suggested_name)

        return suggested_name

    except Exception as e:
        print(f"⚠️  Gemini API error: {e}")
        # フォールバック: 日付＋"音声ファイル"
        fallback_name = f"{date_str}_音声ファイル"
        print(f"  Using fallback filename: {fallback_name}")
        return fallback_name


def sanitize_filename(name):
    """
    ファイル名をサニタイズ（OS互換性）

    Args:
        name: 元のファイル名

    Returns:
        サニタイズされたファイル名
    """
    # 1. 禁止文字を除去
    name = re.sub(r'[/\\:*?"<>|]', '', name)

    # 2. 改行・タブを除去
    name = re.sub(r'[\n\r\t]', '', name)

    # 3. 連続スペース・アンダースコアを1つに
    name = re.sub(r'[\s_]+', '_', name)

    # 4. 前後の空白・アンダースコア除去
    name = name.strip('_')

    # 5. 長さ制限（30文字）
    if len(name) > 30:
        # 単語境界で切る
        name = name[:30]
        # 最後のアンダースコア以降を削除（単語の途中で切れないように）
        if '_' in name:
            name = name.rsplit('_', 1)[0]

    # 6. 空の場合はフォールバック
    if not name:
        name = datetime.now().strftime('%Y%m%d_%H%M%S')

    return name


def rename_local_files(audio_path, new_base_name):
    """
    音声ファイルと関連ファイル（JSON等）を一括リネーム

    Args:
        audio_path: 元の音声ファイルパス
        new_base_name: 新しいベース名（拡張子なし）

    Returns:
        リネームマップ {元のPath: 新しいPath}
    """
    original_path = Path(audio_path)
    original_stem = original_path.stem
    directory = original_path.parent
    extension = original_path.suffix

    # リネームマップ
    rename_map = {}

    # 1. 音声ファイル
    new_audio_path = directory / f"{new_base_name}{extension}"

    # 同名ファイルが既に存在する場合はタイムスタンプ追加
    if new_audio_path.exists() and new_audio_path != original_path:
        timestamp = datetime.now().strftime('%H%M%S')
        new_base_name_with_time = f"{new_base_name}_{timestamp}"
        new_audio_path = directory / f"{new_base_name_with_time}{extension}"
        new_base_name = new_base_name_with_time  # 他のファイルも同じ名前に
        print(f"  ⚠️  同名ファイル存在。タイムスタンプ追加: {new_base_name}")

    rename_map[original_path] = new_audio_path

    # 2. *_structured.json
    structured_json = directory / f"{original_stem}_structured.json"
    if structured_json.exists():
        rename_map[structured_json] = directory / f"{new_base_name}_structured.json"

    # 3. その他関連ファイル（あれば）
    for suffix in ['_summary.md', '.txt', '_enhanced.json', '_structured_with_speakers.json']:
        old_file = directory / f"{original_stem}{suffix}"
        if old_file.exists():
            rename_map[old_file] = directory / f"{new_base_name}{suffix}"

    # 一括リネーム実行
    print(f"\n📝 ローカルファイル名変更:")
    for old_path, new_path in rename_map.items():
        print(f"  {old_path.name} → {new_path.name}")
        old_path.rename(new_path)

    print(f"✅ ローカルリネーム完了（{len(rename_map)}ファイル）")

    return rename_map


def rename_gdrive_file(service, file_id, new_name):
    """
    Google Driveファイルをリネーム

    Args:
        service: Google Drive APIサービス
        file_id: ファイルID
        new_name: 新しいファイル名（拡張子含む）

    Returns:
        更新後のファイル情報
    """
    try:
        file_metadata = {'name': new_name}

        updated_file = service.files().update(
            fileId=file_id,
            body=file_metadata,
            fields='id, name'
        ).execute()

        print(f"✅ Google Driveリネーム完了: {updated_file['name']}")
        return updated_file

    except Exception as e:
        print(f"⚠️  Google Driveリネーム失敗: {e}")
        print(f"  ローカルファイルのリネームは成功しています")
        return None


def main():
    """スタンドアロンテスト用"""
    # コマンドライン引数チェック
    if len(sys.argv) < 2:
        print("使い方: python generate_smart_filename.py <音声ファイルパス>")
        print("\n例: python generate_smart_filename.py downloads/temp_file.m4a")
        print("前提条件: downloads/temp_file_structured.json が存在すること")
        sys.exit(1)

    audio_path = sys.argv[1]
    audio_path_obj = Path(audio_path)

    # ファイル存在チェック
    if not audio_path_obj.exists():
        print(f"❌ エラー: ファイルが見つかりません: {audio_path}")
        sys.exit(1)

    # *_structured.json パスを推測
    json_path = audio_path_obj.parent / f"{audio_path_obj.stem}_structured.json"

    if not json_path.exists():
        print(f"❌ エラー: {json_path} が見つかりません")
        print("先に structured_transcribe.py を実行してください")
        sys.exit(1)

    print("=" * 60)
    print("スマートファイル名生成（Phase 10-1）")
    print("=" * 60)
    print(f"対象ファイル: {audio_path}")
    print(f"JSONファイル: {json_path}")

    # ファイル名生成
    print("\n🤖 Gemini APIで最適なファイル名を生成中...")
    new_name = generate_filename_from_transcription(json_path)
    print(f"\n✨ 提案ファイル名: {new_name}")

    # ユーザー確認
    confirm = input("\nこのファイル名でリネームしますか？ (y/n): ")
    if confirm.lower() != 'y':
        print("❌ キャンセルされました")
        sys.exit(0)

    # リネーム実行
    rename_map = rename_local_files(audio_path, new_name)

    print("\n" + "=" * 60)
    print("🎉 完了!")
    print("=" * 60)
    print(f"新しいパス: {rename_map[audio_path_obj]}")


if __name__ == "__main__":
    main()
