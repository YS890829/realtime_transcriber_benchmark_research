# Project Brief: Voice Memo Transcription & Summarization System (MVP)

## プロジェクト概要

iPhone 17のボイスメモをIntel MacBook Proで取得し、LLMを使って文字起こしと要約を行う**最小構成MVPシステム**を構築する。

## MVP目的（最小限の機能）

- **シンプルな文字起こし**: faster-whisperで正確な文字起こし
- **基本的な要約**: Gemini APIで要約生成
- **手動実行**: スクリプト実行で処理開始（自動監視なし）
- **最小コスト**: 無料・ローカル処理のみ

## ターゲットユーザー

- 会議やインタビューを頻繁に録音するビジネスパーソン
- 講義や研究インタビューを記録する研究者・学生
- ポッドキャストやコンテンツ制作者
- 日常的にボイスメモを活用するユーザー

## MVP コアバリュー

1. **シンプルさ**: 1つのPythonスクリプトで完結
2. **高精度**: faster-whisper mediumで十分な精度
3. **プライバシー**: ローカル処理（faster-whisper）
4. **無料**: Gemini APIフリーティア使用

## MVP 成功基準

- ✅ 新規ボイスメモファイルを検出できる
- ✅ 文字起こしが正常に動作する
- ✅ 要約が生成される
- ✅ TXTとMarkdownファイルに保存される

## MVP実装フェーズ（シンプル化）

### Phase 1: 単一スクリプト実装
**目標**: 1つのPythonファイルで全機能を実装

**実装内容**:
1. ボイスメモフォルダから新規.m4aファイル検出
2. faster-whisperで文字起こし
3. Gemini APIで要約生成
4. TXT + Markdown保存
5. 処理済みリストに記録（`.processed_files.txt`）

**除外した機能**（MVP不要）:
- ❌ watchdog自動監視（手動実行で十分）
- ❌ Whisper API fallback（faster-whisperのみ）
- ❌ Claude API（Gemini APIのみ）
- ❌ リトライロジック（エラーログのみ）
- ❌ 複雑なバッチ処理（シンプルなループ）
- ❌ JSON出力（TXT + Markdownのみ）
- ❌ Strategy Pattern（単純な関数）

## MVP 技術スタック（最小構成）

### 必須ライブラリのみ
```
faster-whisper==1.0.0        # 文字起こし
google-generativeai==0.4.0   # 要約
python-dotenv==1.0.0         # 環境変数
```

### ファイル構成
```
voice-memo-transcriber/
├── .env                    # GEMINI_API_KEY
├── .gitignore
├── requirements.txt
├── transcribe.py           # メインスクリプト（200-300行）
└── .processed_files.txt    # 処理済みリスト
```

### faster-whisper選択理由
- whisper.cppよりIntel CPUで**5倍高速**
- セットアップ簡単（`pip install`のみ）
- 量子化なしでシンプル
- VADフィルタ内蔵

## 制約条件

- Intel MacBook Pro（Apple Silicon非対応）
- Core ML/ANE加速は利用不可
- iCloud同期に依存
- macOS Sonoma (14.x) 以降のみ対応

## MVP リスクと対策

1. **Intel Mac性能**: 処理速度が遅い可能性
   - 対策: mediumモデルで十分高速（60分→4分）
2. **Gemini APIレート制限**: 1日60リクエスト
   - 対策: MVP範囲なら十分

## 次のステップ（MVP）

1. ✅ 技術リサーチ完了
2. ✅ MVP範囲確定
3. ⬜ transcribe.py実装（200-300行）
4. ⬜ requirements.txt作成
5. ⬜ 動作テスト

## 将来の拡張（MVP後）

MVPで不便な場合のみ追加:
- watchdog自動監視
- Whisper API fallback
- バッチ処理最適化
- Web UI
