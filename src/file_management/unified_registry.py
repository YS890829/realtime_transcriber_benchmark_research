#!/usr/bin/env python3
"""
Phase 10-3: 統合ファイルレジストリ（関数ベース）- ファイル名ベース重複管理

Google Drive + iCloud Drive両方の処理履歴を一元管理
- ユーザー表示名（user_display_name）で重複検知
- file_id ↔ ファイル名マッピング
- JSONL形式で追記型ログ
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# 設定
REGISTRY_FILE = Path(os.getenv('PROCESSED_FILES_REGISTRY', '.processed_files_registry.jsonl'))

# グローバルキャッシュ
_registry_cache = {}  # {user_display_name: entry}
_cache_loaded = False


def _load_registry_cache():
    """レジストリをメモリキャッシュにロード"""
    global _registry_cache, _cache_loaded

    if _cache_loaded:
        return

    _registry_cache = {}

    if not REGISTRY_FILE.exists():
        _cache_loaded = True
        return

    try:
        with open(REGISTRY_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                entry = json.loads(line)
                if 'user_display_name' in entry and entry['user_display_name']:
                    _registry_cache[entry['user_display_name']] = entry

        _cache_loaded = True
    except Exception as e:
        print(f"[Warning] Failed to load registry: {e}")
        _cache_loaded = True


def is_processed(user_display_name: str) -> bool:
    """
    ユーザー表示名で処理済みチェック

    Args:
        user_display_name: ユーザー設定の表示名（拡張子なし）

    Returns:
        bool: 処理済みならTrue
    """
    _load_registry_cache()
    return user_display_name in _registry_cache


def get_by_display_name(user_display_name: str) -> Optional[Dict[str, Any]]:
    """
    ユーザー表示名でレジストリエントリ取得

    Args:
        user_display_name: ユーザー設定の表示名（拡張子なし）

    Returns:
        dict or None: レジストリエントリ、存在しなければNone
    """
    _load_registry_cache()
    return _registry_cache.get(user_display_name)


def get_by_file_id(file_id: str) -> Optional[Dict[str, Any]]:
    """
    Google Drive file_idでレジストリエントリ取得

    Args:
        file_id: Google DriveのファイルID

    Returns:
        dict or None: レジストリエントリ、存在しなければNone
    """
    _load_registry_cache()

    for entry in _registry_cache.values():
        if entry.get('file_id') == file_id:
            return entry

    return None


def search(file_id: Optional[str] = None,
          original_name: Optional[str] = None,
          user_display_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    柔軟な検索

    Args:
        file_id: Google DriveのファイルID（オプション）
        original_name: オリジナルファイル名（オプション）
        user_display_name: ユーザー表示名（オプション）

    Returns:
        dict or None: レジストリエントリ、存在しなければNone
    """
    _load_registry_cache()

    for entry in _registry_cache.values():
        if file_id and entry.get('file_id') == file_id:
            return entry
        if original_name and entry.get('original_name') == original_name:
            return entry
        if user_display_name and entry.get('user_display_name') == user_display_name:
            return entry

    return None


def add_to_registry(source: str,
                   original_name: str,
                   user_display_name: str,
                   renamed_to: Optional[str] = None,
                   file_id: Optional[str] = None,
                   local_path: Optional[str] = None):
    """
    新規エントリをレジストリに追加

    Args:
        source: ファイルソース（'google_drive' or 'icloud_drive'）
        original_name: オリジナルファイル名
        user_display_name: ユーザー設定の表示名（拡張子なし）
        renamed_to: リネーム後のファイル名（オプション）
        file_id: Google DriveファイルID（Google Driveのみ）
        local_path: ローカルファイルパス（オプション）
    """
    _load_registry_cache()

    entry = {
        'source': source,
        'file_id': file_id,
        'user_display_name': user_display_name,
        'original_name': original_name,
        'renamed_to': renamed_to,
        'local_path': local_path,
        'processed_at': datetime.now(timezone.utc).isoformat()
    }

    # メモリキャッシュ更新
    _registry_cache[user_display_name] = entry

    # ファイルに追記（JSONL形式）
    with open(REGISTRY_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def update_renamed(user_display_name: str, renamed_to: str):
    """
    リネーム後のファイル名を更新

    Args:
        user_display_name: ユーザー設定の表示名
        renamed_to: リネーム後のファイル名
    """
    _load_registry_cache()

    if user_display_name not in _registry_cache:
        print(f"[Warning] Display name not found in registry: {user_display_name}")
        return

    # メモリキャッシュ更新
    _registry_cache[user_display_name]['renamed_to'] = renamed_to

    # JSONL全体を再書き込み
    _rewrite_registry()


def _rewrite_registry():
    """レジストリ全体を再書き込み（更新用）"""
    try:
        with open(REGISTRY_FILE, 'w', encoding='utf-8') as f:
            for entry in _registry_cache.values():
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"[Error] Failed to rewrite registry: {e}")


def get_stats() -> Dict[str, Any]:
    """
    レジストリ統計情報取得

    Returns:
        dict: 統計情報（総件数、Google Drive件数、iCloud件数）
    """
    _load_registry_cache()

    total = len(_registry_cache)
    google_drive = sum(1 for e in _registry_cache.values() if e.get('source') == 'google_drive')
    icloud_drive = sum(1 for e in _registry_cache.values() if e.get('source') == 'icloud_drive')

    return {
        'total': total,
        'google_drive': google_drive,
        'icloud_drive': icloud_drive
    }


if __name__ == "__main__":
    # テスト用コード
    import sys

    if len(sys.argv) < 2:
        print("Usage: python unified_registry.py <display_name>")
        print("\nTest: Check if display name is processed")
        sys.exit(1)

    display_name = sys.argv[1]

    print(f"Checking display name: {display_name}")

    if is_processed(display_name):
        entry = get_by_display_name(display_name)
        print(f"\n✅ Already processed:")
        print(f"  Source: {entry.get('source')}")
        print(f"  Original: {entry.get('original_name')}")
        print(f"  Renamed: {entry.get('renamed_to')}")
        print(f"  Processed at: {entry.get('processed_at')}")
    else:
        print(f"\n❌ Not processed yet")

    # 統計表示
    stats = get_stats()
    print(f"\nRegistry stats:")
    print(f"  Total: {stats['total']}")
    print(f"  Google Drive: {stats['google_drive']}")
    print(f"  iCloud Drive: {stats['icloud_drive']}")
