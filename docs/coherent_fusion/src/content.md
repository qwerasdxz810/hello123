---
title: 2发5收分布式探测系统相参融合检测算法方案
subtitle: ——基于被动MIMO雷达与空间相参多基地检测理论的10链路信号级融合
---

::: {custom-style="提要"}
**内容提要：**针对由2个非合作信号源与5个接收站构成的分布式探测系统（每站配置参考天线与监视天线，共10条双基地链路），本文以被动MIMO雷达网络集中式检测^\[1,2\]^与空间相参/非相参多基地检测理论^\[4\]^为主要依据，给出10条链路回波的相参融合检测方案。方案的要点是：各接收站以“本站接收的该信号源直达波”作为相位基准完成互模糊处理，使信号源与接收站的载频、初相和相位噪声自动抵消，从而**无需两个信号源之间的时间同步与相位锁定**；融合中心在目标状态空间先进行非相参粗检测，再按亚波长网格进行相位补偿与相参精搜索，并按目标散射相参性自适应选择相参或非相参支路。文中给出了实现相参所需的两信号源条件（照射同时性、载频差、视角差、波形与相位稳定性）及接收站条件（频率基准、时间同步、站址精度与通道标定），以及各站回波处理流程。仿真表明：10条链路相参融合后的输出信噪比较单链路平均值提高 {{S:gain/tc_gain_db|.2f}} dB（理论值10 dB）；若不保留直达波相位基准或不进行通道相位标定，相参增益基本丧失；点目标条件下，$P_d=0.9$、$P_{fa}=10^{-6}$ 所需单链路平均信噪比由最佳单链路检测的 {{T:pd/req_snr_db/point/single|.1f}} dB 降至 {{T:pd/req_snr_db/point/coh|.1f}} dB，较非相参融合再降低 {{T:derived/coh_vs_nc_db|.1f}} dB；当目标尺寸超过约 1 m 时，散射去相关使非相参融合更优，相参/非相参双支路检测在各种情况下均接近两者中的较优者。
:::

# 1 背景与需求

## 1.1 系统组成

本项目采用“2发5收”分布式探测体制：以两个非合作信号源（广播、通信或卫星下行信号，记为T1、T2）作为照射源，在不同站址部署5个接收站（R1~R5）。每个接收站配置两路接收通道：参考天线对准信号源，接收直达波作为参考信号；监视天线对准监视空域，接收飞行目标的散射回波。每个“信号源—接收站”组合构成一条双基地链路，系统共有 $2\times5=10$ 条链路，记为 T$i$R$j$（$i=1,2$；$j=1,\cdots,5$），链路序号 $l=5(i-1)+j$。图1为本文仿真所采用的构型：两个信号源位于接收站群西南方向约15 km处，5个接收站分布在约3 km范围内，目标为距接收站约28 km、高度1.5 km的小型无人机。

![图1 2发5收分布式探测系统构型（仿真场景）](figures/fig_geometry.png){width=14cm}

## 1.2 相参融合的需求与难点

非合作信号源的发射功率与波形均不受控，单条链路对小型无人机等微弱飞行目标的输出信噪比往往不足以完成检测。若能将10条链路的回波在信号层面相参合成，理想情况下融合输出信噪比等于各链路信噪比之和，在链路信噪比相近时可提高约 $10\lg10=10$ dB，这正是项目“时域×多源×多站三维相参融合”中“多信号源间相参”与“分布式接收站间相参”的核心内容。与单站雷达的脉冲间相参积累相比，分布式多源多站相参融合面临以下难点：

（1）信号源非合作：两个信号源之间、信号源与接收站之间均不存在时间与相位同步，发射载频偏差、初相及相位噪声未知；

（2）接收站分布式部署：各站本振与时钟相互独立，站址相距数公里，各链路回波相位随目标位置以波长为周期剧烈变化；

（3）目标散射的空间与频率去相关：不同链路从不同视角、以不同载频照射目标，目标的复散射系数不一定相同；

（4）相参处理需要亚波长级的目标位置假设：几何相位以波长（UHF频段约0.46 m）为周期变化，而距离分辨单元约43 m。

本方案的目标是：给出10链路相参融合检测算法，明确实现相参所需满足的条件（特别是两个信号源之间的条件）与各接收站回波的处理流程，并以仿真实验验证其性能与适用边界。

# 2 参考文献与技术路线

## 2.1 相关研究概况

**被动MIMO雷达与多基地被动雷达检测。**Hack、Patton、Himed与Saville^\[1,2\]^针对由多个非合作照射源和多个双通道（参考/监视）接收站构成的被动MIMO雷达网络，建立了参考通道与监视通道联合的信号模型，分别推导了存在直达波参考信号与不存在直达波参考信号两种情况下的集中式广义似然比检测器（GLRT），论证了在融合中心对全部“发射—接收”通道联合检测的优势。Liu、Li与Himed^\[3\]^针对单照射源、多接收站的被动多基地雷达，提出了需已知噪声功率的广义典型相关检测器与具有恒虚警特性的GLRT检测器。上述工作构成了“多源多站被动雷达集中式检测”的理论框架，这类工作通常将各“发射—接收”对的目标散射系数视为相互独立的未知量，链路间实际上以非相参方式合并。

**空间相参与空间非相参多基地检测。**Derham等^\[4\]^由最优检测器出发推导了多基地雷达的模糊函数，指出最优检测器的形式取决于目标起伏在各接收站之间的空间相参性：空间相参时各通道匹配滤波输出相参求和，空间非相参时各通道输出能量求和；所得模糊函数可在二维/三维的位置—速度空间评估任意波形与布站的分辨性能。Fishler等^\[5\]^与Haimovich等^\[6\]^针对天线广泛分布的MIMO雷达指出：当收发站间距足够大时目标散射在各通道间去相关，最优检测器退化为非相参处理并获得空间分集增益；而在相参处理条件下，可获得远超波形分辨率的定位精度。Godrich等^\[7\]^证明相参处理的定位克拉美-罗界与载频成反比（非相参时与信号有效带宽成反比），并在文献[8]中分析了相位同步误差对相参MIMO雷达定位性能的影响。Gogineni等^\[9\]^以UMTS信号为例分析了被动多基地雷达在相参与非相参两种模式下的模糊函数。

**分布式相参合成与同步。**分布式孔径相参合成雷达通过估计各单元雷达间的时延差与相位差（相参参数）实现多孔径相参合成^\[10,11\]^；万显荣等^\[12\]^针对分布式数字广播电视外辐射源雷达，提出了基于GPS授时的站间时间与频率同步方案并完成了外场测试；Zheng等^\[13\]^在GNSS外辐射源雷达中将多颗卫星信号相参积累用于成像，相对多图像非相参融合获得了更高的增益。

**单站信号处理。**参考信号提纯、直达波与多径杂波对消（ECA）及距离—多普勒处理可参考文献[14,15]；长时间相参积累中的距离走动问题可借鉴Radon-Fourier变换（RFT）思想^\[16\]^；多基地定位与双基地雷达方程见文献[17,18,21]。

## 2.2 方案所依据的核心论文

本方案以文献[1,2]的被动MIMO雷达网络模型与集中式检测框架为基础，引入文献[4]的空间相参检测模型实现链路间相参合成，并结合文献[5-8]给出的相参条件与相位误差分析、文献[10,11]的相参参数估计思想（用于相位标校），形成适用于本项目的10链路相参融合检测算法，见表1。

Table: 表1 核心参考论文及其在本方案中的作用

| 文献 | 主要内容 | 在本方案中的作用 |
|:------|:------|:------|
| Hack等^\[1,2\]^ | 多照射源、多双通道接收站的被动MIMO雷达网络模型与集中式GLRT | 2发5收10链路的信号模型、集中式融合检测框架 |
| Derham等^\[4\]^ | 空间相参/非相参多基地最优检测器及其位置—速度模糊函数 | 目标状态空间中的相参融合统计量与非相参融合统计量 |
| Fishler等^\[5\]^、Haimovich等^\[6\] | 广域分布MIMO雷达的散射去相关与非相参分集 | 目标散射相参条件、非相参支路 |
| Godrich等^\[7,8\]^ | 相参定位精度与相位同步误差灵敏度 | 相位误差容限、波长级相参精定位 |
| 分布式孔径相参合成^\[10,11\]^ | 多孔径相参参数估计与相参合成 | 基于强目标的链路相位自校准 |
| 万显荣等^\[12\]^ | 分布式外辐射源雷达站间时频同步 | 接收站时频基准设计 |

## 2.3 技术路线

方案采用“站内自同步相参积累 + 中心状态空间相参融合”的两级结构（详见第5、6章）：

（1）**站内**：每个接收站对两个信号源分别完成多源分离、参考信号提纯、ECA杂波对消与互模糊函数（CAF）处理，得到2条链路的复数距离—多普勒图。关键在于以本站接收的该信号源直达波作为相位基准，使信号源与本振的相位不确定性在CAF中自动抵消；

（2）**中心**：融合中心在目标状态空间（位置、速度）中，按假设的目标状态读取10条链路的复数输出，先进行非相参粗检测，再进行几何相位补偿、加权与亚波长网格的相参精搜索；

（3）**自适应**：依据链路间散射相参性，在10链路全相参、源间相参、站间相参与非相参之间选择融合方式，或采用相参/非相参双支路并行检测，以兼顾点状目标的相参增益与扩展目标的分集增益。

# 3 信号模型

## 3.1 收发几何与链路参数

设信号源 $i$、接收站 $j$ 与目标的位置分别为 $\mathbf{t}_i$、$\mathbf{r}_j$ 与 $\mathbf{p}(t)=\mathbf{p}+\mathbf{v}(t-t_c)$，其中 $t_c$ 为相参处理间隔（CPI）中心时刻，$\mathbf{p}$、$\mathbf{v}$ 为该时刻目标的位置与速度，目标状态记为 $\boldsymbol{\theta}=(\mathbf{p},\mathbf{v})$。被动雷达测量的是回波相对直达波的双基地距离差，链路 $l=(i,j)$ 的双基地距离差为

$$ R_l(t)=\left\|\mathbf{p}(t)-\mathbf{t}_i\right\|+\left\|\mathbf{p}(t)-\mathbf{r}_j\right\|-\left\|\mathbf{t}_i-\mathbf{r}_j\right\| $$ {#eq:range}

相应的双基地多普勒频率为

$$ f_l=-\frac{\dot{R}_l(t_c)}{\lambda_i}=-\frac{\mathbf{v}^{\mathrm{T}}\left(\mathbf{u}_{\mathrm{T},i}+\mathbf{u}_{\mathrm{R},j}\right)}{\lambda_i},\qquad \mathbf{u}_{\mathrm{T},i}=\frac{\mathbf{p}-\mathbf{t}_i}{\left\|\mathbf{p}-\mathbf{t}_i\right\|},\quad \mathbf{u}_{\mathrm{R},j}=\frac{\mathbf{p}-\mathbf{r}_j}{\left\|\mathbf{p}-\mathbf{r}_j\right\|} $$ {#eq:doppler}

式中，$\lambda_i=c/f_i$ 为信号源 $i$ 的波长。为描述相位随目标位置的变化，定义链路波数矢量（单位：周/米）

$$ \mathbf{k}_l=\frac{\mathbf{u}_{\mathrm{T},i}+\mathbf{u}_{\mathrm{R},j}}{\lambda_i},\qquad \frac{2\pi R_l(\mathbf{p}+\delta\mathbf{p})}{\lambda_i}\approx\frac{2\pi R_l(\mathbf{p})}{\lambda_i}+2\pi\mathbf{k}_l^{\mathrm{T}}\delta\mathbf{p} $$ {#eq:wavenumber}

$\mathbf{k}_l$ 沿双基地角平分线方向，模值为 $2\cos(\beta_l/2)/\lambda_i$，$\beta_l$ 为双基地角。不同链路波数矢量之差 $\Delta\mathbf{k}_{ll'}=\mathbf{k}_l-\mathbf{k}_{l'}$ 同时决定了链路间相位差随目标位置的变化速率与目标散射的链路间相参性（3.4节），是贯穿本方案的关键量。

## 3.2 参考通道与监视通道信号

信号源 $i$ 的发射信号可表示为 $s_i(t)=x_i(t)\exp\{\mathrm{j}[2\pi f_i t+\phi_i(t)]\}$，其中 $x_i(t)$ 为复包络（如OFDM），$\phi_i(t)$ 为发射机振荡器相位，包含未知初相、载频偏差与相位噪声。接收站 $j$ 以本振 $\exp\{-\mathrm{j}[2\pi f_{\mathrm{L},i}t+\vartheta_j(t)]\}$ 将信号源 $i$ 所在信道变换至基带，$f_{\mathrm{L},i}$ 为该信道的本振频率，$\vartheta_j(t)$ 为本振相位；**参考通道与监视通道共用同一本振与采样时钟**。信号源 $i$ 在接收站 $j$ 处的直达波基带信号为

$$ d_{ij}(t)=x_i\left(t-\tau^{\mathrm{d}}_{ij}\right)\exp\left\{\mathrm{j}\left[2\pi\left(f_i-f_{\mathrm{L},i}\right)t-2\pi f_i\tau^{\mathrm{d}}_{ij}+\phi_i\left(t-\tau^{\mathrm{d}}_{ij}\right)-\vartheta_j(t)\right]\right\} $$ {#eq:direct}

式中，$\tau^{\mathrm{d}}_{ij}=\left\|\mathbf{t}_i-\mathbf{r}_j\right\|/c$。参考通道与监视通道（信号源 $i$ 所在信道）的接收信号分别为

$$ y^{\mathrm{r}}_{ij}(t)=b_{ij}\,d_{ij}(t)+n^{\mathrm{r}}_{ij}(t),\qquad y^{\mathrm{s}}_{ij}(t)=a_{ij}d_{ij}(t)+\sum_{k}c_{ijk}\,d_{ij}\left(t-\tau^{\mathrm{c}}_{ijk}\right)+e_l(t)+n^{\mathrm{s}}_{ij}(t) $$ {#eq:channels}

式中，$b_{ij}$、$a_{ij}$ 分别为参考通道与监视通道中直达波的复增益，第二项为多径杂波，$n^{\mathrm{r}}_{ij}$、$n^{\mathrm{s}}_{ij}$ 为接收机噪声。目标回波相对直达波的附加时延为 $\tau_l(t)=R_l(t)/c$。将回波写成直达波的时延形式，并利用CPI内 $\tau_l(t)\approx\tau_l+\dot{\tau}_l(t-t_c)$，可得

$$ e_l(t)=g_l\,\alpha_l\,e^{\mathrm{j}\varkappa^{\mathrm{s}}_{ij}}\,d_{ij}\left(t-\tau_l\right)\exp\left(-\mathrm{j}2\pi f_{\mathrm{L},i}\tau_l\right)\exp\left[\mathrm{j}2\pi f_l\left(t-t_c\right)\right] $$ {#eq:echo}

式中，$g_l$ 为由双基地雷达方程决定的回波幅度，$\alpha_l$ 为目标在链路 $l$ 收发视角下的复散射系数，$\varkappa^{\mathrm{s}}_{ij}$ 为监视天线（目标方向）及监视通道的相位响应。推导中利用了：发射相位噪声在回波与直达波之间的时延差 $\tau_l$（本例小于0.2 ms）内近似不变，本振相位 $\vartheta_j(t)$ 在两路信号中相同。

## 3.3 链路互模糊函数输出及其相位构成

以提纯后保留直达波复增益相位的参考信号 $\hat d_{ij}(t)=e^{\mathrm{j}\varkappa^{\mathrm{r}}_{ij}}d_{ij}(t)$（$\varkappa^{\mathrm{r}}_{ij}=\arg b_{ij}$）对ECA对消后的监视信号作互模糊函数处理，相位基准统一取在CPI中心 $t_c$：

$$ \chi_l(\tau,f)=\int_{t_c-T/2}^{t_c+T/2}y^{\mathrm{s}}_{\perp,ij}(t)\,\hat d^{*}_{ij}(t-\tau)\,e^{-\mathrm{j}2\pi f(t-t_c)}\,\mathrm{d}t $$ {#eq:caf}

在目标所在的时延—多普勒单元，链路 $l$ 的复输出为

$$ z_l=\chi_l\left(\tau_l,f_l\right)=A_l\,\alpha_l\exp\left[\mathrm{j}\left(\kappa_l-\frac{2\pi R_l}{\lambda_l}\right)\right]+w_l,\qquad \kappa_l=\varkappa^{\mathrm{s}}_{ij}-\varkappa^{\mathrm{r}}_{ij},\quad \lambda_l=\frac{c}{f_{\mathrm{L},i}} $$ {#eq:zl}

式中，$A_l$ 为积累后的信号幅度，$w_l\sim\mathcal{CN}(0,\sigma_l^2)$ 为积累后的噪声。式({{eq:zl}})是本方案的出发点，它表明：

（1）**发射机相位 $\phi_i(t)$（初相、载频偏差、相位噪声）与接收机本振相位 $\vartheta_j(t)$ 均不出现在链路输出中。**这是因为同一信号源的回波与直达波经同一接收机、同一本振接收，在互模糊处理中相互抵消，即参考通道的“自同步”特性。因此，各链路输出的相位均以“本站接收的该信号源直达波”为基准；

（2）链路输出相位只由三部分构成：目标散射相位 $\arg\alpha_l$、几何相位 $-2\pi R_l/\lambda_l$（给定目标位置假设后可精确计算）以及通道相位差 $\kappa_l$（可标定）；

（3）几何相位按接收站自身的本振频率 $f_{\mathrm{L},i}$ 计算，与信号源的实际载频无关，因此信号源的载频偏差不影响相参性，但接收站频率基准的误差会引入相位误差（4.2节）；

（4）各站的相位参考时刻必须统一为同一 $t_c$，否则多普勒相位 $2\pi f_l\delta t$ 将引入站间相位差。

## 3.4 目标散射的链路间相参性

将目标视为位于参考点 $\mathbf{p}$ 附近、偏移量为 $\mathbf{q}_m$ 的 $M$ 个散射中心，其复散射幅度为 $\eta_m$，则链路 $l$ 的复散射系数为

$$ \alpha_l=\sum_{m=1}^{M}\eta_m\exp\left(-\mathrm{j}2\pi\mathbf{k}_l^{\mathrm{T}}\mathbf{q}_m\right) $$ {#eq:alpha}

设 $\eta_m$ 相互独立、散射中心在尺寸为 $L_x\times L_y\times L_z$ 的长方体内均匀分布（机体坐标系），则链路间散射系数的相关系数为

$$ \rho_{ll'}=\frac{\mathrm{E}\left[\alpha_l\alpha_{l'}^{*}\right]}{\sqrt{\mathrm{E}|\alpha_l|^2\,\mathrm{E}|\alpha_{l'}|^2}}=\prod_{d\in\{x,y,z\}}\operatorname{sinc}\left(\Delta k_{ll',d}\,L_d\right) $$ {#eq:rho}

式中，$\operatorname{sinc}(x)=\sin(\pi x)/(\pi x)$。由 $\operatorname{sinc}(0.26)\approx0.9$，链路间散射“相参”（$\rho_{ll'}\ge0.9$）的充分条件为

$$ \left\|\Delta\mathbf{k}_{ll'}\right\|L_t\le0.26 $$ {#eq:cohcond}

式中，$L_t$ 为目标尺寸。$\Delta\mathbf{k}_{ll'}$ 由三部分构成：两链路信号源视角之差、接收站视角之差与载频之差。式({{eq:cohcond}})说明，相参融合并非只取决于系统同步，还受目标“电尺寸”与链路几何张角的物理约束：目标越大、波长越短、站址越分散，链路间散射相参性越差。该条件与经典目标起伏模型中“频率捷变间隔超过 $c/(2L_t)$、视角变化超过 $\lambda/(2L_t)$ 时回波去相关”的结论一致^\[20\]^。本系统的最大波数差为 {{T:coherence/kspread_max|.2f}} 周/米，满足 $\rho\ge0.9$ 的目标尺寸上限约为 {{T:coherence/lt_max_rho09|.2f}} m。

# 4 实现相参融合的条件

## 4.1 两个信号源之间应满足的条件

由3.3节可知，各链路以本站接收的该信号源直达波为相位基准，两个信号源的初相、载频偏差与相位噪声在互模糊处理中自动抵消。因此，与有源分布式相参雷达要求各发射机严格时间、相位同步不同^\[10,11\]^，**本系统不要求两个信号源之间以及信号源与接收站之间进行时间同步或相位锁定**，这对非合作信号源至关重要。两个信号源需满足的是如下“可相参”条件。

**（1）时间条件：同时照射、信号连续。**两个信号源须在同一CPI $[t_c-T/2,\,t_c+T/2]$ 内同时照射目标，且CPI内信号连续，不出现节目切换、跳频、波束切换或长时间静默；对时分双工（TDD）通信信号或突发式卫星下行信号，应按有效照射时段划分子CPI。两个信号源的发射时刻无需同步；若两源构成单频网（SFN）并采用统一的解调重构参考信号，则要求两源间的发射时延差稳定，并能由两路直达波估计至远小于 $1/B$（$B$ 为信号带宽）。

**（2）频率条件：载频已知且两源载频差满足散射频率相干条件。**两个信号源的载频可以不同，但几何相位补偿须按各自的波长 $\lambda_l$ 进行（若误用同一波长，8 MHz频差在 $\tau_l\approx170$ μs 时引入的相位误差高达数千弧度）。对于同址的两个信号源，两源链路的波数差 $\left\|\Delta\mathbf{k}\right\|=2|\Delta f|\cos(\beta/2)/c$，由式({{eq:cohcond}})得两源载频差的上限为

$$ \left|\Delta f\right|\le\frac{0.13\,c}{L_t\cos(\beta/2)} $$ {#eq:dfcond}

当 $\beta=20^{\circ}$ 时，$L_t=1$ m、3 m、10 m 对应的载频差上限分别约为 {{T:two_source/1/df_max_mhz|.0f}} MHz、{{T:two_source/3/df_max_mhz|.0f}} MHz 与 {{T:two_source/10/df_max_mhz|.1f}} MHz。本例两源为相邻的8 MHz信道（$\Delta f=8$ MHz），对尺寸数米以内的目标满足要求。此外，各信号源的短期频率稳定度应保证回波与直达波之间的残余相位噪声 $\sigma^2_{\Delta\phi}=2\int S_{\phi}(f)\left[1-\cos(2\pi f\tau_l)\right]\mathrm{d}f\ll1$，广播电视发射机普遍采用的高稳晶振或GNSS驯服频率源均可满足。

**（3）空间条件：两源对目标的视角差足够小。**对同频的两个信号源，$\left\|\Delta\mathbf{k}\right\|\approx\Delta\theta_{\mathrm{T}}/\lambda$，$\Delta\theta_{\mathrm{T}}$ 为两源相对目标的视角差（张角），由式({{eq:cohcond}})得

$$ \Delta\theta_{\mathrm{T}}\le\frac{0.26\,\lambda}{L_t} $$ {#eq:dthcond}

在650 MHz频段，$L_t=1$ m、3 m、10 m 对应的视角差上限分别约为 {{T:two_source/1/dtheta_max_deg|.1f}}°、{{T:two_source/3/dtheta_max_deg|.1f}}° 与 {{T:two_source/10/dtheta_max_deg|.2f}}°。本例两源对目标的张角为 {{T:two_source/this_dtheta_deg|.1f}}°。因此，两信号源宜“同址或近址”，例如同一发射塔的不同频道，或从监视区看去方位相近的两座发射台。图2给出了两源散射相关系数随载频差、视角差的变化及 $\rho\ge0.9$ 的可行域。

![图2 两信号源之间的散射相参条件：(a) 同址异频；(b) 同频异址；(c) ρ≥0.9 的可行域](figures/st_two_source.png){width=15.5cm}

**（4）波形条件：宽带类噪声、带宽相近、可分离、直达波可获取。**①两源信号应为宽带类噪声信号，模糊函数呈图钉形（OFDM体制的数字广播、移动通信与卫星下行信号均满足），且带宽相近，使两源链路的距离分辨单元一致，便于在目标状态空间对齐；②两源信号在各接收站可分离：多频网（MFN）中两源位于不同信道，经数字信道化分离；同频异内容时需进行源间串扰抑制（参考波束空域分离或解调重构后对消）；同频同内容（SFN）时以解调重构的统一信号作参考，要求各站两路直达波的时延差大于 $1/B$，回波归属由目标状态空间的几何关系自动区分；③各接收站参考通道须能获得两个信号源的直达波，直达波信噪比满足正确解调重构的要求（一般不低于20~30 dB），以便重构纯净参考信号并**保留直达波相位**。

**（5）相位稳定性条件。**在一个CPI内，各信号源的发射相位应连续，不发生相位跳变（如单频网重同步、设备切换）；若存在跳变，应检测跳变时刻并按子CPI分段处理。

## 4.2 接收站与系统层面的条件

**（1）频率基准。**若接收站 $j$ 的频率基准相对误差为 $\varepsilon_j$，则按标称本振频率补偿几何相位时，链路 $l$ 引入相位误差

$$ \delta\varphi_l=2\pi\varepsilon_j f_{\mathrm{L},i}\tau_l,\qquad \text{要求}\quad \varepsilon_j\ll\frac{1}{2\pi f_{\mathrm{L},i}\tau_{\max}} $$ {#eq:epscond}

本例 $f\approx650$ MHz、$\tau_{\max}\approx180$ μs，要求 $\varepsilon_j\ll1.4\times10^{-6}$。GNSS驯服的恒温晶振或铷钟（$\varepsilon\le10^{-9}$）引入的损失可以忽略；自由振荡温补晶振（$\varepsilon\approx10^{-6}$）将引入约 {{T:sync/eps_loss_1e-6_db|.1f}} dB 的相参损失。

**（2）时间同步。**由于各链路时延均以本站直达波为基准测量，站间时钟偏差不影响回波包络对齐；其影响在于CPI中心时刻不一致带来的多普勒相位差 $\delta\varphi_l=2\pi f_l\delta t_j$，要求 $\delta t_j\ll1/(2\pi|f_l|)$。本例 $f_l\approx155$ Hz，相参损失达0.5 dB时的时间误差约为 {{E:T['sync']['dt_for_0.5db_this']*1e6|.0f}} μs；GNSS授时精度（约50 ns）远优于此要求。

**（3）站址精度。**接收站与信号源天线相位中心的位置误差 $\delta\mathbf{r}_j$、$\delta\mathbf{t}_i$ 引入的双基地距离误差分别为

$$ \delta R_l=\left(\mathbf{u}_{j\to i}-\mathbf{u}_{\mathrm{R},j}\right)^{\mathrm{T}}\delta\mathbf{r}_j,\qquad \delta R_l=-\left(\mathbf{u}_{\mathrm{T},i}+\mathbf{u}_{j\to i}\right)^{\mathrm{T}}\delta\mathbf{t}_i $$ {#eq:poscond}

式中，$\mathbf{u}_{j\to i}=(\mathbf{t}_i-\mathbf{r}_j)/\left\|\mathbf{t}_i-\mathbf{r}_j\right\|$。按 $2\pi\delta R_l/\lambda_l$ 折算为相位误差后，相参损失0.5 dB对应的接收站与信号源位置误差（三维标准差）分别约为 {{T:sync/rx_pos_for_0.5db_cm|.1f}} cm 与 {{T:sync/tx_pos_for_0.5db_cm|.1f}} cm。接收站可采用RTK测量天线相位中心；非合作信号源天线位置通常只能获得米级精度，必须依靠标校消除。由于这类误差随目标位置缓慢变化，可并入通道相位 $\kappa_l$ 统一标校（6.6节）。

**（4）通道相位标定。**各链路残余相位误差（含通道标定、站址与几何误差）服从标准差为 $\sigma_\varphi$ 的独立高斯分布时，相参融合的信噪比增益为

$$ G(\sigma_\varphi)=\frac{\sum_l s_l^4+e^{-\sigma_\varphi^2}\left[\left(\sum_l s_l^2\right)^2-\sum_l s_l^4\right]}{\bar{s}^2\sum_l s_l^2}\;\xrightarrow{\;s_l=\bar s\;}\;1+(L-1)e^{-\sigma_\varphi^2} $$ {#eq:phaseloss}

式中，$s_l^2$ 为链路 $l$ 的输出信噪比，$\bar{s}^2$ 为其平均值。$L=10$ 时，相参损失不超过0.5 dB与1 dB分别要求 $\sigma_\varphi\le$ {{T:sync/sigma_for_0.5db|.0f}}° 与 $\sigma_\varphi\le$ {{T:sync/sigma_for_1db|.0f}}°。

**（5）统一相位参考时刻与数据格式。**各站须以绝对时间定义CPI并统一相位参考时刻 $t_c$，上报复数（而非幅度）距离—多普勒数据。

## 4.3 条件汇总与本系统评估

实现10链路相参融合的条件汇总于表2。其中，信号源侧的时间与相位同步要求被参考通道的自同步特性“化解”，真正需要保证的是：信号同时、连续且可分离；接收站频率基准、时间基准与站址准确；通道相位可标定；目标散射在链路之间相参。

Table: 表2 实现10链路相参融合的条件

| 类别 | 条件 | 定量要求（本例） | 实现途径 |
|:------|:------|:------|:------|
| 两源时间 | 同时照射、CPI内连续 | 无需两源时间同步 | 选择连续发射的信号源，按照射时段划分子CPI |
| 两源频率 | 载频差满足频率相干 | 式({{eq:dfcond}})，$L_t$=3 m 时 ≤{{T:two_source/3/df_max_mhz|.0f}} MHz | 优选相邻信道；按各源波长分别补偿 |
| 两源空间 | 两源对目标视角差小 | 式({{eq:dthcond}})，$L_t$=1 m 时 ≤{{T:two_source/1/dtheta_max_deg|.1f}}° | 同址或近址信号源 |
| 两源波形 | 宽带类噪声、可分离、直达波可获取 | 参考通道DNR≥20~30 dB | 数字信道化、源间串扰抑制、解调重构 |
| 两源相位 | CPI内相位连续 | 无相位跳变 | 跳变检测与分段处理 |
| 频率基准 | 接收站频率准确度 | $\varepsilon\ll1.4\times10^{-6}$ | GNSS驯服恒温晶振/铷钟 |
| 时间同步 | CPI中心时刻一致 | $\delta t\ll1/(2\pi f_l)$ | GNSS授时（约50 ns） |
| 站址精度 | 天线相位中心位置 | 接收站约{{T:sync/rx_pos_for_0.5db_cm|.1f}} cm，信号源约{{T:sync/tx_pos_for_0.5db_cm|.0f}} cm（0.5 dB） | RTK测量 + 合作目标标校 |
| 通道相位 | 残余相位误差 | $\sigma_\varphi\le$ {{T:sync/sigma_for_0.5db|.0f}}°（0.5 dB） | 注入校准、直达波泄漏监测、自校准 |
| 目标散射 | 链路间散射相参 | 式({{eq:cohcond}})，本例 $L_t\lesssim$ {{T:coherence/lt_max_rho09|.1f}} m | 紧凑布站；否则分组相参或非相参 |

按图1的布站计算10条链路之间的散射相关矩阵（图3）。对于尺寸约0.35 m的小型旋翼无人机，链路间平均相关系数为 {{T:coherence/mean_rho/0.35|.2f}}，满足全相参条件；尺寸1 m时为 {{T:coherence/mean_rho/1|.2f}}；尺寸3 m时降至 {{T:coherence/mean_rho/3|.2f}}，且同源链路之间（对角块）的相关性明显高于异源链路之间；尺寸10 m时仅为 {{T:coherence/mean_rho/10|.2f}}，链路间基本去相关。可见，在本系统布站条件下，10链路全相参融合适用于小型无人机等电尺寸较小的目标，对大尺寸目标应采用分组相参或非相参融合。

![图3 10条链路间目标散射系数的相关矩阵（左：$L_t$=0.35 m；右：$L_t$=3 m）](figures/st_coherence.png){width=13cm}

# 5 各接收站回波处理流程

各接收站的处理流程与融合中心流程如图4所示。每个接收站对两个信号源并行处理，输出2条链路的复数距离—多普勒图及标定参数。

![图4 相参融合检测总体处理流程](figures/fig_flow.png){width=15.5cm}

## 5.1 时频基准与同步采样

各接收站采用GNSS驯服的恒温晶振或铷钟产生10 MHz频率基准与1PPS秒脉冲^\[12\]^，参考通道与监视通道的本振和模数转换器必须同源，这是直达波相位基准在互模糊处理中抵消发射与本振相位的前提。数据按绝对时间分块，以GNSS时间定义各CPI的起止时刻，使5个接收站的CPI中心时刻 $t_c$ 一致。

## 5.2 多源信号分离与辐射源参数估计

对宽带采样数据进行数字下变频与信道化滤波，分别得到两个信号源所在信道的参考通道与监视通道基带信号。两源同频而内容不同时，应在参考通道采用指向不同信号源的波束进行空域分离，并在后续对消中同时引入两源参考信号。随后对每个信号源完成载频偏差、符号定时与帧结构等参数估计，方法见本项目《信号源参数精确估计技术》^\[22\]^。

## 5.3 参考信号提纯

参考通道中的噪声与多径会在互模糊处理中抬高底噪并降低对消深度，需采用解调—再调制方法提纯^\[15\]^：利用循环前缀估计并补偿频偏，逐符号FFT后判决得到各子载波符号，重构纯净的OFDM波形，再恢复直达波的分数时延、复增益与频偏：

$$ \hat d_{ij}(t)=\hat g_{ij}(t)\,\hat x_i\left(t-\hat\tau^{\mathrm{d}}_{ij}\right)\exp\left(\mathrm{j}2\pi\hat\varepsilon_{ij}t\right) $$ {#eq:purify}

式中，$\hat x_i$ 为重构波形，$\hat g_{ij}(t)$ 为由逐符号信道估计平滑得到的复增益，$\hat\varepsilon_{ij}$ 为频偏估计。**必须在提纯参考中保留直达波的复增益（相位）$\hat g_{ij}(t)$**，否则式({{eq:zl}})中的发射相位与本振相位不再抵消，相参融合将失效（7.4节）。

## 5.4 直达波与多径杂波对消

采用扩展对消算法（ECA）^\[14\]^将监视信号投影到参考信号各时延副本所张成子空间的正交补空间：

$$ \mathbf{y}^{\mathrm{s}}_{\perp}=\left[\mathbf{I}-\mathbf{X}\left(\mathbf{X}^{\mathrm{H}}\mathbf{X}\right)^{-1}\mathbf{X}^{\mathrm{H}}\right]\mathbf{y}^{\mathrm{s}},\qquad \mathbf{X}=\left[\hat{\mathbf{d}}_{-K_1},\cdots,\hat{\mathbf{d}}_{0},\cdots,\hat{\mathbf{d}}_{K_2}\right] $$ {#eq:eca}

式中，$\hat{\mathbf{d}}_k$ 为提纯参考信号延迟 $k$ 个样点的向量。由于多径时延一般不是整数个样点，宜同时采用正、负时延抽头（本例 $K_1=16$、$K_2=79$）；杂波随时间缓变时采用分批ECA；两源同频时 $\mathbf{X}$ 应同时包含两源的参考信号副本。

## 5.5 距离—多普勒相参积累

采用批处理算法计算互模糊函数：将CPI划分为 $N_b$ 批、每批 $L_B$ 个样点，

$$ \chi_l(m,f)=\sum_{b=0}^{N_b-1}e^{-\mathrm{j}2\pi f t_b}\sum_{n=0}^{L_B-1}y^{\mathrm{s}}_{\perp}\left(bL_B+n\right)\hat d^{*}\left(bL_B+n-m\right) $$ {#eq:batch}

式中，$m$ 为时延样点，$t_b$ 为第 $b$ 批中心相对 $t_c$ 的时间。以CPI中心为相位参考，可使多普勒失配只引起幅度损失而不引起相位偏差。距离维按带限内插细化（本例8倍），以便融合中心在任意分数时延处读取复数值。对于高速目标，CPI内距离走动超过一个距离单元时，可将CPI划分为子CPI，由融合中心沿目标轨迹完成长时间相参积累（6.5节）。

## 5.6 通道相位标定与噪声归一化

通道相位 $\kappa_l$ 为监视通道（含监视天线在目标方向的相位）与参考通道（含参考天线在信号源方向的相位）的相位差。其标定分三部分：①周期性注入校准信号，测量两路射频通道的相位差；②利用ECA之前监视通道中直达波泄漏的零时延相关峰，连续监测两路通道相位差的漂移；③由暗室测量的天线方向图相位修正目标方向与信号源方向的差异，剩余偏差由6.6节的自校准消除。同时，由距离—多普勒图的噪声底估计 $\sigma_l^2$（采用中值估计以抑制目标与残余杂波的影响），得到归一化输出 $\tilde z_l=z_l/\sigma_l$。

## 5.7 上报融合中心的数据

每个接收站每个CPI向融合中心上报2条链路的数据：监视区对应时延—多普勒窗口内的复数距离—多普勒图、噪声功率 $\sigma_l^2$、通道相位 $\hat\kappa_l$、CPI中心时刻 $t_c$、信道本振频率 $f_{\mathrm{L},i}$、站址坐标及直达波信噪比、对消剩余等质量指标。以400个距离单元、200个多普勒单元、每CPI 0.25 s、单精度复数计，单链路数据率约为20 Mbit/s；采用16位量化或只上报预检测门限以上的单元可进一步压缩，可通过光纤或4G/5G专网传输。

# 6 10链路相参融合检测算法

## 6.1 检测模型

在目标状态假设 $\boldsymbol{\theta}$ 下，由各链路距离—多普勒图读取 $\tilde z_l(\boldsymbol{\theta})=\chi_l\left(\tau_l(\boldsymbol{\theta}),f_l(\boldsymbol{\theta})\right)/\sigma_l$，并计算几何与通道相位补偿量

$$ \hat\Phi_l(\boldsymbol{\theta})=\frac{2\pi R_l(\mathbf{p})}{\lambda_l}-\hat\kappa_l $$ {#eq:phi}

则二元假设检验问题为

$$ \mathcal{H}_0:\ \tilde z_l=\tilde w_l;\qquad \mathcal{H}_1:\ \tilde z_l=s_l\,\alpha_l\,e^{-\mathrm{j}\Phi_l(\boldsymbol{\theta})}+\tilde w_l,\qquad l=1,\cdots,L $$ {#eq:hypo}

式中，$\tilde w_l\sim\mathcal{CN}(0,1)$ 相互独立，$s_l^2$ 为链路 $l$ 的输出信噪比（$\mathrm{E}|\alpha_l|^2=1$），$L=10$。不同链路的 $\alpha_l$ 之间的相关结构由式({{eq:rho}})描述。

## 6.2 广义似然比检测统计量

**（1）10链路全相参融合。**当各链路散射相参（$\alpha_l=\alpha$，空间相参模型^\[4\]^）时，将未知复幅度视为公共参数，其GLRT统计量为

$$ T_{\mathrm{C}}(\boldsymbol{\theta})=\frac{\left|\sum_{l=1}^{L}w_l\,\tilde z_l(\boldsymbol{\theta})\,e^{\mathrm{j}\hat\Phi_l(\boldsymbol{\theta})}\right|^2}{\sum_{l=1}^{L}w_l^2} $$ {#eq:tc}

$\mathcal{H}_0$ 下 $T_{\mathrm{C}}$ 服从单位均值指数分布；$\mathcal{H}_1$ 下其输出信噪比为 $\left(\sum_l w_ls_l\right)^2/\sum_l w_l^2$，在最大比合并（MRC）权 $w_l\propto s_l$ 时达到最大值

$$ \mathrm{SNR}_{\mathrm{C}}=\sum_{l=1}^{L}s_l^2=\sum_{l=1}^{L}\mathrm{SNR}_l $$ {#eq:snrc}

即10条链路信噪比相近时提高 $10\lg10=10$ dB。MRC权可由双基地雷达方程^\[18\]^和各站噪声电平预测；链路信噪比未知时可取等增益权 $w_l=1$。

**（2）非相参融合。**当各链路散射系数相互独立（空间非相参）时，GLRT统计量为

$$ T_{\mathrm{N}}(\boldsymbol{\theta})=\sum_{l=1}^{L}\left|\tilde z_l(\boldsymbol{\theta})\right|^2 $$ {#eq:tn}

$\mathcal{H}_0$ 下 $T_{\mathrm{N}}$ 服从参数为 $(L,1)$ 的伽马分布。非相参融合不需要相位信息，对散射去相关稳健，并可获得空间分集增益^\[5\]^。

**（3）分组相参融合。**将链路分为 $G$ 组 $\mathcal{G}_1,\cdots,\mathcal{G}_G$，组内相参、组间非相参：

$$ T_{\mathrm{G}}(\boldsymbol{\theta})=\sum_{g=1}^{G}\frac{\left|\sum_{l\in\mathcal{G}_g}w_l\,\tilde z_l(\boldsymbol{\theta})\,e^{\mathrm{j}\hat\Phi_l(\boldsymbol{\theta})}\right|^2}{\sum_{l\in\mathcal{G}_g}w_l^2} $$ {#eq:tg}

按接收站分组（每组为同一接收站的两条链路）即“源间相参”，按信号源分组（每组为同一信号源的5条链路）即“站间相参”。四种融合模式如图5所示。

**（4）一般形式。**若 $\boldsymbol{\alpha}\sim\mathcal{CN}(\mathbf{0},\mathbf{C})$，$\mathbf{C}=[\rho_{ll'}]$，则奈曼-皮尔逊最优检测器为估计—相关器^\[19\]^

$$ T_{\mathrm{EC}}(\boldsymbol{\theta})=\tilde{\mathbf{z}}_{\Phi}^{\mathrm{H}}\mathbf{P}\left(\mathbf{P}+\mathbf{I}\right)^{-1}\tilde{\mathbf{z}}_{\Phi},\qquad \mathbf{P}=\mathbf{S}^{1/2}\mathbf{C}\,\mathbf{S}^{1/2} $$ {#eq:tec}

式中，$\tilde{\mathbf{z}}_{\Phi}$ 为相位补偿后的链路输出向量，$\mathbf{S}=\mathrm{diag}(s_1^2,\cdots,s_L^2)$。$\mathbf{C}=\mathbf{1}\mathbf{1}^{\mathrm{T}}$ 时退化为全相参融合，$\mathbf{C}=\mathbf{I}$ 时退化为非相参融合，$\mathbf{C}$ 为块对角全1矩阵时退化为分组相参融合。

![图5 10条链路的四种融合模式](figures/fig_modes.png){width=15.5cm}

## 6.3 目标状态空间“粗—精”两级搜索

相参统计量中的几何相位随目标位置以 $1/\left\|\Delta\mathbf{k}\right\|$ 为周期变化（本例最短约 {{E:1/T['coherence']['kspread_max']|.1f}} m），远小于非相参融合的分辨单元（本例距离向约20 m、横向数百米）。若直接在全监视区以亚波长网格计算 $T_{\mathrm{C}}$，运算量过大。为此采用两级搜索：

**第一级：非相参粗检测。**在目标状态空间布设粗网格（位置间隔不大于非相参分辨单元的一半，速度间隔对应一个多普勒单元），按式({{eq:tn}})计算 $T_{\mathrm{N}}$，以较低门限（如单元虚警概率 $10^{-3}$）选出候选单元。

**第二级：相参精搜索。**在每个候选单元 $\Omega_c$ 内以不大于 $1/(4\max\left\|\Delta\mathbf{k}\right\|)$ 的步长搜索位置偏移 $\delta\mathbf{p}$。由于单元内回波包络基本不变，只需更新相位：

$$ T_{\mathrm{C}}(\boldsymbol{\theta}_c)=\max_{\delta\mathbf{p}\in\Omega_c}\frac{\left|\sum_{l=1}^{L}w_l\,\tilde z_l(\boldsymbol{\theta}_c)\,e^{\mathrm{j}\hat\Phi_l(\boldsymbol{\theta}_c)}\,e^{\mathrm{j}2\pi\mathbf{k}_l^{\mathrm{T}}\delta\mathbf{p}}\right|^2}{\sum_{l=1}^{L}w_l^2} $$ {#eq:fine}

式({{eq:fine}})可写成“候选单元×链路”矩阵与“链路×精细偏移”相位矩阵之积，适合GPU并行或非均匀FFT加速。相参精搜索在完成检测的同时给出波长量级的目标位置估计^\[7\]^。

## 6.4 检测门限与相参性自适应判决

非相参支路的门限由伽马分布给出，$\eta_{\mathrm{N}}=\Gamma^{-1}(1-P_{\mathrm{fa}};L)$。相参支路在每个粗单元内对约 $M$ 个等效独立的精细位置取最大值，为保持相同的单位面积虚警率，其门限应提高为

$$ \eta_{\mathrm{C}}=\ln\frac{M}{P_{\mathrm{fa}}} $$ {#eq:etac}

$M$ 取决于链路几何，可由仿真统计得到，本系统 $M\approx$ {{T:multiplicity/coh/ratio|.0f}}（相对 $M=1$ 时门限提高约 {{T:derived/eta_penalty_db|.1f}} dB）。这一“精搜索代价”是分布式相参融合检测所固有的，布站越分散、$\left\|\Delta\mathbf{k}\right\|$ 越大，代价越高。工程中可采用单元平均恒虚警（CA-CFAR）处理，由目标状态空间中的参考单元估计背景电平。

在目标尺寸未知时，采用相参/非相参双支路并行检测：

$$ D(\boldsymbol{\theta})=\left\{T_{\mathrm{N}}(\boldsymbol{\theta})>\eta'_{\mathrm{N}}\right\}\cup\left\{T_{\mathrm{C}}(\boldsymbol{\theta})>\eta'_{\mathrm{C}}\right\} $$ {#eq:or}

两支路各分配 $P_{\mathrm{fa}}/2$ 的虚警概率。点状目标主要由相参支路检测，扩展目标主要由非相参支路检测，代价仅为门限的轻微提高。若已知目标类型（如由航迹、微多普勒特征判别），可按式({{eq:rho}})计算相关矩阵 $\mathbf{C}$，选择分组相参或估计—相关器。

## 6.5 时域—源—站三维相参的统一形式

当目标速度较高、CPI内距离走动超过一个距离单元，或信号源存在分段照射时，将总积累时间划分为 $K$ 个子CPI（中心时刻 $t_k$），各站按子CPI计算距离—多普勒图 $\chi_{l,k}$，融合中心沿目标轨迹进行时域、源间与站间的统一相参积累：

$$ T_{\mathrm{3D}}(\boldsymbol{\theta})=\frac{\left|\sum_{k=1}^{K}\sum_{l=1}^{L}w_l\,\tilde z_{l,k}(\boldsymbol{\theta})\exp\left[\mathrm{j}\left(\frac{2\pi R_l\left(\mathbf{p}+\mathbf{v}(t_k-t_c)\right)}{\lambda_l}-\hat\kappa_l\right)\right]\right|^2}{K\sum_{l}w_l^2} $$ {#eq:t3d}

式中，$\tilde z_{l,k}(\boldsymbol{\theta})$ 在第 $k$ 个子CPI中按目标轨迹预测的时延与多普勒读取。该式将RFT^\[16\]^的“轨迹匹配”思想推广到多源多站，同时完成距离走动与多普勒走动补偿；目标存在机动时，在 $\boldsymbol{\theta}$ 中增加加速度分量。当某一维不满足相参条件时，可在该维改为非相参累加（7.8节给出了各种组合的检测增益）。

## 6.6 相位自校准

非合作信号源天线位置误差、天线方向图相位误差及缓变的通道漂移，会使各链路存在随目标位置缓变的残余相位偏差。借鉴分布式孔径相参合成雷达的相参参数估计方法^\[10,11\]^，可利用合作标校目标（携带角反射器或龙伯球、装有RTK定位的小型无人机）或高信噪比的点状目标进行自校准：在 $N_c$ 个快拍（目标处于不同位置）下联合估计各链路相位偏差与各快拍的亚波长位置修正量

$$ \left\{\hat\kappa_l,\ \delta\hat{\mathbf{p}}_n\right\}=\arg\max_{\{\kappa_l\},\{\delta\mathbf{p}_n\}}\sum_{n=1}^{N_c}\left|\sum_{l=1}^{L}w_l\,\tilde z_{l,n}\exp\left\{\mathrm{j}\left[\frac{2\pi R_l\left(\hat{\mathbf{p}}_n+\delta\mathbf{p}_n\right)}{\lambda_l}-\kappa_l\right]\right\}\right|^2 $$ {#eq:selfcal}

式中，$\hat{\mathbf{p}}_n$ 为标校目标的RTK位置或非相参定位结果。由于 $\kappa_l$ 不随快拍变化而 $\delta\mathbf{p}_n$ 随快拍变化，二者在目标运动过程中可以分离，可采用交替迭代求解。若进一步将信号源位置误差 $\delta\mathbf{t}_i$ 作为未知参数纳入式({{eq:selfcal}})，则校准结果可推广到整个监视区。

## 6.7 算法流程与运算量

10链路相参融合检测算法的完整流程为：

（1）各接收站按5.1~5.6节处理，上报复数距离—多普勒图及标定参数；

（2）融合中心对每个CPI，在目标状态粗网格上读取10条链路的归一化复值 $\tilde z_l(\boldsymbol{\theta})$，计算非相参统计量 $T_{\mathrm{N}}$，以低门限选出候选单元；

（3）对候选单元按式({{eq:phi}})进行相位补偿与MRC加权，按式({{eq:fine}})进行相参精搜索，得到 $T_{\mathrm{C}}$ 及精细位置；

（4）按式({{eq:or}})双支路判决（或按相关矩阵选择分组相参），经恒虚警处理输出检测结果；

（5）检测结果送航迹处理；对高信噪比点状目标按式({{eq:selfcal}})更新 $\hat\kappa_l$。

运算量主要集中在各站的互模糊函数计算（与单站被动雷达相同）。融合中心粗检测的运算量与状态网格数和链路数之积成正比；精搜索的运算量约为“候选单元数×精细偏移数×$L$”次复数乘加，以1000个候选单元、441个精细偏移计约为 $4.4\times10^6$ 次，实时实现没有困难。

# 7 仿真实验与结果分析

## 7.1 仿真条件

仿真场景如图1所示，主要参数见表3。两个信号源为相邻信道的CP-OFDM数字广播信号（MFN），各自独立调制；为检验参考通道的自同步特性，仿真中为两个信号源设置了随机初相、±10 Hz内的随机载频偏差与相位噪声，为各接收站设置了随机本振初相、相位噪声和 $10^{-9}$ 量级的频率基准误差，为每条链路设置了随机的通道相位差 $\kappa_l$（标定残差5°）。目标采用由5个散射中心构成、尺寸0.35 m的小型无人机模型，各链路信噪比由双基地雷达方程计算。单站处理采用解调—再调制参考提纯、双边抽头ECA与批处理互模糊函数，融合中心采用第6章算法。

Table: 表3 仿真参数

| 参数 | 取值 |
|:------|:------|
| 信号体制 | CP-OFDM，采样率7.56 MHz，2048子载波（有效1890），CP 1/8，QPSK |
| 载频 / 有效带宽 | T1：650 MHz，T2：658 MHz / 6.98 MHz |
| 等效辐射功率 | T1：10 kW，T2：5 kW |
| 信号源非理想因素 | 随机初相、载频偏差 U(−10, 10) Hz、相位噪声 |
| 接收站非理想因素 | 随机本振初相与相位噪声、频率基准误差 U(−1, 1)×10^−9^ |
| 参考通道 | 直达波信噪比30 dB，经解调—再调制提纯 |
| 监视通道 | 直达波泄漏40 dB，8条多径杂波15~33 dB，热噪声 |
| 接收站参数 | 监视天线增益10 dBi，噪声系数5 dB，系统损耗5 dB |
| 目标 | 小型无人机，尺寸0.35 m，RCS 0.1 m²，位置(4.0, 28.0, 1.5) km，速度(−25, −30, 0) m/s |
| CPI / 批处理 | 0.25 s（820个OFDM符号）/ 1024批×1845样点 |
| ECA抽头 | −16~79个样点 |
| 通道相位标定残差 | 5°（标准差） |

各链路的几何参数与输出信噪比见表4。由于T1的辐射功率为T2的两倍，T1各链路的信噪比约高3 dB；单链路输出信噪比为 {{E:min(T['links']['snr_db'])|.1f}}~{{E:max(T['links']['snr_db'])|.1f}} dB，按 $P_{fa}=10^{-6}$ 均不足以可靠检测。实测信噪比较预测值平均低约 {{E:-sum(S['gain']['snr_link_meas_db'][q]-S['gain']['snr_link_design_db'][q] for q in range(10))/10|.1f}} dB，主要来自时延—多普勒跨单元损失、对消损失与目标散射幅度在链路间的起伏。

Table: 表4 各链路几何参数与输出信噪比

| 链路 | 双基地距离差/km | 多普勒/Hz | 双基地角/(°) | 预测SNR/dB | 实测SNR/dB |
|:----:|:----:|:----:|:----:|:----:|:----:|
| T1R1 | {{T:links/R_km/0|.2f}} | {{T:links/fd_hz/0|.1f}} | {{T:links/beta_deg/0|.1f}} | {{T:links/snr_db/0|.2f}} | {{E:S['gain']['snr_link_meas_db'][0]-10|.2f}} |
| T1R2 | {{T:links/R_km/1|.2f}} | {{T:links/fd_hz/1|.1f}} | {{T:links/beta_deg/1|.1f}} | {{T:links/snr_db/1|.2f}} | {{E:S['gain']['snr_link_meas_db'][1]-10|.2f}} |
| T1R3 | {{T:links/R_km/2|.2f}} | {{T:links/fd_hz/2|.1f}} | {{T:links/beta_deg/2|.1f}} | {{T:links/snr_db/2|.2f}} | {{E:S['gain']['snr_link_meas_db'][2]-10|.2f}} |
| T1R4 | {{T:links/R_km/3|.2f}} | {{T:links/fd_hz/3|.1f}} | {{T:links/beta_deg/3|.1f}} | {{T:links/snr_db/3|.2f}} | {{E:S['gain']['snr_link_meas_db'][3]-10|.2f}} |
| T1R5 | {{T:links/R_km/4|.2f}} | {{T:links/fd_hz/4|.1f}} | {{T:links/beta_deg/4|.1f}} | {{T:links/snr_db/4|.2f}} | {{E:S['gain']['snr_link_meas_db'][4]-10|.2f}} |
| T2R1 | {{T:links/R_km/5|.2f}} | {{T:links/fd_hz/5|.1f}} | {{T:links/beta_deg/5|.1f}} | {{T:links/snr_db/5|.2f}} | {{E:S['gain']['snr_link_meas_db'][5]-10|.2f}} |
| T2R2 | {{T:links/R_km/6|.2f}} | {{T:links/fd_hz/6|.1f}} | {{T:links/beta_deg/6|.1f}} | {{T:links/snr_db/6|.2f}} | {{E:S['gain']['snr_link_meas_db'][6]-10|.2f}} |
| T2R3 | {{T:links/R_km/7|.2f}} | {{T:links/fd_hz/7|.1f}} | {{T:links/beta_deg/7|.1f}} | {{T:links/snr_db/7|.2f}} | {{E:S['gain']['snr_link_meas_db'][7]-10|.2f}} |
| T2R4 | {{T:links/R_km/8|.2f}} | {{T:links/fd_hz/8|.1f}} | {{T:links/beta_deg/8|.1f}} | {{T:links/snr_db/8|.2f}} | {{E:S['gain']['snr_link_meas_db'][8]-10|.2f}} |
| T2R5 | {{T:links/R_km/9|.2f}} | {{T:links/fd_hz/9|.1f}} | {{T:links/beta_deg/9|.1f}} | {{T:links/snr_db/9|.2f}} | {{E:S['gain']['snr_link_meas_db'][9]-10|.2f}} |

注：实测SNR为 {{S:gain/n_trials|d}} 次独立试验的统计平均（试验中目标RCS提高10 dB以降低统计起伏，表中已折算回原条件）。

## 7.2 单站处理结果

以接收站R1对信号源T1的处理为例。参考信号经解调—再调制提纯后，与无噪声直达波的相对误差由原始参考信号的 {{S:station/raw_err_db|.1f}} dB 降至 {{S:station/purify_err_db|.1f}} dB。监视通道经ECA对消后，信号功率由高于热噪声 {{S:station/pow_before_db|.1f}} dB 降至高于热噪声 {{S:station/pow_after_db|.2f}} dB，直达波与多径杂波被抑制到噪声电平以下。图6为ECA对消前后的距离—多普勒图：对消前直达波及其距离—多普勒旁瓣抬高了整个平面的底噪（高出热噪声约30~40 dB），对消后底噪回到热噪声电平，仅零多普勒附近残留微弱杂波，而目标（单链路信噪比约7 dB）仍淹没在噪声起伏之中。

![图6 接收站R1对信号源T1的距离—多普勒图：(a) ECA对消前；(b) ECA对消后](figures/sig_station_eca.png){width=15cm}

图7为10条链路在目标附近的距离—多普勒图（括号内为该链路的预测输出信噪比）。各链路的信噪比为 {{E:min(T['links']['snr_db'])|.1f}}~{{E:max(T['links']['snr_db'])|.1f}} dB，目标在单链路图中均无法与噪声峰区分。

![图7 10条链路目标附近的距离—多普勒图（坐标原点为目标真实位置）](figures/sig_link_maps.png){width=15.5cm}

## 7.3 融合检测结果

在目标高度与速度已知的水平面内（以目标为中心±1.5 km，网格间隔10 m），分别计算单链路统计量、非相参融合统计量与“粗—精”两级相参融合统计量，并以 $P_{fa}=10^{-6}$ 的检测门限归一化，结果如图8所示（红色等值线为门限）。单链路T1R1在目标处的统计量低于门限 {{E:-S['maps']['single']['margin_db']|.1f}} dB，无法检测；非相参融合高出门限 {{S:maps/nc/margin_db|.1f}} dB；相参融合高出门限 {{S:maps/coh/margin_db|.1f}} dB，检测裕量最大。相参融合图的背景整体抬高，是每个10 m粗单元内对精细位置取最大值的结果，其门限已按式({{eq:etac}})提高（由背景统计得到每个粗单元的等效独立精细位置数约为 {{S:maps/m_cell|.0f}}）。在距目标300 m以外的背景区（约9万个单元）中，非相参融合图没有超门限单元；相参融合图有 {{S:maps/coh/n_exceed_bg|d}} 个超门限单元，位于目标的非相参模糊带内（距目标约 {{E:(S['maps']['coh']['exceed_xy_m'][0][0]**2+S['maps']['coh']['exceed_xy_m'][0][1]**2)**0.5|.0f}} m，该处非相参统计量仅比门限低 {{E:-S['maps']['coh']['exceed_nc_db'][0]|.1f}} dB），是目标相参响应的栅瓣（见图10）而非噪声虚警。因此，相参检测输出应在非相参分辨单元内进行局部最大值聚类，以剔除栅瓣引起的邻近虚假检测。

![图8 目标所在水平面内的检测统计量（归一化至Pfa=10^−6^门限）：(a) 单链路；(b) 10链路非相参融合；(c) 10链路相参融合](figures/sig_fusion_maps.png){width=15.5cm}

图9为目标附近±25 m范围内以0.1 m间隔计算的精细融合图。非相参融合的峰沿横向展宽达数百米，相参融合则呈现以波长为尺度的干涉条纹，主峰位于 ({{S:fine/peak_dx|.1f}}, {{S:fine/peak_dy|.1f}}) m，与目标真实位置的偏差小于1 m，体现了相参处理的波长级定位能力^\[7\]^；若不标定通道相位 $\kappa_l$（图9(c)），条纹结构被打乱，峰值降低并偏离目标位置。

![图9 目标附近的精细融合图：(a) 非相参融合；(b) 相参融合（已标定）；(c) 相参融合（未标定通道相位）](figures/sig_fine_maps.png){width=15.5cm}

图10为点目标在本系统几何下的非相参与相参融合模糊函数。非相参融合的−3 dB主瓣面积约 {{T:ambiguity/area_nc_m2|.0f}} m²，相参融合主瓣面积仅约 {{T:ambiguity/area_c_m2|.1f}} m²，二者相差约 {{T:ambiguity/ratio|.0f}} 倍；但由于只有10条链路且站址稀疏，相参模糊函数在非相参包络内存在大量栅瓣，最高旁瓣仅比主瓣低 {{E:-T['ambiguity']['psl_c_db']|.1f}} dB。这说明相参融合必须与非相参包络约束（粗检测）配合使用，同时也解释了6.4节精搜索代价的来源。

![图10 点目标的融合模糊函数：(a) 非相参融合；(b) 相参融合；(c) 相参融合主瓣附近](figures/st_ambiguity.png){width=15.5cm}

## 7.4 信噪比增益测量

为降低统计起伏，将目标RCS提高10 dB，进行 {{S:gain/n_trials|d}} 次独立试验（每次试验的OFDM数据、信号源与接收站相位、通道相位、噪声与杂波均重新随机生成），在目标真实状态处测量各融合方式的输出信噪比，结果见表5与图11。

Table: 表5 输出信噪比增益测量结果（目标RCS提高10 dB）

| 融合方式 | 实测输出SNR/dB | 理论值/dB | 相对单链路平均值的增益/dB |
|:------|:----:|:----:|:----:|
| 单链路（平均） | {{S:gain/mean_link_db|.2f}} | — | 0 |
| 最佳单链路 | {{S:gain/best_link_db|.2f}} | — | {{E:S['gain']['best_link_db']-S['gain']['mean_link_db']|.2f}} |
| 源间相参（R2站两源） | {{S:gain/pair_db/1|.2f}} | {{S:gain/pair_sum_db/1|.2f}} | {{E:S['gain']['pair_db'][1]-S['gain']['mean_link_db']|.2f}} |
| 站间相参（T1五站） | {{S:gain/grp_db/0|.2f}} | {{S:gain/grp_sum_db/0|.2f}} | {{E:S['gain']['grp_db'][0]-S['gain']['mean_link_db']|.2f}} |
| 10链路相参（MRC权） | {{S:gain/tc_db|.2f}} | {{S:gain/sum_link_db|.2f}} | {{S:gain/tc_gain_db|.2f}} |
| 10链路相参（等增益权） | {{S:gain/tc_eq_db|.2f}} | {{E:10*log10(sum(10**(x/20) for x in S['gain']['snr_link_meas_db'])**2/10)|.2f}} | {{S:gain/tc_eq_gain_db|.2f}} |
| 10链路相参（未标定 $\kappa_l$） | {{S:gain/tc_nocal_db|.2f}} | ≈{{S:gain/mean_link_db|.1f}} | {{S:gain/tc_nocal_gain_db|.2f}} |
| 10链路相参（参考不含直达波相位） | {{S:gain/tc_x_db|.2f}} | ≈{{S:gain/mean_link_db|.1f}} | {{S:gain/tc_x_gain_db|.2f}} |

结果表明：

（1）10条链路以MRC权相参融合后，输出信噪比为 {{S:gain/tc_db|.2f}} dB，与各链路实测信噪比之和 {{S:gain/sum_link_db|.2f}} dB 仅相差 {{E:abs(S['gain']['tc_db']-S['gain']['sum_link_db'])|.2f}} dB，相对单链路平均值的增益为 {{S:gain/tc_gain_db|.2f}} dB（理论值10 dB，统计标准误差约 {{S:gain/tc_se_db|.2f}} dB），相对最佳单链路的增益为 {{E:S['gain']['tc_db']-S['gain']['best_link_db']|.2f}} dB，验证了式({{eq:snrc}})。等增益合并的增益为 {{S:gain/tc_eq_gain_db|.2f}} dB，较MRC仅低约 {{E:S['gain']['tc_gain_db']-S['gain']['tc_eq_gain_db']|.1f}} dB，说明链路信噪比差异不大时可不依赖精确的链路信噪比预测；

（2）源间相参（同一接收站两个信号源的链路）与站间相参（同一信号源五个接收站的链路）的实测输出信噪比均与相应链路信噪比之和吻合，表明两个信号源之间虽无任何同步，其回波仍可在信号层面相参合成；

（3）若不标定通道相位 $\kappa_l$，或提纯参考信号中不保留直达波相位（相当于不以本站直达波为相位基准），相参增益仅为 {{S:gain/tc_nocal_gain_db|.1f}} dB 与 {{S:gain/tc_x_gain_db|.1f}} dB，基本丧失。这从反面证明：本方案“无需信号源同步”的前提是每条链路以本站直达波为相位基准，并完成通道相位标定。

![图11 信噪比增益测量结果：(a) 各链路输出信噪比；(b) 各融合方式的输出信噪比](figures/sig_gain.png){width=15.5cm}

## 7.5 相参条件的验证

图12为相参融合损失随各类同步与几何误差的变化（蒙特卡罗统计）。（a）接收站频率基准相对误差小于 $10^{-7}$ 时损失可以忽略，相对误差为 $10^{-6}$ 时损失约 {{T:sync/eps_loss_1e-6_db|.1f}} dB，更大时迅速恶化，因此须采用GNSS驯服频率基准；（b）站间时间同步误差在百微秒量级以下时对本例目标（多普勒约155 Hz）的影响可以忽略，对多普勒1 kHz的高速目标要求约 {{E:T['sync']['dt_for_0.5db_1khz']*1e6|.0f}} μs 以内，GNSS授时的精度（约50 ns）裕量很大；（c）、（d）未标校时，接收站与信号源天线相位中心位置误差分别需小于约 {{T:sync/rx_pos_for_0.5db_cm|.1f}} cm 与 {{T:sync/tx_pos_for_0.5db_cm|.1f}} cm，对非合作信号源而言难以直接满足，需要依靠6.6节的标校。

![图12 同步与几何误差对相参融合的影响：(a) 频率基准；(b) 时间同步；(c) 接收站站址；(d) 信号源站址](figures/st_sync.png){width=14cm}

图13为相参融合增益随链路残余相位误差的变化，蒙特卡罗结果与式({{eq:phaseloss}})的理论曲线一致：残余相位误差标准差为 {{T:sync/sigma_for_0.5db|.0f}}° 与 {{T:sync/sigma_for_1db|.0f}}° 时，相参增益分别下降0.5 dB与1 dB；相位误差为均匀随机分布（即未标定）时，增益趋于0 dB。

![图13 相参融合增益与残余相位误差的关系](figures/st_phase_err.png){width=8.5cm}

两个信号源之间的条件已由图2给出。本例两源载频差8 MHz、对目标张角 {{T:two_source/this_dtheta_deg|.1f}}°，按式({{eq:rho}})计算，同一接收站两源链路之间的散射相关系数：尺寸0.35 m的目标约为 {{T:coherence_pair/0.35/mean|.3f}}，1 m的目标约为 {{T:coherence_pair/1/mean|.2f}}，均满足源间相参条件；3 m的目标降至约 {{T:coherence_pair/3/mean|.2f}}，10 m的目标仅约 {{T:coherence_pair/10/mean|.2f}}，源间相参的收益明显下降。

## 7.6 检测性能

在CAF输出层进行蒙特卡罗仿真（每个信噪比点40000次），比较不同融合方式在 $P_{fa}=10^{-6}$（以非相参分辨单元计）下的检测概率。相参类统计量的门限按式({{eq:etac}})计入精搜索代价，其中等效独立单元数之比由噪声随机场仿真得到：全相参 $M\approx$ {{T:multiplicity/coh/ratio|.0f}}，站间相参 $M\approx$ {{T:multiplicity/grp/ratio|.0f}}，源间相参 $M\approx$ {{T:multiplicity/pair/ratio|.1f}}。链路间的信噪比分布按表4。检测概率曲线如图14所示，$P_d=0.9$ 所需的单链路平均信噪比见表6。

![图14 检测概率曲线（Pfa=10^−6^）：(a) 点目标；(b) 尺寸3 m的扩展目标](figures/st_pd.png){width=15.5cm}

Table: 表6 Pd=0.9、Pfa=10^−6^ 所需的单链路平均输出信噪比（dB）

| 融合方式 | 点目标（非起伏） | 扩展目标 $L_t$=3 m（起伏、部分相参） |
|:------|:----:|:----:|
| 最佳单链路 | {{T:pd/req_snr_db/point/single|.1f}} | >16 |
| 非相参融合 | {{T:pd/req_snr_db/point/nc|.1f}} | {{T:pd/req_snr_db/ext3/nc|.1f}} |
| 源间相参 + 站间非相参 | {{T:pd/req_snr_db/point/pair|.1f}} | {{T:pd/req_snr_db/ext3/pair|.1f}} |
| 站间相参 + 源间非相参 | {{T:pd/req_snr_db/point/grp|.1f}} | {{T:pd/req_snr_db/ext3/grp|.1f}} |
| 10链路相参（含精搜索代价） | {{T:pd/req_snr_db/point/coh|.1f}} | {{T:pd/req_snr_db/ext3/coh|.1f}} |
| 10链路相参（目标位置已知至亚波长） | {{T:pd/req_snr_db/point/coh_ideal|.1f}} | {{T:pd/req_snr_db/ext3/coh_ideal|.1f}} |
| 10链路相参，残余相位误差30° | {{T:pd/req_snr_db/point/coh_perr|.1f}} | {{T:pd/req_snr_db/ext3/coh_perr|.1f}} |
| 相参/非相参双支路 | {{T:pd/req_snr_db/point/or|.1f}} | {{T:pd/req_snr_db/ext3/or|.1f}} |

由图14和表6可得：

（1）对点目标，10链路相参融合所需信噪比比最佳单链路检测低 {{E:T['pd']['req_snr_db']['point']['single']-T['pd']['req_snr_db']['point']['coh']|.1f}} dB，比非相参融合低 {{T:derived/coh_vs_nc_db|.1f}} dB；以目标位置已知至亚波长量级（不需精搜索）为理想上限，还可再降低约 {{E:T['pd']['req_snr_db']['point']['coh']-T['pd']['req_snr_db']['point']['coh_ideal']|.1f}} dB，相对非相参融合的优势为 {{T:derived/cohideal_vs_nc_db|.1f}} dB。理想相参融合相对非相参融合的优势本质上来自非相参积累损失，在本例 $L=10$ 时约为2 dB，链路数或与时域积累组合后的积累数越多，优势越大（7.8节）；

（2）残余相位误差30°时，相参融合的优势基本消失（{{T:pd/req_snr_db/point/coh_perr|.1f}} dB，劣于非相参融合），再次说明通道标定的重要性；

（3）对尺寸3 m的扩展目标，链路间散射部分去相关，10链路相参融合所需信噪比反而比非相参融合高 {{E:T['pd']['req_snr_db']['ext3']['coh']-T['pd']['req_snr_db']['ext3']['nc']|.1f}} dB，非相参融合因获得空间分集而最优；

（4）相参/非相参双支路检测在两种情况下所需信噪比分别为 {{T:pd/req_snr_db/point/or|.1f}} dB 与 {{T:pd/req_snr_db/ext3/or|.1f}} dB，与两者中的较优者相差不超过 {{E:max(T['pd']['req_snr_db']['point']['or']-T['pd']['req_snr_db']['point']['coh'], T['pd']['req_snr_db']['ext3']['or']-T['pd']['req_snr_db']['ext3']['nc'])|.1f}} dB，是目标尺寸未知时的稳健选择。

## 7.7 目标尺寸与布站尺度的影响

图15(a)为10链路相参融合的平均输出信噪比增益随目标尺寸的变化：尺寸不超过约0.7 m时增益保持在9.9 dB以上，尺寸1 m时为 {{T:size/mean_gain_db/5|.1f}} dB，3 m时为 {{T:size/mean_gain_db/8|.1f}} dB，10 m时仅为 {{T:size/mean_gain_db/11|.1f}} dB。图15(b)为起伏目标在 $P_d=0.9$、$P_{fa}=10^{-6}$ 下所需的单链路平均信噪比：尺寸小于约0.7 m时全相参融合所需信噪比最低（与站间相参相当，如0.35 m时全相参、站间相参与非相参分别需 {{T:size/req_snr_db/coh/2|.1f}} dB、{{T:size/req_snr_db/grp/2|.1f}} dB 与 {{T:size/req_snr_db/nc/2|.1f}} dB），由于此时各链路随目标起伏同步衰落，非相参融合无法获得分集增益；尺寸约1 m时二者相当；尺寸更大时非相参融合因空间分集而明显占优（10 m时全相参与非相参分别需 {{T:size/req_snr_db/coh/11|.1f}} dB 与 {{T:size/req_snr_db/nc/11|.1f}} dB）；源间相参与站间相参介于二者之间；双支路检测始终接近两者中的较优者。

![图15 目标尺寸的影响：(a) 相参融合平均增益；(b) 检测所需单链路平均信噪比](figures/st_size.png){width=15.5cm}

图16为布站尺度的影响：保持目标位置不变，将接收站群和两信号源间距同比例缩放。本例布站（接收站分布范围约 {{T:layout/at/1/rx_extent_km|.1f}} km）下，0.35 m、1 m、3 m目标的相参平均增益分别为 {{T:layout/at/1/0.35|.1f}} dB、{{T:layout/at/1/1|.1f}} dB 与 {{T:layout/at/1/3|.1f}} dB；布站尺度扩大到4倍（约 {{T:layout/at/4/rx_extent_km|.0f}} km）时，分别降为 {{T:layout/at/4/0.35|.1f}} dB、{{T:layout/at/4/1|.1f}} dB 与 {{T:layout/at/4/3|.1f}} dB。因此，若以小型无人机为主要探测对象并追求10链路全相参，接收站群应相对紧凑（相对目标的张角不超过数度），两信号源宜同址或近址；若布站分散以追求定位几何与覆盖，则应以非相参或分组相参为主。

![图16 布站尺度对10链路相参融合增益的影响](figures/st_layout.png){width=8.5cm}

## 7.8 三维相参组合增益

设总积累时间划分为 $K=4$ 个子CPI，与 $L=10$ 条链路共构成40个“基本积累单元”。按时域、源间、站间三个维度分别采用相参或非相参累加，点目标在 $P_d=0.9$、$P_{fa}=10^{-6}$ 下所需的基本单元信噪比及相对单个单元（所需 {{T:combo/single_req_db|.1f}} dB）的检测增益见表7。

Table: 表7 时域×源×站三维相参组合的检测增益（K=4，L=10，点目标，不计精搜索代价）

| 组合方式 | 非相参累加项数 | 每项相参单元数 | 所需单元SNR/dB | 检测增益/dB |
|:------|:----:|:----:|:----:|:----:|
| {{T:combo/rows/0/name}} | {{T:combo/rows/0/pieces|d}} | {{T:combo/rows/0/coherent|d}} | {{T:combo/rows/0/req_elem_db|.2f}} | {{T:combo/rows/0/gain_db|.2f}} |
| {{T:combo/rows/1/name}} | {{T:combo/rows/1/pieces|d}} | {{T:combo/rows/1/coherent|d}} | {{T:combo/rows/1/req_elem_db|.2f}} | {{T:combo/rows/1/gain_db|.2f}} |
| {{T:combo/rows/2/name}} | {{T:combo/rows/2/pieces|d}} | {{T:combo/rows/2/coherent|d}} | {{T:combo/rows/2/req_elem_db|.2f}} | {{T:combo/rows/2/gain_db|.2f}} |
| {{T:combo/rows/3/name}} | {{T:combo/rows/3/pieces|d}} | {{T:combo/rows/3/coherent|d}} | {{T:combo/rows/3/req_elem_db|.2f}} | {{T:combo/rows/3/gain_db|.2f}} |
| {{T:combo/rows/4/name}} | {{T:combo/rows/4/pieces|d}} | {{T:combo/rows/4/coherent|d}} | {{T:combo/rows/4/req_elem_db|.2f}} | {{T:combo/rows/4/gain_db|.2f}} |
| {{T:combo/rows/5/name}} | {{T:combo/rows/5/pieces|d}} | {{T:combo/rows/5/coherent|d}} | {{T:combo/rows/5/req_elem_db|.2f}} | {{T:combo/rows/5/gain_db|.2f}} |
| {{T:combo/rows/6/name}} | {{T:combo/rows/6/pieces|d}} | {{T:combo/rows/6/coherent|d}} | {{T:combo/rows/6/req_elem_db|.2f}} | {{T:combo/rows/6/gain_db|.2f}} |
| {{T:combo/rows/7/name}} | {{T:combo/rows/7/pieces|d}} | {{T:combo/rows/7/coherent|d}} | {{T:combo/rows/7/req_elem_db|.2f}} | {{T:combo/rows/7/gain_db|.2f}} |

全部非相参时检测增益为 {{T:combo/rows/0/gain_db|.1f}} dB，比三维全相参的理论值 {{T:combo/rows/7/gain_db|.1f}} dB 低约 {{E:T['combo']['rows'][7]['gain_db']-T['combo']['rows'][0]['gain_db']|.1f}} dB；在时域非相参（如目标机动导致子CPI间无法相参）的情况下，10链路相参融合仍可将检测增益提高到 {{T:combo/rows/4/gain_db|.1f}} dB。可见，非相参累加项数越多，链路间相参融合带来的收益越大；在三个维度中优先保证条件最容易满足的维度相参（一般首先是时域，其次是相对目标张角较小的源间或站间维度），是逐步实现“三维相参融合”的可行途径。

# 8 结论与工程实施建议

本文以被动MIMO雷达网络集中式检测与空间相参多基地检测理论为依据，提出了2发5收分布式探测系统10条链路的相参融合检测方案，主要结论如下：

（1）**两个信号源之间无需时间同步与相位锁定。**各接收站以本站接收的该信号源直达波为相位基准完成互模糊处理，信号源的初相、载频偏差、相位噪声以及接收机本振相位均自动抵消。两信号源需要满足的是：同时、连续照射；宽带类噪声、带宽相近、可分离且直达波可获取；CPI内相位连续；载频差与两源相对目标的视角差满足式({{eq:dfcond}})、式({{eq:dthcond}})的散射相参条件（宜选同址或近址、相邻信道的信号源）。

（2）**接收站侧的关键条件**是GNSS驯服的频率基准（相对误差远小于 $10^{-6}$）、统一的CPI中心时刻（GNSS授时即可满足）、参考与监视通道同源本振与时钟、天线相位中心的厘米级站址精度以及残余相位误差不超过约20°的通道相位标定；非合作信号源的站址误差须通过合作目标标校消除。

（3）**各站处理流程**为：同步采样与时间标记→多源分离与参数估计→保留直达波相位的参考信号提纯→双边抽头ECA对消→以CPI中心为相位基准的批处理互模糊函数→通道相位标定与噪声归一化→上报复数距离—多普勒图。

（4）**融合算法**在目标状态空间先非相参粗检测、再相位补偿与亚波长精搜索，按目标散射相参性选择全相参、分组相参或非相参融合，或采用相参/非相参双支路检测。仿真表明10链路相参融合的输出信噪比增益为 {{S:gain/tc_gain_db|.2f}} dB（理论10 dB），对点状小目标的检测灵敏度优于非相参融合，并具有波长级定位能力；对尺寸较大的目标非相参融合更优，双支路检测在各种情况下均接近最优。

工程实施建议：

（1）选择信号源时，优先选用同一发射塔的相邻信道或从监视区看去方位相近的信号源，避免节目切换和相位跳变；

（2）接收站统一配置GNSS驯服铷钟或恒温晶振，参考与监视通道严格同源，并以RTK测量天线相位中心；

（3）建立“注入校准 + 直达波泄漏监测 + 合作无人机标校 + 强目标自校准”的分级相位标定体系，标校时联合估计非合作信号源的站址误差；

（4）以小型无人机为主要对象时，接收站群相对目标的张角宜控制在数度以内；需要兼顾大尺寸目标时，采用双支路或分组相参融合；

（5）后续应利用实测数据验证链路间散射相参性与标定稳定性，并研究单频网同频信号源、低轨卫星等运动信号源（波长更短、相参条件更严格）以及跟踪辅助的长时间三维相参积累。

# 参考文献

::: {custom-style="参考文献"}
[1] Hack D E, Patton L K, Himed B, Saville M A. Detection in passive MIMO radar networks[J]. IEEE Transactions on Signal Processing, 2014, 62(11): 2999-3012.

[2] Hack D E, Patton L K, Himed B, Saville M A. Centralized passive MIMO radar detection without direct-path reference signals[J]. IEEE Transactions on Signal Processing, 2014, 62(11): 3013-3023.

[3] Liu J, Li H, Himed B. Two target detection algorithms for passive multistatic radar[J]. IEEE Transactions on Signal Processing, 2014, 62(22): 5930-5939.

[4] Derham T E, Doughty S, Baker C J, Woodbridge K. Ambiguity functions for spatially coherent and incoherent multistatic radar[J]. IEEE Transactions on Aerospace and Electronic Systems, 2010, 46(1): 230-245.

[5] Fishler E, Haimovich A, Blum R S, Cimini L J, Chizhik D, Valenzuela R A. Spatial diversity in radars—models and detection performance[J]. IEEE Transactions on Signal Processing, 2006, 54(3): 823-838.

[6] Haimovich A M, Blum R S, Cimini L J. MIMO radar with widely separated antennas[J]. IEEE Signal Processing Magazine, 2008, 25(1): 116-129.

[7] Godrich H, Haimovich A M, Blum R S. Target localization accuracy gain in MIMO radar-based systems[J]. IEEE Transactions on Information Theory, 2010, 56(6): 2783-2803.

[8] Godrich H, Haimovich A M, Poor H V. An analysis of phase synchronization mismatch sensitivity for coherent MIMO radar systems[C]//Proceedings of the 3rd IEEE International Workshop on Computational Advances in Multi-Sensor Adaptive Processing (CAMSAP). Aruba, 2009.

[9] Gogineni S, Rangaswamy M, Rigling B D, Nehorai A. Ambiguity function analysis for UMTS-based passive multistatic radar[J]. IEEE Transactions on Signal Processing, 2014, 62(11): 2945-2957.

[10] Coutts S, Cuomo K, McHarg J, Robey F, Weikle D. Distributed coherent aperture measurements for next generation BMD radar[C]//Fourth IEEE Workshop on Sensor Array and Multichannel Processing. Waltham, MA, 2006: 390-393.

[11] 周宝亮, 周东明, 高红卫, 杨杰. 分布式孔径相参合成雷达联合天线增益分析[J]. 雷达学报, 2017, 6(4): 332-339.

[12] 万显荣, 孙绪望, 易建新, 吕敏, 饶云华. 分布式数字广播电视外辐射源雷达系统同步设计与测试[J]. 雷达学报, 2017, 6(1): 65-72.

[13] Zheng Y, Zhang Z, Feng L, Zhu P, Zhou F. Enhanced passive GNSS-based radar imaging based on coherent integrated multi-satellite signals[J]. Sensors, 2020, 20(3): 842.

[14] Colone F, O'Hagan D W, Lombardo P, Baker C J. A multistage processing algorithm for disturbance removal and target detection in passive bistatic radar[J]. IEEE Transactions on Aerospace and Electronic Systems, 2009, 45(2): 698-722.

[15] Palmer J E, Harms H A, Searle S J, Davis L M. DVB-T passive radar signal processing[J]. IEEE Transactions on Signal Processing, 2013, 61(8): 2116-2126.

[16] Xu J, Yu J, Peng Y N, Xia X G. Radon-Fourier transform for radar target detection, I: generalized Doppler filter bank[J]. IEEE Transactions on Aerospace and Electronic Systems, 2011, 47(2): 1186-1202.

[17] Malanowski M, Kulpa K. Two methods for target localization in multistatic passive radar[J]. IEEE Transactions on Aerospace and Electronic Systems, 2012, 48(1): 572-580.

[18] Griffiths H D, Baker C J. Passive coherent location radar systems. Part 1: performance prediction[J]. IEE Proceedings - Radar, Sonar and Navigation, 2005, 152(3): 153-159.

[19] Kay S M. Fundamentals of statistical signal processing, volume II: detection theory[M]. Upper Saddle River, NJ: Prentice Hall, 1998.

[20] Richards M A. Fundamentals of radar signal processing[M]. 2nd ed. New York: McGraw-Hill, 2014.

[21] Willis N J. Bistatic radar[M]. 2nd ed. Raleigh, NC: SciTech Publishing, 2005.

[22] 本项目技术说明. 信号源参数精确估计技术——基于低轨卫星OFDM信号盲识别的原理与验证[R]. 2026.
:::
