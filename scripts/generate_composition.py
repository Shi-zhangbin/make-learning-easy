#!/usr/bin/env python3
"""
# ⚠️ DEPRECATED: 优先使用 HyperFrames Block Catalog。
# 仅当没有匹配的 block 时才用此脚本。
# 参考 BLOCKS.md 查看内容类型→block 映射。

generate_composition.py — 设计系统驱动的 composition 生成器

10 种布局，36 套 html-ppt 主题 + 73 套 DESIGN.md 颜色+排版令牌。
用法:
  python3 scripts/generate_composition.py --list-layouts
  python3 scripts/generate_composition.py --layout hero --sid s1 -o scene.html
  python3 scripts/generate_composition.py --design-system designs/xxx/DESIGN.md --layout concept ...
"""

import argparse, json, os, re, sys, random

GSAP = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"

# ── Design system loader ──

def load_design_system(path):
    """Read DESIGN.md, return {colors, typography, rounded, spacing}."""
    if not path or not os.path.exists(path):
        return {}
    with open(path) as f:
        text = f.read()
    m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if not m:
        return {}
    front = m.group(1)
    result, section, sub = {}, None, None
    for line in front.split('\n'):
        s = line.rstrip()
        st = s.strip()
        if not st or st.startswith('#'):
            continue
        # Top-level section header (non-indented, ends with :)
        if st.endswith(':') and not st.startswith('-') and ' ' not in st.rstrip(':') and not s[0] in (' ', '\t'):
            section = st.rstrip(':')
            sub = None
            continue
        if not section:
            continue
        if section == 'colors':
            if (s.startswith(' ') or s.startswith('\t')) and ':' in s:
                k, v = s.split(':', 1)
                vv = v.strip().strip('"').strip("'")
                if vv.startswith('#') or vv.startswith('rgb'):
                    result.setdefault('colors', {})[k.strip()] = vv
        elif section == 'rounded':
            if (s.startswith(' ') or s.startswith('\t')) and ':' in s:
                k, v = s.split(':', 1)
                result.setdefault('rounded', {})[k.strip()] = v.strip().strip('"').strip("'")
        elif section == 'spacing':
            if (s.startswith(' ') or s.startswith('\t')) and ':' in s:
                k, v = s.split(':', 1)
                result.setdefault('spacing', {})[k.strip()] = v.strip().strip('"').strip("'")
        elif section in ('typography', 'components'):
            # Sub-key: "  display-mega:" or "  button-primary:"
            if st.endswith(':') and not st.startswith('-') and s[0] in (' ', '\t'):
                sub = st.rstrip(':')
                result.setdefault(section, {})[sub] = {}
                continue
            if sub and (s.startswith('  ') or s.startswith('\t')) and ':' in s:
                k, v = s.split(':', 1)
                result[section][sub][k.strip()] = v.strip().strip('"').strip("'")
            elif s[0] in (' ', '\t') and not st.endswith(':') and ':' not in s:
                pass  # description text, skip
            elif s[0] in (' ', '\t') and ':' in s:
                pass  # already handled
    return result


def pick_accent(ds):
    """Pick visible accent color from a design system dict."""
    colors = ds.get('colors', {}) if isinstance(ds, dict) else ds if isinstance(ds, dict) else {}
    for key in ['brand-green', 'brand-green-deep', 'brand-tag', 'primary',
                'brand-warn', 'brand-error', 'link', 'cyan', 'violet']:
        if key in colors:
            v = colors[key]
            if _visible(v):
                return v
    for v in colors.values():
        if isinstance(v, str) and v.startswith('#') and _visible(v):
            return v
    return '#00d4a4'


def pick_bg(ds):
    colors = ds.get('colors', {}) if isinstance(ds, dict) else ds if isinstance(ds, dict) else {}
    top = colors.get('hero-dark-from', colors.get('canvas-dark', '#0a0a1a'))
    bot = colors.get('hero-dark-to', colors.get('primary', '#1a0a2e'))
    return top, bot


def _visible(h):
    try:
        hx = h.lstrip('#')
        if len(hx) == 3: hx = ''.join(c*2 for c in hx)
        if len(hx) != 6: return True
        r, g, b = int(hx[:2],16), int(hx[2:4],16), int(hx[4:],16)
        return 0.299*r + 0.587*g + 0.114*b < 180
    except:
        return True


# ── Base HTML ──

def _base(sid, dur, css, js, extra_css=""):
    return f"""<!doctype html><html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=1920,height=1080">
<script src="{GSAP}"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:1920px;height:1080px;overflow:hidden;background:#000;}}
section{{width:1920px;height:1080px;overflow:hidden;position:relative;}}
{extra_css}
{css}
</style></head><body>
<section data-composition-id="{sid}" data-width="1920" data-height="1080">
{{CONTENT}}
</section>
<script>(function(){{
var tl=gsap.timeline({{paused:true}});
{js}
window.__timelines=window.__timelines||{{}};window.__timelines["{sid}"]=tl;
window.__hf=window.__hf||{{}};window.__hf["{sid}"]={{duration:{dur},seek:function(t){{var tl=window.__timelines&&window.__timelines["{sid}"];if(tl)tl.seek(t);}}}};
if(top===self)tl.progress(1);
}})();
</script></body></html>"""


SLIDE_CSS = lambda a,ff='sans-serif',fs='16px',lw='400': f"""
.sl{{width:100%;height:100%;display:flex;flex-direction:column;padding:50px 80px;position:relative;background:#ffffff;font-family:{ff};font-size:{fs};font-weight:{lw};}}
.sl::before{{content:'';position:absolute;top:0;left:0;width:4px;height:100%;background:linear-gradient(to bottom,{a},{a}cc);}}
.badge{{font-size:11px;color:{a};letter-spacing:2px;font-weight:600;margin-bottom:8px;}}
h2{{font-size:46px;font-weight:700;color:#0a0a0a;line-height:1.15;margin-bottom:16px;}}
.pr{{position:absolute;bottom:18px;right:28px;font-size:13px;color:#888;}}
.card{{background:#fafafa;border:1px solid #e5e5e5;border-radius:8px;padding:16px 18px;margin-bottom:10px;}}
.card-t{{font-size:16px;font-weight:600;color:#0a0a0a;margin-bottom:3px;}}
.card-b{{font-size:14px;color:#5a5a5c;line-height:1.5;}}
"""


# ── Layouts ──

def layout_hero(sid, dur, d):
    a = d.get('accent', '#00d4a4')
    bg_t = d.get('bg_top', '#0a0a1a')
    bg_b = d.get('bg_bot', '#1a0a2e')
    css = f"""
.h{{width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;
background:linear-gradient(135deg,{bg_t},{bg_b});padding:60px;position:relative;}}
.b{{font-size:11px;color:{a};letter-spacing:2px;font-weight:600;margin-bottom:10px;opacity:.8;}}
h1{{font-size:{d.get("h1_size","80px")};font-weight:{d.get("heading_weight","700")};color:#fff;text-align:center;line-height:{d.get("heading_line","1.15")};margin-bottom:14px;letter-spacing:{d.get("heading_letter","-.03em")};}}
.sub{{font-size:22px;color:rgba(255,255,255,.7);text-align:center;max-width:1200px;margin-bottom:30px;}}
.pr{{position:absolute;bottom:18px;right:28px;font-size:13px;color:rgba(255,255,255,.3);}}
"""
    content = f'<div class="h"><div class="b">{d.get("badge","")}</div><h1>{d.get("title","")}</h1><div class="sub">{d.get("subtitle","")}</div><div class="pr">{d.get("page_num","")}</div></div>'
    js = 'tl.from(".h>*",{opacity:0,y:12,duration:.35,stagger:.05});'
    ff = d.get("display_font","sans-serif")
    return _base(sid, dur, css, js, extra_css=f"body{{font-family:{ff};}}").replace("{CONTENT}", content)

def layout_concept(sid, dur, d, flip=False):
    a = d.get('accent', '#00d4a4')
    ff = d.get("body_font","sans-serif")
    fs = d.get("body_size","16px")
    lw = d.get("body_weight","400")
    dir_css = "flex-direction:row-reverse;" if flip else ""
    css = SLIDE_CSS(a, ff, fs, lw) + f"""
.con{{display:flex;flex:1;gap:40px;{dir_css}}}
.con-l{{flex:1;display:flex;flex-direction:column;justify-content:center;}}
.con-r{{flex:1;display:flex;align-items:center;justify-content:center;background:#f5f5f5;border-radius:10px;min-height:400px;}}
"""
    cards = d.get('cards',[]) or [{"t":f"点{i+1}","b":b} for i,b in enumerate(d.get("body",["内容"]))]
    ch = "".join(f'<div class="card"><div class="card-t">{c.get("t","")}</div><div class="card-b">{c.get("b","")}</div></div>' for c in cards)
    img = f'<img src="{d.get("image","")}" class="con-img" alt="">' if d.get("image") else '<div style="color:#aaa;">配图</div>'
    content = f'<div class="sl"><div class="badge">{d.get("badge","")}</div><h2>{d.get("title","")}</h2><div class="con"><div class="con-l">{ch}</div><div class="con-r">{img}</div></div><div class="pr">{d.get("page_num","")}</div></div>'
    js = 'tl.from(".badge,h2,.con>*",{opacity:0,y:10,duration:.3,stagger:.04});'
    return _base(sid, dur, css, js).replace("{CONTENT}", content)

def layout_flipped(sid, dur, d): return layout_concept(sid, dur, d, flip=True)

def layout_comparison(sid, dur, d):
    a = d.get('accent','#00d4a4')
    css = SLIDE_CSS(a) + f"""
.cp{{display:flex;flex:1;gap:30px;}}
.col{{flex:1;background:#fafafa;border:1px solid #e5e5e5;border-radius:8px;padding:24px;}}
.col-h{{font-size:20px;font-weight:700;margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid {a};}}
.col-b{{font-size:15px;color:#5a5a5c;line-height:1.6;flex:1;}}
"""
    cols = d.get('columns',[]) or [{"h":"左侧","b":"A"},{"h":"右侧","b":"B"}]
    ch = "".join(f'<div class="col"><div class="col-h">{c.get("h","")}</div><div class="col-b">{c.get("b","")}</div></div>' for c in cols)
    content = f'<div class="sl"><div class="badge">{d.get("badge","")}</div><h2>{d.get("title","")}</h2><div class="cp">{ch}</div><div class="pr">{d.get("page_num","")}</div></div>'
    js = 'tl.from(".badge,h2,.cp>*",{opacity:0,y:10,duration:.3,stagger:.04});'
    return _base(sid, dur, css, js).replace("{CONTENT}", content)

def layout_code(sid, dur, d):
    a = d.get('accent','#00d4a4'); cf = d.get("code_font","monospace")
    css = f"""
.cw{{width:100%;height:100%;display:flex;flex-direction:column;padding:40px 60px;position:relative;background:#f8f6ff;}}
.ch{{font-size:11px;color:{a};letter-spacing:2px;font-weight:600;margin-bottom:6px;}}
.ct{{font-size:36px;font-weight:700;color:#0a0a0a;margin-bottom:14px;}}
.cb{{flex:1;background:#13131a;border-radius:10px;padding:20px 24px;overflow:hidden;}}
.cb code{{font-family:{cf};font-size:13px;line-height:1.5;color:#e0e0e0;white-space:pre;}}
.pr{{position:absolute;bottom:18px;right:28px;font-size:13px;color:#888;}}
"""
    content = f'<div class="cw"><div class="ch">{d.get("badge","")}</div><div class="ct">{d.get("title","")}</div><div class="cb"><code>{d.get("code","")}</code></div><div class="pr">{d.get("page_num","")}</div></div>'
    js = 'tl.from(".ch,.ct,.cb",{opacity:0,y:10,duration:.3,stagger:.04});'
    return _base(sid, dur, css, js).replace("{CONTENT}", content)

def layout_card_grid(sid, dur, d):
    a = d.get('accent','#00d4a4'); n = min(d.get('cols',3),4)
    css = SLIDE_CSS(a) + f"""
.gd{{display:grid;flex:1;grid-template-columns:repeat({n},1fr);gap:16px;}}
.gc{{background:#fafafa;border:1px solid #e5e5e5;border-radius:8px;padding:16px;}}
.gc-t{{font-size:15px;font-weight:600;margin-bottom:4px;}}
.gc-b{{font-size:13px;color:#5a5a5c;line-height:1.4;}}
"""
    cards = d.get('cards',[]) or [{"t":f"卡{i}","b":b} for i,b in enumerate(d.get("body",[""]*4))]
    ch = "".join(f'<div class="gc"><div class="gc-t">{c.get("t","")}</div><div class="gc-b">{c.get("b","")}</div></div>' for c in cards)
    content = f'<div class="sl"><div class="badge">{d.get("badge","")}</div><h2>{d.get("title","")}</h2><div class="gd">{ch}</div><div class="pr">{d.get("page_num","")}</div></div>'
    js = 'tl.from(".badge,h2,.gc",{opacity:0,y:8,duration:.25,stagger:.03});'
    return _base(sid, dur, css, js).replace("{CONTENT}", content)

def layout_flowchart(sid, dur, d):
    a = d.get('accent','#00d4a4')
    css = SLIDE_CSS(a) + f"""
.fl{{display:flex;flex:1;flex-direction:column;justify-content:center;gap:12px;padding:20px 0;}}
.fr{{display:flex;justify-content:center;gap:12px;}}
.fb{{background:#f0f4ff;border:1px solid {a}44;border-radius:8px;padding:10px 18px;font-size:14px;color:#333;text-align:center;min-width:120px;}}
.fa{{display:flex;align-items:center;justify-content:center;font-size:20px;color:{a};}}
"""
    rows = d.get('rows', [{"boxes":["A","B"]},{"boxes":["C"]}])
    rh = ""
    for row in rows:
        rh += '<div class="fr">' + "".join(f'<div class="fb">{b}</div>' for b in row.get("boxes",[])) + '</div>'
        if row.get("arrow",True): rh += '<div class="fa">↓</div>'
    content = f'<div class="sl"><div class="badge">{d.get("badge","")}</div><h2>{d.get("title","")}</h2><div class="fl">{rh}</div><div class="pr">{d.get("page_num","")}</div></div>'
    js = 'tl.from(".badge,h2,.fr,.fa",{opacity:0,y:8,duration:.25,stagger:.04});'
    return _base(sid, dur, css, js).replace("{CONTENT}", content)

def layout_quote(sid, dur, d):
    a = d.get('accent','#00d4a4')
    css = f"""
.qw{{width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;
background:linear-gradient(135deg,{d.get("bg_top","#0a0a1a")},{d.get("bg_bot","#1a0a2e")});padding:80px;position:relative;}}
.qi{{font-size:60px;color:{a};margin-bottom:20px;opacity:.3;}}
.qt{{font-size:36px;font-weight:400;color:#fff;text-align:center;line-height:1.4;max-width:1400px;margin-bottom:20px;font-style:italic;}}
.qa{{font-size:18px;color:rgba(255,255,255,.6);}}
.pr{{position:absolute;bottom:18px;right:28px;font-size:13px;color:rgba(255,255,255,.3);}}
"""
    content = f'<div class="qw"><div class="qi">"</div><div class="qt">{d.get("text","")}</div><div class="qa">{d.get("author","")}</div><div class="pr">{d.get("page_num","")}</div></div>'
    js = 'tl.from(".qi,.qt,.qa",{opacity:0,y:15,duration:.4,stagger:.06});'
    return _base(sid, dur, css, js).replace("{CONTENT}", content)

def layout_timeline(sid, dur, d):
    a = d.get('accent','#00d4a4')
    css = SLIDE_CSS(a) + f"""
.tl{{display:flex;flex:1;flex-direction:column;justify-content:center;position:relative;padding:20px 0 20px 30px;}}
.tl::before{{content:'';position:absolute;left:10px;top:40px;bottom:40px;width:2px;background:{a};}}
.tli{{position:relative;padding:8px 0 8px 30px;}}
.tli::before{{content:'';position:absolute;left:-3px;top:14px;width:8px;height:8px;border-radius:50%;background:{a};}}
.tli-t{{font-size:13px;color:{a};font-weight:600;}}
.tli-b{{font-size:15px;color:#333;}}
"""
    items = d.get('items',[]) or [{"t":"Step 1","b":"开始"},{"t":"Step 2","b":"执行"},{"t":"Step 3","b":"完成"}]
    ih = "".join(f'<div class="tli"><div class="tli-t">{i.get("t","")}</div><div class="tli-b">{i.get("b","")}</div></div>' for i in items)
    content = f'<div class="sl"><div class="badge">{d.get("badge","")}</div><h2>{d.get("title","")}</h2><div class="tl">{ih}</div><div class="pr">{d.get("page_num","")}</div></div>'
    js = 'tl.from(".badge,h2,.tli",{opacity:0,x:-8,duration:.3,stagger:.04});'
    return _base(sid, dur, css, js).replace("{CONTENT}", content)

def layout_chart(sid, dur, d):
    a = d.get('accent','#00d4a4')
    bars = d.get('bars',[{"l":"A","v":3},{"l":"B","v":7},{"l":"C","v":5}])
    mv = max(b.get("v",1) for b in bars) or 1
    bh = "".join(f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:6px;"><div style="font-size:11px;color:#888;">{b.get("l","")}</div><div style="width:40px;height:{b["v"]/mv*80}%;background:linear-gradient(to top,{a},{a}88);border-radius:4px 4px 0 0;min-height:10px;"></div><div style="font-size:13px;font-weight:600;">{b.get("v","")}</div></div>' for b in bars)
    css = SLIDE_CSS(a) + ".cht{display:flex;flex:1;align-items:flex-end;justify-content:center;gap:12px;padding:20px 0 40px;}"
    content = f'<div class="sl"><div class="badge">{d.get("badge","")}</div><h2>{d.get("title","")}</h2><div class="cht">{bh}</div><div class="pr">{d.get("page_num","")}</div></div>'
    js = 'tl.from(".badge,h2,.cht>*",{opacity:0,y:10,duration:.3,stagger:.03});'
    return _base(sid, dur, css, js).replace("{CONTENT}", content)


LAYOUTS = {
    "hero":layout_hero, "concept":layout_concept, "flipped":layout_flipped,
    "comparison":layout_comparison, "data-chart":layout_chart,
    "flowchart":layout_flowchart, "quote":layout_quote,
    "card-grid":layout_card_grid, "timeline-h":layout_timeline,
    "code-block":layout_code,
}


# ── Main ──

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--layout", choices=list(LAYOUTS)+["random"], default="concept")
    p.add_argument("--sid", default="s1")
    p.add_argument("--duration", type=float, default=10)
    p.add_argument("--output","-o")
    p.add_argument("--print", action="store_true")
    p.add_argument("--title", default="TITLE")
    p.add_argument("--badge", default="")
    p.add_argument("--accent")
    p.add_argument("--subtitle", default="")
    p.add_argument("--page-num", default="")
    p.add_argument("--body", action="append", default=[])
    p.add_argument("--code")
    p.add_argument("--data-file")
    p.add_argument("--design-system", help="DESIGN.md 路径，自动读取颜色+排版")
    p.add_argument("--list-layouts", action="store_true")
    args = p.parse_args()

    if args.list_layouts:
        for k in sorted(LAYOUTS.keys()):
            ds = {"hero":"封面","concept":"左文右图","flipped":"左图右文",
                  "comparison":"双栏","data-chart":"柱状图","flowchart":"流程图",
                  "quote":"引用","card-grid":"卡片","timeline-h":"时间轴","code-block":"代码"}
            print(f"  {k:15s} {ds.get(k,'')}")
        return

    if args.data_file:
        with open(args.data_file) as f:
            d = json.load(f)
    elif args.design_system:
        ds = load_design_system(args.design_system)
        colors = ds.get('colors', {}) if isinstance(ds, dict) else {}
        typography = ds.get('typography', {}) if isinstance(ds, dict) else {}
        accent = args.accent or pick_accent(ds)
        bg_top, bg_bot = pick_bg(ds)
        dm = typography.get('display-mega', {}) if isinstance(typography, dict) else {}
        bm = typography.get('body-md', {}) if isinstance(typography, dict) else {}
        co = typography.get('code', {}) if isinstance(typography, dict) else {}
        d = {"badge":args.badge, "title":args.title, "accent":accent,
             "subtitle":args.subtitle, "page_num":args.page_num,
             "code":args.code, "body":args.body,
             "bg_top":bg_top, "bg_bot":bg_bot,
             "display_font":dm.get('fontFamily','sans-serif'),
             "body_font":bm.get('fontFamily','sans-serif'),
             "code_font":co.get('fontFamily','monospace'),
             "h1_size":dm.get('fontSize','80px'),
             "body_size":bm.get('fontSize','16px'),
             "heading_weight":dm.get('fontWeight','700'),
             "body_weight":bm.get('fontWeight','400'),
             "heading_letter":dm.get('letterSpacing','-.03em'),
             "heading_line":dm.get('lineHeight','1.15')}
    else:
        accent = args.accent or '#00d4a4'
        d = {"badge":args.badge, "title":args.title, "accent":accent,
             "subtitle":args.subtitle, "page_num":args.page_num,
             "code":args.code, "body":args.body}

    layout = args.layout
    if layout == "random":
        layout = random.choice(list(LAYOUTS.keys()))

    fn = LAYOUTS.get(layout)
    if not fn:
        print(f"❌ 未知: {layout}"); sys.exit(1)

    html = fn(args.sid, args.duration, d)
    if args.print:
        print(html)
    elif args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            f.write(html)
        print(f"✅ {args.output} ({layout}, {args.duration}s)")
    else:
        print(html)


if __name__ == "__main__":
    main()
