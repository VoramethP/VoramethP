# -*- coding: utf-8 -*-
"""render_cards.py — วาดการ์ด README ทุกใบเป็น SVG (ธีมมืด + สว่าง) จากข้อมูล GitHub GraphQL
   รันโดย .github/workflows/cards.yml ทุกเช้า · รันเองได้: GH_TOKEN=... python3 scripts/render_cards.py

   แนวคิด v3 — "แบบฟอร์มที่ได้รับอนุมัติ": โปรไฟล์ทั้งหน้าเป็นชุดเอกสารของระบบงานที่เขาสร้างเอง
   ทุกการ์ดวาด 2 ชุด (dark / light) จากสคริปต์เดียว ใช้สีชุดเดียวกับ GitHub เองเพื่อให้กลมกลืนทั้งสองธีม
   README ใช้ <picture> เลือกไฟล์ตาม prefers-color-scheme"""
import json, datetime, collections, os, sys, re, io, base64, urllib.request, pathlib, argparse

PAL = {
    'dark':  dict(paper='#161b22', edge='#30363d', ink='#e6edf3', muted='#8b949e', line='#21262d', field='#0d1117',
                  accent='#3fb950', accent2='#56d364', hi='#12351f', stamp='#3fb950', warn='#d29922', blue='#58a6ff'),
    'light': dict(paper='#ffffff', edge='#d0d7de', ink='#1f2328', muted='#656d76', line='#d8dee4', field='#f6f8fa',
                  accent='#1a7f37', accent2='#2da44e', hi='#dafbe1', stamp='#1a7f37', warn='#9a6700', blue='#0969da'),
}
FONT = "'IBM Plex Sans Thai','Segoe UI',system-ui,sans-serif"
MONO = "'IBM Plex Mono',ui-monospace,Menlo,monospace"
TH_MON = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']

def th_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.day} {TH_MON[d.month-1]} {d.year+543}"

def head(extra_css=''):
    return f"""<style>
  text{{font-family:{FONT}}} .mono{{font-family:{MONO}}}
  @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
  {extra_css}
</style>"""

def paper(p, w, h, r=12):
    """แผ่นกระดาษ: พื้น + ขอบ + เงาบาง ๆ (เงาเป็น rect ซ้อน ไม่ใช้ filter เพื่อให้เบาและชัวร์ใน <img>)"""
    return f"""<rect x="3" y="4" width="{w-4}" height="{h-4}" rx="{r}" fill="{p['edge']}" opacity=".35"/>
<rect x="1" y="1" width="{w-4}" height="{h-4}" rx="{r}" fill="{p['paper']}" stroke="{p['edge']}"/>"""

def stamp_css(delay):
    return f""".stamp{{opacity:0;transform-box:fill-box;transform-origin:center;animation:slam .45s cubic-bezier(.3,1.4,.5,1) forwards {delay}s}}
  @keyframes slam{{0%{{opacity:0;transform:scale(2.6) rotate(-14deg)}}70%{{opacity:1;transform:scale(.96) rotate(-8deg)}}100%{{opacity:.92;transform:scale(1) rotate(-8deg)}}}}
  .ripple{{opacity:0;transform-box:fill-box;transform-origin:center;animation:rip .7s ease-out forwards {delay+.1}s}}
  @keyframes rip{{0%{{opacity:.5;transform:scale(.6)}}100%{{opacity:0;transform:scale(1.6)}}}}"""

def stamp(p, x, y, text_th='อนุมัติ', text_en='APPROVED', delay=2.4, size=1.0):
    return f"""<g transform="translate({x},{y}) scale({size})">
  <circle class="ripple" cx="0" cy="0" r="70" fill="none" stroke="{p['stamp']}" stroke-width="3"/>
  <g class="stamp">
    <rect x="-96" y="-34" width="192" height="68" rx="8" fill="none" stroke="{p['stamp']}" stroke-width="4"/>
    <rect x="-90" y="-28" width="180" height="56" rx="6" fill="none" stroke="{p['stamp']}" stroke-width="1.5" stroke-dasharray="3 3"/>
    <text x="0" y="-2" text-anchor="middle" font-size="26" font-weight="700" fill="{p['stamp']}">{text_th}</text>
    <text x="0" y="20" text-anchor="middle" class="mono" font-size="12" letter-spacing="4" fill="{p['stamp']}">{text_en}</text>
  </g>
</g>"""

# ---------- hero: แบบฟอร์มโปรไฟล์ ----------
def hero(p, d):
    css = f"""
  .type{{animation:reveal 1.1s steps(28) forwards}} .t1{{animation-delay:.3s}} .t2{{animation-delay:1.0s}} .t3{{animation-delay:1.7s}}
  @keyframes reveal{{to{{width:420px}}}} .t3{{animation-duration:.9s;animation-name:reveal3}} @keyframes reveal3{{to{{width:190px}}}}
  .caret{{animation:blink 1s steps(2) infinite}} @keyframes blink{{to{{opacity:0}}}}
  .chk{{stroke-dasharray:24;stroke-dashoffset:24;animation:draw .35s ease forwards}} .c1{{animation-delay:2.0s}} .c2{{animation-delay:2.15s}} .c3{{animation-delay:2.3s}}
  @keyframes draw{{to{{stroke-dashoffset:0}}}}
  .log{{opacity:0;animation:fadein .4s ease forwards}} .l1{{animation-delay:.6s}} .l2{{animation-delay:1.4s}} .l3{{animation-delay:2.2s}} .l4{{animation-delay:2.9s}}
  @keyframes fadein{{to{{opacity:1}}}}
  .sig{{stroke-dasharray:420;stroke-dashoffset:420;animation:draw2 1.2s ease forwards 2.6s}} @keyframes draw2{{to{{stroke-dashoffset:0}}}}
  .dot{{transform-box:fill-box;transform-origin:center;animation:pulse 2.2s ease-in-out infinite}} @keyframes pulse{{50%{{transform:scale(.6);opacity:.4}}}}
  {stamp_css(2.5)}"""
    def field(x, y, w, label, value, cls, mono=False):
        return f"""<text x="{x}" y="{y}" font-size="10.5" letter-spacing="1" fill="{p['muted']}">{label}</text>
<rect x="{x}" y="{y+8}" width="{w}" height="34" rx="6" fill="{p['field']}" stroke="{p['line']}"/>
<clipPath id="clip-{cls}"><rect class="type {cls}" x="{x}" y="{y+8}" width="0" height="34"/></clipPath>
<text clip-path="url(#clip-{cls})" x="{x+12}" y="{y+31}" font-size="{'15' if mono else '17'}" font-weight="{'400' if mono else '600'}" fill="{p['ink']}"{' class="mono"' if mono else ''}>{value}</text>"""
    def logline(y, cls, t, txt, ok=True):
        return f"""<g class="log {cls}"><text x="0" y="{y}" class="mono" font-size="10.5" fill="{p['muted']}">{t}</text><circle cx="52" cy="{y-4}" r="3" fill="{p['accent'] if ok else p['warn']}"/><text x="62" y="{y}" font-size="11.5" fill="{p['ink']}">{txt}</text></g>"""
    checks = ''
    for i, (lbl, x) in enumerate([('ฟอร์มและข้อมูล', 40), ('สิทธิ์ผู้ใช้', 180), ('รายงาน PDF', 300)]):
        checks += f"""<rect x="{x}" y="196" width="16" height="16" rx="4" fill="{p['field']}" stroke="{p['edge']}"/>
<path class="chk c{i+1}" d="M{x+3.5} {204.5} l3.5 3.5 l6 -7" fill="none" stroke="{p['accent']}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
<text x="{x+24}" y="209" font-size="13" fill="{p['ink']}">{lbl}</text>
"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 260" width="100%" role="img" aria-label="Vorameth Patummasut · Web Developer · แบบฟอร์มโปรไฟล์ที่ได้รับอนุมัติ">
{head(css)}
{paper(p, 1000, 260, 14)}
<!-- หัวแบบฟอร์ม -->
<rect x="1" y="1" width="996" height="44" rx="14" fill="{p['field']}"/><rect x="1" y="30" width="996" height="16" fill="{p['field']}"/>
<line x1="1" y1="45.5" x2="997" y2="45.5" stroke="{p['edge']}"/>
<circle class="dot" cx="26" cy="23" r="5" fill="{p['accent']}"/>
<text x="40" y="28" font-size="13" font-weight="600" fill="{p['ink']}">แบบฟอร์มโปรไฟล์นักพัฒนา</text>
<text x="230" y="28" class="mono" font-size="11" fill="{p['muted']}">เลขที่ PF-2569-001</text>
<text x="982" y="28" text-anchor="end" class="mono" font-size="11" fill="{p['muted']}">github.com/VoramethP</text>
<!-- ช่องกรอก -->
{field(40, 70, 420, 'ชื่อ – นามสกุล', 'Vorameth Patummasut · วรเมธ ปทุมสูติ', 't1')}
{field(40, 126, 420, 'ตำแหน่ง', 'Web Developer · ระบบงานองค์กร · HIS', 't2')}
<text x="40" y="186" font-size="10.5" letter-spacing="1" fill="{p['muted']}">ขอบเขตงาน</text>
{checks}
<text x="500" y="78" font-size="10.5" letter-spacing="1" fill="{p['muted']}">เครื่องมือหลัก</text>
<clipPath id="clip-t3"><rect class="type t3" x="500" y="84" width="0" height="80"/></clipPath>
<text clip-path="url(#clip-t3)" x="500" y="104" class="mono" font-size="13" fill="{p['ink']}">Nuxt 4 · Vue 3</text>
<text clip-path="url(#clip-t3)" x="500" y="124" class="mono" font-size="13" fill="{p['ink']}">TypeScript · PostgreSQL</text>
<text clip-path="url(#clip-t3)" x="500" y="144" class="mono" font-size="13" fill="{p['ink']}">Supabase · Vercel</text>
<rect class="caret" x="500" y="152" width="60" height="2" fill="{p['accent']}"/>
<!-- ลายเซ็น -->
<text x="500" y="186" font-size="10.5" letter-spacing="1" fill="{p['muted']}">ผู้ยื่น</text>
<path class="sig" d="M500 226 c10 -22 22 -26 26 -8 c3 14 -8 22 -2 6 c8 -20 20 -24 30 -6 c6 10 14 4 22 -8 c6 -8 10 -4 12 4 c2 10 12 6 26 -6" fill="none" stroke="{p['ink']}" stroke-width="1.6" stroke-linecap="round"/>
<line x1="500" y1="232" x2="660" y2="232" stroke="{p['edge']}"/>
<!-- audit log -->
<rect x="700" y="62" width="280" height="150" rx="8" fill="{p['field']}" stroke="{p['line']}"/>
<text x="716" y="84" class="mono" font-size="10" letter-spacing="2" fill="{p['muted']}">AUDIT LOG</text>
<g transform="translate(716,0)">
{logline(108, 'l1', '09:00', 'สร้างแบบฟอร์ม')}
{logline(132, 'l2', '09:01', 'ตรวจสิทธิ์ผู้ใช้ · role: developer')}
{logline(156, 'l3', '09:02', 'แนบผลงาน 4 รายการ')}
{logline(180, 'l4', '09:03', 'อนุมัติ · ออกรายงาน PDF')}
</g>
{stamp(p, 846, 224, delay=2.5, size=.6)}
</svg>"""

# ---------- tiles ----------
def tile(p, eyebrow, title, sub, href, delay):
    css = f""".in{{animation:swing .9s cubic-bezier(.2,.9,.25,1.2) both {delay}s;transform-origin:50% 100%}}
  @keyframes swing{{from{{opacity:0;transform:translateY(24px) rotate(-1.5deg)}}to{{opacity:1;transform:none}}}}
  .arrow{{animation:nudge 2.4s ease-in-out infinite {delay+1}s}} @keyframes nudge{{0%,100%{{transform:translateX(0)}}50%{{transform:translateX(5px)}}}}"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 150" width="100%" role="img" aria-label="{title}">
{head(css)}
<g class="in">
{paper(p, 320, 150, 12)}
<rect x="1" y="1" width="6" height="146" rx="3" fill="{p['accent']}"/>
<text x="26" y="34" class="mono" font-size="10" letter-spacing="2" fill="{p['accent']}">{eyebrow}</text>
<text x="26" y="72" font-size="21" font-weight="600" fill="{p['ink']}">{title}</text>
<text x="26" y="95" font-size="12.5" fill="{p['muted']}">{sub}</text>
<text x="26" y="128" class="mono" font-size="10.5" fill="{p['muted']}">{href}</text>
<g class="arrow"><path d="M278 122 h18 m-6 -6 l6 6 -6 6" fill="none" stroke="{p['accent']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></g>
</g>
</svg>"""

def tiles(p):
    return [
        tile(p, 'PORTFOLIO', 'ผลงานและ case study', 'ระบบโรงพยาบาล · Nuxel · Medimove', 'vorameth.vercel.app', 0.0),
        tile(p, 'FASTWORK', 'รับทำระบบงานองค์กร', 'บน Nuxel · แพ็กเกจพร้อม MA', 'fastwork.com/user/vorameth', 0.15),
        tile(p, 'LINKEDIN', 'ประวัติการทำงาน', 'Web Developer · HIS · Bangkok', 'linkedin.com/in/vorameth-patummasut', 0.3),
    ]

# ---------- contributions: รายงานปิดกะ ----------
def contributions(p, d, days):
    weeks = collections.OrderedDict()
    for day in days:
        dt = datetime.date.fromisoformat(day['date']); wk = (dt - datetime.timedelta(days=dt.weekday())).isoformat()
        weeks[wk] = weeks.get(wk, 0) + day['contributionCount']
    wk = list(weeks.items())[-20:]
    mx = max(v for _, v in wk) or 1
    x0, y0, bw, gap, H = 330, 214, 18, 6, 140
    bars = ''
    for i, (k, v) in enumerate(wk):
        h = max(3, v / mx * H); x = x0 + i * (bw + gap)
        bars += f'<rect class="b" style="animation-delay:{0.4+i*0.06:.2f}s" x="{x}" y="{y0-h:.1f}" width="{bw}" height="{h:.1f}" rx="3" fill="{p["accent"]}" opacity="{0.45+0.55*v/mx:.2f}"/>\n'
        if i % 4 == 0:
            dt = datetime.date.fromisoformat(k); bars += f'<text x="{x+bw/2}" y="{y0+18}" font-size="10" fill="{p["muted"]}" text-anchor="middle">{dt.day} {TH_MON[dt.month-1]}</text>\n'
    peak = max(wk, key=lambda t: t[1]); pi = wk.index(peak); px = x0 + pi * (bw + gap) + bw / 2
    bars += f'<text x="{px}" y="{y0 - peak[1]/mx*H - 8:.1f}" class="mono" font-size="10.5" fill="{p["accent"]}" text-anchor="middle">{peak[1]}</text>'
    total = d['total']; frames = 16; nums = ''; css = ''
    for i in range(frames + 1):
        v = round(total * (1 - (1 - i / frames) ** 3)); t = 0.3 + i * 0.09
        nums += f'<text class="n n{i}" x="40" y="124" font-size="54" font-weight="700" fill="{p["ink"]}" opacity="0">{v:,}</text>\n'
        css += f'.n{i}{{animation:on 0s forwards {t:.2f}s' + (f',off 0s forwards {t+0.09:.2f}s' if i < frames else '') + '}\n'
    css += f"""@keyframes on{{to{{opacity:1}}}} @keyframes off{{to{{opacity:0}}}}
  .b{{transform-origin:50% {y0}px;transform:scaleY(0);animation:grow .7s cubic-bezier(.2,.8,.2,1.1) forwards}} @keyframes grow{{to{{transform:scaleY(1)}}}}
  .box{{animation:fade .6s ease both}} @keyframes fade{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
  {stamp_css(2.0)}"""
    def box(i, x, y, label, value, sub):
        return f"""<g transform="translate({x},{y})"><g class="box" style="animation-delay:{0.9+i*0.15:.2f}s">
  <rect x="0" y="28" width="130" height="62" rx="8" fill="{p['field']}" stroke="{p['line']}"/>
  <text x="12" y="46" font-size="10.5" fill="{p['muted']}">{label}</text>
  <text x="12" y="70" class="mono" font-size="20" font-weight="600" fill="{p['accent']}">{value}</text>
  <text x="12" y="84" font-size="9.5" fill="{p['muted']}">{sub}</text>
</g></g>"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 250" width="100%" role="img" aria-label="Contributions {total:,} ในปีที่ผ่านมา">
{head(css)}
{paper(p, 1000, 250, 14)}
<text x="40" y="44" class="mono" font-size="11" letter-spacing="2" fill="{p['accent']}">รายงานสรุป · CONTRIBUTIONS ปีที่ผ่านมา</text>
<g>{nums}</g>
<text x="40" y="152" font-size="13" fill="{p['muted']}">commits {d['commits']:,} · pull requests {d['prs']} · issues {d['issues']} · รวม private repo</text>
<text x="40" y="172" font-size="11" fill="{p['muted']}">อัปเดตทุกเช้า · ล่าสุด {th_date(d['asof'])}</text>
<line x1="{x0-10}" y1="{y0}" x2="{x0 + 20*(bw+gap)}" y2="{y0}" stroke="{p['edge']}"/>
<text x="{x0}" y="44" class="mono" font-size="11" letter-spacing="2" fill="{p['muted']}">รายสัปดาห์ · 20 สัปดาห์ล่าสุด</text>
{bars}
{box(1, 830, 0, 'ต่อเนื่องยาวสุด', f"{d['best']} วัน", 'commit ติดกันทุกวัน')}
{box(2, 830, 70, 'มากสุดในวันเดียว', f"{d['busy']['contributionCount']}", th_date(d['busy']['date']))}
{box(3, 830, 140, 'repo สาธารณะ', f"{d['repos']}", f"★ {d['stars']} · ผู้ติดตาม {d['followers']}")}
{stamp(p, 150, 206, 'ตรวจแล้ว', 'VERIFIED', delay=2.0, size=.42)}
</svg>"""

# ---------- languages ----------
def languages(p, d):
    langs = d['langs'] + ([{'name': 'อื่น ๆ', 'pct': d['other'], 'color': '#8b949e'}] if d['other'] > 0 else [])
    x, W, y, h = 40, 920, 70, 18
    segs, legend, cx, lx = '', '', x, x
    for i, l in enumerate(langs):
        w = W * l['pct'] / 100
        segs += f'<rect class="s" style="animation-delay:{0.2+i*0.18:.2f}s;transform-origin:{cx}px 0" x="{cx:.1f}" y="{y}" width="{w:.1f}" height="{h}" fill="{l["color"]}" rx="{3 if i in (0,len(langs)-1) else 0}"/>\n'
        cx += w
    for i, l in enumerate(langs):
        legend += f'<g class="l" style="animation-delay:{0.5+i*0.12:.2f}s" transform="translate({lx},{y+44})"><circle cx="5" cy="-4" r="5" fill="{l["color"]}"/><text x="16" y="0" font-size="13" fill="{p["ink"]}">{l["name"]}</text><text x="{16+6.9*len(l["name"])+8}" y="0" class="mono" font-size="12" fill="{p["muted"]}">{l["pct"]}%</text></g>\n'
        lx += 16 + 6.9 * len(l['name']) + 8 + 7.4 * len(f"{l['pct']}%") + 24
    css = f""".s{{transform:scaleX(0);animation:wide .8s cubic-bezier(.2,.8,.2,1) forwards}} @keyframes wide{{to{{transform:scaleX(1)}}}}
  .l{{opacity:0;animation:fade .5s ease forwards}} @keyframes fade{{to{{opacity:1}}}}"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 150" width="100%" role="img" aria-label="ภาษาที่ใช้">
{head(css)}
{paper(p, 1000, 150, 14)}
<text x="40" y="44" class="mono" font-size="11" letter-spacing="2" fill="{p['accent']}">สัดส่วนภาษา · ตามขนาดโค้ดในทุก repo</text>
<rect x="{x}" y="{y}" width="{W}" height="{h}" rx="3" fill="{p['field']}"/>
{segs}
{legend}
</svg>"""

# ---------- divider / footer ----------
def divider(p):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 14" width="100%" role="presentation">
<style>.run{{stroke-dasharray:4 10;animation:mv 1.6s linear infinite}} @keyframes mv{{to{{stroke-dashoffset:-14}}}} @media (prefers-reduced-motion:reduce){{.run{{animation:none}}}}</style>
<line class="run" x1="0" y1="7" x2="1000" y2="7" stroke="{p['edge']}" stroke-width="2" stroke-linecap="round"/>
<circle cx="500" cy="7" r="4" fill="{p['accent']}"/>
</svg>"""

def footer(p):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 70" width="100%" role="presentation">
<style>.ft{{font-family:{MONO}}} .sh{{animation:sh 5s ease-in-out infinite}} @keyframes sh{{0%,100%{{opacity:.35}}50%{{opacity:1}}}} @media (prefers-reduced-motion:reduce){{.sh{{animation:none}}}}</style>
<line x1="0" y1="20" x2="1000" y2="20" stroke="{p['edge']}" stroke-dasharray="2 6"/>
<text x="500" y="52" text-anchor="middle" font-size="11" letter-spacing="3" fill="{p['muted']}" class="sh ft">— สิ้นสุดเอกสาร · END OF FORM —</text>
</svg>"""


# ---------- ข้อมูลจาก GitHub ----------
QUERY = """query($login:String!){ user(login:$login){ followers{totalCount}
  contributionsCollection{ totalCommitContributions totalPullRequestContributions totalIssueContributions restrictedContributionsCount
    contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } } }
  repositories(first:100, ownerAffiliations:OWNER, isFork:false){ totalCount nodes{ name isPrivate stargazerCount
    languages(first:10, orderBy:{field:SIZE,direction:DESC}){ edges{ size node{ name color } } } } } } }"""
HIDE_LANGS = {'C++', 'CMake', 'Dart', 'Swift', 'C', 'Kotlin', 'Objective-C'}

def fetch(login, token):
    req = urllib.request.Request('https://api.github.com/graphql', data=json.dumps({'query': QUERY, 'variables': {'login': login}}).encode(),
                                 headers={'Authorization': f'bearer {token}', 'Content-Type': 'application/json', 'User-Agent': 'render-cards'})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.load(r)
    if 'errors' in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body['data']['user']

def summarise(u):
    cc = u['contributionsCollection']
    days = [d for w in cc['contributionCalendar']['weeks'] for d in w['contributionDays']]
    best = run = 0
    for d in days:
        run = run + 1 if d['contributionCount'] > 0 else 0; best = max(best, run)
    busy = max(days, key=lambda d: d['contributionCount'])
    lang = collections.Counter(); color = {}
    for r in u['repositories']['nodes']:
        for e in r['languages']['edges']:
            n = e['node']['name']
            if n in HIDE_LANGS: continue
            lang[n] += e['size']; color[n] = e['node']['color'] or '#8b949e'
    tot = sum(lang.values()) or 1
    langs = [{'name': n, 'pct': round(v * 100 / tot, 1), 'color': color[n]} for n, v in lang.most_common(6)]
    pub = [r for r in u['repositories']['nodes'] if not r['isPrivate']]
    return {'total': cc['contributionCalendar']['totalContributions'],
            'commits': cc['totalCommitContributions'] + cc['restrictedContributionsCount'],
            'prs': cc['totalPullRequestContributions'], 'issues': cc['totalIssueContributions'],
            'followers': u['followers']['totalCount'], 'repos': len(pub), 'stars': sum(r['stargazerCount'] for r in pub),
            'best': best, 'busy': busy, 'langs': langs, 'other': round(100 - sum(l['pct'] for l in langs), 1),
            'asof': days[-1]['date']}, days

# ---------- ฝังฟอนต์ (GitHub ไม่ให้ SVG ใน <img> โหลดฟอนต์จากข้างนอก) ----------
FONT_DIR = pathlib.Path(__file__).resolve().parent.parent / 'fonts'
FACES = [('IBM Plex Sans Thai', 400, 'IBMPlexSansThai-Regular.ttf'), ('IBM Plex Sans Thai', 700, 'IBMPlexSansThai-Bold.ttf'),
         ('IBM Plex Mono', 400, 'IBMPlexMono-Regular.ttf')]
_font_cache = {}

def subset_woff2(path, text):
    from fontTools.ttLib import TTFont
    from fontTools.subset import Subsetter, Options
    key = (path, ''.join(sorted(set(text))))
    if key in _font_cache: return _font_cache[key]
    f = TTFont(path); opt = Options(); opt.flavor = 'woff2'; opt.desubroutinize = True; opt.drop_tables += ['meta']
    opt.layout_features = ['*']   # เก็บ ccmp/mark/mkmk ครบ ไม่งั้น สระอำ และวรรณยุกต์ไทยหาย
    s = Subsetter(opt); s.populate(text=text); s.subset(f)
    buf = io.BytesIO(); f.flavor = 'woff2'; f.save(buf)
    _font_cache[key] = buf.getvalue(); return _font_cache[key]

def embed_fonts(svg):
    body = re.sub(r'<style>.*?</style>', '', svg, flags=re.S)  # ตัด CSS ออกก่อน ไม่งั้นจะนับตัวอักษรใน CSS ด้วย
    text = ''.join(re.findall(r'>([^<]+)<', body))          # เฉพาะตัวอักษรที่แสดงจริง
    if not text.strip(): return svg
    faces = ''
    for fam, wt, fn in FACES:
        p = FONT_DIR / fn
        if not p.exists(): print('font missing:', p, file=sys.stderr); continue
        b64 = base64.b64encode(subset_woff2(str(p), text + ' 0123456789\u0e4d\u0e32\u0e33')).decode()
        faces += f"@font-face{{font-family:'{fam}';font-weight:{wt};src:url(data:font/woff2;base64,{b64}) format('woff2')}}\n"
    return svg.replace('<style>', '<style>\n' + faces, 1)

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--login', default=os.environ.get('GH_LOGIN', 'VoramethP'))
    ap.add_argument('--out', default=str(pathlib.Path(__file__).resolve().parent.parent / 'profile' / 'cards'))
    ap.add_argument('--data', help='ใช้ไฟล์ JSON ที่ดึงไว้แล้วแทนการเรียก API (สำหรับทดสอบ)')
    ap.add_argument('--no-fonts', action='store_true')
    a = ap.parse_args()
    if a.data:
        u = json.load(open(a.data))['data']['user']
    else:
        token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        if not token: raise SystemExit('ต้องมี GH_TOKEN (PAT ที่อ่าน private repo ได้) หรือ GITHUB_TOKEN')
        u = fetch(a.login, token)
    d, days = summarise(u)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for theme, p in PAL.items():
        files = {'hero': hero(p, d), 'contrib': contributions(p, d, days), 'langs': languages(p, d), 'divider': divider(p), 'footer': footer(p)}
        for i, t in enumerate(tiles(p)): files[f'tile{i+1}'] = t
        for name, svg in files.items():
            if not a.no_fonts: svg = embed_fonts(svg)
            (out / f'{name}-{theme}.svg').write_text(svg, encoding='utf-8')
    print(f"rendered {len(PAL)*8} cards → {out} · contributions {d['total']:,} · as of {d['asof']}")

if __name__ == '__main__':
    main()
