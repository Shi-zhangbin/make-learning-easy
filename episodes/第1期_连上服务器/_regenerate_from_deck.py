import os, re

base = os.path.expanduser("~/Desktop/启明实验_新管线/第1期_连上服务器")
cd = os.path.join(base, "compositions")

# 读取deck HTML
with open(os.path.join(base, "第1期_完整deck.html")) as f:
    deck = f.read()

# 提取deck的完整CSS（包括所有动画）
style_m = re.search(r'<style>(.*?)</style>', deck, re.DOTALL)
if not style_m:
    print("❌ 找不到style")
    exit(1)

deck_css = style_m.group(1)

# 清理：只保留slide相关的CSS，去掉nav和deck相关
lines = deck_css.split('\n')
clean_lines = []
nav_block = False
for line in lines:
    if '.nav' in line or '.deck{' in line:
        nav_block = True
    if nav_block:
        if '}' in line and nav_block:
            nav_block = False
        continue
    clean_lines.append(line)

deck_css = '\n'.join(clean_lines)

# deck_css已经有了完整样式，但需要适配成composition
# 在deck里.slide是position:absolute的，composition里需要改成block
deck_css = deck_css.replace(
    '.slide{position:absolute;top:0;left:0;width:1920px;height:1080px;opacity:0;z-index:1;transition:opacity 0.3s;pointer-events:none;}',
    '.slide{width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;}'
)
deck_css = deck_css.replace('.slide.active{opacity:1;z-index:2;pointer-events:auto;}', '')
deck_css = deck_css.replace('.deck{position:relative;width:1920px;height:1080px;margin:0 auto;overflow:hidden;}', '')

# 替换字体为sans-serif
deck_css = deck_css.replace("font-family:Inter,-apple-system,BlinkMacSystemFont,sans-serif;", "font-family:sans-serif;")
deck_css = deck_css.replace("font-family:-apple-system,BlinkMacSystemFont,sans-serif;", "font-family:sans-serif;")
deck_css = deck_css.replace("font-family:'Geist Mono','SF Mono','Courier New',monospace;", "font-family:monospace;")
deck_css = deck_css.replace("font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;", "font-family:sans-serif;")

# 提取每个slide的内容（保留section标签）
slides = re.findall(r'(<section class="slide" id="slide-\d+">.*?</section>)', deck, re.DOTALL)

print(f"找到 {len(slides)} 个slide")

durations = [6.0, 8.5, 7.5, 7.5, 13.0, 15.0, 11.0, 15.0, 10.5, 9.5, 11.5, 15.0, 11.0]

for i, slide_html in enumerate(slides, 1):
    dur = durations[i-1]
    
    # 提取title
    title_m = re.search(r'<h[12][^>]*>(.*?)</h[12]>', slide_html)
    title = re.sub(r'<[^>]+>', '', title_m.group(1))[:40] if title_m else f"P{i}"
    
    # 给section加上data-*属性
    slide_html = slide_html.replace(
        f'<section class="slide" id="slide-{i}">',
        f'<section class="slide" id="slide-{i}" data-composition-id="s{i}" data-width="1920" data-height="1080">'
    )
    
    # 组合成完整HTML
    html = f"""<!doctype html><html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=1920,height=1080">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>{deck_css}</style>
</head><body>
{slide_html}
<script>
(function(){{
  var tl = gsap.timeline({{paused:true}});
  tl.from(".sl>*",{{opacity:0,y:8,duration:0.25,stagger:0.04}});
  window.__timelines = window.__timelines || {{}};
  window.__timelines["s{i}"] = tl;
  window.__hf = window.__hf || {{}};
  window.__hf["s{i}"] = {{"duration":{dur:.2f},"seek":function(t){{var tl=window.__timelines&&window.__timelines["s{i}"];if(tl)tl.seek(t);}}}};
  if(top===self)tl.progress(1);
}})();
</script>
</body></html>"""
    
    fpath = os.path.join(cd, f"scene_{i}.html")
    with open(fpath, "w") as f:
        f.write(html)
    
    sz = len(html)
    print(f"✅ P{i:2d}: {title:30s} {sz//1024}KB")

# lint
import subprocess
r = subprocess.run(["hyperframes", "lint", base], capture_output=True, text=True, cwd=base)
err = r.stdout.count("✗")
print(f"\nhyperframes lint: {err} errors")
if err > 0:
    for line in r.stdout.split('\n'):
        if '✗' in line:
            print(f"  {line.strip()}")
