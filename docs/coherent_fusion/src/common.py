#!/usr/bin/env python3
"""2发5收分布式探测系统相参融合仿真：公共参数、几何模型与绘图样式。"""
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

C0 = 299792458.0

# ---------------------------------------------------------------- 信号参数（类DTMB带宽的CP-OFDM广播信号）
FS = 7.56e6                     # 复基带采样率
NFFT = 2048                     # 子载波数
NCP = 256                       # 循环前缀长度
NSYM_LEN = NFFT + NCP
KACT = np.r_[-945:0, 1:946]     # 1890 个有效子载波（直流置零）
B_OCC = len(KACT) * FS / NFFT   # 占用带宽 ≈ 6.98 MHz
NSYM = 820                      # 每个CPI的OFDM符号数
NCPI = NSYM * NSYM_LEN          # 1 889 280 样点
T_CPI = NCPI / FS               # ≈ 0.25 s
LB = 1845                       # 批处理长度（NCPI = 1024 批 × 1845 样点）
F_TX = np.array([650e6, 658e6])  # 两个信号源载频（相邻 8 MHz 信道，MFN）
LAM = C0 / F_TX

# ---------------------------------------------------------------- 站址（本地东-北-天坐标，单位 m）
TX = np.array([[-14.0, -6.0, 0.30],
               [-11.5, -8.0, 0.25]]) * 1e3
RX = np.array([[0.0, 0.0, 0.05],
               [1.4, 0.6, 0.06],
               [-0.9, 1.1, 0.05],
               [0.8, -1.2, 0.04],
               [2.2, -0.4, 0.05]]) * 1e3
NT, NR = len(TX), len(RX)
NL = NT * NR
LINKS = [(i, j) for i in range(NT) for j in range(NR)]   # l = 5*i + j
LINK_NAMES = [f"T{i + 1}R{j + 1}" for i, j in LINKS]

# 目标（小型旋翼无人机，CPI 中心时刻状态）
P0 = np.array([4.0e3, 28.0e3, 1.5e3])
V0 = np.array([-25.0, -30.0, 0.0])

# ---------------------------------------------------------------- 链路功率预算（双基地雷达方程）
ERP = np.array([10e3, 5e3])     # 两源等效辐射功率 W
G_RX = 10 ** (10 / 10)          # 监视天线增益 10 dBi
NF_DB = 5.0                     # 接收机噪声系数
L_SYS_DB = 5.0                  # 系统损耗
RCS = 0.1                       # 目标双基地 RCS, m^2
K_B, T0 = 1.380649e-23, 290.0


def unit(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def link_geometry(p, v=None, tx=TX, rx=RX, f=F_TX):
    """返回各链路双基地距离差 R_l、多普勒 f_l、波数矢量 k_l（周/米）及双基地角。

    p: (..., 3) 目标位置；结果在最后一维增加长度 NL 的链路维。
    """
    p = np.asarray(p, float)
    R = np.empty(p.shape[:-1] + (NL,))
    fd = np.empty_like(R)
    k = np.empty(p.shape[:-1] + (NL, 3))
    beta = np.empty_like(R)
    for l, (i, j) in enumerate(LINKS):
        dT = p - tx[i]
        dR = p - rx[j]
        RT = np.linalg.norm(dT, axis=-1)
        RR = np.linalg.norm(dR, axis=-1)
        uT, uR = dT / RT[..., None], dR / RR[..., None]
        lam = C0 / f[i]
        R[..., l] = RT + RR - np.linalg.norm(tx[i] - rx[j])
        k[..., l, :] = (uT + uR) / lam
        if v is not None:
            fd[..., l] = -np.sum(np.asarray(v) * (uT + uR), axis=-1) / lam
        beta[..., l] = np.degrees(np.arccos(np.clip(np.sum(uT * uR, axis=-1), -1, 1)))
    return R, fd, k, beta


def link_snr_db(p=P0, rcs=RCS, T=T_CPI):
    """双基地雷达方程给出的各链路 CAF 输出信噪比（dB）。"""
    snr = np.empty(NL)
    for l, (i, j) in enumerate(LINKS):
        RT = np.linalg.norm(p - TX[i])
        RR = np.linalg.norm(p - RX[j])
        pr = ERP[i] * G_RX * LAM[i] ** 2 * rcs / ((4 * np.pi) ** 3 * RT ** 2 * RR ** 2)
        n0 = K_B * T0 * 10 ** (NF_DB / 10)
        snr[l] = 10 * np.log10(pr * T / n0) - L_SYS_DB
    return snr


_AMB = {}


def range_ambiguity(dr):
    """OFDM 信号的归一化距离模糊函数（实偶函数），dr 为双基地距离差偏差（m）。

    以 0.25 m 间隔预先计算 ±6 km 范围的查找表，之外取 0。"""
    if not _AMB:
        g = np.arange(0, 6000.0 + 0.25, 0.25)
        kpos = np.arange(1, 946) * FS / NFFT
        v = np.zeros_like(g)
        for kk in np.array_split(kpos, 16):
            v += 2 * np.cos(2 * np.pi * np.multiply.outer(g / C0, kk)).sum(-1)
        _AMB["g"], _AMB["v"] = g, v / len(KACT)
    a = np.abs(np.asarray(dr, float))
    return np.interp(a, _AMB["g"], _AMB["v"], right=0.0)


# ---------------------------------------------------------------- 绘图样式
plt.rcParams.update({
    "font.family": ["sans-serif"],
    "font.sans-serif": ["WenQuanYi Zen Hei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 9,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.3,
    "grid.linewidth": 0.5,
    "grid.alpha": 0.35,
    "savefig.dpi": 300,
    "figure.dpi": 100,
    "legend.fontsize": 8,
    "legend.framealpha": 0.9,
    # 含 $...$ 的中文标签：数学式外的文字用中文字体，变量用衬线斜体
    "mathtext.fontset": "custom",
    "mathtext.rm": "WenQuanYi Zen Hei",
    "mathtext.it": "DejaVu Serif:italic",
    "mathtext.bf": "WenQuanYi Zen Hei",
    "mathtext.sf": "WenQuanYi Zen Hei",
    "mathtext.default": "regular",
})
C1, C2, C3, C4, C5, C6 = "#1f4e9c", "#c0392b", "#2a8c6f", "#d98a1e", "#6a4c9c", "#5f6b7a"
SRC_COL = ["#E07B39", "#C23B5A"]


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print(f"  figure {name}.png")
