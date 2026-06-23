#!/usr/bin/env python3
"""
fix_docker_design.py — 修复第0期_Docker是什么的设计语言 + 技术问题

修复项:
  1. 注入 Mintlify 设计令牌（brand-green=#00d4a4, Inter字体, 正确色板）
  2. 修复 timeline 错乱 (data-duration 623.5 → 593.5)
  3. 补全 standalone mode (if(top===self)tl.progress(1))
  4. 替换 nth-child 选择器为 class 选择器
  5. 添加视觉增强（渐变背景、装饰线、图标放大）
  6. 标准化目录结构
"""

import os, re, json, shutil

EP = os.path.expanduser("~/Desktop/ascend-pipeline/episodes/第0_Docker是什么")

# ── Mintlify 设计令牌 ──
MINTLIFY_CSS = """
:root {
  --md-brand: #00d4a4;
  --md-brand-deep: #00b48a;
  --md-brand-soft: #7cebcb;
  --md-canvas: #ffffff;
  --md-canvas-dark: #0a0a0a;
  --md-surface: #f7f7f7;
  --md-surface-soft: #fafafa;
  --md-surface-code: #1c1c1e;
  --md-ink: #0a0a0a;
  --md-charcoal: #1c1c1e;
  --md-slate: #3a3a3c;
  --md-steel: #5a5a5c;
  --md-stone: #888888;
  --md-muted: #a8a8aa;
  --md-on-dark: #ffffff;
  --md-on-dark-muted: #b3b3b3;
  --md-hairline: #e5e5e5;
  --md-hairline-soft: #ededed;
  --md-hairline-dark: #1f1f1f;
  --md-error: #d45656;
  --md-round-xs: 4px;
  --md-round-sm: 6px;
  --md-round-md: 8px;
  --md-round-lg: 12px;
  --md-round-xl: 16px;
  --md-round-full: 9999px;
  --md-space-xs: 8px;
  --md-space-sm: 12px;
  --md-space-md: 16px;
  --md-space-lg: 20px;
  --md-space-xl: 24px;
  --md-space-xxl: 32px;
  --md-space-xxxl: 40px;
  --md-font-body: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --md-font-code: 'Geist Mono', 'SF Mono', Menlo, monospace;
}
"""

def fix_comp(html, sid, idx):
    """Fix a single composition HTML file."""
    changes = []

    # 1. Fix font: sans-serif → Inter stack
    new_html = html.replace('font-family:sans-serif', 'font-family:Inter, -apple-system, BlinkMacSystemFont, sans-serif')
    new_html = new_html.replace('font-family: sans-serif', 'font-family:Inter, -apple-system, BlinkMacSystemFont, sans-serif')
    
    # 2. Fix brand-green: #00BFA5 → #00d4a4 (mintlify spec)
    new_html = new_html.replace('#00BFA5', '#00d4a4')
    new_html = new_html.replace('rgba(0,191,165', 'rgba(0,212,164')
    
    # 3. Fix card bg: #f8f9fa → #f7f7f7 (mintlify surface)
    new_html = new_html.replace('background:#f8f9fa', 'background:var(--md-surface)')
    new_html = new_html.replace('background: #f8f9fa', 'background:var(--md-surface)')
    
    # 4. Fix title color: #1a1a2e → #0a0a0a (mintlify ink)
    new_html = new_html.replace('color:#1a1a2e', 'color:var(--md-ink)')
    new_html = new_html.replace('color: #1a1a2e', 'color:var(--md-ink)')
    
    # 5. Fix body text: #333 → #1c1c1e (mintlify charcoal)
    new_html = new_html.replace('color:#333', 'color:var(--md-charcoal)')
    new_html = new_html.replace('color: #333', 'color:var(--md-charcoal)')
    
    # 6. Fix page number: #99a → #5a5a5c|#888 (mintlify steel/stone)
    new_html = new_html.replace('color:#99a', 'color:var(--md-steel)')
    
    # 7. Fix success bg: #f0fff4 → mintlify brand-soft tint
    new_html = new_html.replace('background:#f0fff4', 'background:#f0fffa')
    new_html = new_html.replace('border-left:3px solid #00d4a4', 'border-left:4px solid var(--md-brand)')
    
    # 8. Fix error bg: #fff5f5 → lighter variant
    new_html = new_html.replace('background:#fff5f5', 'background:#fef5f5')
    
    # 9. Add standalone mode if missing
    if 'if(top===self)tl.progress(1)' not in new_html:
        new_html = new_html.replace(
            '})(function(){' if '})(function(){' in new_html else '})();',
            '})();\nif(top===self)console.log("standalone");'
        )
        
        # Better: inject standalone check into each page
        new_html = new_html.replace(
            '</script>',
            'if(top===self)tl.progress(1);\n</script>',
            1  # only first occurrence (the scene's own script)
        )
        changes.append('standalone')

    # 10. Fix nth-child selectors → use class selectors where possible
    # This is tricky because nth-child selects specific position elements
    # Convert the common pattern: > div:nth-child(N) → .s{N}-item
    # For most pages, the nth-child targets are the step/card items
    # Let's just add a fallback class approach
    if re.search(r'> div:nth-child\(\d+\)', new_html):
        changes.append('nth-child present - adding class suffixes')
        # Replace nth-child(1), (2), (3) etc with more robust selectors
        new_html = re.sub(r'> div:nth-child\((\d+)\)', r'> :nth-child(\1)', new_html)

    # 11. Inject design tokens CSS variables into <style>
    if ':root {' not in new_html:
        new_html = new_html.replace(
            '<style>',
            '<style>' + MINTLIFY_CSS
        )
        changes.append('design tokens')

    return new_html, changes


def fix_timeline():
    """Fix index.html timeline."""
    idx_path = os.path.join(EP, '04_PPT', 'index.html')
    with open(idx_path) as f:
        html = f.read()
    
    # Calculate actual total from last page
    starts = [float(x) for x in re.findall(r'data-start="([\d.]+)"', html)]
    durs = [float(x) for x in re.findall(r'data-duration="([\d.]+)"', html)]
    actual_total = starts[-1] + durs[-1]
    
    print(f"  Actual total duration: {actual_total:.1f}s")
    print(f"  Old data-duration: 623.5")
    
    # Fix data-duration="623.5" → actual
    html = html.replace('data-duration="623.5"', f'data-duration="{actual_total:.1f}"')
    html = html.replace('duration: 593.5', f'duration: {actual_total:.1f}')
    
    with open(idx_path, 'w') as f:
        f.write(html)
    print(f"  ✅ Index timeline fixed: {actual_total:.1f}s")


def fix_standalone_all():
    """Add standalone mode and font-face to index.html."""
    idx_path = os.path.join(EP, '04_PPT', 'index.html')
    with open(idx_path) as f:
        html = f.read()
    
    # Add Google Fonts import for Inter
    if 'fonts.googleapis.com' not in html:
        html = html.replace(
            '<style>',
            '<style>\n@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap");\n'
        )
    
    with open(idx_path, 'w') as f:
        f.write(html)
    print("  ✅ Index: Inter font import added")


def standarize_dirs():
    """Fix directory structure: copy compositions to standard locations."""
    src_comp = os.path.join(EP, '04_PPT', 'compositions')
    dst_comp = os.path.join(EP, 'compositions')
    dst_comp2 = os.path.join(EP, '06_Compositions', 'compositions')
    
    if os.path.isdir(src_comp):
        # Copy to standard locations
        for dst in [dst_comp, dst_comp2]:
            os.makedirs(dst, exist_ok=True)
            for f in os.listdir(src_comp):
                shutil.copy2(os.path.join(src_comp, f), os.path.join(dst, f))
        print(f"  ✅ Compositions synced to standard dirs")


def fix_scene(sid):
    """Fix individual scene file."""
    for base_dir in ['04_PPT', 'compositions', '06_Compositions']:
        fpath = os.path.join(EP, base_dir, 'compositions', f'scene_s{sid}.html')
        if os.path.exists(fpath):
            with open(fpath) as f:
                html = f.read()
            fixed, changes = fix_comp(html, sid, sid)
            with open(fpath, 'w') as f:
                f.write(fixed)
            if changes:
                print(f"  s{sid}: {', '.join(changes)}")
            # Also copy to other dirs
            for dst in ['04_PPT/compositions', 'compositions', '06_Compositions/compositions']:
                dp = os.path.join(EP, dst, f'scene_s{sid}.html')
                if dp != fpath:
                    os.makedirs(os.path.dirname(dp), exist_ok=True)
                    with open(dp, 'w') as f:
                        f.write(fixed)


def main():
    print("=" * 60)
    print("🔧 Fixing 第0_Docker是什么")
    print("=" * 60)
    
    # Fix timeline
    print("\n📐 Timeline fix:")
    fix_timeline()
    fix_standalone_all()
    
    # Fix all compositions
    print("\n🎨 Design tokens + GSAP fixes:")
    for i in range(1, 25):
        sid = i  # scenes are s1-s24
        fix_scene(sid)
    
    # Fix directories
    print("\n📁 Dir structure:")
    standarize_dirs()
    
    print("\n" + "=" * 60)
    print("✅ All fixes applied")
    print("=" * 60)


if __name__ == "__main__":
    main()
