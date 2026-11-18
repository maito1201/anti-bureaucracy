"""報告で仕事を終えようとした瞬間に、依頼の原文と、その報告が自分で書いた「できていない」の行を並べて返す。

供給するのは判断の材料だけ。合否は判定しない。LLM は呼ばない。
欠けていた機能: 報告の直前に、依頼を出した本人の席から自分の成果物を見ること。届いていない事は報告の末尾に
「限界」「ただし」として自分で書いているのに、完成として出していた。本人に「これで判断できるか」と問われると
その場で否定できたので、材料は持っている。問う瞬間だけが無かった。
依頼の原文は記録ファイルから取るので、文脈の圧縮で消えていても届く。

Stop で呼ばれる。標準入力の JSON から transcript_path を受け取る。次の時は何も出さず、そのまま終わらせる。
  - 直前の本人の発話の後に、道具を一度も使っていない（会話だけの番）
  - 直前の本人の発話の後に、既に一度返した（発話1件につき1回）
ANTI_BUREAUCRACY=off で止まる。
  python before_report.py --try <記録.jsonl> [行数]   その記録の先頭から指定行までで、何が返るかを表示する
"""
import hashlib, json, os, re, sys

MARK = '［報告の前に］'
SKIP = ('[Request interrupted', 'Stop hook feedback', 'This session is being continued', '[SYSTEM', 'Another Claude session',
        'Goal check-in', 'A session-scoped Stop hook', '[Earlier usage', 'Caveat:', '[Image')
MAX_REQ, MAX_EACH, MAX_LINES, MIN_LEN = 5, 500, 8, 15      # 自分で置いた値: 載せる発話の数、1件の字数、報告から抜く行の数、中身のある発話とみなす字数
# 報告の中で、できていない事・確かめていない事を述べる言い回し（自分で置いた目印。判定ではなく抜き出しに使う）
NEG = re.compile(r'ません|ていない|できない|未確認|未達|ただし|限界|控えめ|途中|わかりません|分かりません|'
                 r"\bnot\b|n't\b|\bhowever\b|\bbarely\b|\bunverified\b|\blimit", re.I)


def text_of(c):
    if isinstance(c, list): c = '\n'.join(x.get('text', '') for x in c if isinstance(x, dict) and x.get('type') == 'text')
    return (c or '').strip()


def own_words(t):
    """本人の言葉なら返す。道具の結果や装置の文なら None。"""
    if t.startswith('Base directory for this skill'):       # スキル経由の依頼は ARGUMENTS の後ろが本人の言葉
        j = t.find('ARGUMENTS:')
        return t[j + 10:].strip() or None if j >= 0 else None
    m = re.search(r'<command-args>(.*?)</command-args>', t, re.S)     # /goal などの引数は本人の言葉
    if m:
        w = m.group(1).strip()
        return None if w in ('', 'clear') else w            # 「/goal clear」は依頼ではない
    if t.startswith('<') or t.startswith(SKIP): return None
    return t


def read(path, limit=None):
    """記録を [種類, 文, 日付] の列にする。種類は u=本人 / a=エージェントの文 / t=道具の使用 / m=この差し込み。"""
    rows = []
    with open(path, encoding='utf-8', errors='ignore') as f:
        for n, line in enumerate(f):
            if limit and n >= limit: break
            if '"type":"user"' not in line and '"type":"assistant"' not in line: continue
            try: r = json.loads(line)
            except Exception: continue
            if r.get('isSidechain'): continue
            c = r.get('message', {}).get('content'); day = r.get('timestamp', '')[5:10].replace('-', '/')
            if r.get('type') == 'assistant':
                if isinstance(c, list) and any(isinstance(x, dict) and x.get('type') == 'tool_use' for x in c): rows.append(['t', '', day])
                t = text_of(c)
                if t: rows.append(['a', t, day])
            else:
                t = text_of(c)
                if not t: continue
                if MARK in t[:200]: rows.append(['m', '', day]); continue
                skill = t.startswith('Base directory for this skill')
                if r.get('isMeta') and not skill: continue
                w = own_words(t)
                if w: rows.append(['u', w, day])
    return rows


def sentences(t):
    for line in t.splitlines():
        line = re.sub(r'^[\s\-\*・#>|\d\.]+', '', line).replace('**', '').strip()
        for s in re.split(r'(?<=[。．])|(?<=[.!?])\s', line):
            if s and s.strip(): yield s.strip()


def build(rows, seen=(), report=''):
    # 記録ファイルは遅れて書かれる事があるので、最後の報告は Stop の入力（last_assistant_message）を優先する
    if not report:
        last_a = next((i for i in range(len(rows) - 1, -1, -1) if rows[i][0] == 'a'), None)
        if last_a is None: return None, None
        report = rows[last_a][1]
    key = hashlib.sha1(report.encode('utf-8')).hexdigest()[:16]
    if key in seen: return None, key
    start = next((i for i in range(len(rows) - 1, -1, -1) if rows[i][0] == 'u'), -1)
    after = [k for k, _, _ in rows[start + 1:]]
    if 't' not in after: return None, key       # 仕事をしていない番には返さない
    if 'm' in after: return None, key           # 本人の発話1件につき1回だけ。作業のたびに返すと、済んだ仕事に余計な作業を足させた（実機で確認）
    said = [(d, t) for k, t, d in rows if k == 'u']
    if not said: return None, key
    rest = [x for x in said[1:] if len(x[1]) >= MIN_LEN] or said[1:]      # 短い叱責だけの発話より、中身のある発話を優先する
    pick = said[:1] + rest[-(MAX_REQ - 1):]        # 最初の依頼と、直近の発話
    req = '\n'.join(f'・（{d}）{t[:MAX_EACH]}{"…" if len(t) > MAX_EACH else ""}' for d, t in pick)
    neg = [s[:200] for s in sentences(report) if NEG.search(s)][:MAX_LINES]
    out = [f'{MARK}この報告を受け取るのは、次の言葉を書いた本人。記録からそのまま写した（最初の依頼と、直近の発話）。', req, '']
    if neg:
        out += ['いまの報告が、自分で「できていない・確かめていない」と書いた行:', '\n'.join('・' + s for s in neg), '']
    out += ['本人の席に座って、この報告と成果物だけを受け取ったとして答える。依頼の言葉どおりの事が、これでいまできるか。',
            'できないなら未完。直すのは成果物の側で、依頼の条件の内側で届くまで作る。依頼と違う物に替わっているなら、依頼の物に戻す。',
            '報告の文は直す対象ではない。できていない事を書いた行は消さず、言い換えず、確信の度合いも上げない。文を変えても成果物は変わらない。',
            '依頼が複数に読める時や、本人にしか決められない事が残った時は、それを一つだけ、報告の先頭に書く。',
            'できているなら、同じ報告のまま終える。']
    return '\n'.join(out), key


def main():
    if os.environ.get('ANTI_BUREAUCRACY') == 'off': return
    if len(sys.argv) >= 3 and sys.argv[1] == '--try':
        msg, _ = build(read(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None))
        sys.stdout.buffer.write((msg or '（何も返さない）').encode('utf-8') + b'\n'); return
    try: inp = json.loads(sys.stdin.buffer.read().decode('utf-8', 'ignore') or '{}')
    except Exception: return
    path = inp.get('transcript_path') or ''
    if not os.path.isfile(path): return
    state = path + '.before_report'          # 既に返した報告の印。記録と同じ場所に置く
    seen = set(open(state, encoding='utf-8').read().split()) if os.path.exists(state) else set()
    msg, key = build(read(path), seen, (inp.get('last_assistant_message') or '').strip())
    if not msg: return
    with open(state, 'a', encoding='utf-8') as f: f.write(key + '\n')
    sys.stdout.buffer.write(json.dumps({'decision': 'block', 'reason': msg}, ensure_ascii=False).encode('utf-8'))


if __name__ == '__main__':
    try: main()
    except Exception: pass          # 差し込みの故障で仕事を止めない
