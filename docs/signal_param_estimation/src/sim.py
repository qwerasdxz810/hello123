#!/usr/bin/env python3
"""非合作 OFDM 信号源参数盲估计仿真。

以 Humphreys 等公布的 Starlink Ku 波段下行信号参数构建仿真信号，
依次完成：功率谱/带宽估计、CP 自相关、循环自相关、采样率与子载波数判定、
帧周期与帧保护估计、跨帧相干平均提取同步符号、两级时频同步、调制识别。

运行：python3 docs/signal_param_estimation/src/sim.py
输出：figures/*.png 与 results.json
"""
import json
from pathlib import Path

import numpy as np
import scipy.fft as sfft
from scipy.signal import welch
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent.parent
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.sans-serif": ["WenQuanYi Zen Hei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 9,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.2,
    "grid.linewidth": 0.5,
    "grid.alpha": 0.35,
    "savefig.dpi": 300,
    "figure.dpi": 100,
})
C1, C2, C3, C4, C5 = "#1f4e9c", "#c0392b", "#2a8c6f", "#d98a1e", "#6a4c9c"

rng = np.random.default_rng(20261014)

# ---------------- 信号参数（文献[1]-[3]公布值） ----------------
FS_TX = 240e6          # 发射端采样率 / 信道带宽
N = 1024               # 子载波数
NG = 32                # 循环前缀长度（样点）
NSF = 302              # 每帧符号间隔数
TF = 1 / 750           # 帧周期
DF = FS_TX / N         # 子载波间隔 234.375 kHz
GUTTER = (-2, -1, 0, 1)  # 信道中心 4 个空子载波

# ---------------- 接收端（未知发射参数，采样率不同） ----------------
OS = 1.25
FS = FS_TX * OS        # 接收采样率 300 MHz
NR = int(N * OS)       # 1280
NGR = int(NG * OS)     # 40
LSYM = NR + NGR        # 1320
LF = int(round(TF * FS))   # 400000
LFG = LF - NSF * LSYM      # 1360

K_ALL = np.arange(-N // 2, N // 2)
ACTIVE = np.array([k not in GUTTER for k in K_ALL])
NUSED = int(ACTIVE.sum())


def constellation(name, size):
    if name == "qpsk":
        return np.exp(1j * (np.pi / 4 + np.pi / 2 * rng.integers(0, 4, size)))
    if name == "8psk":
        return np.exp(1j * np.pi / 4 * rng.integers(0, 8, size))
    if name == "16qam":
        lv = np.array([-3, -1, 1, 3])
        return (rng.choice(lv, size) + 1j * rng.choice(lv, size)) / np.sqrt(10)
    raise ValueError(name)


def ofdm(X):
    """X: (nsym, N) 频域符号（按 K_ALL 顺序）→ 带 CP 的时域样点，平均功率为 1。"""
    B = np.zeros((X.shape[0], NR), complex)
    B[:, K_ALL % NR] = X * ACTIVE
    s = sfft.ifft(B, axis=1) * NR / np.sqrt(NUSED)
    return np.concatenate([s[:, -NGR:], s], axis=1)


PSS_X = constellation("qpsk", N)   # 以固定随机序列代替实际 PSS/SSS
SSS_X = constellation("qpsk", N)
SYNC = ofdm(np.vstack([PSS_X, SSS_X])).ravel()   # 2 个符号，2640 样点


def frame(mod="qpsk"):
    X = constellation(mod, (NSF, N))
    X[0], X[1] = PSS_X, SSS_X
    return np.concatenate([ofdm(X).ravel(), np.zeros(LFG)])


def channel(x, snr_db, fd, theta=0, phi=None):
    """时延 theta 样点、频偏 fd、复高斯噪声；SNR 为单样点信噪比（以有信号段功率计）。"""
    phi = rng.uniform(0, 2 * np.pi) if phi is None else phi
    x = np.concatenate([np.zeros(theta), x])
    n = np.arange(len(x))
    y = x * np.exp(1j * (2 * np.pi * fd * n / FS + phi))
    s2 = 10 ** (-snr_db / 10)
    w = np.sqrt(s2 / 2) * (rng.standard_normal(len(x)) + 1j * rng.standard_normal(len(x)))
    return y + w


def parabolic(y, i):
    a, b, c = y[i - 1], y[i], y[i + 1]
    return i + 0.5 * (a - c) / (a - 2 * b + c)


res = {}

# =============== 1. 生成多帧接收信号 ===============
SNR0 = 0.0
FD = 186.4e3                    # 频偏（含多普勒），大于半个子载波间隔
NFR = 16
THETA0 = 123457
tx = np.concatenate([frame() for _ in range(NFR)])
r = channel(tx, SNR0, FD, THETA0).astype(np.complex64)
res["sim"] = dict(snr_db=SNR0, fd_hz=FD, frames=NFR, fs_rx=FS)

# =============== 2. 功率谱：占用带宽、中心空隙、频偏粗估计 ===============
f, P = welch(r, fs=FS, nperseg=65536, noverlap=32768, window="hann",
             return_onesided=False, scaling="density")
f, P = np.fft.fftshift(f), np.fft.fftshift(P)
Ps = np.convolve(P, np.ones(9) / 9, mode="same")      # 频域平滑，降低估计起伏
inband = np.median(Ps[np.abs(f - FD) < 80e6])
noise_floor = np.median(Ps[np.abs(f) > 135e6])
thr = (inband + noise_floor) / 2       # 半功率门限


def runs(mask):
    """返回布尔序列中所有连续 True 区间 [(start, end), ...]。"""
    d = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0] - 1))


def cross(i0, i1):
    """在相邻两点间线性插值门限穿越频率。"""
    return f[i0] + (thr - Ps[i0]) * (f[i1] - f[i0]) / (Ps[i1] - Ps[i0])


bins_5mhz = int(5e6 / (f[1] - f[0]))
sig = [t for t in runs(Ps > thr) if t[1] - t[0] > bins_5mhz]   # 剔除噪声尖峰
iL, iH = sig[0][0], sig[-1][1]
fL, fH = cross(iL - 1, iL), cross(iH, iH + 1)
B_hat = fH - fL
fmid = (fL + fH) / 2
# 中心空隙：频带中心 ±2 MHz 内低于门限的最长连续区间
win = np.abs(f - fmid) < 2e6
g0, g1 = max(runs(win & (Ps < thr)), key=lambda t: t[1] - t[0])
gL, gH = cross(g0 - 1, g0), cross(g1, g1 + 1)
f_gutter = (gL + gH) / 2
res["psd"] = dict(B_hat=B_hat, fL=fL, fH=fH, gutter_width=gH - gL, f_gutter=f_gutter)

fig, ax = plt.subplots(figsize=(5.0, 2.3))
ax.plot(f / 1e6, 10 * np.log10(Ps / inband), color=C1, lw=0.7)
ax.axvline(fL / 1e6, color=C2, ls="--", lw=0.8)
ax.axvline(fH / 1e6, color=C2, ls="--", lw=0.8)
ax.annotate("", xy=(fL / 1e6, 3), xytext=(fH / 1e6, 3),
            arrowprops=dict(arrowstyle="<->", color=C2, lw=0.8))
ax.text(fmid / 1e6, 4.2, f"$\\hat{{B}}$ = {B_hat / 1e6:.2f} MHz", ha="center",
        color=C2, fontsize=8.5)
ax.set_xlim(-150, 150)
ax.set_ylim(-16, 8)
ax.set_xlabel("频率 / MHz")
ax.set_ylabel("归一化功率谱 / dB")
ax.grid(True)
ins = ax.inset_axes([0.44, 0.17, 0.30, 0.36])
m = np.abs(f - f_gutter) < 1.6e6
ins.plot((f[m] - FD) / 1e3, 10 * np.log10(Ps[m] / inband), color=C1, lw=0.8)
ins.axvline((f_gutter - FD) / 1e3, color=C3, ls=":", lw=0.9)
ins.set_title("中心空隙放大（横轴：kHz）", fontsize=6.5, pad=2)
ins.tick_params(labelsize=6)
ins.grid(True)
fig.tight_layout()
fig.savefig(FIG / "fig3_psd.png")
plt.close(fig)

# =============== 3. CP 自相关：有用符号长度 ===============
seg = r[:LF].astype(np.complex128)
nfft = 1 << 20
Rf = sfft.ifft(np.abs(sfft.fft(seg, nfft)) ** 2)
R = Rf[:3000] / Rf[0]
lag0 = 50
i_pk = lag0 + int(np.argmax(np.abs(R[lag0:])))
T_hat = i_pk / FS
DF_hat = 1 / T_hat
res["cp_acf"] = dict(lag=i_pk, T_hat=T_hat, peak=float(np.abs(R[i_pk])), DF_hat=DF_hat)

# =============== 4. 循环自相关：符号周期、CP 长度 ===============
seg2 = r[:2 * LF].astype(np.complex128)
z = seg2[:-i_pk] * np.conj(seg2[i_pk:])
nz = 1 << 23
Z = np.abs(sfft.fft(z, nz)) / len(z)
alpha = np.arange(nz) * FS / nz
amask = (alpha > 50e3) & (alpha < 400e3)
ia = np.where(amask)[0][np.argmax(Z[amask])]
a1 = alpha[0] + parabolic(Z, ia) * FS / nz
# 利用前 4 次谐波最小二乘
harm = []
for k in range(1, 5):
    c = k * a1
    mk = np.abs(alpha - c) < 3e3
    ik = np.where(mk)[0][np.argmax(Z[mk])]
    harm.append((k, parabolic(Z, ik) * FS / nz))
ks = np.array([h[0] for h in harm])
als = np.array([h[1] for h in harm])
alpha_sym = float((ks @ als) / (ks @ ks))
Tsym_hat = 1 / alpha_sym
Tg_hat = Tsym_hat - T_hat
res["cyclic"] = dict(alpha1=alpha_sym, Tsym_hat=Tsym_hat, Tg_hat=Tg_hat)

fig, axs = plt.subplots(1, 2, figsize=(5.0, 2.25))
tau_us = np.arange(len(R)) / FS * 1e6
axs[0].plot(tau_us[lag0:], np.abs(R[lag0:]), color=C1, lw=0.8)
axs[0].plot(tau_us[i_pk], np.abs(R[i_pk]), "o", ms=4, mfc="none", color=C2)
axs[0].annotate(f"τ = {T_hat * 1e6:.4f} μs", xy=(tau_us[i_pk], np.abs(R[i_pk])),
                xytext=(tau_us[i_pk] + 0.9, np.abs(R[i_pk]) * 0.88), fontsize=7.5,
                color=C2, arrowprops=dict(arrowstyle="->", color=C2, lw=0.7))
axs[0].set_xlabel("时延 τ / μs")
axs[0].set_ylabel(r"$|\bar{R}_r(\tau)|/\bar{R}_r(0)$")
axs[0].set_title("(a) CP 自相关函数", fontsize=9)
axs[0].set_xlim(0, 10)
axs[0].grid(True)
am = alpha < 1.2e6
axs[1].plot(alpha[am] / 1e3, Z[am] / Z[0], color=C1, lw=0.8)
for k, a in harm:
    axs[1].plot(a / 1e3, np.interp(a, alpha, Z) / Z[0], "v", ms=4, color=C2)
axs[1].text(0.97, 0.96, f"$\\hat{{\\alpha}}_1$ = {alpha_sym / 1e3:.2f} kHz\n"
            f"$\\hat{{T}}_{{sym}}$ = {Tsym_hat * 1e6:.4f} μs",
            transform=axs[1].transAxes, ha="right", va="top", fontsize=8, color=C2)
axs[1].set_xlabel("循环频率 α / kHz")
axs[1].set_ylabel("归一化循环自相关幅度")
axs[1].set_title("(b) 循环自相关谱", fontsize=9)
axs[1].set_xlim(0, 1200)
axs[1].set_ylim(0, 1.5)
axs[1].grid(True)
fig.tight_layout()
fig.savefig(FIG / "fig4_cp_cyclic.png")
plt.close(fig)

# =============== 5. 采样率、子载波数、CP 样点数判定 ===============
cands = []
for p in range(6, 14):
    Nc = 2 ** p
    Fs_c = Nc / T_hat
    cands.append(dict(N=Nc, Fs=Fs_c, Ng=Tg_hat * Fs_c, ok=Fs_c >= 0.98 * B_hat))
pick = next(c for c in cands if c["ok"])
N_hat, Fs_hat = pick["N"], pick["Fs"]
Ng_hat = int(round(Tg_hat * Fs_hat))
Tsym_ref = (N_hat + Ng_hat) / Fs_hat
res["integer"] = dict(N_hat=N_hat, Fs_hat=Fs_hat, Ng_raw=Tg_hat * Fs_hat, Ng_hat=Ng_hat,
                      Tsym_ref=Tsym_ref,
                      table=[dict(N=c["N"], Fs=c["Fs"], Ng=c["Ng"]) for c in cands[3:6]])

# =============== 6. 帧周期、帧保护、每帧符号数 ===============
nfft2 = 1 << 23
x = r.astype(np.complex64)
Xf = sfft.fft(x, nfft2, workers=4)
Rl = sfft.ifft(np.abs(Xf) ** 2, workers=4)
lags = np.arange(int(0.2e-3 * FS), int(3.0e-3 * FS))
Rl_n = np.abs(Rl[lags]) / np.abs(Rl[0])
iF = lags[np.argmax(Rl_n)]
TF_hat = iF / FS
# 噪声基底统计
mask_noise = np.abs(lags - iF) > 2000
mask_noise &= np.abs(lags - 2 * iF) > 2000
floor_med = float(np.median(Rl_n[mask_noise]))
floor_max = float(Rl_n[mask_noise].max())
res["frame"] = dict(lag=int(iF), TF_hat=TF_hat, peak=float(Rl_n.max()),
                    floor_median=floor_med, floor_max=floor_max)

# 帧同步功率折叠：以估计帧周期为模平均瞬时功率
nf_fold = (len(x) - THETA0) // iF - 1
pw = np.abs(x[:nf_fold * iF].astype(np.complex128)) ** 2
fold = pw.reshape(nf_fold, iF).mean(0)
ker = np.ones(64) / 64
fold_s = np.convolve(np.concatenate([fold, fold[:63]]), ker, mode="valid")[:iF]
lvl_hi, lvl_lo = np.median(fold_s), np.min(fold_s)
thr_f = (lvl_hi + lvl_lo) / 2
lowf = fold_s < thr_f
# 低功率区间（可能跨越首尾），取最长连续段
idx = np.where(lowf)[0]
dd = np.diff(np.concatenate([[idx[0] - 2], idx]))
starts = np.where(dd > 1)[0]
runs = []
for j, s0 in enumerate(starts):
    e0 = starts[j + 1] if j + 1 < len(starts) else len(idx)
    runs.append((idx[s0], idx[e0 - 1]))
g_s, g_e = max(runs, key=lambda t: t[1] - t[0])
Lfg_hat = (g_e - g_s + 1)
Tfg_hat = Lfg_hat / FS
Nsf_hat = int(round((TF_hat - Tfg_hat) / Tsym_ref))
Tfg_ref = TF_hat - Nsf_hat * Tsym_ref
frame_start = (g_e + 1 + 63 // 2) % iF   # 平滑核群时延补偿
res["frame"].update(Tfg_raw=Tfg_hat, Nsf_hat=Nsf_hat, Tfg_ref=Tfg_ref,
                    frame_start=int(frame_start),
                    frame_start_true=int(THETA0 % iF))

fig, axs = plt.subplots(1, 2, figsize=(5.0, 2.25))
axs[0].plot(lags / FS * 1e3, Rl_n * 1e3, color=C1, lw=0.6)
axs[0].plot(TF_hat * 1e3, Rl_n.max() * 1e3, "o", ms=4, mfc="none", color=C2)
axs[0].text(TF_hat * 1e3 + 0.08, Rl_n.max() * 1e3 * 1.06,
            f"$\\hat{{T}}_f$ = {TF_hat * 1e3:.4f} ms", fontsize=7.5, color=C2, va="bottom")
axs[0].set_ylim(0, Rl_n.max() * 1e3 * 1.35)
axs[0].set_xlabel("时延 τ / ms")
axs[0].set_ylabel(r"$|\bar{R}_r(\tau)|/\bar{R}_r(0)$ (×10$^{-3}$)")
axs[0].set_title("(a) 长时延自相关", fontsize=9)
axs[0].grid(True)
tt = (np.arange(iF) - frame_start) % iF
order = np.argsort(tt)
t_us = tt[order] / FS * 1e6
PRE = 3600
sh = np.roll(fold_s / lvl_hi, -int(frame_start) + PRE)
t_axis = (np.arange(iF) - PRE) / FS * 1e6
mz = (t_axis > -12) & (t_axis < 18)
axs[1].plot(t_axis[mz], sh[mz], color=C1, lw=1.0, label="折叠平均功率（平滑）")
axs[1].axvspan(-Tfg_hat * 1e6, 0, color=C4, alpha=0.18, lw=0)
axs[1].annotate(f"帧保护 {Tfg_hat * 1e6:.2f} μs", xy=(-1.0, 0.52), xytext=(2.0, 0.6),
                fontsize=7, color="#8a5a0b", va="center",
                arrowprops=dict(arrowstyle="->", color="#8a5a0b", lw=0.7))
axs[1].set_xlabel("相对帧起点时间 / μs")
axs[1].set_ylabel("归一化功率")
axs[1].set_title("(b) 帧同步功率折叠", fontsize=9)
axs[1].set_ylim(0.3, 1.3)
axs[1].grid(True)
fig.tight_layout()
fig.savefig(FIG / "fig5_frame.png")
plt.close(fig)

# =============== 7. 跨帧相干平均提取同步符号 ===============
def extract_sync(K, snr_db, dfres, trials=40):
    out = []
    Lp = len(SYNC)
    s2 = 10 ** (-snr_db / 10)
    for _ in range(trials):
        acc = np.zeros(Lp, complex)
        phi0 = rng.uniform(0, 2 * np.pi)
        for l in range(K):
            n = np.arange(Lp) + l * LF
            y = SYNC * np.exp(1j * (2 * np.pi * dfres * n / FS + phi0))
            acc += y + np.sqrt(s2 / 2) * (rng.standard_normal(Lp) + 1j * rng.standard_normal(Lp))
        est = acc / K
        out.append(np.abs(np.vdot(SYNC, est)) / (np.linalg.norm(SYNC) * np.linalg.norm(est)))
    return float(np.mean(out))


def rho_theory(K, snr_db, dfres):
    d = dfres * LF / FS                     # 帧间相位增量 2πδ，δ = Δf·T_f
    D = 1.0 if d == 0 else abs(np.sin(np.pi * K * d) / (K * np.sin(np.pi * d)))
    g = K * 10 ** (snr_db / 10)
    return float(D / np.sqrt(D ** 2 + 1 / g))


SNR_EX = -10.0
K_LIST = [1, 2, 4, 8, 16, 32, 64, 128, 256]
sync_curves = {str(d): [extract_sync(K, SNR_EX, d) for K in K_LIST] for d in (0.0, 2.0, 10.0)}
res["sync_extract"] = dict(snr_db=SNR_EX, K=K_LIST, sim=sync_curves,
                           theory={str(d): [rho_theory(K, SNR_EX, d) for K in K_LIST]
                                   for d in (0.0, 2.0, 10.0)})

# =============== 8. 两级时频同步 ===============
def vdb(y, rho, M, L=NR, Lg=NGR, search=LSYM, full=False):
    prod = y[:-L] * np.conj(y[L:])
    pw_ = 0.5 * (np.abs(y[:-L]) ** 2 + np.abs(y[L:]) ** 2)
    c = np.concatenate([[0], np.cumsum(prod)])
    g = c[Lg:] - c[:-Lg]
    cpw = np.concatenate([[0], np.cumsum(pw_)])
    ph = cpw[Lg:] - cpw[:-Lg]
    idx_ = np.arange(search)[:, None] + LSYM * np.arange(M)[None, :]
    G = g[idx_].sum(1)
    Pp = ph[idx_].sum(1)
    th = int(np.argmax(np.abs(G) - rho * Pp))
    if full:
        return th, G[th]
    return th, float(-np.angle(G[th]) / (2 * np.pi))


_EN_CACHE = {}


def da_freq(zv, span=6e3, npt=241):
    """单帧数据辅助频率估计（网格搜索 + 抛物线插值）。"""
    fg = np.linspace(-span, span, npt)
    n_ = np.arange(len(zv))
    A = np.abs(np.exp(-1j * 2 * np.pi * np.outer(fg, n_) / FS) @ zv)
    i = int(np.clip(np.argmax(A), 1, npt - 2))
    return fg[0] + parabolic(A, i) * (fg[1] - fg[0])


def da_multi(Z, offs, span, step, fine=True):
    """多帧相干数据辅助频率估计。Z: (K, Lp) 去调制序列；offs: 各帧起点（样点）。"""
    Lp = Z.shape[1]
    n_ = np.arange(Lp)

    def metric(fg, En=None):
        if En is None:
            En = np.exp(-1j * 2 * np.pi * np.outer(fg, n_) / FS)      # (G, Lp)
        Fl = np.exp(-1j * 2 * np.pi * np.outer(fg, offs) / FS)        # (G, K)
        return np.abs(((En @ Z.T) * Fl).sum(1))

    key = (span, step, Lp)
    if key not in _EN_CACHE:
        fgc = np.arange(-span, span + step / 2, step)
        _EN_CACHE[key] = (fgc, np.exp(-1j * 2 * np.pi * np.outer(fgc, n_) / FS))
    fg, En0 = _EN_CACHE[key]
    A = metric(fg, En0)
    i = int(np.clip(np.argmax(A), 1, len(fg) - 2))
    f1 = fg[0] + parabolic(A, i) * step
    if not fine:
        return f1
    fg2 = f1 + np.linspace(-2 * step, 2 * step, 81)
    A2 = metric(fg2)
    i2 = int(np.clip(np.argmax(A2), 1, len(fg2) - 2))
    return fg2[0] + parabolic(A2, i2) * (fg2[1] - fg2[0])


def crb_multi(K, snr_lin):
    Lp = len(SYNC)
    e = np.tile(np.abs(SYNC) ** 2, K)
    nn = (np.arange(Lp)[None, :] + LF * np.arange(K)[:, None]).ravel()
    nbar = (e @ nn) / e.sum()
    return float(np.sqrt(1 / (2 * snr_lin * (2 * np.pi / FS) ** 2 * (e @ (nn - nbar) ** 2))))


# 8.1 在多帧接收数据上的实际估计（SNR0, FD）
snr_lin = 10 ** (SNR0 / 10)
rho0 = snr_lin / (1 + snr_lin)
f_coarse = f_gutter + DF_hat / 2
nfr_use = NFR - 1
fstarts = [frame_start + l * iF for l in range(nfr_use)]
Gsum = 0
for fs_ in fstarts:
    y = r[fs_ + 10: fs_ + 10 + 300 * LSYM + 10].astype(np.complex128)
    _, Gl = vdb(y, rho0, M=298, full=True)
    Gsum = Gsum + Gl
eps1 = float(-np.angle(Gsum) / (2 * np.pi))
f_fine = eps1 * DF_hat
q = int(np.round((f_coarse - f_fine) / DF_hat))
fd_nda = f_fine + q * DF_hat
# 数据辅助精确定时：在估计帧起点 ±32 样点内与同步符号做互相关
Lp = len(SYNC)
tim = []
for fs_ in fstarts:
    cands_t = np.arange(-32, 33)
    ys = np.stack([r[fs_ + t: fs_ + t + Lp] for t in cands_t]).astype(np.complex128)
    nn = fs_ + cands_t[:, None] + np.arange(Lp)[None, :]
    ys = ys * np.exp(-1j * 2 * np.pi * fd_nda * nn / FS)
    tim.append(int(cands_t[np.argmax(np.abs(ys @ np.conj(SYNC)))]))
fs_ref = [fs_ + t for fs_, t in zip(fstarts, tim)]
# 多帧相干数据辅助精频偏估计
Z = np.stack([r[f0: f0 + Lp].astype(np.complex128) * np.conj(SYNC)
              * np.exp(-1j * 2 * np.pi * fd_nda * (f0 + np.arange(Lp)) / FS) for f0 in fs_ref])
offs = np.array(fs_ref) - fs_ref[0]
fd_da = fd_nda + da_multi(Z, offs, span=300, step=1.0)
res["sync"] = dict(f_coarse=f_coarse, eps=eps1, f_fine=f_fine, q=q, fd_nda=fd_nda,
                   n_frames=nfr_use, nda_symbols=298 * nfr_use,
                   timing_refine=tim[:3], frame_start_ref=int(fs_ref[0]),
                   frame_start_true=int(THETA0), fd_da=fd_da,
                   crb_multi=crb_multi(nfr_use, snr_lin))

# 8.1b Monte Carlo：多帧相干数据辅助估计精度随帧数变化（SNR = 0 dB）
KM = [1, 2, 4, 8, 16, 32, 64]
TRK = 200
mf_rmse, mf_crb = [], []
for K in KM:
    errs = []
    offs_k = LF * np.arange(K)
    for _ in range(TRK):
        fres = rng.uniform(-100, 100)
        phi0 = rng.uniform(0, 2 * np.pi)
        nn = np.arange(Lp)[None, :] + offs_k[:, None]
        Yk = SYNC[None, :] * np.exp(1j * (2 * np.pi * fres * nn / FS + phi0))
        Yk = Yk + np.sqrt(1 / snr_lin / 2) * (rng.standard_normal(Yk.shape)
                                              + 1j * rng.standard_normal(Yk.shape))
        Zk = Yk * np.conj(SYNC)[None, :]
        if K == 1:
            fe = da_multi(Zk, offs_k, span=4000, step=20)
        else:
            fe = da_multi(Zk, offs_k, span=300, step=1.0)
        errs.append(fe - fres)
    mf_rmse.append(float(np.sqrt(np.mean(np.square(errs)))))
    mf_crb.append(crb_multi(K, snr_lin))
res["multiframe"] = dict(snr_db=SNR0, K=KM, rmse=mf_rmse, crb=mf_crb, trials=TRK)

fig, axs = plt.subplots(1, 2, figsize=(5.0, 2.3))
mk_ = dict(ms=3.8, mfc="none")
for (d, c, m) in (("0.0", C1, "o"), ("2.0", C3, "s"), ("10.0", C2, "^")):
    lab = f"残余频偏 {float(d):.0f} Hz"
    axs[0].semilogx(K_LIST, res["sync_extract"]["theory"][d], "-", color=c, lw=0.9, base=2)
    axs[0].semilogx(K_LIST, sync_curves[d], m, color=c, label=lab, base=2, **mk_)
axs[0].set_xlabel("相干平均帧数 K")
axs[0].set_ylabel("提取序列与真值相关系数")
axs[0].set_title(f"(a) 同步符号提取（SNR = {SNR_EX:.0f} dB）", fontsize=9)
axs[0].set_ylim(0, 1.3)
axs[0].set_yticks([0, 0.25, 0.5, 0.75, 1.0])
axs[0].legend(fontsize=6.3, frameon=False, loc="upper left")
axs[0].grid(True, which="both")
axs[1].loglog(KM, mf_rmse, "d", color=C2, label="多帧相干 ML（仿真）", **mk_)
axs[1].loglog(KM, mf_crb, "k--", lw=0.9, label="CRB")
axs[1].set_xscale("log", base=2)
axs[1].set_xlabel("参与估计的帧数 K")
axs[1].set_ylabel("频偏估计 RMSE / Hz")
axs[1].set_title(f"(b) 多帧相干频偏估计（SNR = {SNR0:.0f} dB）", fontsize=9)
axs[1].legend(fontsize=6.8, frameon=False)
axs[1].grid(True, which="both")
fig.tight_layout()
fig.savefig(FIG / "fig7_multiframe.png")
plt.close(fig)

# 8.2 Monte Carlo：频偏 / 定时 RMSE 随 SNR
snrs = np.arange(-15, 21, 5)
TR = 300
mc = {f"nda_M{M}": dict(f=[], t=[], pc=[]) for M in (1, 10, 100)}
mc["da"] = dict(f=[])
crb = []
for sdb in snrs:
    sl = 10 ** (sdb / 10)
    rho = sl / (1 + sl)
    for M in (1, 10, 100):
        ef, et = [], []
        for _ in range(TR):
            X = constellation("qpsk", (M + 2, N))
            s = ofdm(X).ravel()
            th0 = int(rng.integers(0, LSYM))
            fd = rng.uniform(-0.4, 0.4) * DF
            y = channel(s, sdb, fd, th0)
            th, ep = vdb(y, rho, M)
            ef.append(ep * DF - fd)
            d = (th - th0 + LSYM // 2) % LSYM - LSYM // 2
            et.append(d)
        mc[f"nda_M{M}"]["f"].append(float(np.sqrt(np.mean(np.square(ef)))))
        mc[f"nda_M{M}"]["t"].append(float(np.sqrt(np.mean(np.square(et)))))
        mc[f"nda_M{M}"]["pc"].append(float(np.mean(np.abs(et) <= 1)))
    ef = []
    Lp = len(SYNC)
    for _ in range(TR):
        fd = rng.uniform(-2e3, 2e3)
        y = channel(SYNC, sdb, fd, 0)
        ef.append(da_freq(y * np.conj(SYNC)) - fd)
    mc["da"]["f"].append(float(np.sqrt(np.mean(np.square(ef)))))
    e = np.abs(SYNC) ** 2
    nn = np.arange(Lp)
    nbar = (e @ nn) / e.sum()
    crb.append(float(np.sqrt(1 / (2 * sl * (2 * np.pi / FS) ** 2 * (e @ (nn - nbar) ** 2)))))
res["mc"] = dict(snr=snrs.tolist(), trials=TR, crb=crb, **mc)

fig, axs = plt.subplots(1, 2, figsize=(5.0, 2.3))
mk = dict(ms=3.5, mfc="none")
for (M, c, m) in ((1, C1, "o"), (10, C3, "s"), (100, C5, "^")):
    axs[0].semilogy(snrs, mc[f"nda_M{M}"]["f"], m + "-", color=c, label=f"CP-ML, M={M}", **mk)
    axs[1].plot(snrs, mc[f"nda_M{M}"]["pc"], m + "-", color=c, label=f"CP-ML, M={M}", **mk)
h_da, = axs[0].semilogy(snrs, mc["da"]["f"], "d-", color=C2, label="同步符号 ML（单帧）", **mk)
h_crb, = axs[0].semilogy(snrs, crb, "k--", lw=0.9, label="CRB（单帧）")
axs[0].set_xlabel("SNR / dB")
axs[0].set_ylabel("频偏估计 RMSE / Hz")
axs[0].set_title("(a) 频偏估计精度", fontsize=9)
hs, ls = axs[0].get_legend_handles_labels()
leg1 = axs[0].legend(hs[:3], ls[:3], fontsize=6.3, frameon=False, loc="upper right")
axs[0].add_artist(leg1)
axs[0].legend([h_da, h_crb], ["同步符号 ML（单帧）", "CRB（单帧）"], fontsize=6.3, frameon=False,
              loc="lower left")
axs[0].set_ylim(1, 1e8)
axs[0].grid(True, which="both")
axs[1].set_xlabel("SNR / dB")
axs[1].set_ylabel("定时正确概率")
axs[1].set_title("(b) 符号定时估计性能", fontsize=9)
axs[1].set_ylim(-0.03, 1.05)
axs[1].legend(fontsize=6.5, frameon=False)
axs[1].grid(True)
fig.tight_layout()
fig.savefig(FIG / "fig6_sync.png")
plt.close(fig)

# =============== 9. 补偿前后星座图与调制识别 ===============
def demod(y, th, fd, nsym):
    n = np.arange(len(y))
    if fd is not None:
        y = y * np.exp(-1j * 2 * np.pi * fd * n / FS)
    blocks = np.stack([y[th + m * LSYM + NGR: th + m * LSYM + LSYM] for m in range(nsym)])
    Y = sfft.fft(blocks, axis=1) / NR * np.sqrt(NUSED)
    return Y[:, K_ALL % NR]


def run_mod(mod, snr_db, nsym=24, show=False):
    X = constellation(mod, (nsym, N))
    X[0] = SSS_X
    s = ofdm(X).ravel()
    th0 = 777
    y = channel(np.concatenate([s, np.zeros(2000)]), snr_db, FD, th0)
    sl = 10 ** (snr_db / 10)
    th, ep = vdb(y, sl / (1 + sl), M=nsym - 1)
    f_f = ep * DF_hat
    q_ = int(np.round((f_coarse - f_f) / DF_hat))
    fdh = f_f + q_ * DF_hat
    Y0 = demod(y, th, None, nsym)
    Y1 = demod(y, th, fdh, nsym)
    cpe = np.angle(np.vdot(SSS_X[ACTIVE], Y1[0][ACTIVE]))
    Y1 = Y1 * np.exp(-1j * cpe)
    data = Y1[1:][:, ACTIVE].ravel()
    s2n = np.mean(np.abs(Y1[1:][:, ~ACTIVE]) ** 2)   # 由空子载波估计噪声功率
    M20 = np.mean(data ** 2)
    M21 = np.mean(np.abs(data) ** 2)
    M40 = np.mean(data ** 4)
    M42 = np.mean(np.abs(data) ** 4)
    C40 = M40 - 3 * M20 ** 2
    C42 = M42 - np.abs(M20) ** 2 - 2 * M21 ** 2
    nrm = (M21 - s2n) ** 2
    return Y0, Y1, dict(C40=float(np.abs(C40) / nrm), C42=float(np.real(C42) / nrm),
                        sigma2=float(s2n))


Y0, Y1, _ = run_mod("qpsk", 20.0, show=True)
fig, axs = plt.subplots(1, 2, figsize=(5.2, 2.6))
d0 = Y0[1:6][:, ACTIVE].ravel()
d1 = Y1[1:6][:, ACTIVE].ravel()
axs[0].plot(d0.real, d0.imag, ".", ms=1, color=C1, alpha=0.5)
axs[1].plot(d1.real, d1.imag, ".", ms=1, color=C1, alpha=0.5)
for a_, t_ in zip(axs, ("(a) 补偿前", "(b) 时频同步补偿后")):
    a_.set_xlim(-2, 2)
    a_.set_ylim(-2, 2)
    a_.set_aspect("equal")
    a_.set_xlabel("同相分量")
    a_.set_ylabel("正交分量")
    a_.set_title(t_, fontsize=9)
    a_.grid(True)
fig.tight_layout()
fig.savefig(FIG / "fig8_constellation.png")
plt.close(fig)

modtab = []
theory = {"qpsk": (1.0, -1.0), "8psk": (0.0, -1.0), "16qam": (0.68, -0.68)}
for mod in ("qpsk", "8psk", "16qam"):
    vals = [run_mod(mod, 10.0)[2] for _ in range(20)]
    modtab.append(dict(mod=mod, C40_th=theory[mod][0], C42_th=theory[mod][1],
                       C40=float(np.mean([v["C40"] for v in vals])),
                       C40_std=float(np.std([v["C40"] for v in vals])),
                       C42=float(np.mean([v["C42"] for v in vals])),
                       C42_std=float(np.std([v["C42"] for v in vals]))))
res["modulation"] = dict(snr_db=10.0, table=modtab)

(OUT / "src" / "results.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
print(json.dumps(res, indent=2, ensure_ascii=False))
