# WalkFlows 文档索引

当前研发入口：[当前状态与下一步](00-current-status.md)。

状态：规划中｜更新：2026-11-06

WalkFlows 将多摄像头人员轨迹转换为门店空间触点和客户旅程，支持客流、热点、路线和点位盘点。当前目标是离线 MVP，不采集新数据、不自行标注、不训练模型。

| 文档 | 用途 |
| --- | --- |
| [产品与范围](01-product.md) | 目标、用户问题、MVP 范围和边界 |
| [技术方案](02-architecture.md) | 数据流、组件候选、事件模型和质量控制 |
| [数据与许可](03-data-and-licenses.md) | 数据、代码和模型来源及使用限制 |
| [实施与验收](04-roadmap.md) | 可跟踪任务、依赖、验收方法和待决事项 |
| [MVP 决策记录](05-mvp-decisions.md) | 首版默认选择、备选方案和决策依据 |
| [CITIC 数据检查](06-citic-inspection.md) | 数据包、标定、参考标注和本机环境的核查结果 |
| [模型基线结果](07-baseline-results.md) | 本机跟踪、候选关联、复现和模型对照 |
| [开源项目核查](08-open-source-review.md) | 四个项目的实际能力、限制与复用优先级 |
| [上游验证与新增候选](09-upstream-validation.md) | 本机组件测试、接入路径及其他开源项目 |
| [真实门店视频筛选](10-retail-video-selection.md) | 新样片来源、画面质量及适配边界 |

维护约定：任务状态使用「待开始 / 进行中 / 已完成 / 阻塞」；实现或决策变化时同步更新对应文档及实施清单。所有未验证的技术选择与效果均为候选或目标，不视为已实现。

## WSL continuation

- [Environment repair](11-wsl-environment.md)
- [Progress and critical review](12-wsl-progress-review.md)

- [Complete site02 GPU baseline and threshold control](13-site02-gpu-baseline.md)

- [Gap diagnosis and rejected resolution change](14-site02-gap-diagnosis.md)

- [Calibration contract audit](15-site02-calibration-contract.md)

- [Reference export and transform semantics](16-site02-reference-and-transforms.md)

- [Native lift and offline artifact acceptance](17-native-lift-and-reproduction.md)

- [Experimental floor projection and limitations](18-experimental-floor-projection.md)

- [Scene domain and local identity conflicts](19-scene-domain-and-local-conflicts.md)

- [Native geometry and cross-view consistency](20-native-geometry-and-consistency.md)

- [双目与跨相机图像证据](21-stereo-and-crossview-image-evidence.md)

- [参考反投影与标定版本契约](22-reference-reprojection-and-version-contract.md)
- [RetailVision 不确定性处理实测](23-retailvision-uncertainty-experiment.md)

- [观测质量契约与上游适配](25-observation-quality-adapter.md)

- [全片姿态对照](26-full-pose-comparison.md)

- [逐帧证据覆盖](27-frame-evidence-coverage.md)

- [site02 文件时间戳审计](28-timestamp-audit.md)

- [本地研究回放和区域事件](29-local-review.md)
- [单摄像头图像观测热图](31-image-heatmaps.md)

- [研究布局配置与导入导出](33-research-layout.md)

- [参考路径区域滞回](35-reference-hysteresis.md)

- [多区域参考候选时间线](36-reference-route.md)

- [局部轨迹区域研究与视频定位](37-local-track-events.md)

- [site03 六视角参考对照及跨镜候选](38-site03-multiview.md)

- [site03 姿态脚点与区域研究](39-site03-pose-research.md)

- [site03 多镜研究轨迹与空间分析](40-site03-journey-analytics.md)

- [site03 研究区域漏斗](41-site03-research-funnel.md)

- [跨场景脚点与保守回退研究](42-cross-scene-foot-policy.md)

- [site03 本地研究流程](43-local-pipeline.md)

- [site03 association reference-proxy diagnostic](44-association-diagnostic.md)

- [site03 tracker comparison](45-tracker-comparison.md)

- [ByteTrack association threshold counterexample](46-byte-threshold-counterexample.md)

- [Exploratory gap appearance guard](47-gap-appearance-guard.md)

- [Held-out site02 appearance-gap check](48-site02-gap-guard-holdout.md)

- [Association candidate review in the local page](49-association-review-ui.md)

- [Time-window analysis for site03](50-analysis-window.md)

- [Conservative region transition candidates](51-region-transition-candidates.md)

- [Fixed-association hybrid continuity comparison](52-hybrid-continuity.md)

- [Published-reference trajectory comparison](53-reference-analysis.md)

- [Same-window model and reference comparison](54-model-reference-comparison.md)

- [Local tracklet overlap experiment](55-tracklet-overlap.md)

- [Interrupted region-change evidence](56-interrupted-transitions.md)

- [Drawing regions on the research floor](57-draw-layout.md)

- [One-click reference flow example](58-reference-flow-example.md)
