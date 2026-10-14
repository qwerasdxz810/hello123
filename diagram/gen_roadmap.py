#!/usr/bin/env python3
"""生成项目研究思路框图（技术路线图，SVG）。

运行：python3 diagram/gen_roadmap.py
输出：diagram/project_roadmap.svg

结构：问题分析 → 可行性论证 → 技术研究 → 验证演示。
箭头均以多边形绘制、样式写在元素属性中，便于导入 PowerPoint / Visio 后编辑。
"""
import math
from pathlib import Path

W, H = 1400, 944
# 正文宋体、标题黑体；如需统一为微软雅黑，修改这两个变量即可
BODY = "SimSun, 宋体, Songti SC, STSong, Noto Serif CJK SC, serif"
HEAD = "SimHei, 黑体, Heiti SC, STHeiti, Noto Sans CJK SC, sans-serif"

INK = "#1F1F1F"
SUB = "#4D4D4D"
EDGE = "#555555"

PROB = dict(frame="#E06666", box="#F8E4EB", sub="#FDF3F6")
FEAS = dict(frame="#6FA8B0", box="#D3E3E6")
TECH = dict(frame="#9CD3BF", box="#ADDBC9", group="#F4FAF7", gline="#7DBFA6")
VERI = dict(frame="#A8BFE3", box="#C9DAF0")
CHEV_DOWN, CHEV_1, CHEV_2 = "#C5D9E3", "#7FCDB0", "#A9C4E8"

out = []


def add(s):
    out.append(s)


def text_width(s, size):
    return sum(1.0 if ord(c) > 0x2E7F else 0.56 for c in s) * size


def ctext(cx, cy, s, size=20, font=BODY, weight="normal", fill=INK, max_w=None):
    if max_w is not None:
        assert text_width(s, size) <= max_w, f"文字过长: {s}"
    add(f'<text x="{cx:.1f}" y="{cy + 0.36 * size:.1f}" font-family="{font}" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="middle">{s}</text>')


def rect(x, y, w, h, fill, stroke="none", sw=1.2, rx=0, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def line(x1, y1, x2, y2, stroke=EDGE, sw=1.6):
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{sw}" stroke-linecap="square"/>')


def arrow(x1, y1, x2, y2, color=EDGE, sw=1.6, head=10):
    L = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    bx, by = x2 - ux * head, y2 - uy * head
    line(x1, y1, bx, by, color, sw)
    hw = head * 0.45
    pts = [(x2, y2), (bx - uy * hw, by + ux * hw), (bx + uy * hw, by - ux * hw)]
    add(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" '
        f'fill="{color}"/>')


def poly(pts, fill):
    add(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" '
        f'fill="{fill}"/>')


def chevron_right(x0, cy, fill, w=52, hh=50, notch=22):
    poly([(x0, cy - hh), (x0 + w, cy), (x0, cy + hh), (x0 + notch, cy)], fill)


def chevron_down(cx, y0, fill, hw=52, h=54, notch=22):
    poly([(cx - hw, y0), (cx, y0 + notch), (cx + hw, y0), (cx, y0 + h)], fill)


def panel(x, y, w, h, title, frame):
    rect(x, y, w, h, "#FFFFFF", frame, sw=2.2, rx=3)
    ctext(x + w / 2, y + 34, title, 24, font=HEAD, weight="bold")


def box(x, y, w, h, s, fill, size=20, **kw):
    rect(x, y, w, h, fill, EDGE, sw=1.2, rx=2)
    ctext(x + w / 2, y + h / 2, s, size, max_w=w - 16, **kw)


# =====================================================================
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}">')
add('<title>基于多源非合作信号的分布式相参探测项目研究思路框图</title>')
rect(0, 0, W, H, "#FFFFFF")

# ---------- 问题分析 ----------
PX, PY, PW, PH = 360, 20, 680, 270
panel(PX, PY, PW, PH, "问题分析", PROB["frame"])
cx = PX + PW / 2
box(cx - 270, 80, 540, 54, "非合作信号源雷达微弱目标探测威力不足", PROB["box"],
    size=21, weight="bold")
causes = [("信号源非合作", "信号参数未知、不可控"),
          ("干扰环境复杂", "多源串扰与时变杂波强"),
          ("积累增益有限", "单源单站回波能量弱")]
cw, cg, cy0, ch = 200, 20, 180, 92
cxs = [PX + 20 + i * (cw + cg) + cw / 2 for i in range(3)]
line(cx, 134, cx, 156)
line(cxs[0], 156, cxs[-1], 156)
for (t, s), x in zip(causes, cxs):
    arrow(x, 156, x, cy0, head=9)
    rect(x - cw / 2, cy0, cw, ch, PROB["sub"], EDGE, sw=1.2, rx=2)
    ctext(x, cy0 + 30, t, 20, weight="bold", max_w=cw - 16)
    ctext(x, cy0 + 64, s, 17, fill=SUB, max_w=cw - 16)

chevron_down(cx, PY + PH + 10, CHEV_DOWN)

# ---------- 下方三栏 ----------
BY, BH = 362, 560
mid_y = BY + BH / 2
item_cy = [BY + 128 + k * 120 for k in range(4)]   # 左右两栏条目中心

# 可行性论证
LX, LW = 20, 380
panel(LX, BY, LW, BH, "可行性论证", FEAS["frame"])
feas = ["探测威力论证", "三维相参增益分析", "时频同步精度分析", "多站布站可行性分析"]
iw, ih = 222, 60
ix = LX + 20
bus_x = ix + iw + 28
for s, y in zip(feas, item_cy):
    box(ix, y - ih / 2, iw, ih, s, FEAS["box"])
    line(ix + iw, y, bus_x, y)
line(bus_x, item_cy[0], bus_x, item_cy[-1])
sim_x, sim_w = bus_x + 24, 60
sim_y0, sim_y1 = item_cy[0] - ih / 2, item_cy[-1] + ih / 2
rect(sim_x, sim_y0, sim_w, sim_y1 - sim_y0, FEAS["box"], EDGE, sw=1.2, rx=14)
arrow(bus_x, mid_y, sim_x, mid_y)
for k, ch_ in enumerate("计算机仿真"):
    ctext(sim_x + sim_w / 2, mid_y + (k - 2) * 36, ch_, 24)

chevron_right(LX + LW + 14, mid_y, CHEV_1)

# 技术研究
MX, MW = 480, 440
panel(MX, BY, MW, BH, "技术研究", TECH["frame"])
gx, gy, gw, gh = MX + 20, BY + 60, MW - 40, 392
rect(gx, gy, gw, gh, TECH["group"], TECH["gline"], sw=1.4, rx=4, dash="6 4")
ctext(MX + MW / 2, gy + 26, "关键算法研究", 21, font=HEAD, weight="bold")
algos = ["分布式非合作信号源目标回波建模", "辐射源参数估计", "多源串扰抑制算法设计",
         "分布式时变杂波抑制算法", "分布式相参探测算法设计", "分布式相参多站址调度"]
aw, ah, astep = 360, 46, 56
ax = MX + (MW - aw) / 2
for k, s in enumerate(algos):
    box(ax, gy + 48 + k * astep, aw, ah, s, TECH["box"])
plat_y = gy + gh + 26
arrow(MX + MW / 2, gy + gh, MX + MW / 2, plat_y)
box(ax, plat_y, aw, 56, "数字化雷达验证平台研制", TECH["box"])

chevron_right(MX + MW + 14, mid_y, CHEV_2)

# 验证演示
RX, RW = 1000, 380
panel(RX, BY, RW, BH, "验证演示", VERI["frame"])
veri = ["多源场景回波仿真", "关键算法仿真验证", "探测性能评估", "综合验证演示"]
vw = 300
vx = RX + (RW - vw) / 2
for k, (s, y) in enumerate(zip(veri, item_cy)):
    box(vx, y - ih / 2, vw, ih, s, VERI["box"])
    if k < len(veri) - 1:
        arrow(RX + RW / 2, y + ih / 2, RX + RW / 2, item_cy[k + 1] - ih / 2)

add("</svg>")

dst = Path(__file__).with_name("project_roadmap.svg")
dst.write_text("\n".join(out), encoding="utf-8")
print(f"written {dst}")
