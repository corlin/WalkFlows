# 实施与验收

状态：规划中｜更新：2026-11-06

默认技术路线与设备约束见 [MVP 决策记录](05-mvp-decisions.md)。用户已确认首版用于内部研究与原型验证；具体资源许可仍需核验。

2026-11-07：原生 Retail Customer Tracking 已在 CITIC Showroom 的 97–107 秒片段试运行并输出轨迹、区域与视频；存在确认前后统计口径差异，见 [上游验证](09-upstream-validation.md)。多镜头接入仍未验收。

2026-11-07：按用户要求先在 Mac 上使用 site02；配套 C++ 上游 CPU 配置遇到缺少 OpenCV C++ 开发包，已有单镜头组件可处理两路左眼短片。结果及限制见 [视频筛选](10-retail-video-selection.md)。

以下顺序面向离线演示与技术评估，具体状态见表格。精度和性能阈值需在检查参考数据及目标硬件后约定，不能预先承诺。

当前先补做参考项目调研，再决定后续实现；已完成的短片段运行只作为探索性证据，不代表完成了项目选型。

| 编号 | 状态 | 任务 | 产出 / 完成条件 |
| --- | --- | --- | --- |
| W01 | 待开始 | 明确 MVP 演示用途、运行硬件及许可边界 | 记录目标环境、资源选择和许可结论；如涉及商业用途先确认数据授权。 |
| W02 | 进行中 | 检查并准备 CITIC 子集 | 已获取 capture1 两路大厅视频并通过 ZIP CRC，完成元数据和单帧解码检查；仍需验证画面时序、标定投影及参考标注对齐，见 [检查记录](06-citic-inspection.md)。 |
| W03 | 进行中 | 建立可复现运行环境 | 已建立 uv、Python 3.12.9 和基础解码依赖锁文件，短片段可抽帧；模型权重和干净环境复现仍待验证。 |
| W04 | 进行中 | 人员检测与单摄像头跟踪 | 两路各 10 秒已输出轨迹和回放；准确率尚未评估，待核查参考覆盖及对照其他开源模型。见 [基线结果](07-baseline-results.md)。 |
| W05 | 进行中 | 平面坐标及点位配置 | 利用已有标定映射坐标，在平面图定义区域；报告可测的定位误差及无效覆盖。 |
| W06 | 进行中 | 多摄像头关联与去重 | 已生成未合并的同帧空间候选；同步、定位和身份尚未验证，不能作为去重结果。 |
| W07 | 进行中 | 区域事件与质量规则 | 输出进入、离开、停留、转移，处理边界抖动、缺口和遮挡；检查重复与可复算性。 |
| W08 | 进行中 | 分析与可视化 | 平面回放、两种热力图、点位统计、区域路线、旅程与质量说明；指标与明细可核对。 |
| W09 | 待开始 | 模拟业务漏斗 | 如需要，加入带显著标识的模拟咨询/成交事件，展示漏斗与来源；不能与真实观测混淆。 |
| W10 | 待开始 | 综合验收与决策 | 对照参考数据输出误差、缺口、限制、运行耗时及复现步骤；判断是否增加 NVIDIA 零售子集。 |

## 验收原则

- 从指定公开样本到图表可重复运行，记录配置、版本、数据来源和时间区间。
- 轨迹、区域事件和聚合数能相互追溯；无法观测和不确定的部分不伪装成确定事实。
- 检测、位置、关联和业务指标分开评估；优先使用数据集已有标注，不新增标注或训练。
- 交付说明包含许可状态、模拟数据标识、硬件与耗时、已知误差及不适用场景。

## 待确认事项

- 对外演示或商业交付前，重新核对数据与组件许可。
- 目标运行设备、可用磁盘及期望处理速度是什么？
- 第一版是否必须展示跨摄像头连续轨迹，还是允许不确定时显示断点？
- ScreenFlows 采用代码复用、数据接口对接还是仅参考业务逻辑？待检查接口与许可后确定。

## 2026-11-07 WSL continuation

Work now uses corlin at /home/corlin/WalkFlows. W03: pinned environment and both GPUs pass arithmetic/NMS checks; clean reproduction and video inference remain outstanding. W04: full site02 baseline remains outstanding. See [review](12-wsl-progress-review.md). Historical Mac results remain historical evidence.

2026-11-07: W04 now has full 218-frame left-eye GPU runs on both site02 cameras, with conf=0.25/0.10 controls. This verifies runtime and artifact coverage, not identity accuracy. W05/W06 remain unvalidated. See [GPU experiment](13-site02-gpu-baseline.md).

2026-11-07: completed independent gap diagnostics and 640/960 control. Rejected 960 for the current two-view baseline because camera 2 tracking coverage worsens; no accuracy claim. W05/W06 remain unvalidated. See [gap diagnosis](14-site02-gap-diagnosis.md).

2026-11-07: W05 in progress. Scene/binocular models recovered; dimensions, distortion model, hull domain and reference boundary checked. Floor projection and W06 fusion remain unvalidated. See 15-site02-calibration-contract.md.

2026-11-07: W05 verified source transform inversion and reference grid-to-floor formula; exported 218 reference points without clipping. All lie in closed scene bounds. Video projection remains unvalidated; see 16-site02-reference-and-transforms.md.

2026-11-07: W05 now has compiled native lift-vs-analytic comparison (5 inputs, 45 terms, max error 8.9e-16), with source hashes. Full camera geometry remains unvalidated. Offline acceptance checks now cover all six experiment videos and ledgers; see 17-native-lift-and-reproduction.md.

2026-11-07: W05 has an executable source-aligned experimental projection with upstream native polynomial lift; all gates pass 219/227 and 144/191 local observations. Physical positioning remains unvalidated; W06 fusion stays pending. See 18-experimental-floor-projection.md.

2026-11-07: W05 domain review finds sampled outside-scene tracks in external corridor; retain bounds and separate rejected observations. W04 has a duplicate/fragmentation candidate (ID1/ID9), so local IDs cannot be treated as people. See 19-scene-domain-and-local-conflicts.md.

2026-11-07: native core comparison and fixed-support timing sensitivity completed; physical localization and synchronization remain unvalidated. Current next steps: 00-current-status.md; evidence: 20-native-geometry-and-consistency.md.

2026-11-07：完成双目极线自动匹配检查（支持 sensor0 顺序），跨相机经典特征匹配未达到证据要求；W05/W06 仍未验收。离线证据链扩展为 10 步，见 21 文档。

2026-11-07：完成218点双路参考反投影，以及固定 RetailVision 融合源码的不确定性对照。普通加权可能拉偏位置，uncertain也不等于忽略或成功去重；W05/W06仍未验收，见22/23文档。

2026-11-07：实现并测试观测质量契约/上游适配，保留完整数据、来源哈希和逐帧缺口。严格模式未放行未验证观测，W05/W06仍未验收；见25文档。

2026-11-08：完成两路全片姿态研究对照；第二路低脚踝置信度和匹配缺口仍显著，W05/W06未验收，见26文档。

2026-11-08：新增本地视频与参考路径回放、参考区域交互和可处理观测缺口的事件基础；仅为研究原型，不是业务验收。见 [本地回放与区域事件](29-local-review.md)。

2026-11-08：W08 新增基于现有单镜头观测的图像空间热图和交互筛选；不是地面热图或去重人数，见 [热图说明](31-image-heatmaps.md)。

2026-11-08：W05 本地研究布局支持多个矩形区域/点位、修订和 JSON 导入导出；物理定位、布局生效时间和正式业务事件仍未验收。见 [研究布局](33-research-layout.md)。

2026-11-08：W07 增加参考路径区域候选的可调时间/距离滞回与缺口重置；正式客户事件仍待定位、身份和事件质量验证。见 [滞回说明](35-reference-hysteresis.md)。

2026-11-08：W08 增加多区域参考候选时间线和回放跳转，重叠和缺口明确显示；正式轨迹、路线和漏斗仍未验收。见 [参考时间线](36-reference-route.md)。

2026-11-08：W07/W08 已将实际检测局部轨迹接入研究区域候选、质量门禁和可追溯导出，并修复回放定位时序；跨镜身份、正式平面定位及客户旅程仍未验收。见 [局部轨迹研究](37-local-track-events.md)。

2026-11-08：W04/W05/W06 增加六路 site03 基线、已有多人参考对照与保守跨镜候选；W08 增加双视角研究回放。时间/空间/身份真实性与正式业务统计仍待评估。见 [site03 结果](38-site03-multiview.md)。

2026-11-08：W05/W06 增加姿态脚点与框底点的条件对照及研究候选，W07/W08 接入 site03 局部轨迹区域配置与回放。参考选择偏差及严格质量门禁仍在，见 [姿态脚点研究](39-site03-pose-research.md)。

2026-11-08：W06–W08 贯通实验脚点候选、保守多镜研究轨迹、区域候选、热图与可追溯导出；正式身份/定位/业务统计仍未验收。见 [研究轨迹和分析](40-site03-journey-analytics.md)。

2026-11-08：W08 增加研究区域有序漏斗、可配置窗口与逐帧证据；不代表去重顾客或真实咨询/支付。见 [研究区域漏斗](41-site03-research-funnel.md)。

2026-11-08：W05/W06 完成 site02 跨场景脚点与研究回退对照；对照出现阈值敏感和覆盖不足，严格定位/身份仍未通过。见 [跨场景脚点研究](42-cross-scene-foot-policy.md)。
