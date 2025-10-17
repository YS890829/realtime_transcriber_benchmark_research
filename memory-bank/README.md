# Memory Bank

このフォルダは、Claude Code（AIアシスタント）がプロジェクトのコンテキストを理解し、セッション間で一貫性を保つための記憶システムです。

Clineの[Memory Bank](https://docs.cline.bot/prompting/cline-memory-bank)手法を採用しています。

## 📁 ファイル構成

### 核心ファイル（必須）

#### 1. [projectbrief.md](projectbrief.md) - プロジェクトの基盤
- **目的**: プロジェクトの核心的な問題と解決策
- **内容**:
  - 何を作っているか
  - なぜ作っているか
  - 誰のためか
  - 成功の定義
- **更新頻度**: プロジェクト開始時のみ（基本変更なし）

#### 2. [productContext.md](productContext.md) - プロダクトの価値
- **目的**: ユーザー体験とプロダクトの価値提案
- **内容**:
  - ユースケース
  - ユーザーフロー
  - 主要機能
  - UI/UX要件
- **更新頻度**: 機能追加時

#### 3. [systemPatterns.md](systemPatterns.md) - システム設計
- **目的**: アーキテクチャと技術的決定の記録
- **内容**:
  - システムアーキテクチャ
  - デザインパターン
  - 主要な技術的決定
  - コンポーネント関係
- **更新頻度**: アーキテクチャ変更時

#### 4. [techContext.md](techContext.md) - 技術スタック
- **目的**: 開発環境と技術的制約
- **内容**:
  - 使用技術・ライブラリ
  - 開発環境セットアップ
  - API制限・制約
  - 既知の技術的課題
- **更新頻度**: 依存関係変更時

#### 5. [activeContext.md](activeContext.md) - 現在の作業
- **目的**: 今何をしているか、次に何をするか
- **内容**:
  - 現在の作業フォーカス
  - 最近の変更
  - 次のステップ
  - アクティブな決定・考慮事項
  - ブロッカー・課題
- **更新頻度**: 毎セッション

#### 6. [progress.md](progress.md) - 進捗状況
- **目的**: 何ができて、何が残っているか
- **内容**:
  - 完了済みPhase
  - 進行中Phase
  - 予定Phase
  - 既知の問題
  - メトリクス
- **更新頻度**: タスク完了時

## 🔄 ファイルの依存関係

```
projectbrief.md (基盤)
    ↓
    ├── productContext.md (プロダクト価値)
    ├── systemPatterns.md (設計)
    └── techContext.md (技術)
          ↓
          ├── activeContext.md (現在の作業)
          └── progress.md (進捗)
```

## 📝 使い方

### Claude Codeに記憶を呼び出してもらう

**セッション開始時**:
```
"follow your custom instructions"
```
→ Memory Bankを読み込んで、前回の続きから作業開始

**現状確認時**:
```
"What's the current status of Phase 11-4?"
```
→ progress.md と activeContext.md から情報取得

**技術的質問時**:
```
"What API limits do we have for Gemini?"
```
→ techContext.md から制約情報取得

### Memory Bankを更新する

**タスク完了時**:
```
"Update memory bank with Phase 11-4 completion"
```
→ progress.md と activeContext.md を更新

**アーキテクチャ変更時**:
```
"Document the new Vector DB architecture in memory bank"
```
→ systemPatterns.md を更新

**新機能追加時**:
```
"Add Phase 11-5 to memory bank"
```
→ productContext.md, activeContext.md, progress.md を更新

## 🎯 活用例

### 例1: 新しいセッション開始
```
User: "follow your custom instructions"

Claude Code:
1. projectbrief.md → プロジェクト全体を理解
2. activeContext.md → 現在のタスクを把握
3. progress.md → 完了状況を確認
4. "Phase 11-4のenhanced JSON生成から始めますね"
```

### 例2: 既知の問題を確認
```
User: "What are the current blockers?"

Claude Code:
1. activeContext.md → ブロッカーセクション参照
2. "Enhanced JSON未生成がPhase 11-4のブロッカーです"
```

### 例3: タスク完了後の更新
```
User: "Phase 11-4 is complete. Update memory bank"

Claude Code:
1. progress.md → Phase 11-4を完了済みに移動
2. activeContext.md → Phase 11-5を現在のフォーカスに設定
3. "Memory bank updated. Ready for Phase 11-5"
```

## 🔍 その他のファイル

### [gemini-api-tier-management.md](gemini-api-tier-management.md)
- Gemini APIのTier管理とレート制限の詳細
- RPD（Requests Per Day）監視方法
- 制限到達時の対策

## 📚 参考資料

- [Cline Memory Bank公式ドキュメント](https://docs.cline.bot/prompting/cline-memory-bank)
- [Memory Bank活用ブログ](https://cline.bot/blog/memory-bank-how-to-make-cline-an-ai-agent-that-never-forgets)
- [プロジェクトドキュメント](../docs/)
  - [フォルダ構造ガイド](../docs/folder-structure.md)
  - [Phase 11-4検証レポート](../docs/phase_11_4_verification_report.md)

## 🚀 クイックスタート

**新規セッションで作業を始める時**:
1. `"follow your custom instructions"` と指示
2. Claude CodeがMemory Bankを読み込む
3. 前回の続きから作業開始

**タスク完了時**:
1. `"update memory bank"` と指示
2. Claude Codeが進捗を記録
3. 次のタスクへ

**プロジェクトを理解したい時**:
1. `projectbrief.md` から読み始める
2. 全体像 → 詳細へと深掘り

---

**最終更新**: 2025-10-17
**対応バージョン**: Phase 11-3完了、Phase 11-4部分完了
