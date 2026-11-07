# 开源项目源码核查与复用建议

更新：2026-11-06｜范围：源码与文档静态核查；后续组件测试见 [上游验证](09-upstream-validation.md)

## 结论与原则

优先验证和复用现成模块，先证明上游适用，再写必要的适配层。当前最完整的多摄像头候选是 RetailVision；Retail Customer Tracking 可用作 CITIC 单摄像头和区域分析的第二参考；Torchreid 是可选的外观特征工具；MelMOT 的关键功能存在占位，不能作为现成跟踪引擎。选型仍是候选，不能仅凭 README 或我们的短片段演示认定准确度。

本核查以以下固定提交为准；链接指向该版本。本报告原本未运行上游项目；此后对其中两个项目的有限测试与范围记录在 [上游验证](09-upstream-validation.md)，项目自报性能尚未复现。

## 1. RetailVision：优先评估的整合基础

来源：[Jay14090/retailvision](https://github.com/Jay14090/retailvision/tree/a0fae89b97fa45dd7e86ac0627935a682ec68ce8)，提交 `a0fae89b97fa45dd7e86ac0627935a682ec68ce8`。

源码实际包含：[多视角地面融合](https://github.com/Jay14090/retailvision/blob/a0fae89b97fa45dd7e86ac0627935a682ec68ce8/src/retailvision/spatial/fusion.py)、[地面跟踪器](https://github.com/Jay14090/retailvision/blob/a0fae89b97fa45dd7e86ac0627935a682ec68ce8/src/retailvision/cv/floor_tracker.py)、[区域事件](https://github.com/Jay14090/retailvision/blob/a0fae89b97fa45dd7e86ac0627935a682ec68ce8/src/retailvision/spatial/zones.py)、[客户旅程](https://github.com/Jay14090/retailvision/blob/a0fae89b97fa45dd7e86ac0627935a682ec68ce8/src/retailvision/analytics/journeys.py)、平面图、同步检查和仪表板。区域事件已考虑最短停留和未闭合访问；旅程保留部分不确定性。应先确认能否通过配置和数据适配使用这些能力，而不是重写。

融合将同帧、空间接近的不同摄像头观测聚合，并限制一个融合组同摄像头只出现一次；地面跟踪使用卡尔曼预测和距离匹配，也可利用单镜头 tracklet 连续性。它依赖同步与可信地面定位，接近的人可能被错误聚合；源码采用按置信度的贪心聚合及观测独立性假设，需要在目标数据上验证，不可把输出置信度当成已校准概率。

仓库 README 自述默认演示使用合成视频；真实零售跨镜头准确率仍未评估。其开发环境以 Windows、CUDA 和 Python 3.13 为主，CPU 路径未给出基准；本机 macOS/MPS、CITIC 的两种标定格式及输入/输出契约均未验证。它依赖 Ultralytics 与独立 OSNet 权重，不能因主项目标注 MIT 就忽略依赖和权重许可。

许可证据：README 和 `pyproject.toml` 声明代码 MIT，但本次检出的仓库根目录没有独立 LICENSE 文件；具体复制和分发前应核对完整许可声明、保留署名与许可文本，并分别核对依赖与权重条款。

## 2. Retail Customer Tracking：优先用于 CITIC 单摄像头能力核查

来源：[ardaatikk/retail-customer-tracking](https://github.com/ardaatikk/retail-customer-tracking/tree/f3f7c79b5cf113a4caaec72678073f0f8a8ae64a)，提交 `f3f7c79b5cf113a4caaec72678073f0f8a8ae64a`，仓库含 MIT LICENSE。

已有 CITIC Showroom、预训练 YOLO11、ByteTrack、轨迹确认、图像区域、区域汇总、轨迹图、热力图和数据下载/校验工具。可重点检查 [数据下载](https://github.com/ardaatikk/retail-customer-tracking/blob/f3f7c79b5cf113a4caaec72678073f0f8a8ae64a/src/data/download.py)、[区域管理](https://github.com/ardaatikk/retail-customer-tracking/blob/f3f7c79b5cf113a4caaec72678073f0f8a8ae64a/src/zones/zone_manager.py)、[区域汇总](https://github.com/ardaatikk/retail-customer-tracking/blob/f3f7c79b5cf113a4caaec72678073f0f8a8ae64a/src/analytics/summary.py)和 [热图](https://github.com/ardaatikk/retail-customer-tracking/blob/f3f7c79b5cf113a4caaec72678073f0f8a8ae64a/src/analytics/heatmap.py)，优先使用其现成流程作为单摄像头参照。

限制：明确只支持单摄像头，区域坐标和热力图在摄像机画面上，不是经过标定的统一门店平面；ID 不是跨镜头人员 ID。`ZoneManager` 对边界外 20 像素内的点可归入最近区域，需与我们的未知区域口径核对；区域汇总代码按相邻观测时间差计算停留，跟踪中断可能影响口径。不能把这些结果直接称为整店去重客流或完整到访时间。

代码 MIT 不自动覆盖其 Ultralytics、模型或 CITIC 数据许可；项目运行依赖中的 Ultralytics 等版本并未全部锁定，需单独解决可复现环境。

## 3. MelMOT：只作研究思路参考，不能直接当跟踪系统

来源：[Melodiz/MelMOT](https://github.com/Melodiz/MelMOT/tree/0bcc39e98d52150da45df7148e4305c6174cd302)，提交 `0bcc39e98d52150da45df7148e4305c6174cd302`，仓库含 MIT LICENSE。

README 描述 YOLO、BoT-SORT、OSNet 和时空关联，但当前 [单摄像头跟踪源码](https://github.com/Melodiz/MelMOT/blob/0bcc39e98d52150da45df7148e4305c6174cd302/melmot/core/tracker.py#L205) 明确将 BoT-SORT 留作 TODO，现有结果按每帧检测序号赋 ID，不能保证时间连续；[外观匹配源码](https://github.com/Melodiz/MelMOT/blob/0bcc39e98d52150da45df7148e4305c6174cd302/melmot/reid/cross_camera.py#L425) 在有特征时使用占位分数 0.5，并未完成真实特征比较。

仓库有时空投影、分数和后处理代码，可用于理解作者设计；不能复用其占位部分并声称已实现 BoT-SORT 或 OSNet 关联。README 的实时性能表述也未在本次核查中复现。之前推荐其作为开箱即用跨镜头参考的表述应收窄为**算法构思参考**。

## 4. Torchreid：可选 ReID 特征组件

来源：[KaiyangZhou/deep-person-reid](https://github.com/KaiyangZhou/deep-person-reid/tree/f8cd150fdf77e8d9e1ed143b7f308c2c609ded50)，提交 `f8cd150fdf77e8d9e1ed143b7f308c2c609ded50`，仓库含 MIT LICENSE。

其 [FeatureExtractor](https://github.com/KaiyangZhou/deep-person-reid/blob/f8cd150fdf77e8d9e1ed143b7f308c2c609ded50/torchreid/utils/feature_extractor.py) 可对人物裁剪图批量提取特征，支持模型路径；项目提供 OSNet 模型及权重入口。它不负责视频同步、目标检测、摄像头标定、身份分配或端到端轨迹。源码文档示例基于较旧 Python 环境；本机 Python 3.12/MPS 和具体权重未验证。缺少有效 ReID 权重时不能把一般 ImageNet 预训练特征当成已验证的行人重识别效果。应核对权重来源、许可和训练数据；避免把训练数据拿来充当独立测试集。

RetailVision 已有 ONNX OSNet 适配器，因此在评估 RetailVision 之前，不应重复封装 Torchreid；若需要新增外观比较，再对照两个现成接口与权重。

## ScreenFlows 衔接

已查看本地 `apps/engine/semantic/README.md`：其语义层的 `pages.csv` 定义触点名称和阶段，`project.json` 映射数据文件、事件列、会话列与漏斗。可以优先评估将已可靠生成的区域事件导入 ScreenFlows 现有数据入口；实体空间坐标、标定、重叠去重与不确定性仍需上游系统保留。此前的 WalkFlows 实验代码仅作临时证据，是否保留须以现成项目适配评估为准。

## 建议的下一步（未执行）

1. 建立不改变上游的隔离评估环境；先梳理 RetailVision 的输入格式、运行入口和 MIT 许可说明，检查其模块能否从既有轨迹或 CITIC 标定数据接入。
2. 检查 Retail Customer Tracking 的 CITIC 原有下载、配置及区域输出格式，判断能否直接运行与导出；只在必要时做适配。
3. 在同一已有样本和统一指标下比较可运行方案：摄像头同步、投影误差、重复计数、断轨和运行资源。没有可靠参考时明确标记无法评估，不新增标注或训练。
4. 确认业务层导出与 ScreenFlows 导入契约，再决定复用方式。明确不再并行增加另一套自研检测、跟踪、热力图或 ReID 实现，除非现成方案经核查无法满足需求，并记录理由。
