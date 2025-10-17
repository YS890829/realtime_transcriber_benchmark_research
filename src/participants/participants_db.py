#!/usr/bin/env python3
"""
Phase 11-3: 参加者データベース操作API
作成日: 2025-10-16

このモジュールは、参加者情報を管理するSQLiteデータベースのCRUD操作を提供します。
"""

import sqlite3
import json
import uuid
import os
from datetime import datetime
from typing import List, Dict, Optional


class ParticipantsDB:
    """参加者データベース操作クラス"""

    def __init__(self, db_path: str = "data/participants.db"):
        """
        データベース初期化

        Args:
            db_path: データベースファイルパス
        """
        self.db_path = db_path
        self._ensure_data_directory()
        self._init_db()

    def _ensure_data_directory(self):
        """dataディレクトリが存在することを確認"""
        data_dir = os.path.dirname(self.db_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)

    def _init_db(self):
        """データベース初期化（スキーマ作成）"""
        conn = sqlite3.connect(self.db_path)

        # SQLファイルからスキーマを読み込んで実行
        import os
        sql_path = os.path.join(os.path.dirname(__file__), "participants_db.sql")
        with open(sql_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
            conn.executescript(schema_sql)

        conn.close()

    def upsert_participant(
        self,
        canonical_name: str,
        display_names: List[str] = None,
        organization: str = None,
        role: str = None,
        email: str = None,
        notes: str = None
    ) -> str:
        """
        参加者情報を新規作成または更新（UPSERT）

        Args:
            canonical_name: 正規化名（必須）
            display_names: 表記バリエーションリスト
            organization: 組織名
            role: 役職
            email: メールアドレス
            notes: メモ

        Returns:
            participant_id: 参加者ID（UUID）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 既存参加者を検索
        cursor.execute(
            "SELECT participant_id, display_names, notes, meeting_count FROM participants WHERE canonical_name = ?",
            (canonical_name,)
        )
        existing = cursor.fetchone()

        if existing:
            # UPDATE: 既存参加者の情報更新
            participant_id, existing_names, existing_notes, meeting_count = existing

            # display_names のマージ（重複排除）
            existing_names_list = json.loads(existing_names) if existing_names else []
            if display_names:
                merged_names = list(set(existing_names_list + display_names))
            else:
                merged_names = existing_names_list

            # notes の追記
            if notes and existing_notes:
                merged_notes = f"{existing_notes}\n[{datetime.now().isoformat()}] {notes}"
            elif notes:
                merged_notes = notes
            else:
                merged_notes = existing_notes

            cursor.execute("""
                UPDATE participants
                SET display_names = ?,
                    organization = COALESCE(?, organization),
                    role = COALESCE(?, role),
                    email = COALESCE(?, email),
                    notes = ?,
                    updated_at = ?
                WHERE participant_id = ?
            """, (
                json.dumps(merged_names, ensure_ascii=False),
                organization,
                role,
                email,
                merged_notes,
                datetime.now().isoformat(),
                participant_id
            ))
        else:
            # INSERT: 新規参加者作成
            participant_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO participants (
                    participant_id, canonical_name, display_names,
                    organization, role, email, notes,
                    meeting_count, first_seen_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                participant_id,
                canonical_name,
                json.dumps(display_names or [canonical_name], ensure_ascii=False),
                organization,
                role,
                email,
                notes,
                0,  # meeting_count
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

        conn.commit()
        conn.close()
        return participant_id

    def get_participant_info(self, canonical_name: str) -> Optional[Dict]:
        """
        参加者の情報を取得

        Args:
            canonical_name: 正規化名

        Returns:
            参加者情報の辞書、存在しない場合はNone
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT participant_id, canonical_name, display_names, organization,
                   role, email, notes, meeting_count, first_seen_at, updated_at
            FROM participants
            WHERE canonical_name = ?
        """, (canonical_name,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "participant_id": row[0],
            "canonical_name": row[1],
            "display_names": json.loads(row[2]) if row[2] else [],
            "organization": row[3],
            "role": row[4],
            "email": row[5],
            "notes": row[6],
            "meeting_count": row[7],
            "first_seen_at": row[8],
            "updated_at": row[9]
        }

    def register_meeting(
        self,
        structured_file_path: str,
        meeting_date: str,
        meeting_title: str,
        calendar_event_id: str = None,
        participants: List[str] = None
    ) -> str:
        """
        会議を登録し、参加者とのリレーションを作成

        Args:
            structured_file_path: 構造化JSONファイルパス
            meeting_date: 会議日（YYYY-MM-DD形式）
            meeting_title: 会議タイトル
            calendar_event_id: カレンダーイベントID
            participants: 参加者のcanonical_nameリスト

        Returns:
            meeting_id: 会議ID（UUID）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        meeting_id = str(uuid.uuid4())

        # 会議を登録
        cursor.execute("""
            INSERT INTO meetings (meeting_id, structured_file_path, calendar_event_id, meeting_date, meeting_title)
            VALUES (?, ?, ?, ?, ?)
        """, (meeting_id, structured_file_path, calendar_event_id, meeting_date, meeting_title))

        # 参加者との関係を登録 + meeting_count更新
        if participants:
            for canonical_name in participants:
                cursor.execute(
                    "SELECT participant_id FROM participants WHERE canonical_name = ?",
                    (canonical_name,)
                )
                result = cursor.fetchone()
                if result:
                    participant_id = result[0]

                    # 中間テーブルに登録
                    cursor.execute("""
                        INSERT OR IGNORE INTO participant_meetings (participant_id, meeting_id, attended_at)
                        VALUES (?, ?, ?)
                    """, (participant_id, meeting_id, datetime.now().isoformat()))

                    # meeting_count をインクリメント
                    cursor.execute("""
                        UPDATE participants
                        SET meeting_count = meeting_count + 1
                        WHERE participant_id = ?
                    """, (participant_id,))

        conn.commit()
        conn.close()
        return meeting_id

    def get_participant_meeting_history(self, canonical_name: str, limit: int = 10) -> List[Dict]:
        """
        参加者の会議履歴を取得

        Args:
            canonical_name: 正規化名
            limit: 取得する会議数の上限

        Returns:
            会議履歴のリスト（最新順）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT m.meeting_date, m.meeting_title, m.structured_file_path, pm.attended_at
            FROM participants p
            JOIN participant_meetings pm ON p.participant_id = pm.participant_id
            JOIN meetings m ON pm.meeting_id = m.meeting_id
            WHERE p.canonical_name = ?
            ORDER BY m.meeting_date DESC
            LIMIT ?
        """, (canonical_name, limit))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "meeting_date": row[0],
                "meeting_title": row[1],
                "structured_file_path": row[2],
                "attended_at": row[3]
            }
            for row in rows
        ]


if __name__ == "__main__":
    # 簡単な動作確認
    print("=== ParticipantsDB 動作確認 ===")

    # データベース初期化
    db = ParticipantsDB()
    print("✓ データベース初期化完了")

    # 新規参加者登録
    participant_id = db.upsert_participant(
        canonical_name="田中",
        display_names=["田中", "田中部長"],
        organization="営業部",
        role="部長"
    )
    print(f"✓ 新規参加者登録: {participant_id}")

    # 参加者情報取得
    info = db.get_participant_info("田中")
    print(f"✓ 参加者情報取得: {info}")

    # 既存参加者更新
    db.upsert_participant(
        canonical_name="田中",
        display_names=["田中さん"],
        notes="テスト会議に参加"
    )
    print("✓ 既存参加者更新")

    # 更新後の情報取得
    info = db.get_participant_info("田中")
    print(f"✓ 更新後の情報: display_names={info['display_names']}, notes={info['notes']}")

    # 会議登録
    meeting_id = db.register_meeting(
        structured_file_path="test_structured.json",
        meeting_date="2025-01-15",
        meeting_title="テスト会議",
        participants=["田中"]
    )
    print(f"✓ 会議登録: {meeting_id}")

    # 会議履歴取得
    history = db.get_participant_meeting_history("田中")
    print(f"✓ 会議履歴取得: {len(history)}件")

    # meeting_count確認
    info = db.get_participant_info("田中")
    print(f"✓ meeting_count: {info['meeting_count']}")

    print("\n=== すべてのテスト成功 ===")
