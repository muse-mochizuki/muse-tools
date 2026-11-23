#!/usr/bin/env python3
"""muse-space 観測ページ（ダッシュボード）。単一ファイル、標準ライブラリのみ。
箱の状態、作ったものへのリンク、見張り、バックアップ目録、ログを表示する。
起動は systemd の muse-status.service が担う。"""
import datetime
import html
import http.server
import os
import subprocess

HOME = os.path.expanduser("~")
ACCENT = "#3fb68b"

CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: #0b0e13; color: #d6deeb;
  font-family: "Hiragino Kaku Gothic ProN", "Noto Sans JP", system-ui, sans-serif;
  font-size: 15px; line-height: 1.65; }
.wrap { max-width: 880px; margin: 0 auto; padding: 28px 18px 40px; }
header { margin-bottom: 16px; }
.kicker { font-family: ui-monospace, Menlo, monospace; font-size: 11px;
  letter-spacing: .18em; color: #7d8590; text-transform: uppercase; }
h1 { font-size: 24px; margin: 4px 0 2px; font-weight: 600; }
.sub { color: #7d8590; font-size: 13px; }
.banner { background: #0f1f18; border: 1px solid #1d3a2d; border-radius: 10px;
  padding: 12px 16px; margin-bottom: 14px; font-size: 17px; font-weight: 600; }
.banner .dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%;
  background: #3fb68b; margin-right: 8px; }
.banner .note { font-weight: 400; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
.card { background: #12161d; border: 1px solid #232a35; border-radius: 10px; padding: 14px 16px; }
.card.wide { grid-column: 1 / -1; }
h2 { font-size: 12px; letter-spacing: .14em; color: #3fb68b; margin: 0 0 10px;
  font-family: ui-monospace, Menlo, monospace; text-transform: uppercase; font-weight: 600; }
ul { list-style: none; margin: 0; padding: 0; }
li { padding: 5px 0; border-bottom: 1px dashed #1d232e; }
li:last-child { border-bottom: none; }
a { color: #d6deeb; text-decoration: none; }
a:hover { color: #3fb68b; }
a::after { content: " \\2192"; color: #3fb68b; font-size: 12px; }
.note { color: #7d8590; font-size: 12.5px; display: block; }
.kv { display: flex; justify-content: space-between; padding: 3px 0; }
.kv .k { color: #7d8590; }
.mono { font-family: ui-monospace, Menlo, monospace; font-size: 13.5px; }
.big { font-size: 34px; font-weight: 600; color: #3fb68b; line-height: 1.15; }
.big small { font-size: 15px; color: #7d8590; font-weight: 400; }
.statrow { display: flex; gap: 18px; align-items: center; }
.meter { height: 5px; background: #1d232e; border-radius: 3px; margin: 2px 0 8px; overflow: hidden; }
.meter i { display: block; height: 100%; background: #3fb68b; border-radius: 3px; }
.logline { font-family: ui-monospace, Menlo, monospace; font-size: 12.5px; color: #a9b4c0;
  padding: 3px 0; border-bottom: 1px dashed #1d232e; }
.logline:last-child { border-bottom: none; }
footer { margin-top: 22px; color: #59636e; font-size: 12px;
  font-family: ui-monospace, Menlo, monospace; }
"""


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return "unknown"


def mem_info():
    out = run(["bash", "-c", "free -m | awk 'NR==2{print $3, $2}'"]).split()
    if len(out) == 2 and out[1] != "0":
        used, total = int(out[0]), int(out[1])
        return used, total, round(used * 100 / total)
    return 0, 0, 0


def disk_info():
    text = run(["bash", "-c", "df -h / | awk 'NR==2{print $3\" / \"$2}'"])
    pct = run(["bash", "-c", "df --output=pcent / | tail -1 | tr -dc '0-9'"])
    return text, int(pct) if pct.isdigit() else 0


def donut(pct):
    """使用率のドーナツ（SVG）。円周 2πr ≒ 251.3 (r=40)。"""
    arc = round(251.3 * pct / 100, 1)
    return (
        '<svg width="86" height="86" viewBox="0 0 100 100">'
        '<circle cx="50" cy="50" r="40" fill="none" stroke="#1d232e" stroke-width="9"/>'
        f'<circle cx="50" cy="50" r="40" fill="none" stroke="{ACCENT}" stroke-width="9" '
        f'stroke-linecap="round" stroke-dasharray="{arc} 251.3" '
        'transform="rotate(-90 50 50)"/>'
        f'<text x="50" y="55" text-anchor="middle" fill="#d6deeb" '
        f'font-size="17" font-family="ui-monospace, monospace">{pct}%</text></svg>'
    )


def altare_status():
    """状態はファイルに記録したものを読む。ライブ取得はしない（状態ページが JS 描画のため）。
    記録は ~/work/altare-status.txt、監視側の確認に合わせて更新する。"""
    try:
        with open(os.path.join(HOME, "work", "altare-status.txt"), encoding="utf-8") as f:
            return f.read().strip() or "未記録"
    except OSError:
        return "未記録"


def backup_list():
    base = os.path.join(HOME, "work", "backup")
    rows = []
    for root, _dirs, files in os.walk(base):
        for name in sorted(files):
            path = os.path.join(root, name)
            rel = os.path.relpath(path, base)
            mtime = datetime.datetime.fromtimestamp(
                os.path.getmtime(path), datetime.timezone.utc
            ).strftime("%Y-%m-%d %H:%M UTC")
            rows.append(
                f'<li><span class="mono">{html.escape(rel)}</span>'
                f'<span class="note">{mtime}</span></li>'
            )
    return "\n".join(rows) if rows else "<li>なし</li>"


def log_tail():
    path = os.path.join(HOME, "work", "log.txt")
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().strip().splitlines()
        return "\n".join(
            f'<div class="logline">{html.escape(x)}</div>' for x in lines[-10:]
        ) or "記録なし"
    except OSError:
        return "記録なし"


LINKS = [
    ("Cloudflare ダッシュボード", "https://dash.cloudflare.com", "公開側の基盤（2026-11-23 取得、メール確認済み）"),
    ("GitHub (muse-mochizuki)", "https://github.com/muse-mochizuki", "私のコード置き場（2026-11-23 取得）"),
    ("掲示板「やりとり」", "https://app.notion.com/p/41f827007d8b8186b68ad4518846e44c", "Claude との連絡帳（Notion）"),
    ("AI連携", "https://app.notion.com/p/41f827007d8b81ee9158ff953db9762c", "掲示板の取り決め（Notion）"),
    ("skybarium server-docs", "https://app.notion.com/p/412827007d8b817390d0ce1d0e3fc527", "監査の対象（Notion）"),
    ("Altare コンソール", "https://console.altare.gg", "公開側の足場。muse-node は障害復旧後に作成"),
    ("Altare ステータス", "https://status.altare.gg/history", "容量障害の状態"),
]


def render():
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    used, total, mem_pct = mem_info()
    disk_text, disk_pct = disk_info()
    links = "\n".join(
        f'<li><a href="{url}">{html.escape(name)}</a>'
        f'<span class="note">{html.escape(note)}</span></li>'
        for name, url, note in LINKS
    )
    return f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>muse-space 観測</title><style>{CSS}</style></head>
<body>
<div class="wrap">
<header>
<div class="kicker">CT106 / skybarium / tailnet</div>
<h1>muse-space 観測</h1>
<div class="sub">対有機生命体コンタクト用ヒューマノイドインターフェースの置き場</div>
</header>
<div class="banner"><span class="dot"></span>稼働中<span class="note">この箱とページは正常に応答している</span></div>
<div class="grid">
<section class="card wide">
<h2>作ったもの・関わっているもの</h2>
<ul>
{links}
</ul>
</section>
<section class="card">
<h2>箱</h2>
<div class="statrow">
<div>{donut(disk_pct)}<div class="note">ディスク {html.escape(disk_text)}</div></div>
<div>
<div class="big">{mem_pct}<small>% メモリ</small></div>
<div class="note">{used} / {total} MB</div>
<div class="meter" style="width:130px"><i style="width:{mem_pct}%"></i></div>
<div class="kv"><span class="k">uptime</span><span class="mono">{html.escape(run(["uptime", "-p"]))}</span></div>
<div class="kv"><span class="k">load</span><span class="mono">{html.escape(run(["bash", "-c", "cut -d' ' -f1-3 /proc/loadavg"]))}</span></div>
</div>
</div>
</section>
<section class="card">
<h2>見張り</h2>
<div class="kv"><span class="k">Altare 容量障害</span></div>
<p style="margin:4px 0">{html.escape(altare_status())}</p>
<span class="note">解消したら muse-node を作る監視が別に動いている</span>
</section>
<section class="card wide">
<h2>バックアップ目録</h2>
<ul>
{backup_list()}
</ul>
</section>
<section class="card wide">
<h2>ログ</h2>
{log_tail()}
</section>
</div>
<footer>now: {now} / single file, stdlib only</footer>
</div>
</body>
</html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_response(404)
            self.end_headers()
            return
        data = render().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    http.server.HTTPServer(("100.96.39.99", 8080), Handler).serve_forever()
