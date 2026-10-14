---
title: 信号源参数精确估计技术
subtitle: ——基于低轨卫星OFDM信号盲识别的原理与验证
---

::: {custom-style="提要"}
**内容提要：**非合作信号源雷达不掌握照射源的波形参数，而参考信号重构、多源串扰抑制与多源/多站相参融合均以精确的信号源参数为前提。本文以 Humphreys 等关于 Starlink Ku 波段下行信号盲识别的论文^\[1\]^为主要参考，梳理非合作 OFDM 信号源参数“由粗到精、由盲到辅”的估计原理，并依据文献公布的信号参数进行了仿真验证。结果表明：在单样点信噪比为 0 dB 时，采样率、子载波数、循环前缀长度、帧周期及每帧符号数等结构参数均被准确恢复；利用 15 帧同步符号进行多帧相干估计，频偏估计误差约 0.05 Hz，与克拉美-罗界（CRB）处于同一量级。
:::

# 1 技术背景

非合作信号源雷达以广播、通信、导航及低轨卫星互联网等机会照射源作为发射机，具有隐蔽性好、部署灵活等优点。然而，照射源并非为雷达探测而设计，其信号参数通常不公开；接收站与照射源之间不存在时钟同步，低轨卫星还会带来数百 kHz 量级的多普勒频移。信号源参数对后续处理的支撑作用体现在三个方面：一是参考信号重构需要依据采样率、子载波数、循环前缀（CP）长度、帧结构及同步序列对直达波进行解调—再调制，参数失配将引入重构误差并抬高距离—多普勒旁瓣；二是多源串扰抑制需要准确掌握各信号源的载频、带宽与时频结构；三是多信号源间及分布式接收站间的相参融合要求各通道在时间、频率与相位上精确对齐。以跨帧相干积累为例，残余频偏 $\delta f$ 在 $K$ 帧内引入的累积相位约为 $2\pi\delta f K T_f$，要求 $\delta f \ll 1/(KT_f)$；当 $T_f=1.333$ ms、$K=64$ 时，残余频偏须远小于 11.7 Hz。

按物理含义，信号源参数可分为信号层（载频、带宽、采样率、子载波数、CP 长度等）、结构层（帧周期、帧保护、每帧符号数、同步符号等）与同步层（时延、频偏、相位）三个层次。三者逐级依赖，因此估计过程遵循“由粗到精、由盲到辅”的原则：先利用信号统计特征完成盲估计，再利用结构信息提取已知序列，最终借助已知序列实现逼近理论界的精确估计。

# 2 代表性论文概述

Starlink 系统在 Ku 波段（10.7~12.7 GHz）的下行信号采用正交频分复用（OFDM）体制，但其信号结构并未公开。Humphreys、Iannucci、Komodromos 与 Graff 在文献[1]（*IEEE Transactions on Aerospace and Electronic Systems*，2023）中提出了一种针对 Starlink 下行信号的盲信号识别方法：在不依赖运营方资料的条件下，利用地面接收的实测信号，基于 OFDM 循环前缀产生的循环平稳特性，逐步识别出子载波数、采样率、CP 长度、符号周期、信道划分与帧结构，并最终给出了每帧中主同步序列（PSS）与辅同步序列（SSS）的精确取值，可用于生成伪距测量。该工作从“零先验”出发逐级恢复出完整的信号结构与已知序列，是非合作信号源参数精确估计的典型范例；后续研究据此构建了信号仿真器^\[2\]^并分析了帧时序特性^\[3\]^。本文在文献[1]方法框架的基础上，结合 OFDM 盲参数估计^\[5\]^、循环平稳分析^\[6\]^、最大似然时频同步^\[4,7\]^、频率估计理论界^\[8\]^及高阶累积量调制识别^\[9\]^等方法阐述其原理，并通过仿真进行验证。

# 3 信号模型

## 3.1 OFDM 发射信号

设照射源采用 CP-OFDM 体制，采样率为 $F_s$，子载波数为 $N$，CP 长度为 $N_g$ 个样点。第 $m$ 个 OFDM 符号的离散时域表达式为

$$ s_m(n)=\frac{1}{\sqrt{N_{\mathrm{u}}}}\sum_{k\in\mathcal{K}}X_m(k)\,e^{\mathrm{j}2\pi kn/N},\quad n=-N_g,\cdots,N-1 $$ {#eq:ofdm}

式中，$\mathcal{K}$ 为有效子载波集合，$N_{\mathrm{u}}=|\mathcal{K}|$ 为有效子载波数，$X_m(k)$ 为第 $k$ 个子载波上的调制符号。由于 $n<0$ 部分是符号尾部的循环复制，每个符号的前 $N_g$ 个样点与其后 $N$ 个样点处的样点完全相同，这正是 OFDM 信号循环平稳特性的来源。符号的各时间参数满足

$$ T=\frac{N}{F_s},\quad T_g=\frac{N_g}{F_s},\quad T_{\mathrm{sym}}=T+T_g,\quad \Delta f=\frac{1}{T}=\frac{F_s}{N} $$ {#eq:tparam}

式中，$T$ 为有用符号长度，$T_g$ 为 CP 长度，$T_{\mathrm{sym}}$ 为符号周期，$\Delta f$ 为子载波间隔。若干符号构成一帧，帧首部为同步符号，帧尾部可能存在不发射信号的帧保护间隔 $T_{\mathrm{fg}}$，则帧周期为 $T_f=N_{\mathrm{sf}}T_{\mathrm{sym}}+T_{\mathrm{fg}}$，其中 $N_{\mathrm{sf}}$ 为每帧所含符号间隔数。图2给出了文献[1]~[3]所报道的 Starlink 下行信号帧结构、符号结构与信道频域结构。

## 3.2 接收信号

接收机以未知于发射端的采样率 $1/T_s$ 对信号进行采样，接收信号可表示为

$$ r(n)=h\,s(nT_s-\tau_0)\,e^{\mathrm{j}(2\pi f_d nT_s+\varphi_0)}+w(n) $$ {#eq:rx}

式中，$h$ 为信道增益，$\tau_0$ 为时延，$\varphi_0$ 为初始相位，$w(n)$ 为方差 $\sigma_w^2$ 的复高斯白噪声，$f_d=\Delta f_c+f_D$ 为总频偏，由收发本振频差 $\Delta f_c$ 与多普勒频移 $f_D=-f_c\dot{R}(t)/c$ 共同构成，$f_c$ 为载频，$c$ 为光速，$\dot{R}(t)$ 为卫星与接收站间的距离变化率。对于 Ku 波段低轨卫星，若 $\dot{R}=5$ km/s、$f_c=11.7$ GHz，则 $|f_D|\approx195$ kHz，已接近子载波间隔 234.375 kHz，因此频偏估计必须同时解决小数倍与整数倍两部分。参数估计的任务是：在 $F_s$、$N$、$N_g$、$T_f$、$N_{\mathrm{sf}}$、$T_{\mathrm{fg}}$、同步序列以及 $\tau_0$、$f_d$ 均未知的条件下，由 $r(n)$ 逐级恢复上述全部参数。

# 4 参数精确估计原理

## 4.1 总体估计流程

信号源参数精确估计的总体流程如图1所示，分为三个阶段：①利用功率谱、CP 自相关与循环自相关等二阶统计特征盲估计信号层参数，并借助整数约束确定采样率与子载波数；②利用长时延相关与功率折叠识别帧结构，并通过跨帧相干平均提取同步符号；③先以非数据辅助方法估计符号定时与小数倍频偏并解整数倍模糊，再利用同步符号进行多帧相干的数据辅助精确估计，最后完成调制方式识别。

![图1 非合作OFDM信号源参数精确估计总体流程](figures/fig1_flow.png){width=10.5cm}

## 4.2 占用带宽与频偏粗估计

采用 Welch 方法（分段加窗、周期图平均）估计接收信号的功率谱 $\hat{P}(f)$。分别求取带内平均功率 $\bar{P}_{\mathrm{in}}$ 与带外噪声基底 $\bar{P}_{\mathrm{out}}$，以二者的半功率点作为门限，搜索功率谱上升沿与下降沿的穿越频率 $\hat{f}_{\mathrm{L}}$ 与 $\hat{f}_{\mathrm{H}}$，得到占用带宽

$$ \hat{B}=\hat{f}_{\mathrm{H}}-\hat{f}_{\mathrm{L}},\qquad \hat{P}(\hat{f}_{\mathrm{L}})=\hat{P}(\hat{f}_{\mathrm{H}})=\frac{1}{2}\left(\bar{P}_{\mathrm{in}}+\bar{P}_{\mathrm{out}}\right) $$ {#eq:bw}

为获得频偏的粗估计，可利用信道内部具有明确位置的频谱特征。文献[1]发现 Starlink 每个信道中心有 4 个不承载能量的空子载波（中心空隙），且信道中心频率比空隙中点高 $\Delta f/2$。因此，检测功率谱在频带中部低于门限的连续区间，取其中点 $\hat{f}_{\mathrm{gap}}$，即可得到频偏粗估计 $\hat{f}_d^{(0)}=\hat{f}_{\mathrm{gap}}+\Delta f/2$。中心空隙的边沿陡峭，其定位精度可达数 kHz，远小于 $\Delta f/2$，足以为后续整数倍频偏解模糊提供依据。

## 4.3 基于CP自相关的有用符号长度估计

定义接收信号的时间平均自相关函数

$$ \bar{R}_r(\tau)=\frac{1}{L}\sum_{n=0}^{L-1}r(n)\,r^{\ast}(n+\tau) $$ {#eq:acf}

由于 CP 是符号尾部的复制，当时延 $\tau$ 恰好等于有用符号长度对应的样点数 $N$ 时，CP 段与其原始段对齐而相关；对于其他非零时延，不同子载波上的独立调制符号使相关值趋于零。其统计期望近似为

$$ \mathrm{E}\left[\bar{R}_r(\tau)\right]\approx\begin{cases}\sigma_s^2+\sigma_w^2, & \tau=0\\ \dfrac{N_g}{N+N_g}\,\sigma_s^2\,e^{-\mathrm{j}2\pi f_d NT_s}, & \tau=\pm N\\ 0, & \text{其他}\end{cases} $$ {#eq:acfexp}

式中，$\sigma_s^2$ 为信号功率。可见，$|\bar{R}_r(\tau)|$ 在 $\tau=N$ 处出现孤立峰值，且峰值幅度不受频偏影响。于是，在排除零时延附近相关主瓣（$\tau>\tau_{\min}$）后搜索 $|\bar{R}_r(\tau)|$ 的峰值位置 $\hat{\tau}_{\mathrm{pk}}$，即得有用符号长度 $\hat{T}=\hat{\tau}_{\mathrm{pk}}T_s$ 及子载波间隔 $\Delta\hat{f}=1/\hat{T}$。

## 4.4 基于循环平稳特性的符号周期与CP长度估计

CP 结构使得乘积序列 $z(n)=r(n)r^{\ast}(n+\hat{N})$ 在每个符号的 CP 段内具有非零均值，在其余部分均值为零，因此 $z(n)$ 的均值以符号周期为周期变化，即信号具有二阶循环平稳性^\[6\]^。其循环自相关函数定义为

$$ R_r^{\alpha}(\tau)=\lim_{L\to\infty}\frac{1}{L}\sum_{n=0}^{L-1}r(n)\,r^{\ast}(n+\tau)\,e^{-\mathrm{j}2\pi\alpha nT_s} $$ {#eq:caf}

在 $\tau=\hat{N}$ 处，$|R_r^{\alpha}(\hat{N})|$ 仅在循环频率 $\alpha=k/T_{\mathrm{sym}}$（$k$ 为整数）处出现谱线。工程上可对 $z(n)$ 进行快速傅里叶变换得到循环自相关谱，检测各次谐波谱线位置 $\hat{\alpha}_k$，并采用最小二乘拟合 $\hat{\alpha}_k=k/T_{\mathrm{sym}}$，得到

$$ \hat{T}_{\mathrm{sym}}=\frac{\sum_k k^2}{\sum_k k\,\hat{\alpha}_k},\qquad \hat{T}_g=\hat{T}_{\mathrm{sym}}-\hat{T} $$ {#eq:tsym}

## 4.5 采样率与子载波数的整数约束判定

$\hat{T}$ 与式({{eq:tsym}})给出的均是时间量，而采样率 $F_s$、子载波数 $N$ 与 CP 样点数 $N_g$ 需联合确定。由式({{eq:tparam}})可知 $F_s=N/T$。工程中 $N$ 通常取 2 的整数次幂，且 OFDM 信号的占用带宽不超过采样率，于是可按如下准则判定：

$$ \hat{N}=\min\left\{2^{p}:\ \frac{2^{p}}{\hat{T}}\ge(1-\eta)\hat{B}\right\},\quad \hat{F}_s=\frac{\hat{N}}{\hat{T}},\quad \hat{N}_g=\mathrm{round}\left(\hat{T}_g\hat{F}_s\right) $$ {#eq:integer}

式中，$\eta$ 为考虑带宽估计误差的容差系数（本文取 0.02）。整数约束的意义在于：$\hat{T}_g$ 的微小估计误差经取整后被完全消除，此后即可由 $(\hat{N}+\hat{N}_g)/\hat{F}_s$ 反算出精确的符号周期，实现参数精度的“跃升”。由5.1节可知，Starlink 信号的各参数之间同样满足这种严格的整数关系。

## 4.6 帧结构识别与同步符号提取

**（1）帧周期估计。** 同步符号在每一帧中重复出现，而数据符号逐帧随机变化，因此在帧周期的可能范围 $[\tau_1,\tau_2]$ 内搜索 $|\bar{R}_r(\tau)|$ 的峰值，即得帧周期估计 $\hat{T}_f$。由于同步符号仅占一帧的很小比例，该峰值较弱，需利用多帧数据进行长时间平均。

**（2）帧保护与每帧符号数识别。** 以 $\hat{L}_f=\hat{T}_f/T_s$ 为模对瞬时功率进行折叠平均：

$$ \bar{p}(n)=\frac{1}{K}\sum_{l=0}^{K-1}\left|r(n+l\hat{L}_f)\right|^2,\quad n=0,1,\cdots,\hat{L}_f-1 $$ {#eq:fold}

折叠后噪声起伏被压低，帧保护间隔表现为一段明显的功率凹陷，其宽度即 $\hat{T}_{\mathrm{fg}}$，其结束位置即帧起点 $\hat{n}_0$，进而得到每帧符号数 $\hat{N}_{\mathrm{sf}}=\mathrm{round}\left[(\hat{T}_f-\hat{T}_{\mathrm{fg}})/\hat{T}_{\mathrm{sym}}\right]$。

**（3）同步符号提取。** 在帧起点已知的条件下，对各帧首部的同步符号段进行频偏补偿后相干平均：

$$ \hat{p}(i)=\frac{1}{K}\sum_{l=0}^{K-1}r(\hat{n}_0+i+l\hat{L}_f)\,e^{-\mathrm{j}2\pi\hat{f}_d(\hat{n}_0+i+l\hat{L}_f)T_s},\quad i=0,\cdots,L_p-1 $$ {#eq:avg}

式中，$L_p$ 为同步符号长度。相干平均使信噪比提高 $10\lg K$ dB。若存在残余频偏 $\delta f$，则帧间相位旋转导致相干增益损失，提取序列与真实序列的相关系数为

$$ \rho_K=\frac{|D_K|}{\sqrt{|D_K|^2+1/(K\gamma)}},\qquad D_K=\frac{\sin(\pi K\,\delta f\,T_f)}{K\sin(\pi\,\delta f\,T_f)} $$ {#eq:rho}

式中，$\gamma$ 为单样点信噪比。式({{eq:rho}})表明频偏估计精度对同步符号提取具有决定性作用；提取结果还可经子载波符号判决得到无噪声的同步序列。

## 4.7 时频参数的两级精确估计

**（1）非数据辅助的CP最大似然估计。** 在符号参数已知的条件下，van de Beek 等^\[4\]^给出了基于 CP 的符号定时 $\theta$ 与归一化小数倍频偏 $\varepsilon=f_d/\Delta f$ 的联合最大似然估计。其对数似然函数为

$$ \Lambda(\theta,\varepsilon)=\left|\gamma(\theta)\right|\cos\left(2\pi\varepsilon+\angle\gamma(\theta)\right)-\rho\,\Phi(\theta) $$ {#eq:ml}

其中

$$ \gamma(\theta)=\sum_{n=\theta}^{\theta+N_g-1}r(n)\,r^{\ast}(n+N),\qquad \Phi(\theta)=\frac{1}{2}\sum_{n=\theta}^{\theta+N_g-1}\left(|r(n)|^2+|r(n+N)|^2\right) $$ {#eq:gamma}

式中，$\rho=\gamma/(\gamma+1)$ 为 CP 段的相关系数。对 $M$ 个连续符号的相关量进行累加，记 $\gamma_M(\theta)=\sum_{m=0}^{M-1}\gamma(\theta+mN_{\mathrm{sym}})$，$\Phi_M(\theta)$ 同理，则估计量为

$$ \hat{\theta}=\arg\max_{\theta}\left\{|\gamma_M(\theta)|-\rho\,\Phi_M(\theta)\right\},\qquad \hat{\varepsilon}=-\frac{1}{2\pi}\angle\gamma_M(\hat{\theta}) $$ {#eq:mlest}

该方法无需任何已知序列，但仅利用了 CP 段的信息，且 $\hat{\varepsilon}$ 的无模糊范围为 $-0.5<\hat{\varepsilon}\le0.5$，即只能估计频偏的小数倍部分。

**（2）整数倍频偏解模糊。** 结合功率谱粗估计 $\hat{f}_d^{(0)}$，整数倍频偏及完整频偏估计为

$$ \hat{q}=\mathrm{round}\left(\frac{\hat{f}_d^{(0)}}{\Delta\hat{f}}-\hat{\varepsilon}\right),\qquad \hat{f}_d^{(1)}=(\hat{\varepsilon}+\hat{q})\,\Delta\hat{f} $$ {#eq:intcfo}

**（3）同步符号辅助的多帧相干精估计。** 获得同步符号 $p(i)$ 后，首先在帧起点附近搜索互相关峰值以精确定时：

$$ \hat{n}_0=\arg\max_{n}\left|\sum_{i=0}^{L_p-1}r(n+i)\,p^{\ast}(i)\,e^{-\mathrm{j}2\pi\hat{f}_d^{(1)}(n+i)T_s}\right| $$ {#eq:datiming}

然后对 $K$ 帧的去调制序列 $z_l(i)=r(\hat{n}_0+l\hat{L}_f+i)\,p^{\ast}(i)\,e^{-\mathrm{j}2\pi\hat{f}_d^{(1)}(\hat{n}_0+l\hat{L}_f+i)T_s}$ 进行相干搜索，得到残余频偏的最大似然估计：

$$ \hat{f}_d=\hat{f}_d^{(1)}+\arg\max_{\delta f}\left|\sum_{l=0}^{K-1}\sum_{i=0}^{L_p-1}z_l(i)\,e^{-\mathrm{j}2\pi\,\delta f\,(i+l\hat{L}_f)T_s}\right| $$ {#eq:mf}

该估计量的克拉美-罗界为^\[8\]^

$$ \mathrm{CRB}(f_d)=\frac{1}{2\gamma\,(2\pi T_s)^2\sum_{n\in\Omega}|p(n)|^2\,(n-\bar{n})^2} $$ {#eq:crb}

式中，$\Omega$ 为参与估计的全部样点下标集合，$\bar{n}$ 为其能量加权中心。当 $K\gg1$ 且 $|p(n)|^2$ 的均值为 1 时，有

$$ \mathrm{CRB}(f_d)\approx\frac{3}{2\pi^2\,\gamma\,L_p\,K^3\,T_f^2} $$ {#eq:crbapprox}

可见，多帧相干估计的方差随 $K^{-3}$ 下降，这是因为观测基线由单帧的数微秒扩展到 $K$ 个帧周期。需要注意，帧间相干搜索存在以 $1/T_f$ 为间隔的模糊，故要求 $\hat{f}_d^{(1)}$ 的误差小于 $1/(2T_f)$（本例为 375 Hz），这一要求可由多符号累加的 CP 最大似然估计保证。此外，在实际低轨卫星场景中，当相干时间较长时还需联合估计多普勒变化率，将式({{eq:mf}})扩展为频率—频率变化率二维搜索。

## 4.8 子载波调制方式识别

完成时频同步后，对每个符号进行 FFT 即可得到各子载波上的调制符号 $Y$。利用高阶累积量对载波相位不敏感、对高斯噪声免疫的特性^\[9\]^，定义 $M_{pq}=\mathrm{E}\left[Y^{p-q}(Y^{\ast})^{q}\right]$，则归一化四阶累积量为

$$ \tilde{C}_{40}=\frac{|M_{40}-3M_{20}^2|}{(M_{21}-\hat{\sigma}_w^2)^2},\qquad \tilde{C}_{42}=\frac{M_{42}-|M_{20}|^2-2M_{21}^2}{(M_{21}-\hat{\sigma}_w^2)^2} $$ {#eq:cum}

式中，噪声功率 $\hat{\sigma}_w^2$ 可由中心空隙处的空子载波直接估计。QPSK、8PSK 与 16QAM 的理论值 $(\tilde{C}_{40},\tilde{C}_{42})$ 分别为 $(1,-1)$、$(0,-1)$ 与 $(0.68,-0.68)$，据此即可完成调制方式判别。

# 5 结果与分析

## 5.1 文献报道的Starlink信号识别结果

文献[1]利用上述盲识别思路对 Starlink Ku 波段下行实测信号进行了分析，后续研究^\[2,3\]^对其结果进行了确认和补充，主要参数汇总于表1。其中，下行频段划分为 8 个信道，相邻信道间以 10 MHz 保护带隔开；最低的两个信道在文献[1]观测期间处于空闲状态，与避开 10.6~10.7 GHz 射电天文频段有关。

Table: 表1 文献[1]~[3]报道的Starlink Ku波段下行信号参数

| 参数 | 符号 | 取值 |
|:------|:----:|:------|
| 频段 / 信道数 | — | 10.7~12.7 GHz / 8 |
| 信道带宽 / 信道间隔 | $F_s$ / — | 240 MHz / 250 MHz |
| 子载波数 / 中心空子载波数 | $N$ / — | 1024 / 4 |
| 子载波间隔 | $\Delta f$ | 234.375 kHz |
| 有用符号长度 | $T$ | 64/15 μs ≈ 4.267 μs |
| CP 长度 | $N_g$ / $T_g$ | 32 / 2/15 μs ≈ 0.133 μs |
| 符号周期 | $T_{\mathrm{sym}}$ | 4.4 μs |
| 帧周期 | $T_f$ | 1/750 s ≈ 1.333 ms |
| 每帧符号间隔数 | $N_{\mathrm{sf}}$ | 302（首部为 PSS、SSS） |
| 帧保护 | $T_{\mathrm{fg}}$ | 68/15 μs ≈ 4.533 μs |

![图2 Starlink下行信号结构示意（依据文献[1]~[3]绘制）](figures/fig2_frame.png){width=11cm}

由表1可以验证参数间的自洽关系：240 MHz ÷ 1024 = 234.375 kHz，(1024 + 32) ÷ 240 MHz = 4.4 μs，302 × 4.4 μs + 68/15 μs = 1333.33 μs = 1/750 s。这种严格的整数关系正是整数约束判定得以成立的基础。

## 5.2 仿真条件

依据表1参数构建仿真信号：信号结构为 $N=1024$、$N_g=32$、$N_{\mathrm{sf}}=302$；为模拟“非合作”条件，接收采样率设为 300 MHz（不同于发射端的 240 MHz，即估计器不预知 $F_s$）；频偏 $f_d=186.4$ kHz（约 0.795 个子载波间隔）；帧保护期间不发射信号，同步符号以固定的随机 QPSK 符号代替实际 PSS/SSS，数据子载波为随机 QPSK 调制。盲估计采用 16 帧（约 21.3 ms）数据，单样点信噪比（SNR）为 0 dB；时频同步性能采用 300 次（多帧估计为 200 次）蒙特卡洛试验统计。

## 5.3 信号层参数盲估计结果

图3为接收信号的功率谱。由半功率门限测得占用带宽为 240.00 MHz（误差约 2 kHz）；频带中部可清晰观察到宽约 0.93 MHz 的中心空隙（理论值 $4\Delta f=0.9375$ MHz），由此得到频偏粗估计 187.28 kHz，误差 0.88 kHz，远小于 $\Delta f/2=117.2$ kHz。

![图3 接收信号功率谱及中心空隙（SNR = 0 dB）](figures/fig3_psd.png){width=10.5cm}

图4(a)中 CP 自相关函数在 $\tau=1280$ 个接收样点（4.2667 μs）处出现孤立峰值，对应 $\Delta\hat{f}=234.375$ kHz；图4(b)中循环自相关谱线等间隔出现在约 227.25 kHz 的整数倍处，拟合得 $\hat{T}_{\mathrm{sym}}=4.4004$ μs、$\hat{T}_g=0.1337$ μs。按式({{eq:integer}})判定：$N=512$ 对应的采样率 120 MHz 小于占用带宽，被排除；$N=1024$ 为满足约束的最小值，得 $\hat{F}_s=240$ MHz，此时 $\hat{T}_g\hat{F}_s=32.09$，取整得 $\hat{N}_g=32$，与真值一致，并可反算出精确的 $T_{\mathrm{sym}}=4.4$ μs，循环谱估计中约 0.01% 的偏差被完全消除。

![图4 符号参数盲估计结果：(a) CP自相关函数；(b) 循环自相关谱](figures/fig4_cp_cyclic.png){width=11cm}

## 5.4 帧结构识别结果

图5(a)中长时延自相关函数在 1.3333 ms 及其两倍处出现明显峰值（约为噪声基底最大值的 2.2 倍），得 $\hat{T}_f=1/750$ s。图5(b)中功率折叠后帧保护表现为宽约 4.52 μs 的功率凹陷，进而得 $\hat{N}_{\mathrm{sf}}=302$，再按整数关系反算出 $\hat{T}_{\mathrm{fg}}=4.533$ μs。功率折叠给出的帧起点误差为 5 个样点，经式({{eq:datiming}})精确定时后误差为 0。

![图5 帧结构识别结果：(a) 长时延自相关；(b) 帧同步功率折叠](figures/fig5_frame.png){width=11cm}

## 5.5 时频同步精度

由图6(a)可见，CP 最大似然估计的精度随累加符号数 $M$ 增加而显著提高，0 dB 时 $M=1$、10、100 对应的频偏 RMSE 分别约为 17.8 kHz、2.2 kHz 和 0.69 kHz；单帧同步符号辅助估计的 RMSE 与 CRB 基本重合（0 dB 时约 0.88 kHz）。由图6(b)可见，$M=100$ 时符号定时在 −5 dB 及以上全部正确。

![图6 时频同步性能：(a) 频偏估计精度；(b) 符号定时正确概率（误差≤1个样点）](figures/fig6_sync.png){width=11cm}

图7(a)为 SNR = −10 dB 时跨帧相干平均提取同步符号的效果：无残余频偏时，相关系数由单帧的 0.30 提高到 256 帧的 0.98，与式({{eq:rho}})一致；残余频偏为 2 Hz 时，$K>128$ 后性能下降；残余频偏为 10 Hz 时，$K>32$ 后相干增益迅速丧失，说明长时间相干处理要求亚赫兹至数赫兹量级的频偏精度。图7(b)为 SNR = 0 dB 时多帧相干数据辅助估计的 RMSE：$K=1$ 时约 884 Hz，$K=2$ 时骤降至 2.3 Hz，$K=16$ 与 $K=64$ 时分别为 0.090 Hz 与 0.011 Hz，均与 CRB 吻合，验证了式({{eq:crbapprox}})所示的 $K^{-3/2}$ 改善规律。

![图7 跨帧相干处理性能：(a) 同步符号提取（实线为理论值）；(b) 多帧相干频偏估计](figures/fig7_multiframe.png){width=11cm}

## 5.6 调制识别结果

完成时频同步补偿与基于 SSS 的公共相位校正后，对数据子载波计算归一化四阶累积量。表2为 SNR = 10 dB 时 20 次试验的统计结果，三种调制方式的估计值均与理论值接近，可明确区分。

Table: 表2 不同调制方式的归一化四阶累积量（SNR = 10 dB）

| 调制方式 | $\tilde{C}_{40}$ 理论值 | $\tilde{C}_{40}$ 估计值 | $\tilde{C}_{42}$ 理论值 | $\tilde{C}_{42}$ 估计值 |
|:----:|:----:|:----:|:----:|:----:|
| QPSK | 1.00 | {{mod:qpsk:C40}} | −1.00 | {{mod:qpsk:C42}} |
| 8PSK | 0.00 | {{mod:8psk:C40}} | −1.00 | {{mod:8psk:C42}} |
| 16QAM | 0.68 | {{mod:16qam:C40}} | −0.68 | {{mod:16qam:C42}} |

## 5.7 估计结果汇总

SNR = 0 dB 时由 16 帧接收数据得到的参数估计结果汇总于表3。经整数约束与多帧相干处理后，全部结构参数均被准确恢复，频偏估计误差仅为 0.05 Hz。

Table: 表3 信号源参数估计结果汇总（SNR = 0 dB）

| 参数 | 真值 | 盲估计值 | 约束/精估计后 |
|:------|:----:|:----:|:----:|
| 符号周期 $T_{\mathrm{sym}}$ | 4.4 μs | 4.4004 μs | 4.4 μs |
| 采样率 $F_s$ / 子载波数 $N$ | 240 MHz / 1024 | — | 240 MHz / 1024 |
| CP 样点数 $N_g$ | 32 | 32.09 | 32 |
| 帧周期 $T_f$ | 1.3333 ms | 1.3333 ms | — |
| 帧保护 $T_{\mathrm{fg}}$ | 4.533 μs | 4.52 μs | 4.533 μs |
| 每帧符号数 $N_{\mathrm{sf}}$ | 302 | 302 | — |
| 帧起点误差 | 0 | 5 样点 | 0 |
| 频偏 $f_d$ | 186 400 Hz | 187 283 Hz（粗）/ 186 250 Hz（CP-ML） | 186 400.05 Hz |

# 6 结论及在本项目中的应用

本文以文献[1]对 Starlink 下行信号的盲识别为主线，阐述了非合作信号源参数精确估计的原理：利用 CP 结构产生的自相关与循环平稳特征盲估计符号级时间参数；利用采样率、子载波数、CP 长度与帧长之间的整数关系，将带误差的时间估计转化为精确的结构参数；进而提取同步符号，借助多帧相干的数据辅助估计使频偏精度逼近 CRB。

在本项目中，该模块位于多辐射源信号分选之后、分布式相参融合之前，其输出可用于：（1）重构纯净参考信号；（2）为多源串扰抑制提供各信号源的时频结构；（3）为多信号源间及分布式接收站间的时间、频率与相位对齐提供高精度参数，支撑三维相参融合中的长时间相干积累。后续需进一步研究多径信道、多普勒变化率及多星同频叠加条件下的估计方法，并开展实测数据验证。

# 参考文献

::: {custom-style="参考文献"}
[1] Humphreys T E, Iannucci P A, Komodromos Z, Graff A M. Signal structure of the Starlink Ku-band downlink[J]. IEEE Transactions on Aerospace and Electronic Systems, 2023. (arXiv: 2210.11578)

[2] Komodromos Z, et al. Signal simulator for Starlink Ku-band downlink[R/OL]. Radionavigation Laboratory, The University of Texas at Austin.

[3] Qin W, et al. Timing properties of the Starlink Ku-band downlink[EB/OL]. arXiv: 2501.05302, 2025.

[4] van de Beek J J, Sandell M, Börjesson P O. ML estimation of time and frequency offset in OFDM systems[J]. IEEE Transactions on Signal Processing, 1997, 45(7): 1800-1805.

[5] Le Nir V, van Waterschoot T, Moonen M, Duplicy J. Blind CP-OFDM and ZP-OFDM parameter estimation in frequency selective channels[J]. EURASIP Journal on Wireless Communications and Networking, 2009, 2009: 315765.

[6] Gardner W A. Exploitation of spectral redundancy in cyclostationary signals[J]. IEEE Signal Processing Magazine, 1991, 8(2): 14-36.

[7] Schmidl T M, Cox D C. Robust frequency and timing synchronization for OFDM[J]. IEEE Transactions on Communications, 1997, 45(12): 1613-1621.

[8] Rife D C, Boorstyn R R. Single-tone parameter estimation from discrete-time observations[J]. IEEE Transactions on Information Theory, 1974, 20(5): 591-598.

[9] Swami A, Sadler B M. Hierarchical digital modulation classification using cumulants[J]. IEEE Transactions on Communications, 2000, 48(3): 416-429.
:::
