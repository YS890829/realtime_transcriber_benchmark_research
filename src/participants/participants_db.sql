-- Phase 11-3: 参加者データベーススキーマ定義
-- 作成日: 2025-10-16

-- 参加者マスタテーブル
CREATE TABLE IF NOT EXISTS participants (
    participant_id TEXT PRIMARY KEY,       -- UUID
    canonical_name TEXT NOT NULL,          -- 正規化名（例: "田中太郎"）
    display_names TEXT,                    -- JSON配列: ["田中", "田中部長", "田中さん"]
    organization TEXT,                     -- 組織名
    role TEXT,                             -- 役職
    email TEXT,                            -- メールアドレス（任意）
    notes TEXT,                            -- フリーテキストメモ（追記型）
    meeting_count INTEGER DEFAULT 0,       -- 参加会議数
    first_seen_at TIMESTAMP,               -- 初登場日時
    updated_at TIMESTAMP,                  -- 最終更新日時
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会議マスタテーブル
CREATE TABLE IF NOT EXISTS meetings (
    meeting_id TEXT PRIMARY KEY,           -- UUID
    structured_file_path TEXT NOT NULL,    -- 構造化JSONファイルパス
    calendar_event_id TEXT,                -- カレンダーイベントID
    meeting_date DATE NOT NULL,            -- 会議日
    meeting_title TEXT,                    -- 会議タイトル
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 参加者-会議の中間テーブル
CREATE TABLE IF NOT EXISTS participant_meetings (
    participant_id TEXT,
    meeting_id TEXT,
    attended_at TIMESTAMP,
    PRIMARY KEY (participant_id, meeting_id),
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id) ON DELETE CASCADE,
    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id) ON DELETE CASCADE
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_participants_canonical_name ON participants(canonical_name);
CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(meeting_date);
CREATE INDEX IF NOT EXISTS idx_participant_meetings_participant ON participant_meetings(participant_id);
CREATE INDEX IF NOT EXISTS idx_participant_meetings_meeting ON participant_meetings(meeting_id);
