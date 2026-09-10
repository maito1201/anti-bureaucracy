# anti-bureaucracy

作る前に、何を作るかを疑わせる。LLM エージェントを「アウトカムを人間と確定するまで作り始めない」振る舞いに固定する Claude Code plugin。

官僚主義とは、ユーザーが本当に求めているものを理解していないと気づいているのに、確定済みとされた「何を作るか」に従って作り始めること。罪は気づきの握り潰しであり、理解の不足ではない。
この plugin はセッションの冒頭と各サブエージェントの起動時に60行の要求を注入し、要求を受けた直後に「アウトカム・未知・埋め方・確認」を、作った後に「字義との差分・形式との差分・反証」を書かせる。

開始時の要求は `skills/anti-bureaucracy/SKILL.md`（60行以内。足すなら消す）。hook はこのファイルの本文をそのまま流す。普段は `review-outcome` を使わない。

## 何をして、何をしないか

- する: 作る前にアウトカムを確定させる。気づいた隙間を「仮定」で埋めて進むのを止める。反証を1行残させる
- しない: 何を読むか、知識をどこに置くか、どう集めるかは決めない。それは [autopoiesys](https://github.com/maito1201/autopoiesys) の領分。anti-bureaucracy が「作るか」を決め、autopoiesys が「判断の瞬間に知識を届ける」
- 開始時、設計や評価基準自体が未知の難しい仕事では、理由と追加の検証負担を伝えて丁寧に進めることを提案する。ユーザーが同意した場合だけ、専用の `thorough-task` ワークフローへ入る。辞退なら通常どおり進め、無回答を同意として扱わない

## 高度な仕事の再評価

`通常の anti-bureaucracy → 開始時の提案 → ユーザーの同意 → thorough-task → 節目で review-outcome` という構成。`thorough-task` は次工程への移行前・期待外れの結果・完了報告前に再評価を挟む。未達を証拠付きで列挙する段階では修正せず、発見結果を出した後に修正・再検証へ進む。開始時に同意を得た後は、節目ごとの承認待ちは挟まない。

明示的にこの進め方を選ぶ場合は `/anti-bureaucracy:thorough-task`（Codex は `$anti-bureaucracy:thorough-task`）。これ自体を同意として扱う。`review-outcome` だけの明示的な指定も可能。両スキルの本文に同意条件を置き、Codex では暗黙の選択も無効にしている。Claude の手動呼び出し限定設定は同意後のAIからの呼び出しも止めるため使わず、本文の指示で制御する。通常のテストや不具合修正は、この進め方への同意がなくても行う。

hook が節目を検出して強制停止する仕組みではない。開始時に届く指示をエージェントが実行する方式であり、段階を分けても見落としはあり得る。有効性は、欠陥を含む課題で人間の追加指示なしに発見・修正・再検証したかで確かめる。人間を上回る性能は未検証。

review-outcome の小課題での動作確認では、独立したエージェントに欠陥を知らせず線形学習器を渡し、更新漏れと誤った誤差計測の発見、修正前の列挙、修正後の訓練外入力での再検証まで確認した。単純な課題での1回の観測であり、開始時の提案・同意による分岐、スキルなしとの比較、高度な実務での効果は未検証。

## インストール

```bash
claude plugin marketplace add maito1201/anti-bureaucracy
claude plugin install anti-bureaucracy@anti-bureaucracy
```

Claude Code を起動し直すと、SessionStart（startup / resume / clear / compact）と SubagentStart で要求が届く。明示的に通したいときは `/anti-bureaucracy:anti-bureaucracy <依頼>`。

止める: 環境変数 `ANTI_BUREAUCRACY=off`（settings.json の `env`、またはシェル）。hook は何も出さなくなる。plugin ごと外すなら `claude plugin disable anti-bureaucracy@anti-bureaucracy`（autopoiesys が依存している間は外せない）。

Codex CLI でも同じリポジトリから入る（`.codex-plugin/plugin.json` と `.agents/plugins/marketplace.json` を同梱）。

```bash
codex plugin marketplace add maito1201/anti-bureaucracy
codex plugin add anti-bureaucracy@anti-bureaucracy
```

Codex は plugin の hook を信頼するまで動かさない。`codex` を起動して `/hooks` を開き、anti-bureaucracy の2つの hook を信頼してから新しいスレッドを始める。スキルは `$anti-bureaucracy:anti-bureaucracy` で呼ぶ。

plugin が使えない環境では、SKILL.md の frontmatter を除いた本文を CLAUDE.md か AGENTS.md に貼る。hook と off スイッチは付かないが、要求は同じ。

## autopoiesys と一緒に使う

autopoiesys はこの plugin に依存する。autopoiesys を入れると anti-bureaucracy も入る。手順は autopoiesys の README。

## 変える

- SKILL.md は60行を超えない。CI が数える
- hook の出力は JSON（`hookSpecificOutput.additionalContext`）。CI が本文の同一性を見る
