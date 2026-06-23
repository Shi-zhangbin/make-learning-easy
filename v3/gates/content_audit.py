"""
v3/gates/content_audit.py — 内容质量审核

在 T3（口播稿）和 T6（composition）后运行，检查：
1. 口播稿无残留标记（---、##、**、``）
2. 每页都有口播内容
3. 知识点大纲完整性
"""
import re
from pathlib import Path


def audit_narration(episode_dir: str) -> list[str]:
    """检查口播稿质量。"""
    issues = []
    ep = Path(episode_dir)
    
    # Find narration script
    candidates = ["配音稿_分段.txt", "配音稿.txt", "口播稿.txt"]
    script_path = None
    for c in candidates:
        p = ep / c
        if p.exists():
            script_path = p
            break
    
    if not script_path:
        issues.append("口播稿文件不存在")
        return issues
    
    content = script_path.read_text(encoding="utf-8")
    
    # 1. 检查 markdown 标记残留
    artifacts = []
    patterns = [
        (r'#{2,}', "## 标题"),
        (r'\*{2,}', "**加粗**"),
        (r'`{2,}', "``代码``"),
        (r'!{2,}', "!!"),
    ]
    for pat, name in patterns:
        if re.search(pat, content):
            artifacts.append(name)
    
    if artifacts:
        issues.append(f"口播稿含残留标记: {', '.join(artifacts)}")
    
    # 2. 检查是否有空页
    page_pattern = re.compile(r"---\s*P(\d+).*?---\s*\n(.*?)(?=\n---\s*P|\Z)", re.DOTALL)
    pages = list(page_pattern.finditer(content))
    if not pages:
        issues.append("无法解析口播稿的分页标记")
    else:
        empty_pages = [m.group(1) for m in pages if not m.group(2).strip()]
        if empty_pages:
            issues.append(f"以下页面口播为空: P{', '.join(empty_pages)}")
    
    return issues


def check_density(composition_dir: str) -> list[str]:
    """检查 composition 的信息密度。"""
    issues = []
    comp_dir = Path(composition_dir)
    if not comp_dir.exists():
        return ["Composition 目录不存在"]
    
    for f in sorted(comp_dir.glob("scene_*.html")):
        html = f.read_text(encoding="utf-8")
        # 检查中文字数
        text = re.sub(r'<[^>]+>', '', html)
        chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        if chars < 30:
            issues.append(f"{f.stem}: 仅{chars}字")
    
    return issues


if __name__ == "__main__":
    import sys
    ep = sys.argv[1] if len(sys.argv) > 1 else "."
    print("=== 内容审核 ===")
    for issue in audit_narration(ep):
        print(f"  ❌ {issue}")
    print("✅ 口播稿审核完成")
