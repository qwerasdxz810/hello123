#!/usr/bin/env python3
"""2发5收分布式探测系统 —— 信号级端到端仿真。

每个接收站对两个信号源分别完成：参考信号提纯（解调—再调制）→ ECA 直达波/多径杂波对消
→ 批处理互模糊函数（时间基准取 CPI 中心）；融合中心在目标状态空间完成 10 条链路的
非相参融合与“粗—精”两级相参融合。

运行：python3 docs/coherent_fusion/src/sim_signal.py [--trials N]
输出：figures/sig_*.png 与 src/results_signal.json
"""
import argparse
import json
import multiprocessing as mp
import time

import numpy as np

from common import (C0, FS, NFFT, NCP, NSYM_LEN, KACT, NSYM, NCPI, T_CPI, LB, F_TX, LAM, TX, RX,
                    NT, NR, NL, LINKS, LINK_NAMES, P0, V0, link_geometry, link_snr_db, plt, save,
                    C1, C2, C3, C4, C5, C6, SRC_COL, HERE)

PRE, POST = 4096, NSYM_LEN
LTOT = PRE + NCPI + POST
NF = 1 << int(np.ceil(np.log2(LTOT)))
FREQ = np.fft.fftfreq(NF, 1 / FS)
T_ALL = (np.arange(LTOT) - PRE) / FS          # 以 CPI 起点为 0
T_C = NCPI / (2 * FS)                          # CPI 中心
ECA_K = (-16, 79)                              # ECA 双边时延抽头
HALF_LAG = 128                                 # 目标区互模糊函数的时延半窗
UPS = 8                                        # 时延维内插倍数
ND = 4096                                      # 多普勒 FFT 点数（≈0.98 Hz 间隔）
DOP_HALF = 40.0                                # 多普勒半窗 Hz
SIG_CAL_DEG = 5.0                              # 通道相位标定残差（标准差）

G = {}                                         # 供子进程读取的全局数据（fork 共享）


# ================================================================ 发射信号
def ofdm_tx(rng, nsym):
    X = np.exp(1j * (np.pi / 4 + np.pi / 2 * rng.integers(0, 4, (nsym, len(KACT)))))
    B = np.zeros((nsym, NFFT), complex)
    B[:, KACT % NFFT] = X
    s = np.fft.ifft(B, axis=1) * NFFT / np.sqrt(len(KACT))
    return np.concatenate([s[:, -NCP:], s], axis=1).ravel()


def make_sources(rng):
    """两个非合作信号源：独立 OFDM 数据、各自的载频偏差、相位噪声与初相。"""
    npre = int(np.ceil(PRE / NSYM_LEN))
    out = []
    for i in range(NT):
        x = ofdm_tx(rng, NSYM + npre + 1)[npre * NSYM_LEN - PRE:][:LTOT]
        dfT = rng.uniform(-10, 10)                                   # 发射载频偏差 Hz
        ph = np.cumsum(rng.normal(0, np.sqrt(2 * np.pi * 1e-3 / FS), LTOT)) + rng.uniform(0, 2 * np.pi)
        s = x * np.exp(1j * (2 * np.pi * dfT * T_ALL + ph))
        out.append(dict(S=np.fft.fft(s, NF), Sx=np.fft.fft(x, NF), dfT=dfT))
    return out


def scatterer_alpha(rng, k, lt=0.35, ns=5):
    """小型无人机散射模型：ns 个散射中心分布于 lt 尺度内，返回各链路复散射系数。"""
    pos = rng.uniform(-0.5, 0.5, (ns, 3)) * np.array([lt, lt, 0.3 * lt])
    amp = (rng.standard_normal(ns) + 1j * rng.standard_normal(ns)) / np.sqrt(2)
    amp[0] *= 2.0                                                   # 机身主散射中心
    a = (amp[None, :] * np.exp(-2j * np.pi * k @ pos.T)).sum(1)
    return a / np.sqrt(np.mean(np.abs(a) ** 2))


# ================================================================ 单链路回波生成与站内处理
def delayed(S, tau):
    return np.fft.ifft(S * np.exp(-2j * np.pi * FREQ * tau))[:LTOT]


def gen_link(l):
    """生成链路 l 的参考通道与监视通道（该信号源所在数字信道）。"""
    i, j = LINKS[l]
    p = G["par"]
    rng = np.random.default_rng(p["seed"] * 100 + l)
    S = G["src"][i]["S"]
    f = F_TX[i]
    taud = np.linalg.norm(TX[i] - RX[j]) / C0
    # 接收站本振：GNSS 驯服，相对频差 eps_j；相位噪声与初相对两个信道相同
    lo = np.exp(-1j * (2 * np.pi * p["eps"][j] * f * T_ALL + G["lo_ph"][j]))   # 含相位噪声
    d = delayed(S, taud) * np.exp(-2j * np.pi * f * taud)
    ref = np.sqrt(10 ** (p["dnr_ref"] / 10)) * np.exp(1j * p["kref"][l]) * d * lo
    ref += (rng.standard_normal(LTOT) + 1j * rng.standard_normal(LTOT)) / np.sqrt(2)
    # 监视通道：直达波泄漏 + 静态多径杂波 + 目标回波 + 噪声
    H = np.sqrt(10 ** (p["dnr_sur"] / 10)) * np.exp(1j * rng.uniform(0, 2 * np.pi)) * np.ones(NF)
    for _ in range(8):
        dl = rng.uniform(1.5, 60.0)
        H = H + np.sqrt(10 ** (rng.uniform(15, 33) / 10)) * np.exp(1j * rng.uniform(0, 2 * np.pi)) \
            * np.exp(-2j * np.pi * FREQ * dl / FS)
    sur = np.fft.ifft(S * np.exp(-2j * np.pi * FREQ * taud) * H)[:LTOT] * np.exp(-2j * np.pi * f * taud)
    if p["with_target"]:
        tau = taud + G["R0"][l] / C0
        amp = np.sqrt(10 ** (p["snr_db"][l] / 10) / NCPI) * G["alpha"][l]
        echo = delayed(S, tau) * np.exp(-2j * np.pi * f * tau) * np.exp(2j * np.pi * G["fd0"][l] * (T_ALL - T_C))
        sur = sur + amp * echo
    sur = np.exp(1j * p["ksur"][l]) * sur * lo
    sur += (rng.standard_normal(LTOT) + 1j * rng.standard_normal(LTOT)) / np.sqrt(2)
    return ref, sur, taud


def purify(r, dint):
    """参考信号提纯：CP 估计频偏 → 逐符号判决 → 重构纯净波形 → 恢复分数时延、复增益与频偏。

    返回 (含直达波复增益与相位的提纯参考, 频偏估计)。"""
    n = np.arange(LTOT)
    st0 = dint % NSYM_LEN
    starts = st0 + NSYM_LEN * np.arange((LTOT - st0) // NSYM_LEN)
    seg = np.stack([r[s:s + NSYM_LEN] for s in starts])
    acc = np.sum(seg[:, :NCP] * np.conj(seg[:, NFFT:NFFT + NCP]))
    cfo = -np.angle(acc) / (2 * np.pi * NFFT / FS)
    rc = r * np.exp(-2j * np.pi * cfo * n / FS)
    seg = np.stack([rc[s:s + NSYM_LEN] for s in starts])
    Y = np.fft.fft(seg[:, NCP:], axis=1)[:, KACT % NFFT]
    Y4 = Y ** 4
    slope = np.angle(np.sum(Y4[:, 1:] * np.conj(Y4[:, :-1]))) / 4
    kk = KACT.astype(float)
    Yd = Y * np.exp(-1j * slope * kk)[None, :]
    cpe = np.unwrap(np.angle(-np.sum(Yd ** 4, axis=1))) / 4
    Yd = Yd * np.exp(-1j * cpe)[:, None]
    Xh = (np.sign(Yd.real) + 1j * np.sign(Yd.imag)) / np.sqrt(2)
    g = np.mean(Yd / Xh, axis=1) * np.exp(1j * cpe)
    B = np.zeros((len(starts), NFFT), complex)
    B[:, KACT % NFFT] = Xh
    s = np.fft.ifft(B, axis=1) * NFFT / np.sqrt(len(KACT))
    s = np.concatenate([s[:, -NCP:], s], axis=1)
    xh = np.zeros(LTOT, complex)
    for m, st in enumerate(starts):
        xh[st:st + NSYM_LEN] = s[m]
    delta = -slope * NFFT / (2 * np.pi)
    xh = np.fft.ifft(np.fft.fft(xh, NF) * np.exp(-2j * np.pi * np.fft.fftfreq(NF) * delta))[:LTOT]
    cen = starts + NSYM_LEN / 2
    gi = np.interp(n, cen, g.real) + 1j * np.interp(n, cen, g.imag)
    out = xh * gi * np.exp(2j * np.pi * cfo * n / FS)
    out[:starts[0]] = 0
    return out, cfo


def xcorr_fft(a, b, lags):
    """sum_n a(n) conj(b(n - lag))，a 与 b 下标对齐。"""
    n = len(a)
    nf = 1 << int(np.ceil(np.log2(n + np.abs(lags).max() + 1)))
    g = np.fft.ifft(np.fft.fft(a, nf) * np.conj(np.fft.fft(b, nf)))
    return g[lags % nf]


def eca(s, r, kmin, kmax, n0, n1):
    """扩展对消算法（ECA）：在 [n0,n1) 上将 s 投影到 span{r(n-k)} 的正交补空间。"""
    ss = s[n0:n1]
    ks = np.arange(kmin, kmax + 1)
    m = len(ks)
    pad = max(abs(kmin), abs(kmax)) + 1
    rr = r[n0 - pad:n1 + pad]
    ra = xcorr_fft(rr, rr, np.arange(-(m - 1), m))
    Gm = ra[(ks[:, None] - ks[None, :]) + (m - 1)]
    p = xcorr_fft(np.concatenate([np.zeros(pad), ss, np.zeros(pad)]), rr, ks)
    w = np.linalg.solve(Gm, p)
    est = np.zeros(n1 - n0, complex)
    for kk, wk in zip(ks, w):
        est += wk * r[n0 - kk:n1 - kk]
    return ss - est


def caf(s, r, hist, lag0, lag1, dop_lo, dop_hi, nd=ND):
    """批处理互模糊函数：χ(lag, f) = Σ_n s(n) r*(n-lag) e^{-j2πf(t_n - t_c)}。

    s: 监视信号（CPI 内，长 NCPI）；r: 参考信号，r[hist] 对应 s[0]。
    返回 (χ[ndop, nlag], 多普勒轴, 时延轴)。"""
    nb = len(s) // LB
    nl = lag1 - lag0
    nfft = 1 << int(np.ceil(np.log2(LB + nl)))
    Cb = np.empty((nb, nl), complex)
    for b in range(nb):
        sb = s[b * LB:(b + 1) * LB]
        st = hist + b * LB - (lag1 - 1)
        rb = r[st:st + LB + nl - 1]
        g = np.fft.ifft(np.conj(np.fft.fft(sb, nfft)) * np.fft.fft(rb, nfft))[:nl]
        Cb[b] = np.conj(g)[::-1]                      # 按 lag 递增排列
    Tb = LB / FS
    tb0 = 0.5 * Tb - nb * Tb / 2
    fd = np.fft.fftfreq(nd, Tb)
    sel = np.where((fd >= dop_lo) & (fd <= dop_hi))[0]
    sel = sel[np.argsort(fd[sel])]
    F = np.fft.fft(Cb, nd, axis=0)[sel]
    F *= np.exp(-2j * np.pi * fd[sel] * tb0)[:, None]
    return F, fd[sel], np.arange(lag0, lag1)


def upsample_lag(F, ups=UPS):
    """沿时延维做 FFT 内插（带限内插），返回 ups 倍细化的时延网格。"""
    n = F.shape[1]
    X = np.fft.fft(F, axis=1)
    h = (n + 1) // 2
    Z = np.zeros((F.shape[0], n * ups), complex)
    Z[:, :h] = X[:, :h]
    Z[:, -(n - h):] = X[:, h:]
    return np.fft.ifft(Z, axis=1) * ups


def process_link(l):
    """接收站对链路 l 的完整处理，返回目标区互模糊函数表及诊断量。"""
    t0 = time.time()
    p = G["par"]
    ref, sur, taud = gen_link(l)
    dint = int(np.round(taud * FS)) + PRE
    refp, cfo = purify(ref, dint)
    n0, n1 = PRE, PRE + NCPI
    sur_c = eca(sur, refp, *ECA_K, n0, n1)
    out = dict(l=l)
    lag_c = int(np.round(G["R0"][l] / C0 * FS))
    lag0, lag1 = lag_c - HALF_LAG, lag_c + HALF_LAG + 1
    fdc = G["fd0"][l]
    F, fd, lags = caf(sur_c, refp, n0, lag0, lag1, fdc - DOP_HALF, fdc + DOP_HALF)
    # 噪声功率：去除目标邻域后的中值估计
    P = np.abs(F) ** 2
    mask = (np.abs(lags[None, :] - G["R0"][l] / C0 * FS) > 4) | (np.abs(fd[:, None] - fdc) > 12)
    out["noise"] = float(np.median(P[mask]) / np.log(2))
    out["F"] = upsample_lag(F).astype(np.complex64)
    out["fd"] = fd
    out["lag0"] = lag0
    if p.get("xref", False):
        # 对照：以译码重构的发射波形作参考（时延对齐、频偏已补偿，但不含本站直达波的载波相位），
        # 即链路相位不再以“本站接收的该源直达波”为基准
        i, _ = LINKS[l]
        xr = delayed(G["src"][i]["Sx"], taud) * np.exp(2j * np.pi * cfo * (np.arange(LTOT) / FS))
        Fx, _, _ = caf(sur_c, xr, n0, lag0, lag1, fdc - DOP_HALF, fdc + DOP_HALF)
        Px = np.abs(Fx) ** 2
        out["noise_x"] = float(np.median(Px[mask]) / np.log(2))
        out["Fx"] = upsample_lag(Fx).astype(np.complex64)
    if p.get("diag", False) and l == 0:
        # 诊断：T1R1 链路 ECA 前后的宽范围距离—多普勒图
        lagw = (0, 1500)
        Fb, fdw, lw = caf(sur[n0:n1], refp, n0, *lagw, -300, 300, nd=1024)
        Fa, _, _ = caf(sur_c, refp, n0, *lagw, -300, 300, nd=1024)
        out["wide"] = dict(before=np.abs(Fb).astype(np.float32), after=np.abs(Fa).astype(np.float32),
                           fd=fdw, lags=lw)
        sseg = slice(n0 + 4000, n1 - 4000)
        clean = refp[sseg]
        out["pow_before"] = float(np.mean(np.abs(sur[n0:n1]) ** 2))
        out["pow_after"] = float(np.mean(np.abs(sur_c) ** 2))
        # 提纯质量：与无噪声直达波的相对误差
        i, j = LINKS[l]
        d_true = delayed(G["src"][i]["S"], taud) * np.exp(-2j * np.pi * F_TX[i] * taud) * \
            np.exp(-1j * (2 * np.pi * p["eps"][j] * F_TX[i] * T_ALL + G["lo_ph"][j]))
        a, b = d_true[sseg], clean
        rho = np.vdot(a, b) / np.sqrt(np.vdot(a, a).real * np.vdot(b, b).real)
        out["purify_err_db"] = float(10 * np.log10(1 - abs(rho) ** 2))
        rraw = ref[sseg]
        rho2 = np.vdot(a, rraw) / np.sqrt(np.vdot(a, a).real * np.vdot(rraw, rraw).real)
        out["raw_err_db"] = float(10 * np.log10(1 - abs(rho2) ** 2))
    out["time"] = time.time() - t0
    return out


# ================================================================ 融合中心
def read_caf(o, lagf, fdv, key="F"):
    """在 (分数时延, 多普勒) 处双线性读取目标区互模糊函数（复值）。"""
    F = o[key]
    fd = o["fd"]
    x = (lagf - o["lag0"]) * UPS
    y = (fdv - fd[0]) / (fd[1] - fd[0])
    x = np.clip(x, 0, F.shape[1] - 1.001)
    y = np.clip(y, 0, F.shape[0] - 1.001)
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    ax, ay = x - x0, y - y0
    return ((1 - ay) * ((1 - ax) * F[y0, x0] + ax * F[y0, x0 + 1])
            + ay * ((1 - ax) * F[y0 + 1, x0] + ax * F[y0 + 1, x0 + 1]))


def link_values(outs, pts, vel=V0, key="F", noise_key="noise"):
    """目标状态 (pts, vel) 处各链路的归一化复值 z̃_l 与几何相位 2πR_l/λ_l。"""
    R, fd, k, _ = link_geometry(pts, vel)
    z = np.empty(R.shape, complex)
    for l, o in enumerate(outs):
        z[..., l] = read_caf(o, R[..., l] / C0 * FS, fd[..., l], key) / np.sqrt(o[noise_key])
    phase = 2 * np.pi * R / LAM[np.array([i for i, _ in LINKS])]
    return z, phase, k


def fuse(z, phase, kap_hat, w):
    """返回 (单链路统计量, 非相参统计量 T_N, 相参统计量 T_C)。"""
    zc = z * np.exp(1j * (phase - kap_hat))
    tn = np.sum(np.abs(z) ** 2, axis=-1)
    tc = np.abs(np.sum(w * zc, axis=-1)) ** 2 / np.sum(w ** 2)
    return np.abs(z) ** 2, tn, tc


def mrc_weights(snr_db):
    w = np.sqrt(10 ** (np.asarray(snr_db) / 10))
    return w / np.sqrt(np.mean(w ** 2))


# ================================================================ 单次试验
def run_trial(seed, snr_offset=0.0, diag=False, xref=False):
    rng = np.random.default_rng(seed)
    R0, fd0, k0, beta0 = link_geometry(P0, V0)
    snr_db = link_snr_db() + snr_offset
    par = dict(seed=seed, dnr_ref=30.0, dnr_sur=40.0, snr_db=snr_db, with_target=True,
               eps=rng.uniform(-1, 1, NR) * 1e-9, kref=rng.uniform(0, 2 * np.pi, NL),
               ksur=rng.uniform(0, 2 * np.pi, NL), diag=diag, xref=xref)
    G.clear()
    lo_ph = [np.cumsum(rng.normal(0, np.sqrt(2 * np.pi * 1e-3 / FS), LTOT)) + rng.uniform(0, 2 * np.pi)
             for _ in range(NR)]
    G.update(par=par, src=make_sources(rng), R0=R0, fd0=fd0, lo_ph=lo_ph, alpha=scatterer_alpha(rng, k0))
    with mp.get_context("fork").Pool(4) as pool:
        outs = pool.map(process_link, range(NL))
    kap = (par["ksur"] - par["kref"] + np.pi) % (2 * np.pi) - np.pi
    kap_hat = kap + np.radians(SIG_CAL_DEG) * rng.standard_normal(NL)
    return outs, dict(par=par, kap=kap, kap_hat=kap_hat, snr_db=snr_db, R0=R0, fd0=fd0, k0=k0,
                      alpha=G["alpha"].copy(), src_dfT=[s["dfT"] for s in G["src"]])


def fine_offsets(step=0.5, half=5.0):
    g = np.arange(-half, half + 1e-9, step)
    gx, gy = np.meshgrid(g, g, indexing="ij")
    return np.stack([gx.ravel(), gy.ravel(), np.zeros(gx.size)], axis=1)


def coherent_maxpool(z, phase, kap_hat, w, k, offs):
    """粗网格每个单元内以精细偏移搜索相参统计量的最大值（“粗—精”两级搜索）。"""
    zc = (w * z * np.exp(1j * (phase - kap_hat))).reshape(-1, NL)
    E = np.exp(2j * np.pi * np.einsum("ld,od->lo", k, offs))     # (NL, n_off)
    out = np.empty(zc.shape[0])
    for s in range(0, zc.shape[0], 4096):
        out[s:s + 4096] = (np.abs(zc[s:s + 4096] @ E) ** 2).max(1)
    return out.reshape(z.shape[:-1]) / np.sum(w ** 2)


# ================================================================ 主程序
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=20)
    args = ap.parse_args()
    res = {}
    t0 = time.time()
    w = mrc_weights(link_snr_db())

    # ---------------- 1) 演示试验：名义信噪比，生成图件 ----------------
    print("demo trial ...")
    outs, info = run_trial(seed=7, diag=True, xref=True)
    print(f"  link processing time {np.mean([o['time'] for o in outs]):.1f} s/link")
    d0 = outs[0]
    res["station"] = dict(purify_err_db=d0["purify_err_db"], raw_err_db=d0["raw_err_db"],
                          pow_before_db=10 * np.log10(d0["pow_before"]),
                          pow_after_db=10 * np.log10(d0["pow_after"]))
    # 真值处各链路复值
    z0, ph0, k0 = link_values(outs, P0)
    s_link, tn0, tc0 = fuse(z0, ph0, info["kap_hat"], w)
    fig_station(d0, info)
    fig_link_maps(outs, info, s_link)
    res["demo"] = dict(snr_link_db=list(map(float, 10 * np.log10(s_link))),
                       snr_link_design_db=list(map(float, info["snr_db"])),
                       tn=float(tn0), tc=float(tc0), tc_db=float(10 * np.log10(tc0)))
    # 粗网格（10 m）融合图
    hx = np.arange(-1500, 1501, 10.0)
    gx, gy = np.meshgrid(hx, hx, indexing="ij")
    pts = np.stack([P0[0] + gx, P0[1] + gy, np.full(gx.shape, P0[2])], axis=-1)
    z, ph, k = link_values(outs, pts)
    s1, tn, _ = fuse(z, ph, info["kap_hat"], w)
    tcm = coherent_maxpool(z, ph, info["kap_hat"], w, k0, fine_offsets())
    # 精细网格（0.1 m）相参融合图
    hf = np.arange(-25, 25.001, 0.1)
    fx, fy = np.meshgrid(hf, hf, indexing="ij")
    ptf = np.stack([P0[0] + fx, P0[1] + fy, np.full(fx.shape, P0[2])], axis=-1)
    zf, phf, _ = link_values(outs, ptf)
    _, tnf, tcf = fuse(zf, phf, info["kap_hat"], w)
    _, _, tcf_nocal = fuse(zf, phf, np.zeros(NL), w)
    stats = map_stats(gx, gy, s1, tn, tcm)
    res["maps"] = stats
    fig_fusion_maps(hx, s1, tn, tcm, stats)
    ipk = np.unravel_index(np.argmax(tcf), tcf.shape)
    res["fine"] = dict(peak_dx=float(hf[ipk[0]]), peak_dy=float(hf[ipk[1]]),
                       peak_db=float(10 * np.log10(tcf.max())),
                       nocal_peak_db=float(10 * np.log10(tcf_nocal.max())))
    fig_fine_maps(hf, tnf, tcf, tcf_nocal, k0, w)
    print(f"  demo done ({time.time() - t0:.0f} s)")

    # ---------------- 2) 增益测量：多次独立试验（目标 RCS +10 dB 以降低统计起伏） ----------------
    prev = HERE / "results_signal.json"
    if args.trials == 0 and prev.exists():
        old_res = json.loads(prev.read_text(encoding="utf-8"))
        res["trials"], res["gain"] = old_res["trials"], old_res["gain"]
        fig_gain(res["gain"])
        prev.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"demo only, reused {len(res['trials'])} trials ({time.time() - t0:.0f} s)")
        return
    rec = []
    for t in range(args.trials):
        outs, info = run_trial(seed=1000 + t, snr_offset=10.0, xref=True)
        z, ph, _ = link_values(outs, P0)
        zx, _, _ = link_values(outs, P0, key="Fx", noise_key="noise_x")
        s_l, tn, tc = fuse(z, ph, info["kap_hat"], w)
        _, _, tc_eq = fuse(z, ph, info["kap_hat"], np.ones(NL))
        _, _, tc_nocal = fuse(z, ph, np.zeros(NL), w)
        _, _, tc_x = fuse(zx, ph, info["kap_hat"], w)
        # 两源相参（同一接收站两条链路）与站间相参（同一信号源五条链路）
        zc = z * np.exp(1j * (ph - info["kap_hat"]))
        pair = [np.abs(np.sum(w[[j, j + 5]] * zc[[j, j + 5]])) ** 2 / np.sum(w[[j, j + 5]] ** 2) for j in range(NR)]
        grp = [np.abs(np.sum(w[5 * i:5 * i + 5] * zc[5 * i:5 * i + 5])) ** 2 / np.sum(w[5 * i:5 * i + 5] ** 2)
               for i in range(NT)]
        rec.append(dict(s=s_l.tolist(), tn=float(tn), tc=float(tc), tc_eq=float(tc_eq), tc_nocal=float(tc_nocal),
                        tc_x=float(tc_x), pair=list(map(float, pair)), grp=list(map(float, grp)),
                        snr_design=list(map(float, info["snr_db"]))))
        print(f"  trial {t}: tc={10 * np.log10(tc):.2f} dB, mean link={10 * np.log10(np.mean(s_l)):.2f} dB "
              f"({time.time() - t0:.0f} s)")
    res["trials"] = rec
    res["gain"] = gain_summary(rec)
    fig_gain(res["gain"])
    (HERE / "results_signal.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"done in {time.time() - t0:.0f} s")


def gain_summary(rec):
    s = np.array([r["s"] for r in rec]) - 1.0            # 去除噪声项后的信噪比估计
    snr_l = s.mean(0)
    sd = np.array(rec[0]["snr_design"])
    out = dict(snr_link_meas_db=list(map(float, 10 * np.log10(snr_l))),
               snr_link_design_db=list(map(float, sd)))
    mean_link = snr_l.mean()
    for key in ("tc", "tc_eq", "tc_nocal", "tc_x"):
        v = np.mean([r[key] for r in rec]) - 1.0
        out[key + "_db"] = float(10 * np.log10(max(v, 1e-3)))
        out[key + "_gain_db"] = float(10 * np.log10(max(v, 1e-3) / mean_link))
    out["sum_link_db"] = float(10 * np.log10(snr_l.sum()))
    out["mean_link_db"] = float(10 * np.log10(mean_link))
    out["best_link_db"] = float(10 * np.log10(snr_l.max()))
    pair = np.mean([r["pair"] for r in rec], axis=0) - 1.0
    grp = np.mean([r["grp"] for r in rec], axis=0) - 1.0
    out["pair_db"] = list(map(float, 10 * np.log10(pair)))
    out["pair_sum_db"] = [float(10 * np.log10(snr_l[j] + snr_l[j + 5])) for j in range(NR)]
    out["grp_db"] = list(map(float, 10 * np.log10(grp)))
    out["grp_sum_db"] = [float(10 * np.log10(snr_l[5 * i:5 * i + 5].sum())) for i in range(NT)]
    tc = np.array([r["tc"] for r in rec])
    out["tc_se_db"] = float(10 / np.log(10) * np.std(tc) / np.sqrt(len(tc)) / (np.mean(tc) - 1))
    out["n_trials"] = len(rec)
    return out


PFA_MAP = 1e-6


def map_stats(gx, gy, s1, tn, tcm):
    """各融合图的峰值、背景统计与 Pfa=1e-6 检测门限（背景取距目标 300 m 以外区域）。

    单链路与非相参统计量门限按 Exp(1)、Gamma(10) 分布解析给出；粗—精搜索相参统计量为
    单元内精细位置上的最大值，其门限按 P(T>η)≈M·e^{-η} 由背景经验尾部拟合等效独立单元数 M。"""
    from scipy import stats
    far = np.hypot(gx, gy) > 300
    near = np.hypot(gx, gy) <= 20
    bgc = tcm[far]
    xs = np.quantile(bgc, [0.99, 0.995, 0.999])
    m_cell = float(np.mean([np.mean(bgc > x) * np.exp(x) for x in xs]))
    eta = dict(single=float(np.log(1 / PFA_MAP)), nc=float(stats.gamma.isf(PFA_MAP, NL)),
               coh=float(np.log(m_cell / PFA_MAP)))
    out = dict(m_cell=m_cell, eta=eta)
    for name, m in (("single", s1[..., 0]), ("nc", tn), ("coh", tcm)):
        bg = m[far]
        ex = far & (m > eta[name])
        out[name] = dict(peak=float(m[near].max()), bg_mean=float(bg.mean()), bg_max=float(bg.max()),
                         bg_std=float(bg.std()),
                         peak_to_bgmax_db=float(10 * np.log10(m[near].max() / bg.max())),
                         margin_db=float(10 * np.log10(m[near].max() / eta[name])),
                         n_exceed_bg=int(np.sum(bg > eta[name])),
                         exceed_xy_m=[[float(gx[ex][q]), float(gy[ex][q])] for q in range(int(ex.sum()))],
                         exceed_nc_db=[float(10 * np.log10(tn[ex][q] / eta["nc"])) for q in range(int(ex.sum()))])
    return out


# ================================================================ 绘图
def fig_station(d0, info):
    wide = d0["wide"]
    lags = wide["lags"] * C0 / FS / 1e3
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.7), sharey=True)
    for ax, key, title in ((axs[0], "before", "(a) ECA 对消前"), (axs[1], "after", "(b) ECA 对消后")):
        A = wide[key] ** 2
        nz = np.median(wide["after"] ** 2) / np.log(2)
        im = ax.pcolormesh(lags, wide["fd"], 10 * np.log10(A / nz + 1e-12), shading="auto", cmap="viridis",
                           vmin=-5, vmax=60 if key == "before" else 20, rasterized=True)
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("双基地距离差 / km")
        cb = fig.colorbar(im, ax=ax, pad=0.02)
        cb.set_label("相对噪声电平 / dB", fontsize=8)
    axs[0].set_ylabel("多普勒频率 / Hz")
    r0 = info["R0"][0] / 1e3
    axs[1].annotate("目标位置（淹没于噪声）", xy=(r0, info["fd0"][0]), xytext=(r0 - 33, 235),
                    color="w", fontsize=8, arrowprops=dict(arrowstyle="->", color="w", lw=0.8))
    fig.tight_layout()
    save(fig, "sig_station_eca")


def fig_link_maps(outs, info, s_link):
    fig, axs = plt.subplots(2, 5, figsize=(7.4, 3.5), sharex=True, sharey=True)
    for l, o in enumerate(outs):
        ax = axs[l // 5, l % 5]
        F = np.abs(o["F"]) ** 2 / o["noise"]
        lag = (o["lag0"] + np.arange(F.shape[1]) / UPS)
        dr = (lag - info["R0"][l] / C0 * FS) * C0 / FS
        sel = np.abs(dr) <= 1500
        im = ax.pcolormesh(dr[sel] / 1e3, o["fd"] - info["fd0"][l], 10 * np.log10(F[:, sel]), shading="auto",
                           cmap="viridis", vmin=-5, vmax=12, rasterized=True)
        ax.set_title(f"{LINK_NAMES[l]}（{info['snr_db'][l]:.1f} dB）", fontsize=7.5)
        ax.tick_params(labelsize=7)
        ax.plot(0, 0, marker="o", ms=9, mfc="none", mec="w", mew=0.8)
    for ax in axs[1]:
        ax.set_xlabel("ΔR / km", fontsize=8)
    for ax in axs[:, 0]:
        ax.set_ylabel("Δf / Hz", fontsize=8)
    cb = fig.colorbar(im, ax=axs, pad=0.01, fraction=0.025)
    cb.set_label("dB", fontsize=8)
    save(fig, "sig_link_maps")


def fig_fusion_maps(hx, s1, tn, tcm, stats):
    fig, axs = plt.subplots(1, 3, figsize=(7.4, 2.6), sharey=True)
    items = [(s1[..., 0], "(a) 单链路 T1R1", "single"), (tn, "(b) 10 链路非相参融合", "nc"),
             (tcm, "(c) 10 链路相参融合", "coh")]
    for ax, (m, title, key) in zip(axs, items):
        ref = stats["eta"][key]
        im = ax.pcolormesh(hx / 1e3, hx / 1e3, 10 * np.log10(m.T / ref), shading="auto", cmap="viridis",
                           vmin=-12, vmax=4, rasterized=True)
        ax.contour(hx / 1e3, hx / 1e3, 10 * np.log10(m.T / ref), levels=[0], colors="r", linewidths=0.8)
        ax.set_title(title, fontsize=8.5)
        ax.set_xlabel("Δx / km")
        ax.set_aspect("equal")
        ax.plot(0, 0, marker="o", ms=10, mfc="none", mec="w", mew=0.8)
    axs[0].set_ylabel("Δy / km")
    cb = fig.colorbar(im, ax=axs, pad=0.01, fraction=0.03)
    cb.set_label("检测统计量/门限 (Pfa=10$^{-6}$) / dB", fontsize=8)
    save(fig, "sig_fusion_maps")


def fig_fine_maps(hf, tnf, tcf, tcf_nocal, k0, w):
    fig, axs = plt.subplots(1, 3, figsize=(7.4, 2.6), sharey=True)
    vmax = 10 * np.log10(tcf.max())
    items = [(tnf, "(a) 非相参融合", tnf.max()), (tcf, "(b) 相参融合（已标定）", tcf.max()),
             (tcf_nocal, "(c) 相参融合（未标定通道相位）", tcf.max())]
    for ax, (m, title, ref) in zip(axs, items):
        im = ax.pcolormesh(hf, hf, 10 * np.log10(m.T / ref), shading="auto", cmap="magma", vmin=-15, vmax=0,
                           rasterized=True)
        ax.set_title(title, fontsize=8.5)
        ax.set_xlabel("Δx / m")
        ax.set_aspect("equal")
        ax.plot(0, 0, marker="+", ms=8, color="c", mew=1.0)
    axs[0].set_ylabel("Δy / m")
    cb = fig.colorbar(im, ax=axs, pad=0.01, fraction=0.03)
    cb.set_label("归一化 / dB", fontsize=8)
    save(fig, "sig_fine_maps")


def fig_gain(g):
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 2.8), gridspec_kw=dict(width_ratios=[1.35, 1]))
    ax = axs[0]
    x = np.arange(NL)
    ax.bar(x - 0.18, g["snr_link_design_db"], 0.36, color=C6, alpha=0.55, label="雷达方程预测")
    ax.bar(x + 0.18, g["snr_link_meas_db"], 0.36, color=C1, label="仿真实测")
    ax.set_xticks(x)
    ax.set_xticklabels(LINK_NAMES, rotation=45, fontsize=7.5)
    ax.set_ylabel("单链路输出信噪比 / dB")
    ax.set_title("(a) 各链路输出信噪比", fontsize=9)
    ax.grid(axis="y")
    ax.legend(loc="lower left")
    ax = axs[1]
    names = ["最佳单链路", "两源相参\n(单站)", "站间相参\n(单源)", "10链路相参\n(MRC)", "理论上限\nΣSNR"]
    vals = [g["best_link_db"], max(g["pair_db"]), max(g["grp_db"]), g["tc_db"], g["sum_link_db"]]
    cols = [C6, C4, C3, C1, "#9aa5b1"]
    ax.bar(range(len(vals)), vals, color=cols)
    for xx, v in enumerate(vals):
        ax.text(xx, v + 0.3, f"{v:.1f}", ha="center", fontsize=7.5)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels(names, fontsize=7.2)
    ax.set_ylabel("输出信噪比 / dB")
    ax.set_ylim(0, max(vals) + 3)
    ax.set_title("(b) 融合输出信噪比（目标 RCS +10 dB）", fontsize=9)
    ax.grid(axis="y")
    fig.tight_layout()
    save(fig, "sig_gain")


if __name__ == "__main__":
    main()
