#!/usr/bin/env python3
"""
Gemini無料枠で1日13時間の録音を処理できるか計算
"""

# === Gemini API Free Tier制限 ===
# https://ai.google.dev/pricing

# 1. Audio API (音声文字起こし)
AUDIO_RPM_FREE = 15  # 15 requests per minute
AUDIO_RPD_FREE = 1500  # 1,500 requests per day

# 2. Text Generation API (話者推論、トピック抽出、エンティティ抽出、要約、名寄せ)
TEXT_RPM_FREE = 15  # 15 requests per minute
TEXT_RPD_FREE = 1500  # 1,500 requests per day

# 3. Embeddings API (Vector DB構築)
EMBEDDING_RPM_FREE = 1500  # 1,500 requests per minute
EMBEDDING_RPD_FREE = 1500  # 1,500 requests per day (注意: embeddingsは制限が厳しい)

print("=" * 70)
print("Gemini無料枠で1日13時間の録音を処理できるか計算")
print("=" * 70)

# === 録音パラメータ ===
DAILY_HOURS = 13  # 1日の録音時間（時間）
SESSIONS = 2  # セッション数（例: 5時間 + 8時間）
DAILY_MINUTES = DAILY_HOURS * 60
DAILY_SECONDS = DAILY_MINUTES * 60

print(f"\n📊 録音パラメータ:")
print(f"   1日の録音時間: {DAILY_HOURS}時間 ({DAILY_MINUTES}分, {DAILY_SECONDS}秒)")
print(f"   セッション数: {SESSIONS}回（例: 5時間 + 8時間）")

# === Phase 8パイプライン処理内容 ===
print(f"\n🔧 Phase 8パイプライン処理:")
print(f"   1. structured_transcribe.py (Audio API)")
print(f"   2. infer_speakers.py (Text Generation API)")
print(f"   3. add_topics_entities.py (Text Generation API)")
print(f"   4. entity_resolution_llm.py (Text Generation API)")
print(f"   5. build_unified_vector_index.py (Embeddings API)")

# === ステップ1: 音声文字起こし (Audio API) ===
print(f"\n" + "=" * 70)
print("Step 1: 音声文字起こし (Audio API)")
print("=" * 70)

# Gemini Audio APIは1ファイル全体を1リクエストで処理
AUDIO_REQUESTS_PER_SESSION = 1
TOTAL_AUDIO_REQUESTS = SESSIONS * AUDIO_REQUESTS_PER_SESSION

print(f"   リクエスト数: {SESSIONS}セッション × {AUDIO_REQUESTS_PER_SESSION}リクエスト/セッション = {TOTAL_AUDIO_REQUESTS}リクエスト")
print(f"   無料枠: {AUDIO_RPD_FREE}リクエスト/日")

if TOTAL_AUDIO_REQUESTS <= AUDIO_RPD_FREE:
    print(f"   ✅ 音声文字起こし: 無料枠内 ({TOTAL_AUDIO_REQUESTS}/{AUDIO_RPD_FREE})")
    audio_ok = True
else:
    print(f"   ❌ 音声文字起こし: 無料枠超過 ({TOTAL_AUDIO_REQUESTS}/{AUDIO_RPD_FREE})")
    audio_ok = False

# セグメント数の推定（10秒に1セグメント）
AVG_SEGMENT_LENGTH_SECONDS = 10
ESTIMATED_SEGMENTS = DAILY_SECONDS // AVG_SEGMENT_LENGTH_SECONDS
print(f"\n   推定セグメント数: {ESTIMATED_SEGMENTS}セグメント（10秒/セグメント想定）")

# === ステップ2: 話者推論 (Text Generation API) ===
print(f"\n" + "=" * 70)
print("Step 2: 話者推論 (Text Generation API)")
print("=" * 70)

# infer_speakers.pyは1ファイル全体を1リクエストで処理
SPEAKER_REQUESTS_PER_SESSION = 1
TOTAL_SPEAKER_REQUESTS = SESSIONS * SPEAKER_REQUESTS_PER_SESSION

print(f"   リクエスト数: {SESSIONS}セッション × {SPEAKER_REQUESTS_PER_SESSION}リクエスト/セッション = {TOTAL_SPEAKER_REQUESTS}リクエスト")
print(f"   無料枠: {TEXT_RPD_FREE}リクエスト/日")

if TOTAL_SPEAKER_REQUESTS <= TEXT_RPD_FREE:
    print(f"   ✅ 話者推論: 無料枠内 ({TOTAL_SPEAKER_REQUESTS}/{TEXT_RPD_FREE})")
    speaker_ok = True
else:
    print(f"   ❌ 話者推論: 無料枠超過 ({TOTAL_SPEAKER_REQUESTS}/{TEXT_RPD_FREE})")
    speaker_ok = False

# === ステップ3: トピック・エンティティ抽出 (Text Generation API) ===
print(f"\n" + "=" * 70)
print("Step 3: トピック・エンティティ抽出 (Text Generation API)")
print("=" * 70)

# add_topics_entities.pyは1ファイル全体を1リクエストで処理
TOPICS_REQUESTS_PER_SESSION = 1
TOTAL_TOPICS_REQUESTS = SESSIONS * TOPICS_REQUESTS_PER_SESSION

print(f"   リクエスト数: {SESSIONS}セッション × {TOPICS_REQUESTS_PER_SESSION}リクエスト/セッション = {TOTAL_TOPICS_REQUESTS}リクエスト")
print(f"   無料枠: {TEXT_RPD_FREE}リクエスト/日")

if TOTAL_TOPICS_REQUESTS <= TEXT_RPD_FREE:
    print(f"   ✅ トピック抽出: 無料枠内 ({TOTAL_TOPICS_REQUESTS}/{TEXT_RPD_FREE})")
    topics_ok = True
else:
    print(f"   ❌ トピック抽出: 無料枠超過 ({TOTAL_TOPICS_REQUESTS}/{TEXT_RPD_FREE})")
    topics_ok = False

# === ステップ4: エンティティ名寄せ (Text Generation API) ===
print(f"\n" + "=" * 70)
print("Step 4: エンティティ名寄せ (Text Generation API)")
print("=" * 70)

# entity_resolution_llm.pyは1日1回（全ファイル統合処理）
ENTITY_RESOLUTION_REQUESTS_PER_DAY = 1

print(f"   リクエスト数: {ENTITY_RESOLUTION_REQUESTS_PER_DAY}リクエスト/日（全ファイル統合処理）")
print(f"   無料枠: {TEXT_RPD_FREE}リクエスト/日")

if ENTITY_RESOLUTION_REQUESTS_PER_DAY <= TEXT_RPD_FREE:
    print(f"   ✅ エンティティ名寄せ: 無料枠内 ({ENTITY_RESOLUTION_REQUESTS_PER_DAY}/{TEXT_RPD_FREE})")
    entity_ok = True
else:
    print(f"   ❌ エンティティ名寄せ: 無料枠超過 ({ENTITY_RESOLUTION_REQUESTS_PER_DAY}/{TEXT_RPD_FREE})")
    entity_ok = False

# === ステップ5: Vector DB構築 (Embeddings API) ===
print(f"\n" + "=" * 70)
print("Step 5: Vector DB構築 (Embeddings API)")
print("=" * 70)

# build_unified_vector_index.pyは100セグメントごとに1バッチリクエスト
BATCH_SIZE = 100
ESTIMATED_EMBEDDING_BATCHES = (ESTIMATED_SEGMENTS + BATCH_SIZE - 1) // BATCH_SIZE
TOTAL_EMBEDDING_REQUESTS = ESTIMATED_EMBEDDING_BATCHES

print(f"   セグメント数: {ESTIMATED_SEGMENTS}セグメント")
print(f"   バッチサイズ: {BATCH_SIZE}セグメント/バッチ")
print(f"   リクエスト数: {TOTAL_EMBEDDING_REQUESTS}リクエスト")
print(f"   無料枠: {EMBEDDING_RPD_FREE}リクエスト/日")

if TOTAL_EMBEDDING_REQUESTS <= EMBEDDING_RPD_FREE:
    print(f"   ✅ Vector DB構築: 無料枠内 ({TOTAL_EMBEDDING_REQUESTS}/{EMBEDDING_RPD_FREE})")
    embedding_ok = True
else:
    print(f"   ❌ Vector DB構築: 無料枠超過 ({TOTAL_EMBEDDING_REQUESTS}/{EMBEDDING_RPD_FREE})")
    embedding_ok = False

# === 合計リクエスト数 ===
print(f"\n" + "=" * 70)
print("合計リクエスト数")
print("=" * 70)

TOTAL_TEXT_REQUESTS = TOTAL_SPEAKER_REQUESTS + TOTAL_TOPICS_REQUESTS + ENTITY_RESOLUTION_REQUESTS_PER_DAY

print(f"   Audio API: {TOTAL_AUDIO_REQUESTS}リクエスト (制限: {AUDIO_RPD_FREE}/日)")
print(f"   Text Generation API: {TOTAL_TEXT_REQUESTS}リクエスト (制限: {TEXT_RPD_FREE}/日)")
print(f"   Embeddings API: {TOTAL_EMBEDDING_REQUESTS}リクエスト (制限: {EMBEDDING_RPD_FREE}/日)")

# === 最終判定 ===
print(f"\n" + "=" * 70)
print("最終判定")
print("=" * 70)

all_ok = audio_ok and speaker_ok and topics_ok and entity_ok and embedding_ok

if all_ok:
    print(f"\n🎉 結論: 1日{DAILY_HOURS}時間の録音を無料枠で処理可能です！")
    print(f"\n✅ すべての処理が無料枠内:")
    print(f"   - Audio API: {TOTAL_AUDIO_REQUESTS}/{AUDIO_RPD_FREE}")
    print(f"   - Text Generation API: {TOTAL_TEXT_REQUESTS}/{TEXT_RPD_FREE}")
    print(f"   - Embeddings API: {TOTAL_EMBEDDING_REQUESTS}/{EMBEDDING_RPD_FREE}")
else:
    print(f"\n⚠️  結論: 1日{DAILY_HOURS}時間の録音は無料枠を超える可能性があります。")
    print(f"\n制限超過の処理:")
    if not audio_ok:
        print(f"   ❌ Audio API: {TOTAL_AUDIO_REQUESTS}/{AUDIO_RPD_FREE}")
    if not (speaker_ok and topics_ok and entity_ok):
        print(f"   ❌ Text Generation API: {TOTAL_TEXT_REQUESTS}/{TEXT_RPD_FREE}")
    if not embedding_ok:
        print(f"   ❌ Embeddings API: {TOTAL_EMBEDDING_REQUESTS}/{EMBEDDING_RPD_FREE}")

# === 追加情報 ===
print(f"\n" + "=" * 70)
print("追加情報")
print("=" * 70)

print(f"\n📝 注意点:")
print(f"   1. 無料枠は1日あたりの制限（24時間でリセット）")
print(f"   2. Embeddings APIは1,500 RPD制限が厳しい")
print(f"   3. セグメント数は10秒/セグメント想定（実際は音声内容により変動）")
print(f"   4. 1ファイルが長すぎる場合、Audio APIのファイルサイズ制限に注意")

print(f"\n💡 推奨運用:")
print(f"   - 1日13時間を2セッション（5時間 + 8時間）に分割")
print(f"   - 各セッション終了後すぐに処理開始")
print(f"   - Vector DB構築は1日1回（夜間など）にまとめる")

print(f"\n🔄 もし無料枠を超えた場合:")
print(f"   - .envで USE_PAID_TIER=true に設定")
print(f"   - 有料枠: 360 RPM, 10,000 RPD（大幅に緩和）")
print(f"   - コスト: 非常に低額（1日数十円程度）")

print(f"\n" + "=" * 70)
