#!/usr/bin/env python3
"""
Phase 10-2: Cloud File Manager
Google Driveの音声ファイルを安全に削除する機能

機能:
1. 削除前検証（JSON完全性チェック）
2. Google Drive API経由での削除
3. 削除ログ記録（.deletion_log.jsonl）
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional


class SafeDeletionValidator:
    """
    削除前検証クラス
    JSON構造化データの完全性を検証してから削除を許可する
    """

    def __init__(self, json_path: Path):
        """
        Args:
            json_path: 検証対象のJSONファイルパス
        """
        self.json_path = json_path
        self.validation_results = {}

    def validate(self) -> bool:
        """
        5項目の完全性チェックを実行

        Returns:
            bool: 全チェック合格ならTrue
        """
        try:
            # 1. ファイル存在チェック
            if not self.json_path.exists():
                self.validation_results['file_exists'] = False
                return False
            self.validation_results['file_exists'] = True

            # 2. ファイルサイズチェック（0バイト以上）
            file_size = self.json_path.stat().st_size
            if file_size == 0:
                self.validation_results['file_size_ok'] = False
                return False
            self.validation_results['file_size_ok'] = True
            self.validation_results['file_size_bytes'] = file_size

            # 3. JSONパース可能性チェック
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.validation_results['json_parseable'] = True

            # 4. segments配列チェック（存在 & 要素数>0）
            segments = data.get('segments', [])
            if not isinstance(segments, list) or len(segments) == 0:
                self.validation_results['segments_ok'] = False
                return False
            self.validation_results['segments_ok'] = True
            self.validation_results['segments_count'] = len(segments)

            # 5. full_textチェック（存在 & 長さ>10文字）
            full_text = data.get('full_text', '')
            if not isinstance(full_text, str) or len(full_text) < 10:
                self.validation_results['full_text_ok'] = False
                return False
            self.validation_results['full_text_ok'] = True
            self.validation_results['full_text_length'] = len(full_text)

            # 6. metadataフィールド存在チェック
            metadata = data.get('metadata', {})
            if not isinstance(metadata, dict):
                self.validation_results['metadata_ok'] = False
                return False
            self.validation_results['metadata_ok'] = True

            # 全チェック合格
            return True

        except json.JSONDecodeError as e:
            self.validation_results['json_parseable'] = False
            self.validation_results['error'] = f"JSON parse error: {str(e)}"
            return False
        except Exception as e:
            self.validation_results['error'] = str(e)
            return False

    def get_validation_details(self) -> Dict:
        """
        検証結果の詳細を取得

        Returns:
            dict: 検証結果の詳細
        """
        return self.validation_results


def delete_gdrive_file(service, file_id: str, file_name: str) -> bool:
    """
    Google Driveファイルを削除

    Args:
        service: Google Drive API service object
        file_id: 削除対象のファイルID
        file_name: ファイル名（ログ用）

    Returns:
        bool: 削除成功ならTrue

    Raises:
        Exception: API呼び出し失敗時
    """
    try:
        service.files().delete(fileId=file_id).execute()
        print(f"  ✅ Google Drive file deleted: {file_id}", flush=True)
        return True
    except Exception as e:
        print(f"  ❌ Google Drive deletion failed: {e}", flush=True)
        raise


def log_deletion(file_info: Dict, validation_results: Dict, deleted: bool, error: Optional[str] = None):
    """
    削除イベントをログファイルに記録（JSONL形式）

    Args:
        file_info: ファイル情報（file_id, file_name, json_path等）
        validation_results: 検証結果の詳細
        deleted: 削除成功フラグ
        error: エラーメッセージ（失敗時）
    """
    log_file = Path(os.getenv('DELETION_LOG_FILE', '.deletion_log.jsonl'))

    # ログエントリ作成
    log_entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'file_id': file_info.get('file_id'),
        'file_name': file_info.get('file_name'),
        'original_name': file_info.get('original_name'),
        'json_path': str(file_info.get('json_path', '')),
        'validation_passed': validation_results.get('file_exists', False) and
                           validation_results.get('segments_ok', False) and
                           validation_results.get('full_text_ok', False),
        'validation_details': validation_results,
        'deleted': deleted,
        'error': error
    }

    # JSONL形式で追記
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    print(f"  📝 Deletion log recorded: {log_file}", flush=True)


def get_file_size_mb(service, file_id: str) -> Optional[float]:
    """
    Google Driveファイルのサイズを取得（MB単位）

    Args:
        service: Google Drive API service object
        file_id: ファイルID

    Returns:
        float: ファイルサイズ（MB）、取得失敗時はNone
    """
    try:
        file_metadata = service.files().get(fileId=file_id, fields='size').execute()
        size_bytes = int(file_metadata.get('size', 0))
        return round(size_bytes / (1024 * 1024), 2)
    except Exception:
        return None


if __name__ == "__main__":
    # テスト用コード
    import sys

    if len(sys.argv) < 2:
        print("Usage: python cloud_file_manager.py <json_path>")
        sys.exit(1)

    json_path = Path(sys.argv[1])

    print(f"Validating: {json_path}")
    validator = SafeDeletionValidator(json_path)

    if validator.validate():
        print("✅ Validation PASSED")
        print(json.dumps(validator.get_validation_details(), indent=2, ensure_ascii=False))
    else:
        print("❌ Validation FAILED")
        print(json.dumps(validator.get_validation_details(), indent=2, ensure_ascii=False))
        sys.exit(1)
