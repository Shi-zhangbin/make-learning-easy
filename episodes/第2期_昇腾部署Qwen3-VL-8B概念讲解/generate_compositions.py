#!/usr/bin/env python3
"""Generate 29 HyperFrames composition files + index.html for the video."""

import json
import os
import re

BASE = os.path.expanduser("~/Desktop/ascend-pipeline/episodes/第2期_昇腾部署Qwen3-VL-8B概念讲解")
IMG_JSON = os.path.join(BASE, "05_图片素材", "images_b64.json")
TIMELINE_JSON = os.path.join(BASE, "03_音频", "timeline.json")
OUT_DIR = os.path.join(BASE, "06_Compositions", "compositions")
INDEX_PATH = os.path.join(BASE, "index.html")

# Load data
with open(IMG_JSON, "r") as f:
    images_data = json.load(f)
all_images = images_data.get("images", {})

with open(TIMELINE_JSON, "r") as f:
    timeline_data = json.load(f)
slides = timeline_data.get("slides", [])

# Build slide lookup by id (both padded and unpadded)
slide_map = {}
for s in slides:
    slide_map[s["id"]] = s
    # Also add unpadded version for pages 1-9
    unpadded = s["id"].lstrip("s").lstrip("0")
    if unpadded:
        slide_map[f"s{unpadded}"] = s

def get_img(key):
    """Get base64 image URL by exact key."""
    return all_images.get(key, "")

def make_style(page_id, layout):
    """Generate CSS for the composition."""
    is_hero = layout == "hero"
    is_dark = layout in ("hero", "quote")
    
    bg = "#0D1B2A" if is_dark else "#FFFFFF"
    title_color = "#FFFFFF" if is_dark else "#0D1B2A"
    text_color = "#E0E0E0" if is_dark else "#333333"
    subtitle_color = "#A0A0A0" if is_dark else "#666666"
    
    return f"""<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 1920px; height: 1080px; overflow: hidden; font-family: sans-serif; background: {bg}; }}
.page-container {{ width: 1920px; height: 1080px; position: relative; display: flex; flex-direction: column; padding: 40px 60px; }}
.hero-container {{ width: 1920px; height: 1080px; position: relative; display: flex; flex-direction: column; justify-content: center; align-items: center; background: linear-gradient(135deg, #0D1B2A 0%, #1B3A4B 50%, #0D1B2A 100%); overflow: hidden; }}
/* Hero bg glow effect */
.hero-glow {{ position: absolute; bottom: -100px; left: 50%; transform: translateX(-50%); width: 800px; height: 400px; background: radial-gradient(ellipse, rgba(0,191,165,0.15) 0%, transparent 70%); }}
.badge {{ display: inline-block; background: #00BFA5; color: #0D1B2A; font-size: 18px; font-weight: 700; padding: 6px 16px; border-radius: 8px; margin-bottom: 16px; align-self: flex-start; }}
h2 {{ font-size: 54px; color: {title_color}; margin-bottom: 30px; font-weight: 800; line-height: 1.2; }}
.hero-title {{ font-size: 80px; color: #FFFFFF; font-weight: 900; text-align: center; z-index: 1; margin-bottom: 20px; }}
.hero-subtitle {{ font-size: 32px; color: #B0BEC5; text-align: center; z-index: 1; max-width: 1200px; }}
.hero-tag {{ display: inline-block; background: #00BFA5; color: #0D1B2A; font-size: 20px; font-weight: 700; padding: 8px 24px; border-radius: 8px; margin-bottom: 30px; z-index: 1; }}
.content {{ flex: 1; display: flex; flex-direction: column; position: relative; }}
.content-row {{ display: flex; flex: 1; gap: 30px; }}
.content-left {{ flex: 1.2; display: flex; flex-direction: column; }}
.content-right {{ flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; }}
.card {{ background: #F5F7FA; border-radius: 12px; padding: 14px 20px; margin-bottom: 14px; }}
.card h4 {{ font-size: 22px; color: #0D1B2A; font-weight: 700; margin-bottom: 6px; }}
.card p {{ font-size: 18px; color: #555; line-height: 1.5; }}
.visual-img {{ max-width: 100%; max-height: 450px; border-radius: 12px; object-fit: contain; }}
/* Comparison layout */
.compare-row {{ display: flex; flex: 1; gap: 20px; }}
.compare-col {{ flex: 1; background: #F5F7FA; border-radius: 12px; padding: 20px; display: flex; flex-direction: column; }}
.compare-col h4 {{ font-size: 22px; color: #0D1B2A; font-weight: 700; margin-bottom: 10px; }}
.compare-col .icon {{ font-size: 48px; margin-bottom: 10px; text-align: center; }}
.compare-col p {{ font-size: 18px; color: #555; line-height: 1.5; }}
.compare-divider {{ width: 2px; background: #00BFA5; align-self: stretch; }}
/* Quote layout */
.quote-wrap {{ display: flex; flex: 1; flex-direction: column; justify-content: center; align-items: center; padding: 60px; }}
.quote-text {{ font-size: 36px; color: #FFFFFF; text-align: center; line-height: 1.5; max-width: 1400px; font-weight: 700; margin-bottom: 30px; }}
.quote-sub {{ font-size: 24px; color: #B0BEC5; text-align: center; margin-bottom: 20px; }}
.quote-source {{ font-size: 20px; color: #00BFA5; text-align: center; font-weight: 700; }}
/* Flowchart */
.flow-row {{ display: flex; align-items: center; justify-content: space-between; flex: 1; padding: 20px 0; }}
.flow-node {{ background: #F5F7FA; border-radius: 12px; padding: 20px; text-align: center; min-width: 220px; }}
.flow-node .fn-icon {{ font-size: 36px; }}
.flow-node .fn-title {{ font-size: 20px; font-weight: 700; color: #0D1B2A; margin: 8px 0 4px; }}
.flow-node .fn-desc {{ font-size: 16px; color: #555; }}
.flow-arrow {{ font-size: 36px; color: #00BFA5; font-weight: 700; }}
/* Data chart */
.chart-row {{ display: flex; flex-direction: column; flex: 1; justify-content: center; gap: 20px; }}
.chart-bar {{ display: flex; align-items: center; gap: 10px; }}
.chart-label {{ min-width: 100px; font-size: 16px; color: #0D1B2A; font-weight: 600; }}
.chart-fill {{ height: 40px; border-radius: 6px; background: #00BFA5; display: flex; align-items: center; padding-left: 10px; font-size: 14px; color: #fff; font-weight: 600; }}
.chart-fill-shared {{ background: #0D1B2A; }}
.chart-fill-diff {{ background: #E53935; }}
.chart-note {{ font-size: 18px; color: #555; text-align: center; margin-top: 10px; font-weight: 600; }}
/* Card grid */
.grid-row {{ display: flex; flex: 1; gap: 20px; }}
.grid-card {{ flex: 1; background: #F5F7FA; border-radius: 12px; padding: 20px; display: flex; flex-direction: column; }}
.grid-card .gc-icon {{ font-size: 40px; margin-bottom: 10px; }}
.grid-card h4 {{ font-size: 22px; color: #0D1B2A; font-weight: 700; margin-bottom: 8px; }}
.grid-card p {{ font-size: 18px; color: #555; line-height: 1.5; }}
/* Code block */
.code-wrap {{ display: flex; flex: 1; gap: 30px; }}
.code-panel {{ flex: 1.5; background: #13131a; border-radius: 12px; padding: 20px; font-family: "Courier New", monospace; font-size: 18px; color: #E0E0E0; line-height: 1.6; overflow-y: auto; }}
.code-panel .comment {{ color: #6A9955; }}
.code-panel .cmd {{ color: #569CD6; }}
.code-panel .output {{ color: #9CDCFE; }}
.code-side {{ flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; }}
/* Timeline layout */
.timeline-wrap {{ display: flex; flex: 1; flex-direction: column; justify-content: center; }}
.timeline-track {{ display: flex; align-items: flex-start; justify-content: space-between; position: relative; padding: 40px 0; }}
.timeline-track::before {{ content: ''; position: absolute; top: 70px; left: 5%; right: 5%; height: 4px; background: #00BFA5; }}
.timeline-node {{ display: flex; flex-direction: column; align-items: center; width: 30%; z-index: 1; }}
.timeline-dot {{ width: 24px; height: 24px; border-radius: 50%; background: #00BFA5; margin-bottom: 16px; }}
.timeline-node h4 {{ font-size: 22px; color: #0D1B2A; text-align: center; font-weight: 700; }}
.timeline-node p {{ font-size: 18px; color: #555; text-align: center; line-height: 1.5; margin-top: 6px; }}
/* Page number */
.page-num {{ position: absolute; bottom: 20px; right: 30px; font-size: 16px; color: #999; font-weight: 600; z-index: 10; }}
/* Bottom hint */
.bottom-hint {{ font-size: 16px; color: #999; text-align: center; margin-top: auto; padding: 10px; }}
/* Helpers */
.mt-auto {{ margin-top: auto; }}
.text-center {{ text-align: center; }}
</style>"""

def make_gsap(page_id, duration):
    """Generate GSAP timeline JS with __hf API."""
    return f"""<script>
(function() {{
  var tl = gsap.timeline({{paused:true}});
  tl.from(".hf-anim", {{opacity:0, y:20, duration:0.4, stagger:0.1}});
  tl.from(".hf-anim-delay", {{opacity:0, y:20, duration:0.3, stagger:0.15}}, "-=0.2");

  window.__timelines = window.__timelines || {{}};
  window.__timelines["{page_id}"] = tl;
  window.__hf = window.__hf || {{}};
  window.__hf["{page_id}"] = {{
    duration: {duration},
    seek: function(t) {{
      var tl = window.__timelines && window.__timelines["{page_id}"];
      if (tl) tl.seek(t);
    }}
  }};
  if(top===self)tl.progress(1);
}})();
</script>"""

# ============================================================
# Scene generators
# ============================================================

def gen_s01(page_id="s01"):
    s = slide_map[page_id]
    dur = s["duration"]
    return f"""{make_style("s01", "hero")}
<div class="hero-container">
  <div class="hero-glow"></div>
  <span class="hero-tag hf-anim">概念讲解</span>
  <h1 class="hero-title hf-anim">昇腾部署 Qwen3-VL-8B</h1>
  <p class="hero-subtitle hf-anim-delay">把一个能看图的AI，跑在国产NPU上</p>
  <div style="margin-top:40px;z-index:1;">
    <div style="display:flex;gap:6px;justify-content:center;">
      <div style="width:40px;height:3px;background:#00BFA5;border-radius:2px;"></div>
      <div style="width:40px;height:3px;background:#00BFA5;border-radius:2px;opacity:0.4;"></div>
      <div style="width:40px;height:3px;background:#00BFA5;border-radius:2px;opacity:0.3;"></div>
    </div>
  </div>
  <div class="page-num" style="color:#666;">1/29</div>
</div>
{make_gsap("s01", dur)}"""

def gen_s02(page_id="s02"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("real_P02_s02.jpg")
    return f"""{make_style("s02", "concept")}
<div class="page-container">
  <span class="badge hf-anim">💡 能力展示</span>
  <h2 class="hf-anim">Qwen3-VL 能做什么？</h2>
  <div class="content-row">
    <div class="content-left">
      <div class="card hf-anim">
        <h4>场景理解</h4>
        <p>给一张图，AI能描述场景、人物、光线——"一只橘猫趴在窗台上，阳光从左边照进来"</p>
      </div>
      <div class="card hf-anim">
        <h4>多语言OCR</h4>
        <p>39种语言文字识别，手写潦草字也能读，连价格都对得上</p>
      </div>
      <div class="card hf-anim">
        <h4>视觉编程</h4>
        <p>手绘网页草图 → AI自动生成可运行的HTML代码</p>
      </div>
    </div>
    <div class="content-right hf-anim-delay">
      <img src="{img}" class="visual-img" alt="橘猫窗台" style="border-radius:12px;max-width:100%;">
    </div>
  </div>
  <div class="page-num">2/29</div>
</div>
{make_gsap("s02", dur)}"""

def gen_s03(page_id="s03"):
    s = slide_map[page_id]
    dur = s["duration"]
    img1 = get_img("real_P03_s03.jpg")
    img2 = get_img("real_P03_s03_2.jpg")
    return f"""{make_style("s03", "flipped")}
<div class="page-container">
  <span class="badge hf-anim">🎯 三个场景</span>
  <h2 class="hf-anim">不只是识别，是真正"看懂"</h2>
  <div class="content-row" style="flex-direction:row-reverse;">
    <div class="content-left">
      <div class="card hf-anim">
        <h4>餐馆菜单</h4>
        <p>手写潦草字 → AI一字不差读出，连价格都对得上</p>
      </div>
      <div class="card hf-anim">
        <h4>草图→代码</h4>
        <p>白纸画框框 → AI生成可运行HTML</p>
      </div>
    </div>
    <div class="content-right hf-anim-delay" style="gap:10px;">
      <div style="display:flex;gap:10px;align-items:center;">
        <div style="flex:1;text-align:center;">
          <p style="font-size:14px;color:#999;margin-bottom:4px;">输入：潦草菜单</p>
          <img src="{img1}" style="max-width:100%;max-height:180px;border-radius:8px;object-fit:cover;">
        </div>
        <div style="color:#00BFA5;font-size:24px;">→</div>
        <div style="flex:1;text-align:center;">
          <p style="font-size:14px;color:#999;margin-bottom:4px;">输入：手绘草图</p>
          <img src="{img2}" style="max-width:100%;max-height:180px;border-radius:8px;object-fit:cover;">
        </div>
      </div>
    </div>
  </div>
  <div class="page-num">3/29</div>
</div>
{make_gsap("s03", dur)}"""

def gen_s04(page_id="s04"):
    s = slide_map[page_id]
    dur = s["duration"]
    bg_img = get_img("ai_P4_s04_bg.png")
    return f"""{make_style("s04", "quote")}
<div class="hero-container" style="background:linear-gradient(135deg,#0D1B2A 0%,#1B3A4B 50%,#0D1B2A 100%);">
  <div class="hero-glow"></div>
  <div class="quote-wrap" style="position:relative;z-index:1;">
    <div class="quote-text hf-anim">"这些能力，就叫视觉语言模型——它不光能看懂文字，还能看懂图片、图表、手写稿。"</div>
    <div class="quote-sub hf-anim-delay">"而今天的主角 Qwen3-VL-8B 跑在国产的昇腾NPU上，是咱们自己的芯片。"</div>
    <div class="quote-source hf-anim-delay">—— 昇腾NPU | Qwen3-VL-8B</div>
  </div>
  <div class="page-num" style="color:#666;">4/29</div>
</div>
{make_gsap("s04", dur)}"""

def gen_s05(page_id="s05"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("ai_P5_s05_visual.png")
    return f"""{make_style("s05", "comparison")}
<div class="page-container">
  <span class="badge hf-anim">🧠 第一个概念</span>
  <h2 class="hf-anim">NPU — AI专用计算卡</h2>
  <div class="compare-row hf-anim">
    <div class="compare-col">
      <div class="icon">🎮</div>
      <h4>GPU（显卡）</h4>
      <p>全能运动员，跑步游泳都能来 → 渲染画面、打游戏</p>
    </div>
    <div class="compare-divider"></div>
    <div class="compare-col">
      <div class="icon">🧠</div>
      <h4>NPU（AI芯片）</h4>
      <p>专项运动员，只练AI推理 → 效率更高、成本更低</p>
    </div>
  </div>
  <div style="text-align:center;margin-top:10px;">
    <div style="background:#F5F7FA;border-radius:8px;padding:12px 20px;display:inline-block;">
      <p style="font-size:18px;color:#0D1B2A;font-weight:600;">NPU是专门为AI计算设计的芯片，不是用来渲染画面的</p>
    </div>
  </div>
  <div class="page-num">5/29</div>
</div>
{make_gsap("s05", dur)}"""

def gen_s06(page_id="s06"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("real_P06_s06.jpg")
    return f"""{make_style("s06", "flipped")}
<div class="page-container">
  <span class="badge hf-anim">🔍 认识NPU</span>
  <h2 class="hf-anim">NPU在服务器里的样子</h2>
  <div class="content-row" style="flex-direction:row-reverse;">
    <div class="content-left">
      <div class="card hf-anim">
        <h4>/dev/davinci0</h4>
        <p>NPU在Linux中被映射成设备文件，是NPU的入口"小门"</p>
      </div>
      <div class="card hf-anim">
        <h4>npu-smi info</h4>
        <p>查看NPU状态的命令，像任务管理器——显存、温度、芯片忙不忙</p>
      </div>
    </div>
    <div class="content-right hf-anim-delay">
      <img src="{img}" class="visual-img" alt="终端截图" style="max-width:100%;border-radius:8px;">
    </div>
  </div>
  <div class="bottom-hint hf-anim-delay">记住：/dev/davinci0 → 入口 | npu-smi → 体检报告 | NPU → 发动机</div>
  <div class="page-num">6/29</div>
</div>
{make_gsap("s06", dur)}"""

def gen_s07(page_id="s07"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("ai_P7_s07_visual.png")
    return f"""{make_style("s07", "concept")}
<div class="page-container">
  <span class="badge hf-anim">📐 第二个概念</span>
  <h2 class="hf-anim">Qwen3-VL-8B — 80亿参数的"眼睛"</h2>
  <div class="content-row">
    <div class="content-left">
      <div class="card hf-anim">
        <h4>巨大数学公式</h4>
        <p>80亿个参数，如果每个参数是一个字 ≈ 一千套《红楼梦》</p>
      </div>
      <div class="card hf-anim">
        <h4>训练后能理解</h4>
        <p>见过海量图片和文字，能理解"橘猫趴在窗台上"和像素点的对应关系</p>
      </div>
      <div class="card hf-anim">
        <h4>单卡可跑</h4>
        <p>80亿参数不大，一张昇腾NPU卡就能跑起来，无需多卡并联</p>
      </div>
    </div>
    <div class="content-right hf-anim-delay">
      <img src="{img}" class="visual-img" alt="80亿参数" style="max-width:100%;border-radius:8px;">
    </div>
  </div>
  <div class="page-num">7/29</div>
</div>
{make_gsap("s07", dur)}"""

def gen_s08(page_id="s08"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("ai_P8_s08_visual.png")
    return f"""{make_style("s08", "comparison")}
<div class="page-container">
  <span class="badge hf-anim">📦 第三个概念</span>
  <h2 class="hf-anim">Docker不是虚拟机</h2>
  <div class="compare-row hf-anim">
    <div class="compare-col">
      <div class="icon">🏠🏠</div>
      <h4>虚拟机</h4>
      <p>在Windows里装软件跑完整Linux → 房间里再盖一个房间，全套装修特别重</p>
    </div>
    <div class="compare-divider"></div>
    <div class="compare-col">
      <div class="icon">🍳</div>
      <h4>Docker容器</h4>
      <p>只打包程序和依赖，直接跑在宿主机上 → 隔一个小厨房，轻量快捷</p>
    </div>
  </div>
  <div style="text-align:center;margin-top:10px;">
    <div style="background:#F5F7FA;border-radius:8px;padding:12px 20px;display:inline-block;">
      <p style="font-size:18px;color:#0D1B2A;font-weight:600;">Docker是轻量级虚拟化，不是真的虚拟机</p>
    </div>
  </div>
  <div class="page-num">8/29</div>
</div>
{make_gsap("s08", dur)}"""

def gen_s09(page_id="s09"):
    s = slide_map[page_id]
    dur = s["duration"]
    bg_img = get_img("ai_P9_s09_bg.png")
    return f"""{make_style("s09", "quote")}
<div class="hero-container" style="background:linear-gradient(135deg,#0D1B2A 0%,#1B3A4B 50%,#0D1B2A 100%);">
  <div class="hero-glow"></div>
  <div class="quote-wrap" style="position:relative;z-index:1;">
    <div class="quote-text hf-anim">"不搞清楚这三个概念，你后面每一步都会走得很痛苦。"</div>
    <div style="display:flex;gap:20px;margin:30px 0;">
      <div style="background:rgba(0,191,165,0.15);border-radius:12px;padding:16px 24px;text-align:center;">
        <span style="font-size:28px;">🧠</span>
        <p style="color:#fff;font-size:18px;margin-top:6px;">NPU<br>AI计算发动机</p>
      </div>
      <div style="background:rgba(0,191,165,0.15);border-radius:12px;padding:16px 24px;text-align:center;">
        <span style="font-size:28px;">📐</span>
        <p style="color:#fff;font-size:18px;margin-top:6px;">Qwen3-VL-8B<br>视觉语言模型</p>
      </div>
      <div style="background:rgba(0,191,165,0.15);border-radius:12px;padding:16px 24px;text-align:center;">
        <span style="font-size:28px;">📦</span>
        <p style="color:#fff;font-size:18px;margin-top:6px;">Docker<br>容器化部署</p>
      </div>
    </div>
    <div class="quote-sub hf-anim-delay">"接下来，带你完整走一遍Docker的核心逻辑——四个场景，一个故事。"</div>
  </div>
  <div class="page-num" style="color:#666;">9/29</div>
</div>
{make_gsap("s09", dur)}"""

def gen_s10(page_id="s10"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("ai_P10_s10_visual.png")
    return f"""{make_style("s10", "concept")}
<div class="page-container">
  <span class="badge hf-anim">🛋️ 场景一</span>
  <h2 class="hf-anim">镜像 = 宜家家具套装</h2>
  <div class="content-row">
    <div class="content-left">
      <div class="card hf-anim">
        <h4>什么是一个镜像</h4>
        <p>一个大箱子，里面所有木板、螺丝、说明书、L型扳手都装好了。在Docker世界，镜像把程序需要的代码、环境、依赖、配置全部打包</p>
      </div>
      <div class="card hf-anim">
        <h4>不缺任何零件</h4>
        <p>拿到镜像 = 你拥有了运行程序的一切</p>
      </div>
      <div style="margin-top:10px;background:#F0FDF9;border-radius:8px;padding:10px 16px;display:inline-block;">
        <span style="color:#0D1B2A;font-weight:600;">🛋️ 宜家家具套装 → Docker镜像</span>
      </div>
    </div>
    <div class="content-right hf-anim-delay">
      <img src="{img}" class="visual-img" alt="宜家箱子" style="max-width:100%;border-radius:8px;">
    </div>
  </div>
  <div class="page-num">10/29</div>
</div>
{make_gsap("s10", dur)}"""

def gen_s11(page_id="s11"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("ai_P11_s11_visual.png")
    return f"""{make_style("s11", "flowchart")}
<div class="page-container">
  <span class="badge hf-anim">📥 获取镜像</span>
  <h2 class="hf-anim">docker pull = 网上下单</h2>
  <div class="flow-row hf-anim">
    <div class="flow-node">
      <div class="fn-icon">🖥️</div>
      <div class="fn-title">你的电脑</div>
      <div class="fn-desc">执行 docker pull</div>
    </div>
    <div class="flow-arrow">→</div>
    <div class="flow-node">
      <div class="fn-icon">☁️</div>
      <div class="fn-title">镜像仓库</div>
      <div class="fn-desc">像宜家官网的网上商城</div>
    </div>
    <div class="flow-arrow">→</div>
    <div class="flow-node">
      <div class="fn-icon">📦</div>
      <div class="fn-title">镜像下载</div>
      <div class="fn-desc">箱子送到你家门口</div>
    </div>
    <div class="flow-arrow">→</div>
    <div class="flow-node">
      <div class="fn-icon">✅</div>
      <div class="fn-title">确认已本地</div>
      <div class="fn-desc">docker images</div>
    </div>
  </div>
  <div class="page-num">11/29</div>
</div>
{make_gsap("s11", dur)}"""

def gen_s12(page_id="s12"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("ai_P12_s12_visual.png")
    return f"""{make_style("s12", "data-chart")}
<div class="page-container">
  <span class="badge hf-anim">🧩 分层设计</span>
  <h2 class="hf-anim">分层下载 — 存一次，用多次</h2>
  <div class="chart-row hf-anim">
    <div class="chart-bar">
      <div class="chart-label">镜像A</div>
      <div style="display:flex;flex:1;gap:2px;">
        <div class="chart-fill chart-fill-shared" style="width:75%;">共用底层 90%</div>
        <div class="chart-fill chart-fill-diff" style="width:15%;">10%</div>
      </div>
    </div>
    <div class="chart-bar">
      <div class="chart-label">镜像B</div>
      <div style="display:flex;flex:1;gap:2px;">
        <div class="chart-fill chart-fill-shared" style="width:75%;">共用底层 90%</div>
        <div class="chart-fill chart-fill-diff" style="width:15%;">10%</div>
      </div>
    </div>
    <div class="chart-note">省时间省空间：共用底层，只下载差异部分</div>
    <div style="text-align:center;color:#999;font-size:16px;margin-top:6px;">像宜家书柜和电视柜共享底座</div>
  </div>
  <div class="page-num">12/29</div>
</div>
{make_gsap("s12", dur)}"""

def gen_s13(page_id="s13"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("ai_P13_s13_visual.png")
    return f"""{make_style("s13", "concept")}
<div class="page-container">
  <span class="badge hf-anim">🍳 场景二</span>
  <h2 class="hf-anim">docker run = 拆箱开火</h2>
  <div class="content-row">
    <div class="content-left">
      <div class="card hf-anim">
        <h4>创建容器</h4>
        <p>每执行一次docker run，就像在厨房里隔出一个独立小厨房。有自己的灶台（文件系统）、水槽（网络）、砧板（内存）</p>
      </div>
      <div class="card hf-anim">
        <h4>互不干扰</h4>
        <p>在小厨房炒菜不会影响大厨房。装Python3.12不影响宿主机3.10，删系统文件也伤不到宿主机</p>
      </div>
      <div style="margin-top:10px;background:#F0FDF9;border-radius:8px;padding:10px 16px;display:inline-block;">
        <span style="color:#0D1B2A;font-weight:600;">🍳 独立小厨房 → 容器隔离</span>
      </div>
    </div>
    <div class="content-right hf-anim-delay">
      <img src="{img}" class="visual-img" alt="厨房隔间" style="max-width:100%;border-radius:8px;">
    </div>
  </div>
  <div class="page-num">13/29</div>
</div>
{make_gsap("s13", dur)}"""

def gen_s14(page_id="s14"):
    s = slide_map[page_id]
    dur = s["duration"]
    return f"""{make_style("s14", "card-grid")}
<div class="page-container">
  <span class="badge hf-anim">✨ 容器核心价值</span>
  <h2 class="hf-anim">容器的三个核心优势</h2>
  <div class="grid-row hf-anim">
    <div class="grid-card">
      <div class="gc-icon">🛡️</div>
      <h4>隔离</h4>
      <p>每个容器互不干扰。油烟不飘到大厨房，用完就扔，干净利落</p>
    </div>
    <div class="grid-card">
      <div class="gc-icon">⚡</div>
      <h4>快速</h4>
      <p>启动毫秒级。花两分钟拉隔板比花两小时砌墙快得多</p>
    </div>
    <div class="grid-card">
      <div class="gc-icon">📦</div>
      <h4>可移植</h4>
      <p>把"宜家箱子"给任何人，拆箱出来的厨房一模一样。再也不会说"在我电脑上明明能跑啊"</p>
    </div>
  </div>
  <div class="bottom-hint" style="color:#999;">容器 vs 虚拟机：轻量隔离 + 毫秒启动 + 一致环境</div>
  <div class="page-num">14/29</div>
</div>
{make_gsap("s14", dur)}"""

def gen_s15(page_id="s15"):
    s = slide_map[page_id]
    dur = s["duration"]
    return f"""{make_style("s15", "comparison")}
<div class="page-container">
  <span class="badge hf-anim">⏱️ 速度对决</span>
  <h2 class="hf-anim">容器启动 vs 虚拟机启动</h2>
  <div class="compare-row hf-anim">
    <div class="compare-col" style="border:2px solid #00BFA5;">
      <div class="icon" style="font-size:48px;">⚡</div>
      <h4 style="color:#00BFA5;">容器</h4>
      <div style="font-size:36px;font-weight:800;color:#0D1B2A;margin:10px 0;">毫秒级</div>
      <p>隔板拉起来瞬间<br>"两分钟拉好隔板"</p>
    </div>
    <div class="compare-divider"></div>
    <div class="compare-col" style="border:2px solid #E53935;">
      <div class="icon" style="font-size:48px;">🐢</div>
      <h4 style="color:#E53935;">虚拟机</h4>
      <div style="font-size:36px;font-weight:800;color:#0D1B2A;margin:10px 0;">几十秒~几分钟</div>
      <p>砌一堵墙的过程<br>"两小时砌一堵墙"</p>
    </div>
  </div>
  <div style="text-align:center;margin-top:10px;">
    <div style="background:#00BFA5;border-radius:8px;padding:12px 20px;display:inline-block;">
      <p style="font-size:18px;color:#fff;font-weight:600;">容器优势 = 轻量隔离 + 毫秒启动 + 一致环境</p>
    </div>
  </div>
  <div class="page-num">15/29</div>
</div>
{make_gsap("s15", dur)}"""

def gen_s16(page_id="s16"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("ai_P16_s16_visual.png")
    return f"""{make_style("s16", "concept")}
<div class="page-container">
  <span class="badge hf-anim">🎮 场景三</span>
  <h2 class="hf-anim">--device — 把NPU"插进"容器</h2>
  <div class="content-row">
    <div class="content-left">
      <div class="card hf-anim">
        <h4>问题</h4>
        <p>AI程序在容器里跑，NPU在外面大厨房。容器默认隔离，看不到NPU</p>
      </div>
      <div class="card hf-anim">
        <h4>解决方案</h4>
        <p>--device参数 = 外接显卡坞的USB-C线。把/dev/davinci0直通到容器，性能几乎零损耗</p>
      </div>
      <div style="margin-top:10px;background:#F0FDF9;border-radius:8px;padding:10px 16px;display:inline-block;">
        <span style="color:#0D1B2A;font-weight:600;">🎮 外接显卡坞的USB-C线 → --device挂载NPU</span>
      </div>
    </div>
    <div class="content-right hf-anim-delay">
      <img src="{img}" class="visual-img" alt="显卡坞" style="max-width:100%;border-radius:8px;">
    </div>
  </div>
  <div class="page-num">16/29</div>
</div>
{make_gsap("s16", dur)}"""

def gen_s17(page_id="s17"):
    s = slide_map[page_id]
    dur = s["duration"]
    return f"""{make_style("s17", "card-grid")}
<div class="page-container">
  <span class="badge hf-anim">🔗 类比串讲</span>
  <h2 class="hf-anim">三个类比，全部串起来了</h2>
  <div class="grid-row hf-anim">
    <div class="grid-card" style="border-top:4px solid #00BFA5;">
      <div class="gc-icon">🛋️</div>
      <h4 style="color:#00BFA5;">镜像 = 宜家箱子</h4>
      <p>装了你程序需要的一切。docker pull = 网上下单</p>
    </div>
    <div class="grid-card" style="border-top:4px solid #1B3A4B;">
      <div class="gc-icon">🍳</div>
      <h4 style="color:#1B3A4B;">容器 = 独立厨房</h4>
      <p>拆箱开火 = docker run，创建独立隔离环境</p>
    </div>
    <div class="grid-card" style="border-top:4px solid #E53935;">
      <div class="gc-icon">🎮</div>
      <h4 style="color:#E53935;">--device = USB-C线</h4>
      <p>把NPU算力直通到容器，性能零损耗</p>
    </div>
  </div>
  <div style="margin-top:15px;position:relative;">
    <div style="height:4px;background:linear-gradient(90deg,#00BFA5,#1B3A4B,#E53935);border-radius:2px;"></div>
    <div style="display:flex;justify-content:space-between;margin-top:6px;">
      <span style="font-size:14px;color:#00BFA5;font-weight:600;">docker pull</span>
      <span style="font-size:14px;color:#1B3A4B;font-weight:600;">docker run</span>
      <span style="font-size:14px;color:#E53935;font-weight:600;">--device</span>
    </div>
  </div>
  <div class="page-num">17/29</div>
</div>
{make_gsap("s17", dur)}"""

def gen_s18(page_id="s18"):
    s = slide_map[page_id]
    dur = s["duration"]
    return f"""{make_style("s18", "hero")}
<div class="hero-container" style="background:linear-gradient(135deg,#0D1B2A 0%,#1B3A4B 50%,#0D1B2A 100%);">
  <div class="hero-glow"></div>
  <h1 class="hero-title hf-anim">理论结束，实战开始</h1>
  <p class="hero-subtitle hf-anim-delay">真正需要你亲手敲的命令，只有四条</p>
  <div style="margin-top:50px;display:flex;gap:15px;z-index:1;">
    <div style="width:60px;height:4px;background:#00BFA5;border-radius:2px;animation:blink 1s infinite;"></div>
    <div style="width:60px;height:4px;background:rgba(255,255,255,0.2);border-radius:2px;"></div>
    <div style="width:60px;height:4px;background:rgba(255,255,255,0.2);border-radius:2px;"></div>
    <div style="width:60px;height:4px;background:rgba(255,255,255,0.2);border-radius:2px;"></div>
  </div>
  <style>@keyframes blink {{ 0%,100%{{opacity:1;}}50%{{opacity:0.3;}}}}</style>
  <div class="page-num" style="color:#666;">18/29</div>
</div>
{make_gsap("s18", dur)}"""

def gen_s19(page_id="s19"):
    s = slide_map[page_id]
    dur = s["duration"]
    return f"""{make_style("s19", "code-block")}
<div class="page-container">
  <span class="badge hf-anim">📋 步骤 1/4 & 2/4</span>
  <h2 class="hf-anim">检查硬件 + 拉取镜像</h2>
  <div class="code-wrap hf-anim">
    <div class="code-panel">
      <span class="comment"># 第一步：检查NPU</span><br>
      <span class="cmd">npu-smi info</span><br>
      <span class="output"># 输出示例：看到NPU名称、驱动版本、显存总量</span><br>
      <span class="comment"># 如果报错 → 检查驱动/NPU卡是否插好</span><br>
      <br>
      <span class="comment"># 第二步：拉取镜像</span><br>
      <span class="cmd">docker pull qwen3-vl-8b:latest</span><br>
      <span class="output"># 分层下载：每层都是"宜家箱子"的一个零件</span><br>
      <span class="cmd">docker images</span><br>
      <span class="output"># 确认镜像已本地</span>
    </div>
    <div class="code-side">
      <div style="background:#F5F7FA;border-radius:12px;padding:16px;text-align:center;">
        <div style="font-size:48px;">🔍</div>
        <p style="font-size:18px;color:#0D1B2A;font-weight:600;margin-top:8px;">终端输出截图</p>
        <div style="background:#13131a;border-radius:8px;padding:10px;margin-top:8px;text-align:left;">
          <span style="color:#6A9955;font-size:12px;font-family:monospace;"># npu-smi info output</span><br>
          <span style="color:#9CDCFE;font-size:12px;font-family:monospace;">NPU: Ascend910B<br>Driver: 23.0.rc1<br>Memory: 32768MB</span>
        </div>
      </div>
    </div>
  </div>
  <div class="page-num">19/29</div>
</div>
{make_gsap("s19", dur)}"""

def gen_s20(page_id="s20"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("ai_P20_s20_visual.png")
    return f"""{make_style("s20", "concept")}
<div class="page-container">
  <span class="badge hf-anim">🚀 步骤 3/4</span>
  <h2 class="hf-anim">启动容器 + 挂载NPU</h2>
  <div class="content-row">
    <div class="content-left">
      <div class="card hf-anim">
        <h4>docker run --name</h4>
        <p>给容器起名字 | <strong>--device /dev/davinci0</strong>：把NPU挂载进去 | <strong>-p</strong>：端口映射暴露服务</p>
      </div>
      <div class="card hf-anim">
        <h4>docker ps</h4>
        <p>查看运行中的容器列表，状态为"Up"即正常</p>
      </div>
      <div style="background:#13131a;border-radius:8px;padding:12px 16px;margin-top:8px;">
        <code style="color:#9CDCFE;font-size:15px;font-family:monospace;">docker run --name qwen-vl --device /dev/davinci0 -p 8000:8000 qwen3-vl-8b:latest</code>
      </div>
    </div>
    <div class="content-right hf-anim-delay">
      <img src="{img}" class="visual-img" alt="NPU直通" style="max-width:100%;border-radius:8px;">
    </div>
  </div>
  <div class="page-num">20/29</div>
</div>
{make_gsap("s20", dur)}"""

def gen_s21(page_id="s21"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("real_P21_s21.jpg")
    return f"""{make_style("s21", "flipped")}
<div class="page-container">
  <span class="badge hf-anim">✅ 步骤 4/4</span>
  <h2 class="hf-anim">验证服务 — 部署完成！</h2>
  <div class="content-row" style="flex-direction:row-reverse;">
    <div class="content-left">
      <div class="card hf-anim">
        <h4>curl验证</h4>
        <p>发请求到服务器对应端口，返回AI服务信息 → 部署成功</p>
      </div>
    </div>
    <div class="content-right hf-anim-delay">
      <img src="{img}" class="visual-img" alt="curl验证" style="max-width:100%;border-radius:8px;">
    </div>
  </div>
  <div style="margin-top:15px;">
    <div style="display:flex;gap:8px;justify-content:center;">
      <div style="width:80px;height:6px;background:#00BFA5;border-radius:3px;"></div>
      <div style="width:80px;height:6px;background:#00BFA5;border-radius:3px;"></div>
      <div style="width:80px;height:6px;background:#00BFA5;border-radius:3px;"></div>
      <div style="width:80px;height:6px;background:#00BFA5;border-radius:3px;"></div>
    </div>
    <p style="text-align:center;font-size:16px;color:#999;margin-top:6px;">从硬件检查到服务上线 ✓ 已完成</p>
  </div>
  <div class="page-num">21/29</div>
</div>
{make_gsap("s21", dur)}"""

def gen_s22(page_id="s22"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("real_P22_s22.jpg")
    return f"""{make_style("s22", "concept")}
<div class="page-container">
  <span class="badge hf-anim">🖼️ 用例 1/3</span>
  <h2 class="hf-anim">图片理解 — 真正的视觉理解</h2>
  <div class="content-row">
    <div class="content-left">
      <div class="card hf-anim">
        <h4>场景</h4>
        <p>一张城市街景照片，有行人、车、招牌</p>
      </div>
      <div class="card hf-anim">
        <h4>AI回复</h4>
        <p>城市街道白天场景，左侧蓝色招牌咖啡店，门口几位顾客，右侧行人过马路…… 这不是物体检测，是真正的视觉理解</p>
      </div>
    </div>
    <div class="content-right hf-anim-delay">
      <img src="{img}" class="visual-img" alt="街景" style="max-width:100%;border-radius:8px;">
      <div style="background:#00BFA5;border-radius:12px;padding:10px 16px;margin-top:10px;max-width:100%;">
        <p style="color:#fff;font-size:16px;font-weight:600;">"城市街道白天场景，左侧蓝色招牌咖啡店..."</p>
      </div>
    </div>
  </div>
  <div class="page-num">22/29</div>
</div>
{make_gsap("s22", dur)}"""

def gen_s23(page_id="s23"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("real_P23_s23.jpg")
    return f"""{make_style("s23", "flipped")}
<div class="page-container">
  <span class="badge hf-anim">📝 用例 2/3</span>
  <h2 class="hf-anim">OCR文档识别 — 潦草字也能读</h2>
  <div class="content-row" style="flex-direction:row-reverse;">
    <div class="content-left">
      <div class="card hf-anim">
        <h4>输入</h4>
        <p>手写便签照片，字迹相当潦草</p>
      </div>
      <div class="card hf-anim">
        <h4>输出</h4>
        <p>AI一字不差读出——"周三下午三点开会，记得带笔记本，顺便买两杯咖啡"，连被划掉的词也标注了</p>
      </div>
    </div>
    <div class="content-right hf-anim-delay">
      <img src="{img}" class="visual-img" alt="手写便签" style="max-width:100%;border-radius:8px;">
    </div>
  </div>
  <div class="bottom-hint hf-anim-delay">随手拍白板/名片/合同 → AI提取文字，无需人工录入</div>
  <div class="page-num">23/29</div>
</div>
{make_gsap("s23", dur)}"""

def gen_s24(page_id="s24"):
    s = slide_map[page_id]
    dur = s["duration"]
    img = get_img("real_P24_s24.jpg")
    return f"""{make_style("s24", "concept")}
<div class="page-container">
  <span class="badge hf-anim">🎨 用例 3/3</span>
  <h2 class="hf-anim">草图生成代码 — 画出来就能跑</h2>
  <div class="content-row">
    <div class="content-left">
      <div class="card hf-anim">
        <h4>输入</h4>
        <p>纸上画网页布局——上搜索框、左导航栏、中内容区、右广告位</p>
      </div>
      <div class="card hf-anim">
        <h4>输出</h4>
        <p>AI返回完整HTML代码。保存→浏览器打开→布局颜色间距几乎一模一样</p>
      </div>
    </div>
    <div class="content-right hf-anim-delay">
      <img src="{img}" class="visual-img" alt="草图生成" style="max-width:100%;border-radius:8px;">
    </div>
  </div>
  <div class="page-num">24/29</div>
</div>
{make_gsap("s24", dur)}"""

def gen_s25(page_id="s25"):
    s = slide_map[page_id]
    dur = s["duration"]
    bg_img = get_img("ai_P25_s25_bg.png")
    return f"""{make_style("s25", "quote")}
<div class="hero-container" style="background:linear-gradient(135deg,#0D1B2A 0%,#1B3A4B 50%,#0D1B2A 100%);">
  <div class="hero-glow"></div>
  <div class="quote-wrap" style="position:relative;z-index:1;">
    <div class="quote-text hf-anim">"这些能力全部跑在一张国产的昇腾NPU上。国产芯片不仅能跑大模型，而且跑得挺好。"</div>
    <div class="quote-source hf-anim-delay">💪 昇腾NPU × Qwen3-VL-8B</div>
  </div>
  <div class="page-num" style="color:#666;">25/29</div>
</div>
{make_gsap("s25", dur)}"""

def gen_s26(page_id="s26"):
    s = slide_map[page_id]
    dur = s["duration"]
    return f"""{make_style("s26", "card-grid")}
<div class="page-container">
  <span class="badge hf-anim">🤔 选型思考</span>
  <h2 class="hf-anim">为什么选这套组合？</h2>
  <div class="grid-row hf-anim">
    <div class="grid-card" style="background:#F0FDF9;">
      <div class="gc-icon" style="font-size:36px;">❓ → ✅</div>
      <h4>为什么用昇腾？</h4>
      <p><strong>国产可控</strong>：国产化替代不是可选项是必选项。推理性能已达高水平，单卡跑80B模型，生态快速完善</p>
    </div>
    <div class="grid-card" style="background:#F0FDF9;">
      <div class="gc-icon" style="font-size:36px;">❓ → ✅</div>
      <h4>为什么是8B？</h4>
      <p><strong>性价比甜蜜点</strong>：80亿参数已够用，更大模型延迟高、显存大。单卡流畅运行，先跑起来再考虑更大</p>
    </div>
    <div class="grid-card" style="background:#F0FDF9;">
      <div class="gc-icon" style="font-size:36px;">❓ → ✅</div>
      <h4>为什么用Docker？</h4>
      <p><strong>环境一致性</strong>：镜像拉下来就能跑，不因OS/Python/库版本不同而报错。团队协作和运维的标准答案</p>
    </div>
  </div>
  <div class="page-num">26/29</div>
</div>
{make_gsap("s26", dur)}"""

def gen_s27(page_id="s27"):
    s = slide_map[page_id]
    dur = s["duration"]
    return f"""{make_style("s27", "comparison")}
<div class="page-container">
  <span class="badge hf-anim">🎯 最终结论</span>
  <h2 class="hf-anim">选最合适的，不是选最好的</h2>
  <div class="compare-row hf-anim">
    <div class="compare-col" style="background:#FFF3E0;">
      <div class="icon" style="font-size:48px;">⚙️</div>
      <h4>其他方案</h4>
      <p>大模型+多GPU+手动部署 → 性能可能更高，但门槛高、成本高、环境不一致</p>
    </div>
    <div class="compare-divider"></div>
    <div class="compare-col" style="background:#F0FDF9;border:2px solid #00BFA5;">
      <div class="icon" style="font-size:48px;">✅</div>
      <h4 style="color:#00BFA5;">本方案</h4>
      <p>昇腾NPU + Qwen3-VL-8B + Docker → 当前最合适的一套组合。单卡可跑，成本可控，开箱即用</p>
    </div>
  </div>
  <div style="text-align:center;margin-top:10px;">
    <div style="background:#00BFA5;border-radius:8px;padding:12px 24px;display:inline-block;">
      <p style="font-size:20px;color:#fff;font-weight:800;">昇腾 + Qwen3-VL-8B + Docker = 最合适组合</p>
    </div>
  </div>
  <div class="page-num">27/29</div>
</div>
{make_gsap("s27", dur)}"""

def gen_s28(page_id="s28"):
    s = slide_map[page_id]
    dur = s["duration"]
    return f"""{make_style("s28", "timeline")}
<div class="page-container">
  <span class="badge hf-anim">📌 记住这三句话</span>
  <h2 class="hf-anim">在脑子里扎三个桩</h2>
  <div class="timeline-wrap">
    <div class="timeline-track hf-anim">
      <div class="timeline-node">
        <div class="timeline-dot"></div>
        <h4>🛋️ 第一句</h4>
        <p>镜像就是宜家箱子，docker run就是开箱做菜，容器就是独立厨房</p>
      </div>
      <div class="timeline-node">
        <div class="timeline-dot"></div>
        <h4>🎮 第二句</h4>
        <p>--device就是接显卡坞的USB-C线，连上NPU，AI程序瞬间有算力</p>
      </div>
      <div class="timeline-node">
        <div class="timeline-dot"></div>
        <h4>📋 第三句</h4>
        <p>四步走——检查硬件、拉镜像、启动容器、验证服务</p>
      </div>
    </div>
    <div class="bottom-hint hf-anim-delay" style="font-size:20px;font-weight:600;color:#0D1B2A;">这三句话你记住了，今天这视频就没白看</div>
  </div>
  <div class="page-num">28/29</div>
</div>
{make_gsap("s28", dur)}"""

def gen_s29(page_id="s29"):
    s = slide_map[page_id]
    dur = s["duration"]
    return f"""{make_style("s29", "hero")}
<div class="hero-container" style="background:linear-gradient(135deg,#0D1B2A 0%,#1B3A4B 50%,#0D1B2A 100%);">
  <div class="hero-glow"></div>
  <h1 class="hero-title hf-anim">下一期，实操见！</h1>
  <p class="hero-subtitle hf-anim-delay">从零开始——裸机服务器 → SSH → 敲命令 → Qwen3-VL-8B上线</p>
  <div style="margin-top:40px;z-index:1;display:flex;flex-direction:column;align-items:center;gap:6px;">
    <div style="color:#B0BEC5;font-size:20px;">系列名：昇腾从零到一</div>
    <div style="background:#00BFA5;border-radius:8px;padding:10px 28px;margin-top:8px;">
      <span style="color:#fff;font-size:18px;font-weight:700;">关注 + 订阅</span>
    </div>
  </div>
  <div style="position:absolute;bottom:60px;left:50%;transform:translateX(-50%);z-index:1;color:#B0BEC5;font-size:18px;text-align:center;">
    <p>评论区置顶有镜像地址、命令模板、验证脚本</p>
    <p style="margin-top:4px;">我是史导，一个想把复杂技术讲成大白话的昇腾布道师</p>
  </div>
  <div class="page-num" style="color:#666;">29/29</div>
</div>
{make_gsap("s29", dur)}"""

# ============================================================
# Generation
# ============================================================

generators = {
    "s01": gen_s01,
    "s02": gen_s02,
    "s03": gen_s03,
    "s04": gen_s04,
    "s05": gen_s05,
    "s06": gen_s06,
    "s07": gen_s07,
    "s08": gen_s08,
    "s09": gen_s09,
    "s10": gen_s10,
    "s11": gen_s11,
    "s12": gen_s12,
    "s13": gen_s13,
    "s14": gen_s14,
    "s15": gen_s15,
    "s16": gen_s16,
    "s17": gen_s17,
    "s18": gen_s18,
    "s19": gen_s19,
    "s20": gen_s20,
    "s21": gen_s21,
    "s22": gen_s22,
    "s23": gen_s23,
    "s24": gen_s24,
    "s25": gen_s25,
    "s26": gen_s26,
    "s27": gen_s27,
    "s28": gen_s28,
    "s29": gen_s29,
}

# Generate all 29 scene files
for i in range(1, 30):
    sid = f"s{i}"
    sid_02 = f"s{i:02d}"
    print(f"Generating {sid}...")
    content = generators[sid_02](sid)
    out_path = os.path.join(OUT_DIR, f"scene_{i}.html")
    with open(out_path, "w") as f:
        f.write(content)

# Generate index.html
total_duration = timeline_data["total_duration"]
index_parts = []
index_parts.append(f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>昇腾部署Qwen3-VL-8B概念讲解</title>
<style>
html, body {{ margin: 0; padding: 0; width: 1920px; height: 1080px; overflow: hidden; font-family: sans-serif; background: #000; }}
#root {{ width: 1920px; height: 1080px; position: relative; }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total_duration}" data-width="1920" data-height="1080">
''')

for i, s in enumerate(slides):
    idx = i + 1
    index_parts.append(f'  <div data-composition-id="s{idx}" data-composition-src="compositions/scene_{idx}.html" data-start="{s["start"]:.2f}" data-duration="{s["duration"]:.2f}" data-width="1920" data-height="1080"></div>\n')

index_parts.append(f'''</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js"></script>
<script>
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = gsap.timeline({{paused: true}});
window.__hf = window.__hf || {{}};
window.__hf["main"] = {{
  duration: {total_duration},
  seek: function(t) {{
    var tl = window.__timelines && window.__timelines["main"];
    if (tl) tl.seek(t);
  }}
}};
</script>
</body>
</html>''')

with open(INDEX_PATH, "w") as f:
    f.write("".join(index_parts))

print(f"\nDone! Generated 29 scene files in {OUT_DIR}")
print(f"Index file: {INDEX_PATH}")
print(f"Total duration: {total_duration}s")
