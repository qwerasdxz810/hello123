#!/usr/bin/env python3
"""2发5收分布式探测系统 —— 相参融合的统计性能分析（互模糊函数输出层仿真）。

内容：目标散射相参性与两源相参条件、同步/标定误差容限、“粗—精”搜索的等效独立单元数、
检测概率曲线、目标尺寸对相参增益的影响、时域×源×站三维相参组合增益、布站尺度影响。

运行：python3 docs/coherent_fusion/src/sim_stats.py
输出：figures/st_*.png 与 src/results_stats.json
"""
import json
import time

import numpy as np
from scipy import stats

from common import (C0, FS, F_TX, LAM, TX, RX, NT, NR, NL, LINKS, LINK_NAMES, P0, V0, T_CPI, B_OCC,
                    link_geometry, link_snr_db, range_ambiguity, plt, save, C1, C2, C3, C4, C5, C6, HERE)

rng = np.random.default_rng(20261014)
PFA = 1e-6
PD_REQ = 0.9
SNR_DB = link_snr_db()
A_REL = np.sqrt(10 ** (SNR_DB / 10) / np.mean(10 ** (SNR_DB / 10)))   # 链路相对幅度（均方为 1）
R0, FD0, K0, BETA0 = link_geometry(P0, V0)
SRC = np.array([i for i, _ in LINKS])
RCV = np.array([j for _, j in LINKS])
GROUPS = {
    "nc": [[l] for l in range(NL)],
    "pair": [[j, j + NR] for j in range(NR)],                 # 同一接收站两个信号源（源间相参）
    "grp": [list(range(i * NR, (i + 1) * NR)) for i in range(NT)],   # 同一信号源五个接收站（站间相参）
    "coh": [list(range(NL))],
}
res = {}


# ================================================================ 目标散射模型
def body_axes(v=V0):
    ex = v / np.linalg.norm(v)
    ez = np.array([0.0, 0.0, 1.0])
    ey = np.cross(ez, ex)
    return np.stack([ex, ey, ez])                    # 行：机体 x/y/z 轴在 ENU 中的方向


DIMS = np.array([1.0, 0.8, 0.25])                   # 机体尺寸比例（长:宽:高）


def coherence_matrix(lt, k=K0):
    """均匀分布散射中心模型下的链路间散射系数相关矩阵 ρ_ll' = Π sinc(Δk·L)。"""
    kb = k @ body_axes().T                           # 机体坐标系波数（周/米）
    dk = kb[:, None, :] - kb[None, :, :]
    return np.prod(np.sinc(dk * (lt * DIMS)), axis=-1)


def draw_alpha(lt, n, ns=12, k=K0):
    """随机散射中心目标：返回 (n, NL) 复散射系数，E|α|²=1。"""
    pos = (rng.uniform(-0.5, 0.5, (n, ns, 3)) * (lt * DIMS)) @ body_axes()
    amp = (rng.standard_normal((n, ns)) + 1j * rng.standard_normal((n, ns))) / np.sqrt(2 * ns)
    return np.einsum("nm,nml->nl", amp, np.exp(-2j * np.pi * np.einsum("nmd,ld->nml", pos, k)))


# ================================================================ 1) 两源相参条件
def two_source_conditions():
    print("two-source conditions ...")
    lts = [0.35, 1.0, 3.0, 10.0]
    beta = np.radians(20.0)
    out = {}
    fig, axs = plt.subplots(1, 3, figsize=(7.4, 2.5))
    # (a) 载频差（两源同址）：Δk = 2Δf cos(β/2)/c，沿双基地角平分线
    df = np.linspace(0, 60e6, 400)
    ax = axs[0]
    for lt, col in zip(lts, (C1, C3, C4, C2)):
        rho = np.abs(np.sinc(2 * df * np.cos(beta / 2) * lt / C0))
        ax.plot(df / 1e6, rho, color=col, label=f"$\\mathit{{L_t}}$={lt:g} m")
    ax.axhline(0.9, color="k", ls=":", lw=0.8)
    ax.set_xlabel("两源载频差 Δf / MHz")
    ax.set_ylabel("散射系数相关系数 ρ")
    ax.set_title("(a) 两源同址、载频不同", fontsize=8.5)
    ax.set_ylim(0, 1.05)
    ax.grid()
    ax.legend(fontsize=7, loc="upper right")
    # (b) 两源视角差（同频）：|Δk| ≈ Δθ/λ
    dth = np.radians(np.linspace(0, 20, 400))
    ax = axs[1]
    lam = LAM[0]
    for lt, col in zip(lts, (C1, C3, C4, C2)):
        rho = np.abs(np.sinc(2 * np.sin(dth / 2) / lam * lt))
        ax.plot(np.degrees(dth), rho, color=col)
    ax.axhline(0.9, color="k", ls=":", lw=0.8)
    ax.set_xlabel("两源对目标的视角差 Δθ$_\\mathit{T}$ / (°)")
    ax.set_title("(b) 两源同频、站址不同", fontsize=8.5)
    ax.set_ylim(0, 1.05)
    ax.grid()
    # (c) ρ≥0.9 可行域
    ax = axs[2]
    dfg = np.linspace(0, 40e6, 300)
    dtg = np.radians(np.linspace(0, 12, 300))
    DF, DT = np.meshgrid(dfg, dtg, indexing="ij")
    # 视角差引起的横向波数差与频差引起的纵向波数差近似正交
    for lt, col in zip(lts, (C1, C3, C4, C2)):
        kx = 2 * np.sin(DT / 2) / lam * lt
        kz = 2 * DF * np.cos(beta / 2) / C0 * lt
        rho = np.abs(np.sinc(kx) * np.sinc(kz))
        cs = ax.contour(np.degrees(DT), DF / 1e6, rho, levels=[0.9], colors=[col], linewidths=1.2)
    ax.set_xlabel("视角差 Δθ$_\\mathit{T}$ / (°)")
    ax.set_ylabel("载频差 Δf / MHz")
    ax.set_title("(c) ρ≥0.9 的可行域（曲线左下）", fontsize=8.5)
    ax.grid()
    fig.tight_layout()
    save(fig, "st_two_source")
    # 数值：ρ=0.9 时的最大允许频差与视角差
    for lt in lts:
        x09 = 0.2595                                         # sinc(x)=0.9
        out[f"{lt:g}"] = dict(df_max_mhz=float(x09 * C0 / (2 * np.cos(beta / 2) * lt) / 1e6),
                              dtheta_max_deg=float(np.degrees(2 * np.arcsin(min(1.0, x09 * lam / (2 * lt))))))
    # 本系统几何：两源对目标的视角差与载频差
    uT = (P0 - TX) / np.linalg.norm(P0 - TX, axis=1, keepdims=True)
    out["this_dtheta_deg"] = float(np.degrees(np.arccos(uT[0] @ uT[1])))
    out["this_df_mhz"] = float((F_TX[1] - F_TX[0]) / 1e6)
    res["two_source"] = out


# ================================================================ 2) 同步、频率基准与几何误差容限
def coherent_loss_db(phase_err, a=A_REL):
    """给定各链路相位误差（..., NL），返回 MRC 相参融合的信噪比损失（dB，正值）。"""
    g = np.abs(np.sum(a ** 2 * np.exp(1j * phase_err), axis=-1)) ** 2 / np.sum(a ** 2) ** 2
    return -10 * np.log10(np.mean(g, axis=0) if np.ndim(g) else g)


def sync_tolerances():
    print("sync tolerances ...")
    n = 4000
    tau = R0 / C0
    out = {}
    fig, axs = plt.subplots(2, 2, figsize=(7.0, 4.6))
    axs = axs.ravel()
    # (a) 接收站频率基准相对误差 ε：相位误差 2π ε f τ_l
    eps = np.logspace(-11, -5, 60)
    loss = []
    for e in eps:
        ej = rng.uniform(-1, 1, (n, NR)) * e
        loss.append(coherent_loss_db(2 * np.pi * ej[:, RCV] * F_TX[SRC] * tau))
    ax = axs[0]
    ax.semilogx(eps, loss, color=C1)
    ax.axvline(1e-10, color=C6, ls=":", lw=0.8)
    ax.text(1.4e-10, 9.6, "GNSS驯服\n铷钟/OCXO", fontsize=6.8, color=C6, va="top")
    ax.axvline(1e-6, color=C6, ls=":", lw=0.8)
    ax.text(0.7e-6, 9.6, "自由振荡\nTCXO", fontsize=6.8, color=C6, va="top", ha="right")
    ax.set_xlabel("接收站频率基准相对误差 ε")
    ax.set_ylabel("相参融合损失 / dB")
    ax.set_title("(a) 频率基准", fontsize=8.5)
    ax.set_ylim(0, 10.5)
    ax.grid(which="both")
    out["eps_loss_1e-9_db"] = float(coherent_loss_db(2 * np.pi * (rng.uniform(-1, 1, (n, NR)) * 1e-9)[:, RCV]
                                                      * F_TX[SRC] * tau))
    out["eps_loss_1e-6_db"] = float(coherent_loss_db(2 * np.pi * (rng.uniform(-1, 1, (n, NR)) * 1e-6)[:, RCV]
                                                      * F_TX[SRC] * tau))
    out["eps_for_0.5db"] = float(np.interp(0.5, loss, eps))
    # (b) 接收站时间同步误差 δt：相位误差 2π f_D δt（目标多普勒 f_D）
    dts = np.logspace(-9, -2, 60)
    ax = axs[1]
    for key, fdv, col, lab in (("this", FD0, C1, "本例 $\\mathit{f_D}$≈155 Hz"),
                               ("1khz", FD0 * 1000 / 155, C2, "$\\mathit{f_D}$≈1 kHz")):
        loss = []
        for dt in dts:
            tj = rng.normal(0, dt, (n, NR))
            loss.append(coherent_loss_db(2 * np.pi * fdv * tj[:, RCV]))
        ax.semilogx(dts, loss, color=col, label=lab)
        out[f"dt_for_0.5db_{key}"] = float(np.interp(0.5, loss, dts))
    ax.axvline(50e-9, color=C6, ls=":", lw=0.8)
    ax.text(70e-9, 6.0, "GNSS授时\n≈50 ns", fontsize=6.8, color=C6, va="top")
    ax.set_xlabel("站间时间同步误差 $\\mathit{σ_t}$ / s")
    ax.set_title("(b) 时间同步", fontsize=8.5)
    ax.set_ylim(0, 10.5)
    ax.grid(which="both")
    ax.legend(fontsize=6.8, loc="upper left")
    # (c) 接收站天线相位中心位置误差：δR_l = (u_{r→t} - u_R)·δr_j
    sig = np.logspace(-3, 0, 60)
    uR = (P0 - RX) / np.linalg.norm(P0 - RX, axis=1, keepdims=True)
    uT = (P0 - TX) / np.linalg.norm(P0 - TX, axis=1, keepdims=True)
    loss_r, loss_t = [], []
    for s_ in sig:
        dr = rng.normal(0, s_, (n, NR, 3))
        dt_ = rng.normal(0, s_, (n, NT, 3))
        dRr = np.zeros((n, NL))
        dRt = np.zeros((n, NL))
        for l, (i, j) in enumerate(LINKS):
            urt = (TX[i] - RX[j]) / np.linalg.norm(TX[i] - RX[j])
            dRr[:, l] = dr[:, j] @ (urt - uR[j])
            dRt[:, l] = -dt_[:, i] @ (uT[i] + urt)
        loss_r.append(coherent_loss_db(2 * np.pi * dRr / LAM[SRC]))
        loss_t.append(coherent_loss_db(2 * np.pi * dRt / LAM[SRC]))
    ax = axs[2]
    ax.semilogx(sig * 100, loss_r, color=C1)
    ax.axvline(2, color=C6, ls=":", lw=0.8)
    ax.text(2.6, 9.6, "RTK\n≈2 cm", fontsize=6.8, color=C6, va="top")
    ax.set_xlabel("接收站天线相位中心位置误差 $\\mathit{σ_r}$ / cm")
    ax.set_ylabel("相参融合损失 / dB")
    ax.set_title("(c) 接收站站址精度（未标校）", fontsize=8.5)
    ax.set_ylim(0, 10.5)
    ax.grid(which="both")
    out["rx_pos_for_0.5db_cm"] = float(np.interp(0.5, loss_r, sig * 100))
    ax = axs[3]
    ax.semilogx(sig * 100, loss_t, color=C2)
    ax.set_xlabel("发射站天线相位中心位置误差 $\\mathit{σ_T}$ / cm")
    ax.set_title("(d) 发射站站址精度（未标校）", fontsize=8.5)
    ax.set_ylim(0, 10.5)
    ax.grid(which="both")
    out["tx_pos_for_0.5db_cm"] = float(np.interp(0.5, loss_t, sig * 100))
    fig.tight_layout()
    save(fig, "st_sync")

    # 相位误差—增益关系（理论与仿真）
    sg = np.radians(np.linspace(0, 90, 46))
    th = []
    mc = []
    for s in sg:
        e = rng.normal(0, s, (n, NL)) if s > 0 else np.zeros((n, NL))
        mc.append(-coherent_loss_db(e) + 10 * np.log10(NL))
        r = np.exp(-s ** 2)
        a2 = A_REL ** 2
        th.append(10 * np.log10((np.sum(a2 ** 2) + r * (np.sum(a2) ** 2 - np.sum(a2 ** 2))) / np.sum(a2)))
    fig, ax = plt.subplots(figsize=(3.6, 2.6))
    ax.plot(np.degrees(sg), th, color=C1, label="理论（MRC）")
    ax.plot(np.degrees(sg)[::3], np.array(mc)[::3], "o", ms=3.5, mfc="none", color=C2, label="蒙特卡罗")
    ax.axhline(10 * np.log10(NL), color=C6, ls=":", lw=0.8)
    ax.text(2, 10 * np.log10(NL) + 0.25, "理想 10lg10 = 10 dB", fontsize=7, color=C6)
    for tol in (0.5, 1.0):
        x = np.interp(10 * np.log10(NL) - tol, th[::-1], np.degrees(sg)[::-1])
        ax.plot([x, x], [0, 10 * np.log10(NL) - tol], color=C4, ls="--", lw=0.8)
        if tol < 1:
            ax.text(x - 1.2, 0.6, f"损失{tol:g} dB\nσ={x:.0f}°", fontsize=6.5, color=C4, ha="right")
        else:
            ax.text(x + 1.2, 0.6, f"损失{tol:g} dB\nσ={x:.0f}°", fontsize=6.5, color=C4)
        out[f"sigma_for_{tol:g}db"] = float(x)
    ax.set_xlabel("各链路残余相位误差标准差 $\\mathit{σ_φ}$ / (°)")
    ax.set_ylabel("相参融合信噪比增益 / dB")
    ax.set_ylim(0, 11)
    ax.grid()
    ax.legend(loc="upper right", fontsize=7, bbox_to_anchor=(1.0, 0.93))
    fig.tight_layout()
    save(fig, "st_phase_err")
    res["sync"] = out


# ================================================================ 3) 粗—精搜索的等效独立单元数
def multiplicity(n_trials=600, half=(200.0, 60.0), step=0.4):
    """H0 下在目标附近区域（相参条纹尺度精细网格）上求各统计量的最大值分布，拟合等效独立单元数。"""
    print("search multiplicity (H0 random fields) ...")
    t0 = time.time()
    gx = np.arange(-half[0], half[0] + 1e-9, step)
    gy = np.arange(-half[1], half[1] + 1e-9, step)
    X, Y = np.meshgrid(gx, gy, indexing="ij")
    pts = np.stack([P0[0] + X, P0[1] + Y, np.full(X.shape, P0[2])], -1).reshape(-1, 3)
    R, _, _, _ = link_geometry(pts)
    ph = np.exp(2j * np.pi * R / LAM[SRC]).astype(np.complex64)
    # 各链路时延维噪声过程：在整数样点上生成带限白噪声，FFT 上采样至约 0.25 m 间隔
    rmin, rmax = R.min(0) - 200, R.max(0) + 200
    n0 = 64
    ups = 160
    dR = C0 / FS / ups
    nocc = int(round(n0 * B_OCC / FS))
    idx = []
    for l in range(NL):
        pos = (R[:, l] - rmin[l]) / dR
        idx.append(pos)
    idx = np.stack(idx, 1)
    i0 = np.floor(idx).astype(np.int32)
    fr = (idx - i0).astype(np.float32)
    lim = n0 * ups
    assert i0.max() + 1 < lim, "range span too large"
    stat = {k: [] for k in GROUPS}
    w = A_REL.astype(np.float32)
    for t in range(n_trials):
        Z = np.zeros((NL, n0), complex)
        h = nocc // 2
        Z[:, :h + 1] = rng.standard_normal((NL, h + 1)) + 1j * rng.standard_normal((NL, h + 1))
        Z[:, -h:] = rng.standard_normal((NL, h)) + 1j * rng.standard_normal((NL, h))
        Zp = np.zeros((NL, lim), complex)
        Zp[:, :h + 1] = Z[:, :h + 1]
        Zp[:, -h:] = Z[:, -h:]
        wf = np.fft.ifft(Zp, axis=1)
        wf /= np.sqrt(np.mean(np.abs(wf) ** 2, axis=1, keepdims=True))
        wf = wf.astype(np.complex64)
        z = np.empty_like(ph)
        for l in range(NL):
            z[:, l] = (1 - fr[:, l]) * wf[l, i0[:, l]] + fr[:, l] * wf[l, i0[:, l] + 1]
        zc = z * ph * w
        for key, groups in GROUPS.items():
            if key == "nc":
                T = np.sum(np.abs(z) ** 2, axis=1)
            else:
                T = sum(np.abs(zc[:, g].sum(1)) ** 2 / np.sum(w[g] ** 2) for g in groups)
            stat[key].append(float(T.max()))
        if t % 100 == 0:
            print(f"  trial {t} ({time.time() - t0:.0f} s)")
    out = {}
    for key, groups in GROUPS.items():
        ng = len(groups)
        mx = np.array(stat[key])
        # P(max<=x) = F1(x)^M  →  M = ln P / ln F1
        qs = np.array([0.5, 0.7, 0.8, 0.9])
        xs = np.quantile(mx, qs)
        Ms = np.log(qs) / stats.gamma.logcdf(xs, ng)
        out[key] = dict(M=float(np.exp(np.mean(np.log(Ms)))), M_q=list(map(float, Ms)), ngroups=ng)
    base = out["nc"]["M"]
    for key in out:
        out[key]["ratio"] = out[key]["M"] / base
    out["area_m2"] = float((2 * half[0]) * (2 * half[1]))
    res["multiplicity"] = out
    print("  multiplicity:", {k: round(v["M"], 1) for k, v in out.items() if isinstance(v, dict)})
    return out


def ambiguity_slices():
    """点目标的非相参/相参融合模糊函数（水平面），用于说明分辨率与条纹结构。"""
    print("ambiguity ...")
    h = np.arange(-300, 300.01, 1.0)
    X, Y = np.meshgrid(h, h, indexing="ij")
    pts = np.stack([P0[0] + X, P0[1] + Y, np.full(X.shape, P0[2])], -1)
    R, _, _, _ = link_geometry(pts)
    dR = R - R0
    chi = range_ambiguity(dR)
    a = A_REL
    af_nc = np.sum(a ** 2 * chi ** 2, -1) / np.sum(a ** 2)
    af_c = np.abs(np.sum(a ** 2 * chi * np.exp(2j * np.pi * dR / LAM[SRC]), -1)) ** 2 / np.sum(a ** 2) ** 2
    hz = np.arange(-20, 20.001, 0.05)
    Xz, Yz = np.meshgrid(hz, hz, indexing="ij")
    ptz = np.stack([P0[0] + Xz, P0[1] + Yz, np.full(Xz.shape, P0[2])], -1)
    Rz, _, _, _ = link_geometry(ptz)
    dRz = Rz - R0
    chz = range_ambiguity(dRz)
    afz = np.abs(np.sum(a ** 2 * chz * np.exp(2j * np.pi * dRz / LAM[SRC]), -1)) ** 2 / np.sum(a ** 2) ** 2
    # -3 dB 主瓣面积
    cell = (h[1] - h[0]) ** 2
    area_nc = float(np.sum(af_nc >= 0.5) * cell)
    lab = (afz >= 0.5)
    from scipy import ndimage
    lbl, _ = ndimage.label(lab)
    c = lbl[len(hz) // 2, len(hz) // 2]
    area_c = float(np.sum(lbl == c) * (hz[1] - hz[0]) ** 2)
    res["ambiguity"] = dict(area_nc_m2=area_nc, area_c_m2=area_c, ratio=area_nc / area_c,
                            psl_c_db=float(10 * np.log10(np.sort(afz[lbl != c])[-1])))
    fig, axs = plt.subplots(1, 3, figsize=(7.6, 2.7), gridspec_kw=dict(wspace=0.38))
    im = axs[0].pcolormesh(h, h, 10 * np.log10(af_nc.T + 1e-6), cmap="magma", vmin=-20, vmax=0, shading="auto",
                           rasterized=True)
    axs[0].set_title("(a) 非相参融合（±300 m）", fontsize=8.5)
    axs[1].pcolormesh(h, h, 10 * np.log10(af_c.T + 1e-6), cmap="magma", vmin=-20, vmax=0, shading="auto",
                      rasterized=True)
    axs[1].set_title("(b) 相参融合（±300 m）", fontsize=8.5)
    axs[2].pcolormesh(hz, hz, 10 * np.log10(afz.T + 1e-6), cmap="magma", vmin=-20, vmax=0, shading="auto",
                      rasterized=True)
    axs[2].set_title("(c) 相参融合（±20 m）", fontsize=8.5)
    for ax in axs:
        ax.set_aspect("equal")
        ax.set_xlabel("Δx / m")
        ax.set_ylabel("Δy / m", labelpad=1)
    cb = fig.colorbar(im, ax=axs, pad=0.04, fraction=0.025)
    cb.set_label("归一化 / dB", fontsize=8)
    save(fig, "st_ambiguity")


# ================================================================ 4) 检测概率
def thresholds(mult):
    th = {}
    for key, groups in GROUPS.items():
        ng = len(groups)
        m = mult[key]["ratio"] if key != "nc" else 1.0
        th[key] = float(stats.gamma.isf(PFA / m, ng))
    th["coh_ideal"] = float(stats.gamma.isf(PFA, 1))
    th["single"] = float(stats.gamma.isf(PFA, 1))
    return th


def statistics(z, w=A_REL):
    """z: (..., NL) 已完成相位补偿的归一化复值。返回各统计量。"""
    out = {"nc": np.sum(np.abs(z) ** 2, -1)}
    zc = z * w
    for key in ("pair", "grp", "coh"):
        out[key] = sum(np.abs(zc[..., g].sum(-1)) ** 2 / np.sum(w[g] ** 2) for g in GROUPS[key])
    out["single"] = np.abs(z[..., int(np.argmax(SNR_DB))]) ** 2
    return out


def pd_curves(th, n=40000):
    print("Pd curves ...")
    snr = np.arange(-6, 16.01, 0.25)
    s_lin = 10 ** (snr / 10)
    out = {}
    cases = {}
    w0 = (rng.standard_normal((n, NL)) + 1j * rng.standard_normal((n, NL))) / np.sqrt(2)
    # (a) 点目标（非起伏、散射完全相参）
    alpha = np.ones((n, NL), complex)
    cases["point"] = alpha
    # (b) 扩展目标 L_t = 3 m（起伏、部分相参）
    cases["ext3"] = draw_alpha(3.0, n)
    perr = np.radians(30) * rng.standard_normal((n, NL))
    for cname, al in cases.items():
        curves = {k: [] for k in ("single", "nc", "pair", "grp", "coh", "coh_ideal", "coh_perr", "or")}
        for s in s_lin:
            z = np.sqrt(s) * A_REL * al + w0
            st = statistics(z)
            for k in ("single", "nc", "pair", "grp", "coh"):
                curves[k].append(float(np.mean(st[k] > th[k])))
            curves["coh_ideal"].append(float(np.mean(st["coh"] > th["coh_ideal"])))
            stp = statistics(z * np.exp(1j * perr))
            curves["coh_perr"].append(float(np.mean(stp["coh"] > th["coh"])))
            curves["or"].append(float(np.mean((st["nc"] > th["or_nc"]) | (st["coh"] > th["or_coh"]))))
        out[cname] = curves
    req = {}
    for cname, curves in out.items():
        req[cname] = {}
        for k, v in curves.items():
            v = np.array(v)
            req[cname][k] = float(np.interp(PD_REQ, v, snr)) if v.max() >= PD_REQ else None
    res["pd"] = dict(snr_db=snr.tolist(), curves=out, req_snr_db=req)
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.3), sharey=True)
    styles = [("single", "最佳单链路", C6, "-"), ("nc", "非相参融合(10链路)", C3, "-"),
              ("pair", "源间相参+站间非相参", C4, "--"), ("grp", "站间相参+源间非相参", C5, "--"),
              ("coh", "10链路相参(含精搜索代价)", C1, "-"), ("coh_ideal", "10链路相参(位置已知)", C1, ":"),
              ("coh_perr", "10链路相参, $\\mathit{σ_φ}$=30°", C2, "-.")]
    for ax, cname, title in ((axs[0], "point", "(a) 点目标（散射相参、非起伏）"),
                             (axs[1], "ext3", "(b) 扩展目标 $\\mathit{L_t}$=3 m（部分相参、起伏）")):
        for k, lab, col, ls in styles:
            ax.plot(snr, out[cname][k], color=col, ls=ls, label=lab)
        ax.set_title(title, fontsize=8.5)
        ax.set_xlabel("单链路平均输出信噪比 / dB")
        ax.grid()
        ax.set_xlim(snr[0], snr[-1])
    axs[0].set_ylabel("检测概率 $\\mathit{P_d}$")
    h, lab = axs[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=4, fontsize=7, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    save(fig, "st_pd")


def size_sweep(th, n=12000):
    print("target size sweep ...")
    lts = np.array([0.1, 0.2, 0.35, 0.5, 0.7, 1.0, 1.4, 2.0, 3.0, 4.5, 7.0, 10.0, 15.0, 20.0])
    snr = np.arange(-6, 32.01, 0.5)
    s_lin = 10 ** (snr / 10)
    keys = ("single", "nc", "pair", "grp", "coh", "or")
    req = {k: [] for k in keys}
    gain = []
    w0 = (rng.standard_normal((n, NL)) + 1j * rng.standard_normal((n, NL))) / np.sqrt(2)
    for lt in lts:
        al = draw_alpha(lt, n)
        rho = coherence_matrix(lt)
        a = A_REL
        gain.append(float(10 * np.log10(np.real(a ** 2 @ rho @ a ** 2) / np.sum(a ** 2))))
        pd = {k: [] for k in keys}
        for s in s_lin:
            z = np.sqrt(s) * A_REL * al + w0
            st = statistics(z)
            for k in ("single", "nc", "pair", "grp", "coh"):
                pd[k].append(np.mean(st[k] > th[k]))
            pd["or"].append(np.mean((st["nc"] > th["or_nc"]) | (st["coh"] > th["or_coh"])))
        for k in keys:
            v = np.array(pd[k])
            req[k].append(float(np.interp(PD_REQ, v, snr)) if v.max() >= PD_REQ else np.nan)
    res["size"] = dict(lt=lts.tolist(), req_snr_db={k: list(map(float, v)) for k, v in req.items()},
                       mean_gain_db=gain)
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.1))
    ax = axs[0]
    ax.semilogx(lts, gain, "o-", color=C1, ms=3.5, label="10链路相参（参考点）")
    ax.axhline(10, color=C6, ls=":", lw=0.8)
    ax.set_xlabel("目标尺寸 $\\mathit{L_t}$ / m")
    ax.set_ylabel("平均输出信噪比增益 / dB")
    ax.set_title("(a) 相参融合平均增益", fontsize=8.5)
    ax.grid(which="both")
    ax.set_ylim(-1, 11)
    ax = axs[1]
    styles = [("single", "最佳单链路", C6, "-"), ("nc", "非相参融合", C3, "-"),
              ("pair", "源间相参+站间非相参", C4, "--"), ("grp", "站间相参+源间非相参", C5, "--"),
              ("coh", "10链路相参", C1, "-"), ("or", "相参/非相参双支路", C2, ":")]
    for k, lab, col, ls in styles:
        ax.semilogx(lts, req[k], color=col, ls=ls, marker="o", ms=2.8, label=lab)
    ax.set_xlabel("目标尺寸 $\\mathit{L_t}$ / m")
    ax.set_ylabel("所需单链路平均信噪比 / dB")
    ax.set_title(f"(b) $\\mathit{{P_d}}$={PD_REQ}、$\\mathit{{P_{{fa}}}}$=10$^{{-6}}$ 所需信噪比", fontsize=8.5)
    ax.grid(which="both")
    h, lab = ax.get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=6, fontsize=6.8, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    save(fig, "st_size")


def coherence_figure():
    fig, axs = plt.subplots(1, 2, figsize=(6.4, 2.9))
    for ax, lt in zip(axs, (0.35, 3.0)):
        rho = coherence_matrix(lt)
        im = ax.imshow(np.abs(rho), cmap="Blues", vmin=0, vmax=1)
        ax.set_xticks(range(NL))
        ax.set_yticks(range(NL))
        ax.set_xticklabels(LINK_NAMES, rotation=90, fontsize=6.5)
        ax.set_yticklabels(LINK_NAMES, fontsize=6.5)
        ax.set_title(f"$\\mathit{{L_t}}$ = {lt:g} m（平均 |ρ| = {np.mean(np.abs(rho[~np.eye(NL, dtype=bool)])):.2f}）",
                     fontsize=8.5)
        ax.axhline(4.5, color="w", lw=1.2)
        ax.axvline(4.5, color="w", lw=1.2)
    cb = fig.colorbar(im, ax=axs, pad=0.02, fraction=0.03)
    cb.set_label("|ρ|", fontsize=8)
    save(fig, "st_coherence")
    kspread = np.linalg.norm(K0[:, None] - K0[None], axis=-1)
    pair_rho = {f"{lt:g}": [float(abs(coherence_matrix(lt)[j, j + NR])) for j in range(NR)]
                for lt in (0.35, 1.0, 3.0, 10.0)}
    res["coherence_pair"] = {k: dict(min=min(v), max=max(v), mean=float(np.mean(v))) for k, v in pair_rho.items()}
    res["coherence"] = dict(kspread_max=float(kspread.max()),
                            lt_max_rho09=float(0.2595 / kspread.max()),
                            mean_rho={f"{lt:g}": float(np.mean(np.abs(coherence_matrix(lt)[~np.eye(NL, dtype=bool)])))
                                      for lt in (0.35, 1.0, 3.0, 10.0)})


# ================================================================ 5) 三维相参组合（时域 × 源 × 站）
def combo_table():
    print("3-D coherence combinations ...")

    def req_piece(n_pieces):
        eta = stats.gamma.isf(PFA, n_pieces)
        f = lambda s: stats.ncx2.sf(2 * eta, 2 * n_pieces, 2 * n_pieces * s) - PD_REQ
        lo, hi = 1e-3, 1e4
        for _ in range(100):
            mid = np.sqrt(lo * hi)
            lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
        return mid

    K, L = 4, NL
    rows = [("全部非相参", K * L, 1), ("仅时域相参", L, K), ("仅源间相参", K * NR, NT),
            ("仅站间相参", K * NT, NR), ("10链路相参，时域非相参", K, L), ("时域+源间相参", NR, K * NT),
            ("时域+站间相参", NT, K * NR), ("三维全相参", 1, K * L)]
    single = 10 * np.log10(req_piece(1))
    out = []
    for name, npcs, ncoh in rows:
        s = req_piece(npcs)
        elem = 10 * np.log10(s / ncoh)
        out.append(dict(name=name, pieces=npcs, coherent=ncoh, req_elem_db=float(elem),
                        gain_db=float(single - elem), ideal_db=float(10 * np.log10(K * L))))
    res["combo"] = dict(K=K, L=L, single_req_db=float(single), rows=out)


# ================================================================ 6) 布站尺度
def layout_scale():
    print("layout scale ...")
    scales = np.logspace(np.log10(0.25), np.log10(8), 25)
    lts = (0.35, 1.0, 3.0)
    txc, rxc = TX.mean(0), RX.mean(0)
    gains = {lt: [] for lt in lts}
    kmax = []
    rx_extent = []
    for s in scales:
        tx = txc + (TX - txc) * s
        rx = rxc + (RX - rxc) * s
        _, _, k, _ = link_geometry(P0, V0, tx=tx, rx=rx)
        kmax.append(float(np.linalg.norm(k[:, None] - k[None], axis=-1).max()))
        rx_extent.append(float(np.ptp(rx[:, :2], axis=0).max() / 1e3))
        for lt in lts:
            rho = coherence_matrix(lt, k)
            a = A_REL
            gains[lt].append(float(10 * np.log10(np.real(a ** 2 @ rho @ a ** 2) / np.sum(a ** 2))))
    at = {}
    for sc in (0.5, 1, 2, 4, 8):
        tx = txc + (TX - txc) * sc
        rx = rxc + (RX - rxc) * sc
        _, _, k, _ = link_geometry(P0, V0, tx=tx, rx=rx)
        at[f"{sc:g}"] = dict(rx_extent_km=float(np.ptp(rx[:, :2], axis=0).max() / 1e3),
                             kmax=float(np.linalg.norm(k[:, None] - k[None], axis=-1).max()))
        for lt in lts:
            rho = coherence_matrix(lt, k)
            at[f"{sc:g}"][f"{lt:g}"] = float(10 * np.log10(np.real(A_REL ** 2 @ rho @ A_REL ** 2) / np.sum(A_REL ** 2)))
    res["layout"] = dict(scale=scales.tolist(), rx_extent_km=rx_extent, kmax=kmax,
                         gain_db={f"{lt:g}": v for lt, v in gains.items()}, at=at)
    fig, ax = plt.subplots(figsize=(3.8, 2.7))
    for lt, col in zip(lts, (C1, C3, C4)):
        ax.semilogx(rx_extent, gains[lt], color=col, label=f"$\\mathit{{L_t}}$={lt:g} m")
    ax.axvline(rx_extent[np.argmin(np.abs(scales - 1))], color=C6, ls=":", lw=0.8)
    ax.text(rx_extent[np.argmin(np.abs(scales - 1))] * 1.08, 1.0, "本例布站", fontsize=7, color=C6)
    ax.set_xlabel("接收站分布范围 / km（两源间距同比例缩放）")
    ax.set_ylabel("10链路相参平均增益 / dB")
    ax.set_ylim(0, 10.5)
    ax.grid(which="both")
    ax.legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    save(fig, "st_layout")


def main():
    t0 = time.time()
    res["links"] = dict(names=LINK_NAMES, snr_db=list(map(float, SNR_DB)), R_km=list(map(float, R0 / 1e3)),
                        fd_hz=list(map(float, FD0)), beta_deg=list(map(float, BETA0)),
                        k=K0.tolist(), lag=list(map(float, R0 / C0 * FS)))
    two_source_conditions()
    sync_tolerances()
    coherence_figure()
    ambiguity_slices()
    mult = multiplicity()
    th = thresholds(mult)
    # 双支路（相参/非相参取“或”）：两支路各分配 Pfa/2
    th["or_nc"] = float(stats.gamma.isf(PFA / 2, NL))
    th["or_coh"] = float(stats.gamma.isf(PFA / 2 / mult["coh"]["ratio"], 1))
    res["thresholds"] = th
    pd_curves(th)
    req = res["pd"]["req_snr_db"]["point"]
    best = float(SNR_DB.max() - 10 * np.log10(np.mean(10 ** (SNR_DB / 10))))
    res["derived"] = dict(eta_penalty_db=float(10 * np.log10(th["coh"] / th["coh_ideal"])),
                          best_link_offset_db=best, single_req_db=float(req["single"] + best),
                          coh_vs_nc_db=float(req["nc"] - req["coh"]),
                          cohideal_vs_nc_db=float(req["nc"] - req["coh_ideal"]))
    size_sweep(th)
    combo_table()
    layout_scale()
    (HERE / "results_stats.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
