#!/usr/bin/env python3
"""绘制方案文档中的示意图：系统几何（按比例）、总体处理流程、融合模式。

运行：python3 docs/coherent_fusion/src/schematics.py
输出：figures/fig_geometry.png、figures/fig_flow.{svg,png}、figures/fig_modes.{svg,png}
"""
import math
import subprocess

import numpy as np

from common import (HERE, FIG, TX, RX, P0, V0, NL, LINKS, LINK_NAMES, C0, B_OCC, link_geometry, plt, save,
                    SRC_COL, C6)

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
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="{sw}"{d}/>')

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
        """segs: 字符串，或 [(文字, ''|'i'|'sub'|'sup'), ...]。"""
        size = size * self.fs
        if isinstance(segs, str):
            segs = [(segs, "")]
        body = []
        cur = 0.0                                    # 当前基线偏移（像素，向下为正）
        for t, kind in segs:
            off = {"sub": 0.28 * size, "sup": -0.38 * size}.get(kind, 0.0)
            dy = off - cur
            cur = off
            dya = f' dy="{dy:.1f}"' if abs(dy) > 1e-6 else ""
            if kind in ("sub", "sup"):
                body.append(f'<tspan font-size="{size * 0.68:.1f}"{dya}>{t}</tspan>')
            elif kind == "i":
                body.append(f'<tspan font-style="italic" font-family="Times New Roman, serif"{dya}>{t}</tspan>')
            else:
                body.append(f"<tspan{dya}>{t}</tspan>")
        self.add(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
                 f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{"".join(body)}</text>')

    def save(self, name, scale=3):
        self.add("</svg>")
        svg = FIG / f"{name}.svg"
        svg.write_text("\n".join(self.o), encoding="utf-8")
        subprocess.run(["node", str(HERE / "render.js"), str(svg), str(FIG / f"{name}.png"), str(scale)],
                       check=True)
        print(f"  figure {name}.png")


STA = dict(head="#23826F", body="#EEF7F5")
FUS = dict(head="#2B5FAE", body="#EEF3FB")
OUT = "#46505C"


# ======================= 图：总体处理流程 =======================
def fig_flow():
    W, H = 1240, 980
    g = Svg(W, H, fs=1.0)
    # ---- 接收站 ----
    X0, CW = 20, 560
    g.rect(X0, 20, CW, H - 40, STA["body"], STA["head"], sw=1.8, rx=10)
    g.rect(X0, 20, CW, 52, STA["head"], rx=10)
    g.rect(X0, 52, CW, 20, STA["head"], rx=0)
    g.text(X0 + CW / 2, 56, "接收站 j（j = 1, …, 5）站内处理", 23, "#fff", "bold")
    # 天线输入
    ay = 96
    for k, (t, s) in enumerate((("参考天线", "对准两个信号源"), ("监视天线", "对准监视空域"))):
        x = X0 + 30 + k * 260
        g.rect(x, ay, 240, 64, "#fff", STA["head"], sw=1.4)
        g.text(x + 120, ay + 28, t, 19, STA["head"], "bold")
        g.text(x + 120, ay + 52, s, 15, SUB)
        g.arrow([(x + 120, ay + 65), (x + 120, ay + 98)], STA["head"])
    L = ("l", "sub")
    steps = [
        ("同步采样与时间标记", [("两通道共用本振/时钟（GNSS 驯服），以 CPI 中心时刻 ", ""), ("t", "i"), ("c", "sub"),
                          (" 打标", "")]),
        ("① 数字信道化与多源分离", "分别得到信号源 T1、T2 的参考/监视基带信号"),
        ("② 辐射源参数估计", "载频偏差、符号定时、帧结构（见《信号源参数精确估计技术》）"),
        ("③ 参考信号提纯", "解调—再调制重构，并保留本站直达波的复增益与相位"),
        ("④ 直达波/多径杂波对消", [("ECA：将监视信号投影到 {", ""), ("d̂", "i"), ("(", ""), ("n", "i"), ("−", ""),
                             ("k", "i"), (")} 的正交补空间", "")]),
        ("⑤ 距离—多普勒相参积累", [("批处理互模糊函数 ", ""), ("χ", "i"), L, ("(", ""), ("τ", "i"), (", ", ""),
                             ("f", "i"), (")，相位基准统一到 ", ""), ("t", "i"), ("c", "sub")]),
        ("⑥ 通道相位标定与噪声归一化", [("相位 ", ""), ("κ", "i"), L, ("（注入校准 + 直达波泄漏监测）、噪声 ", ""),
                                ("σ", "i"), L, ("²", "")]),
    ]
    sy, sh, sg = ay + 100, 74, 16
    for k, (t, s) in enumerate(steps):
        y = sy + k * (sh + sg)
        g.rect(X0 + 30, y, CW - 60, sh, "#fff", STA["head"], sw=1.4)
        g.text(X0 + CW / 2, y + 30, t, 19, STA["head"], "bold")
        g.text(X0 + CW / 2, y + 56, s, 14.5, INK)
        if k < len(steps) - 1:
            g.arrow([(X0 + CW / 2, y + sh + 1), (X0 + CW / 2, y + sh + sg - 1)], STA["head"])
    g.text(X0 + CW - 40, sy + 2 * (sh + sg) - 4, "×2（两源并行）", 14, STA["head"], anchor="end")
    oy = sy + len(steps) * (sh + sg) + 4
    g.arrow([(X0 + CW / 2, oy - sg + 1), (X0 + CW / 2, oy - 1)], STA["head"])
    g.rect(X0 + 30, oy, CW - 60, 66, OUT, rx=8)
    g.text(X0 + CW / 2, oy + 28, "每站输出 2 条链路（T1R j、T2R j）", 18, "#fff", "bold")
    g.text(X0 + CW / 2, oy + 52, [("复数距离—多普勒图 ", ""), ("χ", "i"), L, ("(", ""), ("τ", "i"), (", ", ""),
                                  ("f", "i"), (")、", ""), ("σ", "i"), L, ("²、", ""), ("κ", "i"), L,
                                  ("、时间戳、站址", "")], 14.5, "#E5E9EE")

    # ---- 融合中心 ----
    X1, CW1 = 660, 560
    g.rect(X1, 20, CW1, H - 40, FUS["body"], FUS["head"], sw=1.8, rx=10)
    g.rect(X1, 20, CW1, 52, FUS["head"], rx=10)
    g.rect(X1, 52, CW1, 20, FUS["head"], rx=0)
    g.text(X1 + CW1 / 2, 56, "融合中心：10 链路相参融合检测", 23, "#fff", "bold")
    fsteps = [
        ("⑦ 目标状态空间网格", [("θ", "i"), (" = (", ""), ("p", "i"), (", ", ""), ("v", "i"), (")：计算 ", ""), ("R", "i"), L,
                          ("(θ)、", ""), ("f", "i"), L, ("(θ)、波数矢量 ", ""), ("k", "i"), L]),
        ("⑧ 非相参粗检测（包络级）", [("T", "i"), ("N", "sub"), ("(θ) = Σ", ""), L, (" |", ""), ("z̃", "i"), L,
                              ("|²，粗网格、低门限 → 候选单元", "")]),
        ("⑨ 相位补偿与加权", [("z̃", "i"), L, (" exp[ j(2π", ""), ("R", "i"), L, ("/", ""), ("λ", "i"), L, (" − ", ""),
                         ("κ", "i"), L, (") ]，MRC 权 ", ""), ("w", "i"), L, (" ∝ (SNR", ""), L, (")", ""),
                         ("1/2", "sup")]),
        ("⑩ 相参精搜索（相位级）", [("T", "i"), ("C", "sub"), (" = max", ""), ("δp", "sub"), (" |Σ ", ""), ("w", "i"), L,
                             ("z̃", "i"), L, (" exp( j2π", ""), ("k", "i"), L, ("·δ", ""), ("p", "i"),
                             (") |² / Σ", ""), ("w", "i"), L, ("²", "")]),
        ("⑪ 相参性自适应判决", "相参/非相参双支路（Pfa 分配）或分组相参 → CFAR"),
        ("⑫ 检测输出与精定位", "目标状态估计（波长级相参定位）→ 航迹"),
    ]
    fy = 116
    fh, fg = 84, 26
    for k, (t, s) in enumerate(fsteps):
        y = fy + k * (fh + fg)
        g.rect(X1 + 30, y, CW1 - 60, fh, "#fff", FUS["head"], sw=1.4)
        g.text(X1 + CW1 / 2, y + 34, t, 19, FUS["head"], "bold")
        g.text(X1 + CW1 / 2, y + 62, s, 14.5, INK)
        if k < len(fsteps) - 1:
            g.arrow([(X1 + CW1 / 2, y + fh + 1), (X1 + CW1 / 2, y + fh + fg - 1)], FUS["head"])
    # 站 → 中心
    yin = fy + fh / 2
    g.arrow([(X0 + CW - 30, oy + 33), (X0 + CW + 40, oy + 33), (X0 + CW + 40, yin), (X1 + 29, yin)], OUT, 2.4, 12)
    g.text(X1 + CW1 / 2, 100, "输入：5 站 × 2 源 = 10 条链路", 16, OUT, "bold")
    # 反馈：标定更新
    yb = fy + 5 * (fh + fg) + fh / 2
    ystep6 = sy + 6 * (sh + sg) + sh / 2
    g.arrow([(X1 + CW1 - 30, yb), (X1 + CW1 - 12, yb), (X1 + CW1 - 12, H - 52), (X0 + CW + 20, H - 52),
             (X0 + CW + 20, ystep6), (X0 + CW - 29, ystep6)], "#A15C10", 1.8, 10, dash="7 5")
    g.text(X1 + CW1 / 2, H - 62, [("强目标/合作标校目标相位自校准 → 更新 ", ""), ("κ", "i"), L, ("、站址/通道选择", "")],
           14.5, "#A15C10")
    g.save("fig_flow")


# ======================= 图：融合模式 =======================
def fig_modes():
    W, H = 1240, 400
    g = Svg(W, H)
    pw, gap = 290, 20
    titles = ["(a) 非相参融合", "(b) 源间相参", "(c) 站间相参", "(d) 10 链路全相参"]
    Z = [("w", "i"), ("ij", "sub"), ("z̃", "i"), ("ij", "sub"), (" e", ""), ("jΦ", "sup")]
    forms = [[("T", "i"), ("N", "sub"), (" = Σ", ""), ("i,j", "sub"), (" |", ""), ("z̃", "i"), ("ij", "sub"), ("|²", "")],
             [("Σ", ""), ("j", "sub"), (" |Σ", ""), ("i", "sub"), (" ", "")] + Z + [("|²", "")],
             [("Σ", ""), ("i", "sub"), (" |Σ", ""), ("j", "sub"), (" ", "")] + Z + [("|²", "")],
             [("|Σ", ""), ("i,j", "sub"), (" ", "")] + Z + [("|²", "")]]
    conds = ["无相位要求；对散射去相关稳健", "两源对目标视角差、载频差小",
             "接收站相对目标张角小（站址紧凑）", "（b）（c）条件同时满足"]
    cols = ["#2A8C6F", "#D98A1E", "#6A4C9C", "#2B5FAE"]
    for m in range(4):
        x0 = 20 + m * (pw + gap)
        g.rect(x0, 16, pw, H - 32, "#FAFBFC", "#C5CCD5", sw=1.2, rx=8)
        g.text(x0 + pw / 2, 50, titles[m], 20, cols[m], "bold")
        cs, cg = 44, 8
        gx0 = x0 + (pw - (5 * cs + 4 * cg)) / 2
        gy0 = 110
        # 分组框
        if m == 0:
            boxes = [(i, j, i, j) for i in range(2) for j in range(5)]
        elif m == 1:
            boxes = [(0, j, 1, j) for j in range(5)]
        elif m == 2:
            boxes = [(i, 0, i, 4) for i in range(2)]
        else:
            boxes = [(0, 0, 1, 4)]
        for (i0, j0, i1, j1) in boxes:
            bx = gx0 + j0 * (cs + cg) - 4
            by = gy0 + i0 * (cs + cg) - 4
            bw = (j1 - j0) * (cs + cg) + cs + 8
            bh = (i1 - i0) * (cs + cg) + cs + 8
            g.rect(bx, by, bw, bh, "none", cols[m], sw=2.2, rx=7)
        for i in range(2):
            for j in range(5):
                x = gx0 + j * (cs + cg)
                y = gy0 + i * (cs + cg)
                g.rect(x, y, cs, cs, ["#FBE3D3", "#F6D3DC"][i], ["#E07B39", "#C23B5A"][i], sw=1.2, rx=4)
                g.text(x + cs / 2, y + 20, f"T{i + 1}", 12.5, INK)
                g.text(x + cs / 2, y + 36, f"R{j + 1}", 12.5, INK)
        g.text(gx0 - 14, gy0 + 28, "源1", 12.5, "#E07B39", anchor="end")
        g.text(gx0 - 14, gy0 + cs + cg + 28, "源2", 12.5, "#C23B5A", anchor="end")
        g.text(x0 + pw / 2, 268, forms[m], 18, INK)
        g.text(x0 + pw / 2, 312, "适用条件：", 15, SUB)
        g.text(x0 + pw / 2, 340, conds[m], 15, INK)
    g.save("fig_modes")


# ======================= 图：系统几何（按比例） =======================
def fig_geometry():
    R0, fd0, k0, beta0 = link_geometry(P0, V0)
    fig = plt.figure(figsize=(7.4, 3.6))
    ax = fig.add_axes([0.07, 0.12, 0.42, 0.82])
    km = 1e3
    for i in range(2):
        ax.plot([TX[i, 0] / km, P0[0] / km], [TX[i, 1] / km, P0[1] / km], color=SRC_COL[i], lw=1.0)
        for j in range(5):
            ax.plot([TX[i, 0] / km, RX[j, 0] / km], [TX[i, 1] / km, RX[j, 1] / km], color=SRC_COL[i], lw=0.6,
                    ls="--", alpha=0.7)
    for j in range(5):
        ax.plot([P0[0] / km, RX[j, 0] / km], [P0[1] / km, RX[j, 1] / km], color=C6, lw=0.7)
    ax.plot(TX[:, 0] / km, TX[:, 1] / km, "^", ms=8, color="k", mfc="#E07B39", zorder=5)
    for i in range(2):
        ax.text(TX[i, 0] / km - 0.6, TX[i, 1] / km + (0.8 if i == 0 else -2.2), f"T{i + 1}", fontsize=8,
                ha="right")
    ax.plot(RX[:, 0] / km, RX[:, 1] / km, "o", ms=4, color="k", mfc="#2B5FAE", zorder=5)
    ax.plot(P0[0] / km, P0[1] / km, "*", ms=11, color="#C0392B", zorder=6)
    ax.annotate("", xy=(P0[0] / km + V0[0] / 12, P0[1] / km + V0[1] / 12), xytext=(P0[0] / km, P0[1] / km),
                arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1.0))
    ax.annotate("目标（无人机）\n高度 1.5 km，39 m/s", xy=(P0[0] / km - 0.4, P0[1] / km - 0.3),
                xytext=(-16.2, 25.5), fontsize=7.5, color="#C0392B",
                arrowprops=dict(arrowstyle="->", color="#C0392B", lw=0.7))
    ax.annotate("接收站群 R1~R5\n（右下放大）", xy=(0.3, 1.2), xytext=(-8.5, 6.5), fontsize=7.5, color="#2B5FAE",
                arrowprops=dict(arrowstyle="->", color="#2B5FAE", lw=0.7))
    ax.set_xlabel("东向 x / km")
    ax.set_ylabel("北向 y / km")
    ax.set_xlim(-17, 12)
    ax.set_ylim(-11, 31)
    ax.set_aspect("equal")
    ax.grid()
    ax.set_title("(a) 2 发 5 收构型（俯视）", fontsize=8.5)
    # 插图：接收站群
    ins = ax.inset_axes([0.60, 0.035, 0.385, 0.27])
    ins.plot(RX[:, 0] / km, RX[:, 1] / km, "o", ms=4, color="k", mfc="#2B5FAE")
    for j in range(5):
        ins.text(RX[j, 0] / km + 0.15, RX[j, 1] / km + 0.12, f"R{j + 1}", fontsize=6.5)
    ins.set_xlim(-1.6, 3.2)
    ins.set_ylim(-1.8, 1.8)
    ins.tick_params(labelsize=6)
    ins.set_aspect("equal")
    ins.grid()
    # (b) 目标附近等双基地距离线
    ax2 = fig.add_axes([0.58, 0.12, 0.40, 0.82])
    h = np.linspace(-1500, 1500, 301)
    X, Y = np.meshgrid(h, h, indexing="ij")
    pts = np.stack([P0[0] + X, P0[1] + Y, np.full(X.shape, P0[2])], -1)
    R, _, _, _ = link_geometry(pts)
    for l in range(NL):
        i, j = LINKS[l]
        dr = C0 / B_OCC
        ax2.contour(h / km, h / km, (R[..., l] - R0[l]).T, levels=[-dr, 0, dr], colors=[SRC_COL[i]],
                    linewidths=[0.5, 1.0, 0.5], linestyles=["--", "-", "--"])
    ax2.plot(0, 0, "*", ms=10, color="#C0392B")
    for i in range(2):
        ax2.plot([], [], color=SRC_COL[i], label=f"T{i + 1} 的 5 条链路")
    ax2.legend(fontsize=7, loc="upper right")
    ax2.set_xlabel("Δx / km")
    ax2.set_ylabel("Δy / km")
    ax2.set_aspect("equal")
    ax2.grid()
    ax2.set_title("(b) 目标附近 10 条链路的等双基地距离线（虚线：±c/B）", fontsize=8.5)
    save(fig, "fig_geometry")


if __name__ == "__main__":
    fig_geometry()
    fig_flow()
    fig_modes()
    print("done")
