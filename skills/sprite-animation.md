---
name: sprite-animation
description: 生成 3×3 精灵图动画的技能。输入"小动物做某动作"，自动拆解 9 帧动画循环，生成 sprite strip + 预览 HTML。
---

# Sprite Animation · 精灵图生成技能

## 核心思路

将任意动作拆解为一个 **9 帧循环** —— 帧 1 是动作起始，帧 9 是动作收尾，帧 9 → 帧 1 无缝循环。

## 方法论

### Step 1 · 理解动作类型

确定动作是属于**循环型**还是**一次性**：

| 类型 | 特点 | 例子 |
|------|------|------|
| **循环型**（推荐） | 帧 9 自然过渡到帧 1，连续播放 | 跑步、走路、打字、骑车 |
| **一次性** | 有明确的开始和结束 | 跳跃、伸懒腰（也可以做循环） |

### Step 2 · 拆解 9 帧

按"起→承→转→合→回到起"的节奏，把动作分成 9 个独立的姿势。**每帧必须全身参与**（腿、手、头、躯干都要动）。

模板框架：

```
Cell 1: [动作起始姿势，明确描述四肢/头位置]
Cell 2: [动作第一步变化，哪个部位先动]
Cell 3: [过渡姿势，肢体交叉或变换]
Cell 4: [动作第二相位，另一侧肢体主导]
Cell 5: [动作中间点，最典型的姿势]
Cell 6: [继续变化，向收势过渡]
Cell 7: [收势前奏，开始回归]
Cell 8: [即将回到起始，但还不完全一样]
Cell 9: [收势，与 Cell 1 不同但无缝衔接]
```

### Step 3 · 质量规则（必须写入 prompt）

每一条都必须出现在 prompt 中：

```
CRITICAL: IDENTICAL character SIZE, POSITION and HEIGHT in all 9 cells.
All 9 cells MUST be distinctly different poses — this is a full animation cycle,
NOT 9 similar drawings. Every limb moves: legs, arms, head, and torso
all change position per cell. Cell 9 must be DIFFERENT from cell 1
but flow seamlessly into it for looping. No vertical bouncing.
Minimal pixel change between consecutive cells.
Simple flat vector pixel art, thick outlines, white background.
```

### Step 4 · 角色描述锚

写 20-30 字的角色特征，精确到颜色/体型：

```
cute baby blue dinosaur with tiny arms, big head, and long tail that bounces
ginger tabby orange cat with round head and pointy ears sitting at desk
cute chibi boy with short dark hair, blue t-shirt, blue shorts, white sneakers
```

### Step 5 · 生成

```bash
python3 -m core.sprite_runner generate --prompt "[完整 prompt]" --out /tmp/grid.png
```

或用管线预设：

```bash
python3 -m core.sprite_runner preset --style boy
```

生成产物：
- `{style}.png` — 540×60 的 9 帧 strip
- `sprite-preview.html` — 可预览的 HTML 调试页

## 已固化的预设

| 名称 | 动作 | 文件 | 说明 |
|------|------|------|------|
| `boy` | 跑步 🏃 | `core/assets/sprites/boy.png` | 人形跑步，手臂摆动与腿部相反 |
| `dino` | 恐龙跑步 🦖 | `core/assets/sprites/dino.png` | 短腿碎步，尾巴弹跳，大头摇晃 |
| `cat` | 橘猫打字 🐱 | `core/assets/sprites/cat.png` | 坐姿打字 + 伸懒腰 + 爪子落回键盘 |

## 添加新预设

1. 写 9 帧循环描述 → 加到 `ANIMATION_CYCLES` 字典
2. 添加 preset 条目到 `SPRITE_PRESETS`，指定 `anim_type` + `char`
3. 运行 `python3 -m core.sprite_runner preset --style 新名称`
4. 打开 `sprite-preview.html` 检查效果
