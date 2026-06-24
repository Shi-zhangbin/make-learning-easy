"""
v3/designs/base.py — Design token loader

Loads a YAML preset, resolves {token.refs} against the full token tree,
and provides a flat CSS variable map for template rendering.
"""
import os, yaml, re
from pathlib import Path

PRESETS_DIR = Path(__file__).resolve().parent / "presets"


def _resolve_refs(obj, context: dict, max_depth: int = 10):
    """Recursively resolve {foo.bar.baz} references in a YAML tree."""
    if isinstance(obj, str):
        if "{" not in obj:
            return obj
        def _replace(m):
            key_path = m.group(1).split(".")
            val = context
            for k in key_path:
                if isinstance(val, dict):
                    val = val.get(k, m.group(0))
                else:
                    return m.group(0)
            if isinstance(val, str) and "{" in val:
                return _resolve_refs(val, context, max_depth - 1)
            return str(val) if not isinstance(val, (dict, list)) else m.group(0)
        return re.sub(r"\{([\w.]+)\}", _replace, obj)
    elif isinstance(obj, dict):
        return {k: _resolve_refs(v, context, max_depth - 1) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_refs(v, context, max_depth - 1) for v in obj]
    return obj


def load_preset(name: str) -> dict:
    """Load a design preset by name (e.g. 'claude', 'mintlify')."""
    path = PRESETS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Design preset not found: {name} (tried {path})")
    with open(path) as f:
        raw = yaml.safe_load(f)
    return _resolve_refs(raw, raw)


def list_presets() -> list[dict]:
    """List all available design presets."""
    results = []
    for f in sorted(PRESETS_DIR.glob("*.yaml")):
        with open(f) as fh:
            raw = yaml.safe_load(fh)
        results.append({
            "name": raw.get("name", f.stem),
            "display_name": raw.get("display_name", f.stem),
            "description": raw.get("description", ""),
        })
    return results


def preset_to_css_vars(preset: dict) -> str:
    """Convert a resolved preset dict to CSS custom properties string."""
    d = preset.get("layout_defaults", {})
    lines = [":root {"]
    for key in d:
        val = d.get(key, "")
        if val:
            css_key = "--" + key.replace("_", "-")
            lines.append(f"  {css_key}: {val};")
    lines.append("}")
    return "\n".join(lines)


def preset_css_font_import(preset: dict) -> str:
    """Generate @import for Google Fonts based on the preset's font families."""
    imports = []
    known = {
        "Inter": "Inter:wght@400;500;600;700",
        "JetBrains Mono": "JetBrains+Mono:wght@400;500",
    }
    all_text = str(preset.get("typography", {}))
    for name, param in known.items():
        if name in all_text:
            imp = f'@import url("https://fonts.googleapis.com/css2?family={param}&display=swap");'
            if imp not in imports:
                imports.append(imp)
    return "\n".join(imports) + "\n" if imports else ""

