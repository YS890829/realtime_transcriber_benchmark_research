#!/usr/bin/env python3
"""
Phase 10-3: iCloud Drive Monitor (watchdog based)

iCloud Driveの音声ファイルを自動検知して文字起こし処理を実行
- watchdogライブラリでリアルタイム検知
- ファイル安定待機（iCloud同期完了確認）
- CloudRecordings.dbからユーザー表示名取得
- ファイル名ベース重複検知
- 統合レジストリと連携
"""

import os
import sys
import time
import subprocess
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# 自作モジュール
from src.file_management import unified_registry as registry

# 設定
ICLOUD_PATH = Path(os.getenv('ICLOUD_DRIVE_PATH',
                             '~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings')).expanduser()
DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', 'downloads'))
CLOUD_RECORDINGS_DB = ICLOUD_PATH / 'CloudRecordings.db'
AUDIO_EXTENSIONS = {'.m4a', '.mp3', '.wav', '.aac', '.flac', '.ogg', '.qta'}
FILE_STABILITY_WAIT = 5  # 秒（ファイルサイズ変化なし確認）
FILE_STABILITY_CHECK_INTERVAL = 2  # 秒（サイズチェック間隔）


def get_user_display_name(file_path: Path) -> Optional[str]:
    """
    CloudRecordings.dbからユーザー設定の表示名を取得

    Args:
        file_path: ボイスメモファイルのパス（実ファイル名）

    Returns:
        Optional[str]: ユーザー表示名（拡張子なし）、取得失敗時はNone
    """
    try:
        if not CLOUD_RECORDINGS_DB.exists():
            print(f"  ⚠️ CloudRecordings.db not found: {CLOUD_RECORDINGS_DB}", flush=True)
            return None

        conn = sqlite3.connect(str(CLOUD_RECORDINGS_DB))
        cursor = conn.cursor()

        # ZPATHから ZENCRYPTEDTITLE を取得
        cursor.execute(
            "SELECT ZENCRYPTEDTITLE FROM ZCLOUDRECORDING WHERE ZPATH = ?",
            (file_path.name,)
        )

        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            display_name = result[0]
            print(f"  📝 User display name: {display_name}", flush=True)
            return display_name
        else:
            # データベースに見つからない場合はファイル名を使用（拡張子なし）
            print(f"  ⚠️ Display name not found in DB, using filename", flush=True)
            return file_path.stem

    except Exception as e:
        print(f"  ⚠️ Failed to get display name from DB: {e}", flush=True)
        # エラー時はファイル名を使用（拡張子なし）
        return file_path.stem


class AudioFileHandler(FileSystemEventHandler):
    """
    音声ファイル作成イベントを処理するハンドラ
    """

    def on_created(self, event):
        """
        ファイル作成イベント処理

        Args:
            event: watchdogのFileSystemEvent
        """
        # ディレクトリは無視
        if event.is_directory:
            return

        # FileCreatedEventのみ処理
        if not isinstance(event, FileCreatedEvent):
            return

        file_path = Path(event.src_path)

        # 拡張子チェック
        if file_path.suffix.lower() not in AUDIO_EXTENSIONS:
            return

        # 隠しファイル除外
        if file_path.name.startswith('.'):
            return

        print(f"\n🔔 New audio file detected: {file_path.name}", flush=True)

        # 非同期処理（別スレッドでファイル処理）
        process_new_audio_file(file_path)


def wait_for_file_stability(file_path: Path,
                            stability_duration: int = FILE_STABILITY_WAIT,
                            check_interval: int = FILE_STABILITY_CHECK_INTERVAL) -> bool:
    """
    ファイルサイズが安定するまで待機（iCloud同期完了確認）

    Args:
        file_path: 監視対象ファイル
        stability_duration: 安定判定までの待機時間（秒）
        check_interval: サイズチェック間隔（秒）

    Returns:
        bool: 安定化成功ならTrue、タイムアウトならFalse
    """
    print(f"  ⏳ Waiting for file stability (iCloud sync)...", flush=True)

    max_wait = 300  # 最大5分
    elapsed = 0
    last_size = -1
    stable_duration = 0

    while elapsed < max_wait:
        if not file_path.exists():
            time.sleep(check_interval)
            elapsed += check_interval
            continue

        try:
            current_size = file_path.stat().st_size

            if current_size == last_size and current_size > 0:
                stable_duration += check_interval

                if stable_duration >= stability_duration:
                    print(f"  ✅ File stable: {current_size:,} bytes", flush=True)
                    return True
            else:
                # サイズ変化検知 → 安定カウンターリセット
                if last_size != -1:
                    print(f"  📊 Size changed: {last_size:,} → {current_size:,} bytes", flush=True)
                stable_duration = 0
                last_size = current_size

            time.sleep(check_interval)
            elapsed += check_interval

        except Exception as e:
            print(f"  ⚠️ File check error: {e}", flush=True)
            time.sleep(check_interval)
            elapsed += check_interval

    print(f"  ❌ File stability timeout ({max_wait}s)", flush=True)
    return False


def process_new_audio_file(file_path: Path):
    """
    新規音声ファイルの処理メインフロー

    Args:
        file_path: 処理対象ファイル（iCloudボイスメモフォルダ内）
    """
    copied_file = None
    converted_file = None

    try:
        # 1. ファイル安定待機
        if not wait_for_file_stability(file_path):
            print(f"  ⚠️ Skipping unstable file: {file_path.name}", flush=True)
            return

        # 2. downloadsフォルダにコピー
        DOWNLOAD_DIR.mkdir(exist_ok=True)
        copied_file = DOWNLOAD_DIR / file_path.name
        print(f"  📋 Copying to downloads folder...", flush=True)
        shutil.copy2(file_path, copied_file)
        print(f"  ✅ Copied: {copied_file}", flush=True)

        # 3. CloudRecordings.dbからユーザー表示名を取得
        print(f"  📝 Getting user display name from CloudRecordings.db...", flush=True)
        user_display_name = get_user_display_name(file_path)

        if not user_display_name:
            print(f"  ⚠️ Could not get user display name, using filename", flush=True)
            user_display_name = file_path.stem

        # 4. 重複チェック（ユーザー表示名ベース）
        if registry.is_processed(user_display_name):
            existing = registry.get_by_display_name(user_display_name)
            print(f"  ⚠️ DUPLICATE DETECTED - Already processed:", flush=True)
            print(f"    Source: {existing.get('source')}", flush=True)
            print(f"    Original: {existing.get('original_name')}", flush=True)
            print(f"    Display name: {user_display_name}", flush=True)
            print(f"    Processed at: {existing.get('processed_at')}", flush=True)
            print(f"  ➡️ Skipping transcription", flush=True)

            # 重複の場合はコピーしたファイルと元ファイルを削除
            if copied_file and copied_file.exists():
                copied_file.unlink()
            if file_path.exists():
                file_path.unlink()
                print(f"  🗑️ Deleted original from Voice Memos folder", flush=True)
            return

        # 5. レジストリ登録（処理前）
        print(f"  📝 Registering to unified registry...", flush=True)
        registry.add_to_registry(
            source='icloud_drive',
            original_name=file_path.name,
            user_display_name=user_display_name,
            renamed_to=None,  # Phase 10-1で更新される
            file_id=None,     # iCloudにはfile_id概念なし
            local_path=str(copied_file)  # downloadsフォルダのパス
        )

        # 6. 文字起こし処理実行（downloadsフォルダのファイルで）
        print(f"  🎙️ Starting transcription...", flush=True)
        converted_file = transcribe_audio_file(copied_file, user_display_name)

        # 7. ボイスメモフォルダのファイル削除
        print(f"  🗑️ Cleaning up Voice Memos folder...", flush=True)

        # 7-1. 元の.qtaファイル削除
        if file_path.exists():
            file_path.unlink()
            print(f"    ✓ Deleted original .qta", flush=True)

        # 7-2. 変換後の.m4aファイル削除（ボイスメモフォルダに残っている場合）
        original_m4a = file_path.with_suffix('.m4a')
        if original_m4a.exists():
            original_m4a.unlink()
            print(f"    ✓ Deleted converted .m4a", flush=True)

        # 7-3. JSONファイル削除（ボイスメモフォルダに作成された場合）
        # Phase 10-1でリネーム前後のJSONファイルを探して削除
        voice_memo_dir = file_path.parent
        for json_file in voice_memo_dir.glob("*.json"):
            # 同じタイムスタンプのJSONファイルを削除
            if json_file.stem.startswith(file_path.stem[:15]):  # "20251016 101544"部分でマッチ
                json_file.unlink()
                print(f"    ✓ Deleted JSON: {json_file.name}", flush=True)

        # 8. 完了ログ
        print(f"  ✅ iCloud file processing completed: {file_path.name}", flush=True)
        print(f"  📁 All files saved to: downloads/", flush=True)

    except Exception as e:
        print(f"  ❌ Error processing file: {e}", flush=True)
        import traceback
        traceback.print_exc()


def convert_qta_to_m4a(qta_path: Path) -> Path:
    """
    .qtaファイルを.m4aに変換（同じディレクトリ内）

    Args:
        qta_path: .qtaファイルパス

    Returns:
        Path: 変換後の.m4aファイルパス
    """
    m4a_path = qta_path.with_suffix('.m4a')

    print(f"  🔄 Converting .qta to .m4a...", flush=True)

    cmd = [
        'ffmpeg',
        '-i', str(qta_path),
        '-c:a', 'aac',  # AACコーデック
        '-b:a', '128k',  # ビットレート
        '-y',  # 上書き
        str(m4a_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"FFmpeg conversion failed: {result.stderr}")

    print(f"  ✅ Converted: {m4a_path.name}", flush=True)

    # 元の.qtaファイルを削除（downloadsフォルダ内の）
    if qta_path.exists():
        qta_path.unlink()
        print(f"  🗑️ Deleted .qta file from downloads: {qta_path.name}", flush=True)

    return m4a_path


def transcribe_audio_file(file_path: Path, user_display_name: str) -> Optional[Path]:
    """
    structured_transcribe.pyを呼び出して文字起こし実行

    Args:
        file_path: 音声ファイルパス（downloadsフォルダ内）
        user_display_name: ユーザー表示名（レジストリ更新用）

    Returns:
        Optional[Path]: 変換後のファイルパス（.qta→.m4aの場合）
    """
    converted_file = None

    try:
        # .qta形式の場合は.m4aに変換
        actual_file_path = file_path
        if file_path.suffix.lower() == '.qta':
            converted_file = convert_qta_to_m4a(file_path)
            actual_file_path = converted_file

        # structured_transcribe.py実行
        cmd = [
            sys.executable,  # 現在のPythonインタプリタ
            '-m',
            'src.transcription.structured_transcribe',
            str(actual_file_path)
        ]

        print(f"  💬 Executing: {' '.join(cmd)}", flush=True)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=os.environ.copy(),  # 環境変数を継承
            timeout=3600  # 1時間タイムアウト
        )

        if result.returncode == 0:
            print(f"  ✅ Transcription successful", flush=True)

            # Phase 11-3のログ出力を表示
            if "Phase 11-3" in result.stdout:
                print("\n" + "=" * 70, flush=True)
                print("📊 Phase 11-3 実行ログ:", flush=True)
                print("=" * 70, flush=True)
                # Phase 11-3セクションのみ抽出して表示
                for line in result.stdout.split('\n'):
                    if 'Phase 11-3' in line or 'Step' in line or 'Meeting ID' in line or '✓' in line or '⏭' in line:
                        print(f"  {line}", flush=True)
                print("=" * 70 + "\n", flush=True)

            # Phase 10-1でリネームされた可能性があるのでレジストリ更新
            # （structured_transcribe.py内でgenerate_smart_filenameが呼ばれる）
            update_registry_after_rename(actual_file_path, user_display_name)
        else:
            print(f"  ❌ Transcription failed (exit code: {result.returncode})", flush=True)
            print(f"  stderr: {result.stderr}", flush=True)

        return converted_file

    except subprocess.TimeoutExpired:
        print(f"  ❌ Transcription timeout (>1 hour)", flush=True)
        return converted_file
    except Exception as e:
        print(f"  ❌ Transcription error: {e}", flush=True)
        return converted_file


def update_registry_after_rename(original_path: Path, user_display_name: str):
    """
    Phase 10-1によるリネーム後、レジストリを更新

    Args:
        original_path: オリジナルファイルパス
        user_display_name: ユーザー表示名
    """
    try:
        # リネーム後のファイル名を探す
        # Phase 10-1は同じディレクトリ内でリネームする
        parent_dir = original_path.parent

        # 元のファイルが存在しない = リネームされた可能性
        if not original_path.exists():
            # 同じディレクトリ内で最新の音声ファイルを探す
            audio_files = sorted(
                [f for f in parent_dir.glob('*') if f.suffix.lower() in AUDIO_EXTENSIONS],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            if audio_files:
                renamed_file = audio_files[0]
                print(f"  📝 Updating registry with renamed file: {renamed_file.name}", flush=True)
                registry.update_renamed(user_display_name, renamed_file.name)

    except Exception as e:
        print(f"  ⚠️ Registry update error (non-critical): {e}", flush=True)


def start_monitoring():
    """
    iCloud Drive監視を開始
    """
    # 環境変数チェック
    if os.getenv('ENABLE_ICLOUD_MONITORING', 'false').lower() != 'true':
        print("⚠️ iCloud monitoring is DISABLED")
        print("   Set ENABLE_ICLOUD_MONITORING=true in .env to enable")
        return

    # iCloudパス存在チェック
    if not ICLOUD_PATH.exists():
        print(f"❌ iCloud Drive path not found: {ICLOUD_PATH}")
        print("   Please check ICLOUD_DRIVE_PATH in .env")
        return

    print("=" * 60)
    print("🚀 iCloud Drive Monitor Started (Phase 10-3)")
    print("=" * 60)
    print(f"📁 Monitoring path: {ICLOUD_PATH}")
    print(f"🎵 Audio extensions: {', '.join(AUDIO_EXTENSIONS)}")
    print(f"⏱️  File stability wait: {FILE_STABILITY_WAIT}s")
    print(f"📊 Registry stats: {registry.get_stats()}")
    print("=" * 60)
    print("Press Ctrl+C to stop monitoring\n")

    # watchdog設定
    event_handler = AudioFileHandler()
    observer = Observer()
    observer.schedule(event_handler, str(ICLOUD_PATH), recursive=True)

    try:
        observer.start()
        print("✅ Monitoring active...\n", flush=True)

        # メインループ
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping iCloud monitor...", flush=True)
        observer.stop()
        observer.join()
        print("✅ Monitor stopped gracefully", flush=True)

    except Exception as e:
        print(f"\n❌ Monitor error: {e}", flush=True)
        observer.stop()
        observer.join()


if __name__ == "__main__":
    start_monitoring()
