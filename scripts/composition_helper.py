#!/usr/bin/env python3
"""
composition_helper.py — 标准 Composition 工具库

所有 Hermes 的 gen_compositions.py 必须 import 此模块（不import = 违规）。
提供：
  1. GSAP 头部 + CSS design token 变量注入
  2. 布局类名（harness 可识别）
  3. Standalone 模式自动注入
  4. 品牌色验证
  5. 管线状态闸门（T6 前必须 T5 完成）
"""

import json, os, sys


def check_pipeline_gate():
    """
    T6 前置闸门：校验管线状态。
    如果 T5 未完成，拒绝继续。
    """
    # Try to find pipeline_state.json in cwd or parent dirs
    for start in [os.getcwd()] + [os.path.dirname(os.getcwd())]:
        sp = os.path.join(start, "pipeline_state.json")
        if os.path.exists(sp):
            with open(sp) as f:
                state = json.load(f)
            steps = state.get("steps", {})
            t5 = steps.get("T5", {}).get("status", "")
            t6 = steps.get("T6", {}).get("status", "")
            if t6 == "done":
                return  # Already past T6, fine
            if t5 == "skipped":
                return  # Explicitly skipped, fine
            if t5 != "done":
                print("\n" + "!" * 60)
                print("!  BLOCKED: T5 (配图) 未完成")
                print("!  composition_helper 要求 T5 图片就绪后再生成 composition")
                print("!  解决方案:")
                print("!    A) 完成 T5: python3 scripts/generate_images.py . --api wuyinkeji")
                print("!    B) 显式跳过: python3 scripts/pipeline.py skip --step T5")
                print("!" * 60 + "\n")
                sys.exit(1)
            return

# Run gate check on import
check_pipeline_gate()

# 支持的设计风格
DESIGN_PROFILES = {
    "mintlify": {
        "brand_color": "#00d4a4",
        "font_body": "Inter",
        "surface": "#f7f7f7",
        "ink": "#0a0a0a",
        "charcoal": "#1c1c1e",
        "steel": "#5a5a5c",
    },
    "notion": {
        "brand_color": "#5645d4",
        "font_body": "Notion Sans",
        "surface": "#f6f5f4",
        "ink": "#1a1a1a",
        "charcoal": "#37352f",
        "steel": "#5d5b54",
    },
    "linear.app": {
        "brand_color": "#5e6ad2",
        "font_body": "Inter",
        "surface": "#0f1011",
        "ink": "#f7f8f8",
        "charcoal": "#010102",
        "steel": "#8a8f98",
    },
}

# 布局类名前缀（harness LAYOUT_NAMES 需要识别）
LAYOUT_CLASSES = {
    "hero": "hero-container",
    "concept": "content-row",
    "flipped": "content-row flipped", 
    "comparison": "compare-row",
    "flowchart": "flow-row",
    "chart": "chart-row",
    "quote": "quote-wrap",
    "card-grid": "card-grid",
    "timeline": "timeline-h",
    "code-block": "code-block",
}


def get_design_tokens(style="mintlify"):
    """获取设计令牌 CSS 变量字符串"""
    profile = DESIGN_PROFILES.get(style, DESIGN_PROFILES.get("mintlify"))
    return f"""
:root {{
  --md-brand: {profile['brand_color']};
  --md-surface: {profile['surface']};
  --md-ink: {profile['ink']};
  --md-charcoal: {profile['charcoal']};
  --md-steel: {profile['steel']};
  --md-font: {profile['font_body']}, -apple-system, BlinkMacSystemFont, sans-serif;
  --md-radius: 12px;
  --md-space: 24px;
}}
"""


def gsap_head(style="mintlify"):
    """生成 <head> 内容：GSAP CDN + CSS 令牌 + Google Fonts"""
    tokens = get_design_tokens(style)
    profile = DESIGN_PROFILES.get(style, DESIGN_PROFILES.get("mintlify"))
    font_import = f'@import url("https://fonts.googleapis.com/css2?family={profile["font_body"].replace(" ", "+")}:wght@400;500;600;700&display=swap");'
    return f'''<meta charset="UTF-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1920px;height:1080px;overflow:hidden;font-family:var(--md-font);background:#fff}}
{tokens}
</style>'''


def gsap_timeline(sid, duration, fade_in_selectors=None):
    """
    生成 GSAP timeline + __hf + standalone 样板代码。
    
    sid: 场景编号（如 "s1"）
    duration: 场景时长
    fade_in_selectors: [(selector, {gsap_from_options}), ...]
                       如果为 None，自动检测 .hf-animate 元素
    """
    js = f'''(function(){{
  var tl = gsap.timeline({{paused:true}});
  var sc = '[data-composition-id="{sid}"]';'''

    if fade_in_selectors:
        for sel, opts in fade_in_selectors:
            opts_json = json.dumps(opts)
            js += f'\n  tl.from(sc+" {sel}", {opts_json});'
    else:
        # 自动检测 .hf-animate-N 元素 → 展开为独立 tl.from 调用（满足 harness ≥3 步检查）
        js += f'''
  var animEls = [];
  for(var i=1; i<=20; i++){{
    var el = document.querySelector(sc+" .hf-animate-"+i);
    if(el) animEls.push(el);
    else break;
  }}
  for(var i=0; i<animEls.length; i++){{
    tl.from(animEls[i], {{opacity:0, y:15, duration:0.3, ease:"power2.out"}}, "-=0.05");
  }}'''

    js += f'''
  window.__timelines = window.__timelines || {{}};
  window.__timelines["{sid}"] = tl;
  window.__hf = window.__hf || {{}};
  window.__hf["{sid}"] = {{duration:{duration}, seek:function(t){{var tl=window.__timelines&&window.__timelines["{sid}"];if(tl)tl.seek(t);}}}};
}})();
if(top===self){{var tl=window.__timelines&&window.__timelines["{sid}"];if(tl)tl.progress(1);}}'''
    return js


def scene_wrapper(sid, layout, inner_html, duration):
    """
    生成完整 scene HTML。
    
    layout: hero / concept / flipped / comparison / flowchart / chart / quote / card-grid / timeline
    inner_html: 页面主体内容
    duration: 页面时长
    """
    cls = LAYOUT_CLASSES.get(layout, "content-row")
    return f'''<!DOCTYPE html>
<html lang="zh-CN"><head>{gsap_head()}</head>
<body>
<div data-composition-id="{sid}" data-width="1920" data-height="1080"
     class="{cls}" style="width:1920px;height:1080px;position:relative;overflow:hidden;">
{inner_html}
</div>
<script>{gsap_timeline(sid, duration)}</script>
</body></html>'''


def index_html(pages, total_duration):
    """
    生成主 index.html。
    
    pages: [(sid, src, start, duration), ...]
    total_duration: 总时长
    """
    items = '\n'.join(
        f'  <div data-composition-id="{sid}" data-composition-src="{src}" '
        f'data-start="{start:.1f}" data-duration="{duration:.1f}" data-width="1920" data-height="1080"></div>'
        for sid, src, start, duration in pages
    )
    return f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<style>*{{margin:0;padding:0}}html,body{{width:1920px;height:1080px;overflow:hidden;background:#000}}</style>
</head><body>
<div id="root" data-composition-id="main" data-start="0"
     data-duration="{total_duration:.1f}" data-width="1920" data-height="1080">
{items}
</div>
<script>
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = gsap.timeline({{paused:true}});
window.__hf = window.__hf || {{}};
window.__hf["main"] = {{duration:{total_duration:.1f}, seek:function(t){{var tl=window.__timelines&&window.__timelines["main"];if(tl)tl.seek(t);}}}};
</script>
</body></html>'''


def verify_brand_color(project_dir):
    """验证 composition 是否使用了正确的品牌色"""
    profile = DESIGN_PROFILES.get("mintlify")
    expected = profile["brand_color"]
    comp_dir = os.path.join(project_dir, "compositions")
    if not os.path.isdir(comp_dir):
        return 0, 0
    ok, total = 0, 0
    for fname in sorted(os.listdir(comp_dir)):
        if not fname.endswith(".html"):
            continue
        with open(os.path.join(comp_dir, fname)) as f:
            c = f.read()
        total += 1
        if expected in c:
            ok += 1
    return ok, total


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "--verify":
        project = sys.argv[2] if len(sys.argv) > 2 else "."
        ok, total = verify_brand_color(os.path.expanduser(project))
        print(f"Brand color check: {ok}/{total} pages use #00d4a4")
        sys.exit(0 if ok == total else 1)
    else:
        print("composition_helper.py — Composition 标准工具库")
        print("用法:")
        print("  from composition_helper import scene_wrapper, index_html, gsap_head")
        print("  html = scene_wrapper('s1', 'hero', '<div>...</div>', 18.3)")
        print("  python3 composition_helper.py --verify <project_dir>")
