# anti-bureaucracy

作る前に、何を作るかを疑わせる。LLM エージェントを「アウトカムを人間と確定するまで作り始めない」振る舞いに固定する Claude Code plugin。

官僚主義とは、ユーザーが本当に求めているものを理解していないと気づいているのに、確定済みとされた「何を作るか」に従って作り始めること。罪は気づきの握り潰しであり、理解の不足ではない。
この plugin はセッションの冒頭と各サブエージェントの起動時に60行の要求を注入し、要求を受けた直後に「アウトカム・未知・埋め方・確認」を、作った後に「字義との差分・形式との差分・反証」を書かせる。

実体は `skills/anti-bureaucracy/SKILL.md` の1ファイル（60行以内。足すなら消す）。hook はこのファイルの本文をそのまま流す。写しは無い。

## 何をして、何をしないか

- する: 作る前にアウトカムを確定させる。気づいた隙間を「仮定」で埋めて進むのを止める。反証を1行残させる
- しない: 何を読むか、知識をどこに置くか、どう集めるかは決めない。それは [autopoiesys](https://github.com/maito1201/autopoiesys) の領分。anti-bureaucracy が「作るか」を決め、autopoiesys が「判断の瞬間に知識を届ける」
- しない: 強度モード・review コマンド・他プラットフォーム用のアダプタ。要る人が現れたら足す

## インストール

```bash
claude plugin marketplace add maito1201/anti-bureaucracy
claude plugin install anti-bureaucracy@anti-bureaucracy
```

Claude Code を起動し直すと、SessionStart（startup / resume / clear / compact）と SubagentStart で要求が届く。明示的に通したいときは `/anti-bureaucracy:anti-bureaucracy <依頼>`。

止める: 環境変数 `ANTI_BUREAUCRACY=off`（settings.json の `env`、またはシェル）。hook は何も出さなくなる。plugin ごと外すなら `claude plugin disable anti-bureaucracy@anti-bureaucracy`（autopoiesys が依存している間は外せない）。

plugin が使えない環境では、SKILL.md の frontmatter を除いた本文を CLAUDE.md か AGENTS.md に貼る。hook と off スイッチは付かないが、要求は同じ。

## autopoiesys と一緒に使う

autopoiesys はこの plugin に依存する。autopoiesys を入れると anti-bureaucracy も入る。手順は autopoiesys の README。

## 変える

- SKILL.md は60行を超えない。CI が数える
- hook の出力は JSON（`hookSpecificOutput.additionalContext`）。CI が本文の同一性を見る
