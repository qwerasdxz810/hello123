#!/usr/bin/env python3
"""生成项目框图（SVG）。

运行：python3 diagram/gen_block_diagram.py
输出：diagram/project_block_diagram.svg

说明：箭头均以多边形绘制、文字基线手工计算、样式全部写在元素属性中，
便于在 PowerPoint / Visio / Inkscape 中导入后“转换为形状”再编辑。
"""
import math
from pathlib import Path

W, H = 1400, 1026
FONT = ("Microsoft YaHei, 微软雅黑, PingFang SC, Noto Sans CJK SC, "
        "Source Han Sans SC, WenQuanYi Zen Hei, SimHei, sans-serif")

# ---------- 配色 ----------
INK = "#1F2933"
SUB = "#52606D"
FLOW = "#3E4C59"
BG = "#FFFFFF"

SCN = dict(head="#46505C", body="#F7F8FA", line="#9AA5B1")
MOD = dict(head="#5B6B7F", body="#F1F4F8", line="#5B6B7F", chip="#8A99AD")
PRE = dict(head="#23826F", body="#EEF7F5", line="#23826F", chip="#5FAE9E")
COH = dict(head="#2B5FAE", body="#EEF3FB", line="#2B5FAE", chip="#6F95D0")
SCH = dict(head="#6A4C9C", body="#F4F0FA", line="#6A4C9C", chip="#9C86C2")
PLT = dict(head="#A15C10", body="#FDF6EC", line="#A15C10", chip="#C98A3E")
ACCENT = "#C0392B"
IO1, IO2 = "#E07B39", "#C23B5A"

out = []


def add(s):
    out.append(s)


def text_width(s, size):
    """粗略估计文字宽度：CJK 字符 1em，其余 0.56em。"""
    return sum(1.0 if ord(c) > 0x2E7F else 0.56 for c in s) * size


def text(x, y, s, size=20, weight="normal", fill=INK, anchor="middle",
         max_w=None):
    if max_w is not None:
        assert text_width(s, size) <= max_w, f"文字过长: {s}"
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}">{s}</text>')


def ctext(cx, cy, s, size=20, **kw):
    """以 (cx, cy) 为中心放置单行文字。"""
    text(cx, cy + 0.36 * size, s, size, **kw)


def rect(x, y, w, h, fill, stroke="none", sw=1.5, rx=8, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def line(x1, y1, x2, y2, stroke, sw=2, dash=None, opacity=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    o = f' stroke-opacity="{opacity}"' if opacity else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"{d}{o}/>')


def arrow(pts, color=FLOW, sw=2.2, dash=None, head=11, opacity=None):
    """折线箭头，箭头头部为实心三角形（不依赖 marker）。"""
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    L = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    bx, by = x2 - ux * head, y2 - uy * head
    body = pts[:-1] + [(bx, by)]
    d = f' stroke-dasharray="{dash}"' if dash else ""
    o = f' stroke-opacity="{opacity}" fill-opacity="{opacity}"' if opacity else ""
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in body)
    add(f'<polyline points="{p}" fill="none" stroke="{color}" '
        f'stroke-width="{sw}" stroke-linejoin="round"{d}{o}/>')
    hw = head * 0.45
    tri = [(x2, y2), (bx - uy * hw, by + ux * hw), (bx + uy * hw, by - ux * hw)]
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in tri)
    o = f' fill-opacity="{opacity}"' if opacity else ""
    add(f'<polygon points="{p}" fill="{color}"{o}/>')


def card(x, y, w, h, title, sty, hh=40, size=22):
    """带色条标题栏的卡片。"""
    r = 8
    rect(x, y, w, h, sty["body"], "none", rx=r)
    add(f'<path d="M{x},{y + hh} L{x},{y + r} A{r},{r} 0 0 1 {x + r},{y} '
        f'L{x + w - r},{y} A{r},{r} 0 0 1 {x + w},{y + r} L{x + w},{y + hh} Z" '
        f'fill="{sty["head"]}"/>')
    rect(x, y, w, h, "none", sty["line"], sw=1.6, rx=r)
    text(x + 16, y + hh / 2 + 0.36 * size, title, size, "bold", "#FFFFFF",
         anchor="start", max_w=w - 32)


def chip(x, y, w, h, s, sty, size=20):
    rect(x, y, w, h, "#FFFFFF", sty["chip"], sw=1.5, rx=6)
    ctext(x + w / 2, y + h / 2, s, size, fill=INK, max_w=w - 16)


def label_bg(cx, cy, s, size, fill=BG, pad=6):
    """带底色的连线标注（遮住其下方的连线）。"""
    w = text_width(s, size) + 2 * pad
    rect(cx - w / 2, cy - size * 0.68, w, size * 1.36, fill, rx=3)


# ---------- 图元：信号源、目标、接收站 ----------
def tower(cx, top, base, color):
    ey = top + 4
    line(cx - 17, base, cx, ey + 4, color, 2.4)
    line(cx + 17, base, cx, ey + 4, color, 2.4)
    for t in (0.38, 0.68):
        yy = ey + 4 + (base - ey - 4) * t
        line(cx - 17 * t, yy, cx + 17 * t, yy, color, 2)
    line(cx - 24, base, cx + 24, base, color, 2.6)
    add(f'<circle cx="{cx}" cy="{ey}" r="4.5" fill="{color}"/>')
    for rad in (11, 19):
        a = math.radians(40)
        dx, dy = rad * math.cos(a), rad * math.sin(a)
        add(f'<path d="M{cx + dx:.1f},{ey - dy:.1f} A{rad},{rad} 0 0 1 '
            f'{cx + dx:.1f},{ey + dy:.1f}" fill="none" stroke="{color}" '
            f'stroke-width="2.2" stroke-linecap="round"/>')
        add(f'<path d="M{cx - dx:.1f},{ey - dy:.1f} A{rad},{rad} 0 0 0 '
            f'{cx - dx:.1f},{ey + dy:.1f}" fill="none" stroke="{color}" '
            f'stroke-width="2.2" stroke-linecap="round"/>')
    return cx, ey


def plane(cx, cy, s=1.35, rot=-30, color="#34435A"):
    d = ("M0,-22 C3,-22 4,-18 4,-14 L4,-4 L26,6 L26,11 L4,5 L4,14 L10,19 "
         "L10,23 L0,20 L-10,23 L-10,19 L-4,14 L-4,5 L-26,11 L-26,6 L-4,-4 "
         "L-4,-14 C-4,-18 -3,-22 0,-22 Z")
    add(f'<path d="{d}" fill="{color}" '
        f'transform="translate({cx},{cy}) rotate({rot}) scale({s})"/>')


def dish(cx, base, color="#46505C"):
    line(cx, base - 22, cx, base, color, 2.4)
    line(cx - 11, base, cx + 11, base, color, 2.6)
    add(f'<path d="M{cx - 16},{base - 40} Q{cx},{base - 10} {cx + 16},{base - 40} Z" '
        f'fill="#DDE3EA" stroke="{color}" stroke-width="2.2" stroke-linejoin="round"/>')
    line(cx, base - 25, cx, base - 44, color, 1.8)
    add(f'<circle cx="{cx}" cy="{base - 46}" r="3" fill="{color}"/>')
    return cx, base - 46


def shorten(p, q, a=0.0, b=0.0):
    """把线段 p->q 两端分别缩短 a、b。"""
    L = math.hypot(q[0] - p[0], q[1] - p[1])
    ux, uy = (q[0] - p[0]) / L, (q[1] - p[1]) / L
    return (p[0] + ux * a, p[1] + uy * a), (q[0] - ux * b, q[1] - uy * b)


# =====================================================================
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}">')
add('<title>基于多源非合作信号的分布式相参探测项目框图</title>')
rect(0, 0, W, H, BG, rx=0)

# ---------- 左侧：探测场景 ----------
PX, PY, PW, PH = 20, 20, 316, 754
card(PX, PY, PW, PH, "多源非合作探测场景", SCN)
pcx = PX + PW / 2

text(98, 92, "非合作信号源1", 19, "bold", IO1)
text(258, 92, "非合作信号源2", 19, "bold", IO2)
text(pcx, 116, "（广播/通信/卫星信号）", 16, fill=SUB)

e1 = tower(98, 132, 206, IO1)
e2 = tower(258, 132, 206, IO2)
tgt = (178, 400)
rx_base = 650
rxs = [dish(x, rx_base) for x in (48, 113, 178, 243, 308)]

# 直达波（参考信号）
for e, r, c in ((e1, rxs[0], IO1), (e2, rxs[4], IO2)):
    p, q = shorten(e, r, 26, 6)
    arrow([p, q], c, 1.8, dash="7 5", head=10, opacity=0.75)
# 照射信号
for e, c in ((e1, IO1), (e2, IO2)):
    p, q = shorten(e, tgt, 26, 34)
    arrow([p, q], c, 2.4, head=12)
# 目标回波
for r in rxs:
    p, q = shorten(tgt, r, 34, 8)
    arrow([p, q], FLOW, 1.8, head=10)

plane(*tgt)
label_bg(214 + text_width("微弱目标", 19) / 2, 377, "微弱目标", 19, SCN["body"], pad=3)
text(214, 384, "微弱目标", 19, "bold", INK, anchor="start")

for i, (x, _) in enumerate(rxs, 1):
    text(x, rx_base + 26, f"Rx{i}", 18, "bold", INK)
text(pcx, 712, "2发 × 5收：10组双基地通道", 18, fill=SUB)

# 图例
ly = 748
lx = 34
for kind, lab in (("io", "照射信号"), ("echo", "目标回波"), ("direct", "直达波")):
    if kind == "io":
        line(lx, ly - 6, lx + 22, ly - 6, IO1, 2.6)
    elif kind == "echo":
        line(lx, ly - 6, lx + 22, ly - 6, FLOW, 2.2)
    else:
        line(lx, ly - 6, lx + 22, ly - 6, SUB, 2, dash="5 4")
    text(lx + 28, ly, lab, 16, fill=SUB, anchor="start")
    lx += 28 + text_width(lab, 16) + 14

# ---------- 右侧：研究内容 ----------
CX, CW = 420, 960
IN = 20  # 卡片内边距

# 行 1：回波建模
R1Y, R1H = 20, 112
card(CX, R1Y, CW, R1H, "分布式非合作信号源目标回波建模", MOD)
chips1 = ["收发几何模型", "直达波模型", "目标回波模型", "时变杂波模型",
          "多源串扰模型", "同步误差模型"]
cw1 = 143
gap1 = (CW - 2 * IN - len(chips1) * cw1) / (len(chips1) - 1)
for i, s in enumerate(chips1):
    chip(CX + IN + i * (cw1 + gap1), R1Y + 56, cw1, 40, s, MOD)

# 行 2：信号预处理（参数估计 → 串扰抑制 → 杂波抑制）
R2Y, R2H = 172, 172
c2w, c2g = 296, 36
cards2 = [
    ("辐射源参数估计", ["载频、带宽与调制识别", "符号速率与帧结构估计",
                    "时延/频偏/相位偏差估计"]),
    ("多源串扰抑制算法设计", ["多源信号分离与参考重构", "源间互相关串扰抑制",
                       "互模糊函数旁瓣抑制"]),
    ("分布式时变杂波抑制算法", ["直达波与多径杂波对消", "时变杂波自适应抑制",
                        "多站联合杂波抑制"]),
]
c2x = [CX + i * (c2w + c2g) for i in range(3)]
mid2 = R2Y + 40 + (R2H - 40) / 2
for x, (title, items) in zip(c2x, cards2):
    card(x, R2Y, c2w, R2H, title, PRE)
    for k, s in enumerate(items):
        cy = mid2 + (k - 1) * 34
        add(f'<circle cx="{x + 22}" cy="{cy:.1f}" r="4" fill="{PRE["head"]}"/>')
        text(x + 34, cy + 0.36 * 19, s, 19, fill=INK, anchor="start",
             max_w=c2w - 34 - 12)
for i in range(2):
    arrow([(c2x[i] + c2w + 2, mid2), (c2x[i + 1] - 2, mid2)], FLOW, 2.4)

# 行 1 → 行 2：模型支撑
for x in c2x:
    arrow([(x + c2w / 2, R1Y + R1H + 2), (x + c2w / 2, R2Y - 1)], MOD["head"],
          2.2, head=10)
text(c2x[1] + c2w / 2 + 10, R2Y - 14, "模型支撑", 18, fill=MOD["head"],
     anchor="start")

# 行 3：分布式相参探测
R3Y, R3H = 388, 230
card(CX, R3Y, CW, R3H, "分布式相参探测算法设计", COH)
det_x, det_w = CX + IN, 210
dim_x0 = det_x + det_w + 40
dim_w, dim_g = 214, 14
dim_y, dim_h = R3Y + 58, 64
fus_y, fus_h = dim_y + dim_h + 30, 60
dims = [("时域相参", "长时间相参积累"),
        ("多信号源间相参", "源间时频相位对齐"),
        ("分布式接收站间相参", "站间时间/相位同步")]
dim_cx = []
for i, (t, s) in enumerate(dims):
    x = dim_x0 + i * (dim_w + dim_g)
    dim_cx.append(x + dim_w / 2)
    rect(x, dim_y, dim_w, dim_h, "#FFFFFF", COH["line"], sw=1.6, rx=6)
    ctext(x + dim_w / 2, dim_y + 22, t, 20, weight="bold", fill=COH["head"],
          max_w=dim_w - 12)
    ctext(x + dim_w / 2, dim_y + 46, s, 17, fill=SUB, max_w=dim_w - 12)
    arrow([(x + dim_w / 2, dim_y + dim_h + 1), (x + dim_w / 2, fus_y - 1)],
          COH["head"], 2.2, head=10)
fus_x = dim_x0
fus_w = 3 * dim_w + 2 * dim_g
rect(fus_x, fus_y, fus_w, fus_h, COH["head"], rx=6)
ctext(fus_x + fus_w / 2, fus_y + 21, "三维相参融合处理", 22, weight="bold",
      fill="#FFFFFF")
ctext(fus_x + fus_w / 2, fus_y + 45, "时域 × 多源 × 多站联合相参积累，增强目标回波能量",
      17, fill="#DCE7F7", max_w=fus_w - 20)
# 检测
det_y, det_h = dim_y, fus_y + fus_h - dim_y
rect(det_x, det_y, det_w, det_h, "#FFFFFF", COH["line"], sw=1.6, rx=6)
ctext(det_x + det_w / 2, det_y + 26, "微弱目标检测", 20, weight="bold",
      fill=COH["head"])
ctext(det_x + det_w / 2, det_y + 58, "恒虚警(CFAR)检测", 17, fill=INK)
ctext(det_x + det_w / 2, det_y + 84, "多站关联与定位", 17, fill=INK)
foot_h = 40
add(f'<path d="M{det_x},{det_y + det_h - foot_h} L{det_x + det_w},{det_y + det_h - foot_h} '
    f'L{det_x + det_w},{det_y + det_h - 6} A6,6 0 0 1 {det_x + det_w - 6},{det_y + det_h} '
    f'L{det_x + 6},{det_y + det_h} A6,6 0 0 1 {det_x},{det_y + det_h - 6} Z" '
    f'fill="{ACCENT}"/>')
rect(det_x, det_y, det_w, det_h, "none", COH["line"], sw=1.6, rx=6)
ctext(det_x + det_w / 2, det_y + det_h - foot_h / 2, "探测能力提升", 19,
      weight="bold", fill="#FFFFFF")
arrow([(fus_x - 1, fus_y + fus_h / 2), (det_x + det_w + 1, fus_y + fus_h / 2)],
      COH["head"], 2.4)

# 行 2 → 行 3：主数据流 + 辐射源参数
main_x = dim_cx[2]
arrow([(main_x, R2Y + R2H + 2), (main_x, R3Y - 1)], FLOW, 2.6, head=12)
text(main_x + 10, R3Y - 16, "抑制后回波", 18, fill=FLOW, anchor="start")
px = c2x[0] + c2w / 2
ey = R2Y + R2H + 22
arrow([(px, R2Y + R2H + 2), (px, ey), (dim_cx[1], ey), (dim_cx[1], R3Y - 1)],
      PRE["head"], 2, dash="7 5", head=10)
lab = "源间时频/相位参数"
label_bg((px + dim_cx[1]) / 2, ey, lab, 18)
ctext((px + dim_cx[1]) / 2, ey, lab, 18, fill=PRE["head"])

# 行 4：多站址调度
R4Y, R4H = 662, 112
card(CX, R4Y, CW, R4H, "分布式相参多站址调度", SCH)
chips4 = ["站址几何构型优化", "收发通道组合优选", "目标态势驱动调度", "相参融合资源分配"]
cw4 = 218
gap4 = (CW - 2 * IN - len(chips4) * cw4) / (len(chips4) - 1)
for i, s in enumerate(chips4):
    chip(CX + IN + i * (cw4 + gap4), R4Y + 56, cw4, 40, s, SCH)

# 行 3 ↔ 行 4
dcx = det_x + det_w / 2
arrow([(dcx, det_y + det_h + 1), (dcx, R4Y - 1)], FLOW, 2.4)
text(dcx + 10, R4Y - 16, "目标态势", 18, fill=FLOW, anchor="start")
fcx = fus_x + fus_w / 2
arrow([(fcx, R4Y - 1), (fcx, fus_y + fus_h + 1)], SCH["head"], 2.2,
      dash="7 5", head=10)
text(fcx + 10, R4Y - 16, "站址/通道选择", 18, fill=SCH["head"], anchor="start")

# 场景 → 研究内容
arrow([(PX + PW + 2, R1Y + 56 + 20), (CX - 2, R1Y + 56 + 20)], FLOW, 2.4)
ctext((PX + PW + CX) / 2, R1Y + 56 + 20 - 18, "场景参数", 18, fill=FLOW)
arrow([(PX + PW + 2, mid2), (CX - 2, mid2)], FLOW, 2.6, head=12)
ctext((PX + PW + CX) / 2, mid2 - 18, "回波数据", 18, fill=FLOW)

# 调度 → 接收站（反馈）
fx = 378
fy_in = rx_base - 22
arrow([(CX - 1, R4Y + 70), (fx, R4Y + 70), (fx, fy_in), (PX + PW + 2, fy_in)],
      SCH["head"], 2.2, dash="7 5", head=10)
for k, ch in enumerate("站址配置"):
    text(fx + 21, fy_in + 26 + k * 20, ch, 17, fill=SCH["head"])

# ---------- 底部：数字化雷达验证平台 ----------
BY, BH = 822, 184
card(PX, BY, W - 2 * PX, BH, "基于多源非合作信号的数字化雷达验证平台", PLT, size=23)
mods = [("多源场景仿真", ["信号源/目标/站址配置", "非合作信号波形生成"]),
        ("多站回波生成", ["多通道回波数据仿真", "杂波/串扰/噪声注入"]),
        ("算法集成处理", ["参数估计与干扰抑制", "三维相参融合检测"]),
        ("性能评估验证", ["检测概率/虚警概率", "信噪比增益/定位精度"])]
mw, mg = 295, 44
mx0 = PX + 24
my, mh = BY + 58, 108
for i, (t, items) in enumerate(mods):
    x = mx0 + i * (mw + mg)
    rect(x, my, mw, mh, "#FFFFFF", PLT["chip"], sw=1.6, rx=6)
    ctext(x + mw / 2, my + 26, t, 20, weight="bold", fill=PLT["head"])
    for k, s in enumerate(items):
        ctext(x + mw / 2, my + 58 + k * 28, s, 17, fill=INK, max_w=mw - 16)
    if i < len(mods) - 1:
        arrow([(x + mw + 2, my + mh / 2), (x + mw + mg - 2, my + mh / 2)],
              PLT["head"], 2.4)

# 研究内容 ↔ 验证平台
acx = mx0 + 2 * (mw + mg) + mw / 2
arrow([(acx - 50, R4Y + R4H + 2), (acx - 50, BY - 1)], FLOW, 2.4)
text(acx - 60, BY - 18, "算法集成验证", 18, fill=FLOW, anchor="end")
arrow([(acx + 50, BY - 1), (acx + 50, R4Y + R4H + 2)], PLT["head"], 2.4)
text(acx + 60, BY - 18, "性能评估反馈", 18, fill=PLT["head"], anchor="start")

add("</svg>")

dst = Path(__file__).with_name("project_block_diagram.svg")
dst.write_text("\n".join(out), encoding="utf-8")
print(f"written {dst}")
