#!/usr/bin/env python3
"""
calc_timeline_offsets.py — 从时长列表自动计算 data-start 偏移

用法:
  python3 scripts/calc_timeline_offsets.py --list "6,8.5,7.5,7.5,13"
  python3 scripts/calc_timeline_offsets.py --json timeline.json
  python3 scripts/calc_timeline_offsets.py --segmented 配音稿_分段.txt
  python3 scripts/calc_timeline_offsets.py --list "6,8.5" --verify index.html
"""

import argparse, json, os, re, sys


def from_json(path):
    if not os.path.exists(path):
        print(f"❌ 文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        data = json.load(f)
    slides = data.get("slides", data if isinstance(data, list) else [])
    return [(s.get("page", i+1), float(s["duration"])) for i, s in enumerate(slides) if isinstance(s, dict) and "duration" in s]


def from_list(text):
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        print("❌ 空列表", file=sys.stderr)
        sys.exit(1)
    return [(i+1, float(p)) for i, p in enumerate(parts)]


def from_segmented(path):
    with open(path) as f:
        content = f.read()
    pages = re.findall(r"---\s*P(\d+).*?\((\d+(?:\.\d+)?)(?:s|秒|秒数)\)\s*---", content)
    if not pages:
        print(f"❌ 未匹配到分段格式", file=sys.stderr)
        sys.exit(1)
    return [(int(p), float(d)) for p, d in pages]


def verify(index_path, durations):
    with open(index_path) as f:
        html = f.read()
    declared = {}
    for m in re.finditer(r'data-composition-id="s(\d+)"[^>]*data-duration="([\d.]+)"', html):
        declared[int(m.group(1))] = float(m.group(2))

    m = re.search(r'data-duration="([\d.]+)"', html)
    declared_total = float(m.group(1)) if m else None
    total = sum(d for _, d in durations)
    issues = []
    for page, dur in durations:
        if page in declared and abs(declared[page] - dur) > 0.01:
            issues.append(f"P{page}: 声明={declared[page]}s, 实际={dur}s")
    if declared_total and abs(declared_total - total) > 0.1:
        issues.append(f"总时长: 声明={declared_total}s, 实际={total:.2f}s")
    return issues


def main():
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--json")
    g.add_argument("--list")
    g.add_argument("--segmented")
    p.add_argument("--verify")
    p.add_argument("--format", choices=["html", "json"], default="html")
    p.add_argument("--prefix", default="compositions/scene_{sid}.html")
    args = p.parse_args()

    if args.json:
        durations = from_json(args.json)
    elif args.list:
        durations = from_list(args.list)
    elif args.segmented:
        durations = from_segmented(args.segmented)

    if args.verify:
        issues = verify(args.verify, durations)
        total = sum(d for _, d in durations)
        if issues:
            for i in issues:
                print(f"  ❌ {i}")
            sys.exit(1)
        else:
            print(f"✅ 验证通过 — 总时长 {total:.2f}s")
        return

    total = sum(d for _, d in durations)
    start = 0.0
    lines = []
    for page, dur in durations:
        src = args.prefix.replace("{sid}", str(page))
        lines.append(f'  <div data-composition-id="s{page}" data-composition-src="{src}" data-start="{start:.2f}" data-duration="{dur:.2f}" data-width="1920" data-height="1080"></div>')
        start += dur

    if args.format == "json":
        print(json.dumps({"pages": len(durations), "total": round(total,2),
                          "durations": [{"page":p,"duration":d} for p,d in durations]}))
    else:
        for l in lines:
            print(l)


if __name__ == "__main__":
    main()
