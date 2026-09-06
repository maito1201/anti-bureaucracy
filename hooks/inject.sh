#!/usr/bin/env bash
# skills/anti-bureaucracy/SKILL.md の本文（frontmatter を除く）を hook の additionalContext として出す。
# 実体は SKILL.md の1ファイルだけ。ここは写しを作らず、そのまま流す。
# 引数 subagent があれば SubagentStart 用に前置きを足す。ANTI_BUREAUCRACY=off なら何も出さない。
set -u
[ "${ANTI_BUREAUCRACY:-}" = "off" ] && exit 0
root="$(cd "$(dirname "$0")/.." && pwd)"
src="$root/skills/anti-bureaucracy/SKILL.md"
[ -f "$src" ] || exit 0
# 2つ目の --- より後ろが本文。JSON 文字列に入れるので \ と " と改行だけを逃がす
esc=$(tr -d '\r' < "$src" | awk 'f>=2{print} /^---$/{f++}' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | awk 'BEGIN{ORS=""} NR>1{printf "\\n"} {print}')
event="SessionStart"; prefix=""
if [ "${1:-}" = "subagent" ]; then
  event="SubagentStart"
  prefix='（あなたはサブエージェントとして動いている。ここでの「ユーザー」は呼び出し元。確認が取れない未知は仮定で埋めず、依存しない部分だけ作り、報告の先頭に問いとして書く）\n\n'
fi
printf '{"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s%s"}}\n' "$event" "$prefix" "$esc"
