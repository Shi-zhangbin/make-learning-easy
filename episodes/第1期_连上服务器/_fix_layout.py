import os, re

cd = os.path.expanduser("~/Desktop/启明实验_新管线/第1期_连上服务器/compositions")

CSS = (
    '*{margin:0;padding:0;box-sizing:border-box;font-family:sans-serif;}\n'
    'html,body{width:1920px;height:1080px;overflow:hidden;background:#ffffff;}\n'
    '.wrap{width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;}\n'
    '.sl{width:100%;height:100%;display:flex;flex-direction:column;padding:50px 80px;position:relative;background:#ffffff;}\n'
    '.sl::before{content:"";position:absolute;top:0;left:0;width:4px;height:100%;background:linear-gradient(to bottom,#00d4a4,#00b48a);}\n'
    '.badge{font-size:11px;color:#00d4a4;letter-spacing:2px;text-transform:uppercase;font-weight:600;margin-bottom:8px;}\n'
    'h1{font-size:64px;font-weight:700;color:#0a0a0a;line-height:1.1;margin-bottom:12px;}\n'
    'h2{font-size:46px;font-weight:700;color:#0a0a0a;line-height:1.1;margin-bottom:18px;}\n'
    '.card{background:#fafafa;border:1px solid #e5e5e5;border-radius:8px;padding:16px 18px;margin-bottom:10px;}\n'
    '.card-title{font-size:16px;font-weight:600;color:#0a0a0a;margin-bottom:3px;}\n'
    '.card-body{font-size:14px;color:#5a5a5c;line-height:1.5;}\n'
    '.tag{display:inline-block;padding:3px 10px;border-radius:4px;font-size:12px;background:#f7f7f7;color:#888;border:1px solid #e5e5e5;margin:2px;}\n'
    '.tag-g{background:#e8faf4;color:#0d9373;border-color:#b8ead9;font-family:monospace;}\n'
    '.cmd-box{background:#1c1c1e;border-radius:6px;padding:14px 18px;font-family:monospace;font-size:15px;line-height:1.6;color:#e0e0e0;margin:10px 0;}\n'
    '.tip{background:#fef9e7;border:1px solid #f5e6c0;border-radius:6px;padding:10px 14px;margin:6px 0;font-size:13px;color:#b8860b;line-height:1.4;}\n'
    '.pr{font-size:13px;color:#888;position:absolute;bottom:18px;right:28px;}\n'
)

for i in range(1, 14):
    fpath = os.path.join(cd, f"scene_{i}.html")
    with open(fpath) as f:
        c = f.read()
    
    # Replace CSS
    c = re.sub(r'<style>.*?</style>', f'<style>{CSS}</style>', c, flags=re.DOTALL)
    
    # Replace root div with wrap+sl structure
    c = c.replace('<div class="root"', '<div class="wrap"><div class="sl"')
    
    # Fix closing: the original ends with </div><script>
    # Now we have </div></div><script> - need to make sure it's correct
    # The structure is: wrap > sl > (content + pr) 
    # Original ending: ...content...<span class="pr">...</span>\n</div>\n<script>
    # Need: ...content...<span class="pr">...</span>\n</div></div>\n<script>
    c = c.replace('</div>\n<script>', '</div></div>\n<script>')
    
    # Remove any text-align:center from h2
    c = c.replace('text-align:center;', '')
    
    with open(fpath, "w") as f:
        f.write(c)
    
    # Verify
    with open(fpath) as f:
        c2 = f.read()
    checks = []
    if 'class="wrap"' in c2: checks.append("wrap")
    if 'class="sl"' in c2: checks.append("sl")
    if 'data-composition-id=' in c2: checks.append("ID")
    print(f"  P{i}: {' '.join(checks)}")

print("✅ 全部改为deck结构")
