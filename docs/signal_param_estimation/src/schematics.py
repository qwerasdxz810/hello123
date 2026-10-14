#!/usr/bin/env python3
"""绘制文档中的示意图（SVG），并用 Chromium 渲染为 PNG。

运行：python3 docs/signal_param_estimation/src/schematics.py
输出：figures/fig1_flow.{svg,png}、figures/fig2_frame.{svg,png}
"""
import math
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIG = HERE.parent / "figures"
FONT = "Microsoft YaHei, WenQuanYi Zen Hei, PingFang SC, sans-serif"
INK, SUB, EDGE = "#1F2933", "#4B5563", "#4A5562"


class Svg:
    def __init__(self, w, h, fs=1.0):
        self.w, self.h, self.o, self.fs = w, h, [], fs
        self.o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
                      f'viewBox="0 0 {w} {h}"><rect width="{w}" height="{h}" fill="#fff"/>')

    def add(self, s):
        self.o.append(s)

    def rect(self, x, y, w, h, fill, stroke="none", sw=1.4, rx=6, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, c=EDGE, sw=1.6, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" '
                 f'stroke-width="{sw}"{d}/>')

    def arrow(self, pts, c=EDGE, sw=1.8, head=10, dash=None):
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        L = math.hypot(x2 - x1, y2 - y1)
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        bx, by = x2 - ux * head, y2 - uy * head
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts[:-1] + [(bx, by)])
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<polyline points="{p}" fill="none" stroke="{c}" stroke-width="{sw}"{d}/>')
        hw = head * 0.45
        tri = [(x2, y2), (bx - uy * hw, by + ux * hw), (bx + uy * hw, by - ux * hw)]
        self.add(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in tri)}" fill="{c}"/>')

    def text(self, x, y, segs, size=18, fill=INK, weight="normal", anchor="middle"):
        """segs: 字符串，或 [(文字, 'sub'|''), ...]，支持下标。"""
        size = size * self.fs
        if isinstance(segs, str):
            segs = [(segs, "")]
        body = []
        for t, kind in segs:
            if kind == "sub":
                body.append(f'<tspan font-size="{size * 0.68:.1f}" dy="{size * 0.28:.1f}">{t}</tspan>'
                            f'<tspan dy="{-size * 0.28:.1f}"></tspan>')
            elif kind == "i":
                body.append(f'<tspan font-style="italic" font-family="Times New Roman, serif">{t}</tspan>')
            else:
                body.append(f"<tspan>{t}</tspan>")
        self.add(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
                 f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{"".join(body)}</text>')

    def save(self, name, scale=3):
        self.add("</svg>")
        svg = FIG / f"{name}.svg"
        svg.write_text("\n".join(self.o), encoding="utf-8")
        subprocess.run(["node", str(HERE / "render.js"), str(svg), str(FIG / f"{name}.png"),
                        str(scale)], check=True)


def V(s):
    """变量符号：斜体字母 + 可选下标，例如 V('T','sym')。"""
    return s


# ======================= 图1 估计流程 =======================
def fig_flow():
    W, H = 1200, 800
    g = Svg(W, H, fs=1.3)
    cols = [
        ("① 信号层参数盲估计", "#2B5FAE", "#EEF3FB"),
        ("② 帧结构参数识别", "#23826F", "#EEF7F5"),
        ("③ 时频参数精确估计", "#A15C10", "#FDF6EC"),
    ]
    cw, gap, x0 = 360, 40, 20
    xs = [x0 + i * (cw + gap) for i in range(3)]
    hy, hh = 96, 50
    # 输入
    g.rect(xs[0] + 70, 14, 220, 52, "#46505C", rx=26)
    g.text(xs[0] + 180, 50, [("接收信号 ", ""), ("r", "i"), ("(", ""), ("n", "i"), (")", "")],
           20, "#fff", "bold")
    g.arrow([(xs[0] + 180, 66), (xs[0] + 180, hy - 2)], "#46505C")
    for i, (t, c, _) in enumerate(cols):
        g.rect(xs[i], hy, cw, hh, c, rx=6)
        g.text(xs[i] + cw / 2, hy + 35, t, 21, "#fff", "bold")
        if i < 2:
            cx = xs[i] + cw + gap / 2
            g.add(f'<polygon points="{cx - 12},{hy + 8} {cx + 10},{hy + hh / 2} '
                  f'{cx - 12},{hy + hh - 8} {cx - 4},{hy + hh / 2}" fill="#9AA5B1"/>')

    boxes = [
        [("功率谱估计", ["占用带宽、中心空隙位置", "→ 频偏粗估计"]),
         ("CP 自相关", [[("有用符号长度 ", ""), ("T", "i")],
                       [("子载波间隔 Δ", ""), ("f", "i"), (" = 1/", ""), ("T", "i")]]),
         ("循环自相关", [[("符号周期 ", ""), ("T", "i"), ("sym", "sub")],
                       [("CP 长度 ", ""), ("T", "i"), ("g", "sub"), (" = ", ""), ("T", "i"),
                        ("sym", "sub"), (" − ", ""), ("T", "i")]]),
         ("整数约束判定", [[("采样率 ", ""), ("F", "i"), ("s", "sub"), ("、子载波数 ", ""), ("N", "i")],
                         [("CP 样点数 ", ""), ("N", "i"), ("g", "sub"), ("，反算精确参数", "")]])],
        [("长时延自相关", [[("帧周期 ", ""), ("T", "i"), ("f", "sub")]]),
         ("帧同步功率折叠", [[("帧保护 ", ""), ("T", "i"), ("fg", "sub"), ("、每帧符号数 ", ""),
                            ("N", "i"), ("sf", "sub")], "帧起点位置"]),
         ("跨帧相干平均", ["同步符号（PSS/SSS）", "波形提取"])],
        [("CP 最大似然估计", ["符号定时、小数倍频偏", "（非数据辅助，多符号累加）"]),
         ("整数倍频偏解模糊", ["结合功率谱频偏粗估计", "→ 完整频偏估计"]),
         ("同步符号辅助估计", ["精确定时、多帧相干频偏", "（数据辅助，逼近 CRB）"]),
         ("解调与调制识别", ["高阶累积量特征", "→ 子载波调制方式"])],
    ]
    by0, bh, bg = 166, 112, 30
    for i, col in enumerate(boxes):
        c, tint = cols[i][1], cols[i][2]
        for j, (title, lines) in enumerate(col):
            y = by0 + j * (bh + bg)
            g.rect(xs[i], y, cw, bh, tint, c, sw=1.6)
            g.text(xs[i] + cw / 2, y + 34, title, 20, c, "bold")
            for k, ln in enumerate(lines):
                g.text(xs[i] + cw / 2, y + (78 if len(lines) == 1 else 67 + k * 30), ln, 17, INK)
            if j < len(col) - 1:
                g.arrow([(xs[i] + cw / 2, y + bh + 1), (xs[i] + cw / 2, y + bh + bg - 1)], c)
        g.arrow([(xs[i] + cw / 2, hy + hh + 1), (xs[i] + cw / 2, by0 - 1)], c)
    # 同步符号 → 数据辅助估计
    y3 = by0 + 2 * (bh + bg) + bh / 2
    g.arrow([(xs[1] + cw + 1, y3), (xs[2] - 1, y3)], "#23826F", dash="6 4")
    g.text(xs[1] + cw + gap / 2, y3 - 8, "", 14)
    # 输出
    oy = by0 + 4 * (bh + bg) - bg + 30
    g.arrow([(xs[2] + cw / 2, by0 + 3 * (bh + bg) + bh + 1), (xs[2] + cw / 2, oy - 1)], cols[2][1])
    g.rect(xs[0], oy, W - 2 * x0, 54, "#46505C", rx=6)
    g.text(W / 2, oy + 36, "参数输出：参考信号重构 · 多源串扰抑制 · 多源/多站相参融合", 20, "#fff", "bold")
    g.save("fig1_flow")


# ======================= 图2 帧/符号/频域结构 =======================
def fig_frame():
    W, H = 1200, 700
    g = Svg(W, H, fs=1.25)
    BLUE, TEAL, AMB, GRAY = "#2B5FAE", "#23826F", "#A15C10", "#9AA5B1"

    def dim(x1, x2, y, label, c=INK, size=17):
        g.line(x1, y - 7, x1, y + 7, c, 1.2)
        g.line(x2, y - 7, x2, y + 7, c, 1.2)
        g.arrow([(x1 + 30, y), (x1 + 1, y)], c, 1.2, 8) if False else None
        g.line(x1, y, x2, y, c, 1.2)
        for xa, sgn in ((x1, 1), (x2, -1)):
            g.add(f'<polygon points="{xa},{y} {xa + 9 * sgn},{y - 4} {xa + 9 * sgn},{y + 4}" fill="{c}"/>')
        g.text((x1 + x2) / 2, y - 9, label, size, c)

    # (a) 帧结构
    g.text(30, 36, "(a) 帧结构", 19, INK, "bold", "start")
    X0, X1, Y, Hb = 70, 1090, 92, 50
    pss_w = 70
    guard_w = 62
    g.rect(X0, Y, pss_w, Hb, BLUE, rx=2)
    g.text(X0 + pss_w / 2, Y + 32, "PSS", 18, "#fff", "bold")
    g.rect(X0 + pss_w, Y, pss_w, Hb, "#5B86C9", rx=2)
    g.text(X0 + 1.5 * pss_w, Y + 32, "SSS", 18, "#fff", "bold")
    dx0 = X0 + 2 * pss_w
    dx1 = X1 - guard_w
    g.rect(dx0, Y, dx1 - dx0, Hb, "#DCE7F7", BLUE, sw=1.2, rx=2)
    nsym_draw = 14
    sw_ = (dx1 - dx0) / nsym_draw
    for k in range(1, nsym_draw):
        g.line(dx0 + k * sw_, Y, dx0 + k * sw_, Y + Hb, "#9DB6E0", 1)
    g.rect(dx0 + 5 * sw_ + 2, Y + 3, sw_ * 4 - 4, Hb - 6, "#DCE7F7", rx=0)
    g.text(dx0 + 7 * sw_, Y + 32, "… 数据符号 …", 17, BLUE, "bold")
    g.rect(dx1, Y, guard_w, Hb, "#F1F2F4", GRAY, sw=1.2, rx=2, dash="4 3")
    g.text(dx1 + guard_w / 2, Y + 32, "保护", 16, SUB)
    g.rect(X1 + 8, Y, 60, Hb, "#2B5FAE", rx=2)
    g.add(f'<rect x="{X1 + 8}" y="{Y}" width="60" height="{Hb}" fill="#fff" fill-opacity="0.55"/>')
    g.text(X1 + 38, Y + 32, "下一帧", 14, "#1d3f78")
    dim(X0, X1, Y - 22, "", INK)
    g.text((X0 + X1) / 2, Y - 37, [("帧周期 ", ""), ("T", "i"), ("f", "sub"),
                                    (" = 1/750 s ≈ 1.333 ms", "")], 17)
    dim(X0, dx1, Y + Hb + 58, "", BLUE)
    g.text((X0 + dx1) / 2 + 60, Y + Hb + 45,
           [("N", "i"), ("sf", "sub"), (" = 302 个符号间隔（首部为 PSS、SSS）", "")], 17, BLUE)
    g.text(dx1 + guard_w / 2, Y + Hb + 30, [("T", "i"), ("fg", "sub"), (" = 68/15 μs", "")], 16, SUB)

    # (b) 符号结构
    yb = 300
    g.text(30, yb - 50, "(b) OFDM 符号结构", 19, INK, "bold", "start")
    zx = dx0 + 3 * sw_
    g.line(zx, Y + Hb, 260, yb, GRAY, 1, "4 3")
    g.line(zx + sw_, Y + Hb, 940, yb, GRAY, 1, "4 3")
    g.rect(zx, Y, sw_, Hb, "none", "#C0392B", sw=2, rx=1)
    cpw = 120
    g.rect(260, yb, cpw, 52, "#F6D7A7", AMB, sw=1.4, rx=2)
    g.text(260 + cpw / 2, yb + 33, "CP", 18, AMB, "bold")
    g.rect(260 + cpw, yb, 940 - 260 - cpw, 52, "#DCE7F7", BLUE, sw=1.4, rx=2)
    g.text((260 + cpw + 940) / 2, yb + 33, "有用符号（IFFT 输出）", 18, BLUE, "bold")
    tail = 940 - cpw
    g.rect(tail, yb, cpw, 52, "#F6D7A7", AMB, sw=1.2, rx=2, dash="5 3")
    g.text(tail + cpw / 2, yb + 33, "尾部", 16, AMB)
    g.add(f'<path d="M{tail + cpw / 2},{yb - 4} C{tail},{yb - 52} {380},{yb - 52} {320},{yb - 6}" '
          f'fill="none" stroke="{AMB}" stroke-width="1.6"/>')
    g.add(f'<polygon points="320,{yb - 2} 314,{yb - 14} 327,{yb - 12}" fill="{AMB}"/>')
    g.text(620, yb - 54, "循环复制", 16, AMB)
    dim(260, 260 + cpw, yb + 80, "", AMB)
    g.text(260 + cpw / 2, yb + 106, [("N", "i"), ("g", "sub"), (" = 32，", ""), ("T", "i"),
                                     ("g", "sub"), (" = 2/15 μs", "")], 16, AMB)
    dim(260 + cpw, 940, yb + 80, "", BLUE)
    g.text((260 + cpw + 940) / 2, yb + 106, [("N", "i"), (" = 1024，", ""), ("T", "i"),
                                             (" = 64/15 μs ≈ 4.267 μs", "")], 16, BLUE)
    dim(260, 940, yb + 132, "", INK)
    g.text(600, yb + 158, [("T", "i"), ("sym", "sub"), (" = ", ""), ("T", "i"), (" + ", ""),
                           ("T", "i"), ("g", "sub"), (" = 4.4 μs", "")], 17)

    # (c) 频域结构
    yc = 610
    g.text(30, yc - 76, "(c) 信道频域结构", 19, INK, "bold", "start")
    cx, half = 600, 300
    top = yc - 50
    g.add(f'<path d="M{cx - half},{yc} L{cx - half},{top} L{cx - 7},{top} L{cx - 7},{yc - 6} '
          f'L{cx + 7},{yc - 6} L{cx + 7},{top} L{cx + half},{top} L{cx + half},{yc} Z" '
          f'fill="#DCE7F7" stroke="{BLUE}" stroke-width="1.4"/>')
    for sx in (cx - half - 25 - 150, cx + half + 25):
        g.rect(sx, top, 150, 50, "#EEF1F5", GRAY, sw=1.2, rx=0, dash="5 3")
    g.text(cx - half - 25 - 75, top + 32, "相邻信道", 15, SUB)
    g.text(cx + half + 25 + 75, top + 32, "相邻信道", 15, SUB)
    g.line(100, yc, 1100, yc, INK, 1.2)
    g.text(cx, top + 32 - 4, "", 16)
    g.text(cx - 150, top + 32, [("F", "i"), ("s", "sub"), (" = 240 MHz", "")], 17, BLUE)
    g.text(cx + 150, top + 32, [("Δ", ""), ("f", "i"), (" = 234.375 kHz", "")], 17, BLUE)
    g.arrow([(cx + 40, yc + 32), (cx + 6, yc - 2)], "#C0392B", 1.4, 8)
    g.text(cx + 46, yc + 40, "中心空隙（4 个空子载波）", 15, "#C0392B", anchor="start")
    gx = cx - half - 12.5
    g.line(gx, yc + 4, gx, yc + 12, SUB, 1)
    g.text(gx, yc + 30, "保护带 10 MHz", 14, SUB)
    dim(cx, cx + half + 25 + 75, top - 16, "", SUB)
    g.text(cx + (half + 100) / 2, top - 24, "信道间隔 250 MHz", 14, SUB)
    g.save("fig2_frame")


if __name__ == "__main__":
    fig_flow()
    fig_frame()
    print("done")
