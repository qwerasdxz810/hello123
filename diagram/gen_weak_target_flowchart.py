#!/usr/bin/env python3
"""生成“基于多源非合作信号的微弱目标探测技术”算法流程图（SVG）。

运行：python3 diagram/gen_weak_target_flowchart.py
输出：diagram/weak_target_flowchart.svg

版式仿照“站址调度—双支路—相参融合”的简图：
顶部站址调度经分叉连线引出参考通道、回波通道两条支路，
两支路经汇合连线进入空、时域混合相参融合，最终输出微弱目标检测与定位结果。
箭头均以多边形绘制、样式写在元素属性中，便于导入 Word / PowerPoint / Visio 后编辑。
"""
import math
from pathlib import Path

W, H = 650, 1082
# 支路方框用宋体，首末方框用黑体加粗；如需统一为微软雅黑，修改这两个变量即可
BODY = "SimSun, 宋体, Songti SC, STSong, Noto Serif CJK SC, WenQuanYi Zen Hei, serif"
HEAD = "SimHei, 黑体, Heiti SC, STHeiti, Noto Sans CJK SC, WenQuanYi Zen Hei, sans-serif"

INK = "#000000"
EDGE = "#000000"
FRAME = "#7F7F7F"
# Office 主题色“淡色 80%”，与原图一致
TOP = "#F2F2F2"     # 白色，背景 1，深色 5%
SRC = "#F2DCDB"     # 红色，强调 2，淡色 80%
ECHO = "#FFF2CC"    # 金色，强调 4，淡色 80%
FUSE = "#EBF1DE"    # 橄榄绿，强调 3，淡色 80%

SW = 2.0            # 方框边线与连线线宽
HEAD_L, HEAD_W = 24, 17

out = []


def add(s):
    out.append(s)


def text_width(s, size, spacing=0.0):
    return sum(1.0 if ord(c) > 0x2E7F else 0.56 for c in s) * size + spacing * len(s)


def ctext(cx, cy, lines, size, font=BODY, weight="normal", spacing=0.0,
          lead=1.3, max_w=None):
    """以 (cx, cy) 为中心放置一行或多行文字。"""
    if isinstance(lines, str):
        lines = [lines]
    y0 = cy - (len(lines) - 1) * lead * size / 2
    for k, s in enumerate(lines):
        if max_w is not None:
            assert text_width(s, size, spacing) <= max_w, f"文字过长: {s}"
        ls = f' letter-spacing="{spacing}"' if spacing else ""
        # letter-spacing 会在末字后多留一个间距，左移半个间距保持居中
        add(f'<text x="{cx + spacing / 2:.1f}" y="{y0 + k * lead * size + 0.36 * size:.1f}" '
            f'font-family="{font}" font-size="{size}" font-weight="{weight}" '
            f'fill="{INK}" text-anchor="middle"{ls}>{s}</text>')


def rect(x, y, w, h, fill, stroke=EDGE, sw=SW):
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def polyline(pts, stroke=EDGE, sw=SW):
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    add(f'<polyline points="{p}" fill="none" stroke="{stroke}" '
        f'stroke-width="{sw}" stroke-linejoin="miter"/>')


def arrow(pts, color=EDGE):
    """折线箭头，末端为实心三角形（不依赖 marker）。"""
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    L = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    bx, by = x2 - ux * HEAD_L, y2 - uy * HEAD_L
    polyline(pts[:-1] + [(bx, by)], color)
    hw = HEAD_W / 2
    tri = [(x2, y2), (bx - uy * hw, by + ux * hw), (bx + uy * hw, by - ux * hw)]
    add(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in tri)}" '
        f'fill="{color}"/>')


def box(x, y, w, h, lines, fill, bold=False):
    rect(x, y, w, h, fill)
    if bold:
        ctext(x + w / 2, y + h / 2, lines, 27, font=HEAD, weight="bold",
              spacing=1, max_w=w - 20)
    else:
        ctext(x + w / 2, y + h / 2, lines, 25, spacing=3, max_w=w - 20)


# =====================================================================
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}">')
add('<title>基于多源非合作信号的微弱目标探测技术算法流程图</title>')
add(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#FFFFFF"/>')
rect(1.5, 1.5, W - 3, H - 3, "none", FRAME, sw=1.5)

M = 12                      # 方框距外框的边距
BW, BH = 236, 84            # 支路方框尺寸
LX, RX = M, W - M - BW      # 左、右支路方框左边界
LCX, RCX = LX + BW / 2, RX + BW / 2
MID = W / 2

# ---------- 顶部：站址调度 ----------
TOP_Y, TOP_H = M, 82
box(M, TOP_Y, W - 2 * M, TOP_H, "站址调度", TOP, bold=True)

# 分叉连线
ROW0 = 195                  # 第一行方框顶边
SPLIT_Y = TOP_Y + TOP_H + 38
polyline([(MID, TOP_Y + TOP_H), (MID, SPLIT_Y)])
polyline([(LCX, SPLIT_Y), (RCX, SPLIT_Y)])
arrow([(LCX, SPLIT_Y), (LCX, ROW0)])
arrow([(RCX, SPLIT_Y), (RCX, ROW0)])

# ---------- 两条支路 ----------
ROW_LAST = 650              # 最后一行方框顶边
src = ["参考通道信号", "辐射源信号分选", ["辐射源参数", "精确估计"]]
echo = ["回波通道信号", "抗栅瓣处理", "串扰与杂波抑制", ["长时间积累", "运动补偿"]]


def column(x, items, fill):
    n = len(items)
    step = (ROW_LAST - ROW0) / (n - 1)
    ys = [ROW0 + k * step for k in range(n)]
    for k, (s, y) in enumerate(zip(items, ys)):
        box(x, y, BW, BH, s, fill)
        if k < n - 1:
            arrow([(x + BW / 2, y + BH), (x + BW / 2, ys[k + 1])])


column(LX, src, SRC)
column(RX, echo, ECHO)

# 汇合连线
FUSE_Y = ROW_LAST + BH + 82
MERGE_Y = ROW_LAST + BH + 32
polyline([(LCX, ROW_LAST + BH), (LCX, MERGE_Y), (RCX, MERGE_Y), (RCX, ROW_LAST + BH)])
arrow([(MID, MERGE_Y), (MID, FUSE_Y)])

# ---------- 底部：相参融合与检测定位 ----------
FW, FH = 380, 120
box(MID - FW / 2, FUSE_Y, FW, FH, ["空、时域混合", "分布式相参融合"], FUSE, bold=True)

OUT_Y = FUSE_Y + FH + 50
arrow([(MID, FUSE_Y + FH), (MID, OUT_Y)])
OW, OH = 380, 84
box(MID - OW / 2, OUT_Y, OW, OH, "微弱目标检测与定位", TOP, bold=True)
assert OUT_Y + OH + M <= H, "画布高度不足"

add("</svg>")

dst = Path(__file__).with_name("weak_target_flowchart.svg")
dst.write_text("\n".join(out), encoding="utf-8")
print(f"written {dst}  (bottom margin {H - OUT_Y - OH:.0f}px)")
