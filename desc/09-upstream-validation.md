# 上游项目验证与新增候选

更新：2026-11-07｜阶段：上游单镜头真实样本已试运行，多镜头未验收

## CITIC Showroom 原生流程试运行（2026-11-07）

使用用户指出的人物出现时间，从 capture1 Showroom 原视频截取 97–107 秒；视频来自公开数据，按 ZIP CRC 验证。原项目 `f3f7c79b` 在临时 uv 环境中运行其原生 `run_tracking_pipeline`，用已下载的预训练 YOLO11n 和原有 Showroom 区域配置；为了无界面运行，仅在试验进程中替换了 OpenCV GUI 调用，没有修改上游代码。结果已复制到 `data/processed/upstream_showroom_97s/`，该目录不入库。

- 250 帧，原项目确认 1 条本地轨迹，路径为 Entrance → Main Area → Demo Area；得到带框视频、调试和确认轨迹 Parquet、区域/轨迹统计文件。该数字是模型输出，并未验证是否等于实际人数。
- 本次启动到执行结束约 10.56 秒，包含模型加载和处理，但取自一次运行，不能代表稳定吞吐；项目运行设备为默认选择，未经明确设备参数确认，不能宣称使用 MPS 或作设备对比。
- 截取后的文件和输出时间从 0 秒计，若映射回原视频必须加 97 秒；不能不加偏移与其他摄像头进行关联。本次未测原视频的绝对时间和跨摄像头同步。
- 首次误选原视频 0–10 秒得到 0 条确认轨迹；检查 0、2、5、8 秒抽帧均未见人，不能将零结果认定为模型失败。稀疏抽帧也不能证明全部帧无人。
- 输出中入口停留两种数值不同：控制台状态汇总为 2.20 秒，确认帧导出的区域汇总为 1.16 秒。确认轨迹的 Entrance 首条时间为 1.04 秒，调试轨迹从 0 秒开始；结合代码可知状态从确认前开始累计，而确认帧输出只包含确认时及之后的帧。两条指标的时间覆盖不同，不能混用；遮挡和插值还会引入其他误差。
- 该视频片段验证了上游的**单摄像头**流程和现成区域配置能够运行，不能证明多摄像头融合、真实停留精度、商店行为或成交归因。

## 本机已做的验证

以 uv 为 RetailVision 和 Retail Customer Tracking 分别建立临时独立 Python 3.12.9 环境，检出版本见 [项目核查](08-open-source-review.md)。只安装运行所选测试所需的依赖，没有修改上游源码，也没有下载新视频或训练模型。

| 项目及范围 | 结果 | 能说明 / 不能说明 |
| --- | --- | --- |
| RetailVision `tests/test_floor_tracking.py` | 15 项通过 | 融合和地面跟踪在构造的测试数据下可在本机执行；不是对真实门店视频的准确率验证。 |
| Retail Customer Tracking 的 `tests/unit/test_zones.py` 和 `test_analytics.py` | 17 项通过 | 区域及汇总测试在本机执行通过；输入为测试数据，未运行完整视频管线。 |
| RetailVision 地面融合 API 对现有 10 秒观测数据的只读适配试验 | 225 个含观测帧调用完成，出现最多两路观测组成的融合组 | 仅证明已有 CSV 可转换为上游 `Observation` 并调用 `fuse_views` / `FloorTracker`；没有验证同步、坐标、去重或身份准确度，不生成业务人数。试验只传入含观测帧，不能作为完整时序评估。 |

使用的测试依赖分别安装于临时 uv 环境：RetailVision 为 NumPy 1.26.4、SciPy 1.15.3、pytest 8.4.1；Retail Customer Tracking 为 NumPy 1.26.4、OpenCV 4.11.0.86、pandas 2.3.3、pytest 8.4.1。上游依赖清单更大，本次不是完整安装和兼容性证明。

## RetailVision 输入与路径：关键发现

- `pipeline/processor.py` 的常规 `process_cameras` 使用 `GlobalIdentityResolver` 做跨镜头关联；其另一套 `fuse_views` + `FloorTracker` 是在 `evaluation/smartspaces.py:track_on_floor` 调用的评估路径。两者不能混为一谈，也不能宣称地面融合已在通用仪表板端到端接入。
- `track_on_floor` 消费 SmartSpaces 场景、按摄像头的检测缓存、摄像头投影及帧号；底层 `Observation` 支持摄像头、地面坐标、置信度、不确定性和可选局部 tracklet key。CITIC 需要配置或数据适配，而且 HallWide 的内外参和 HallSeg 的单应矩阵形式不同。适配方式待先验证上游入口，不能把实验脚本直接当完成品。
- 上游同步检查可以使用摄像头偏移，但缺失偏移时只是报告零偏移假设，并不自动测出真正同步。必须保留这个区别；当前 CITIC 两镜头偏移仍未确认。
- Retail Customer Tracking 的文件模式使用摄像头配置区域，仓库已给 Showroom 配置；其区域是摄像机画面像素坐标。现有 HallSeg / HallWide 没有直接对应的原项目区域配置，不可套用 Showroom 配置。

## 新增候选：按作用区分

| 候选 | 已有能力及许可证据 | 对本项目的价值与限制 |
| --- | --- | --- |
| [Intel Open Model Zoo 多摄像头跟踪 Demo](https://github.com/openvinotoolkit/open_model_zoo/blob/master/demos/multi_camera_multi_target_tracking_demo/python/README.md) | 项目代码 Apache-2.0；官方 Demo 支持多视频、预训练人员检测和 ReID 模型，输出框和跨摄像头 ID。 | 非 YOLO 的可运行对照候选；不默认提供门店统一平面、热图或业务触点。模型许可、版本及输入同步需分别核查。Open Model Zoo 自称模型来源处于维护模式。OpenVINO 文档支持 Apple Silicon CPU，但该 Demo 本机尚未验证。 |
| [Roboflow Supervision](https://github.com/roboflow/supervision) | MIT；提供检测结果适配、区域、多种可视化等通用工具。 | 可避免重写区域计数、绘制等基础轮子；不是完整的跨摄像头身份系统。版本接口会变化：0.31 起原 `sv.ByteTrack` 已移出，选用时需固定版本并核对对应 API。 |
| [YOLOX](https://github.com/Megvii-BaseDetection/YOLOX) + [原版 ByteTrack](https://github.com/FoundationVision/ByteTrack) | YOLOX 代码 Apache-2.0，提供预训练模型；原版 ByteTrack 代码 MIT。 | 非 Ultralytics 人员检测与单摄像头跟踪候选；并不自动提供跨镜头全局 ID。单独验证权重、数据来源、依赖和本机运行。 |
| [Norfair](https://github.com/tryolabs/norfair) | BSD-3-Clause 的检测器无关跟踪库。 | 可作单摄像头或点位跟踪组件对照；不是现成门店多摄像头系统；Apple Silicon 和所需版本尚未测。 |
| [BoxMOT](https://github.com/mikel-brostrom/boxmot) | 多种现成 MOT 跟踪器；当前仓库标注 AGPL-3.0。 | 可以对照多种单镜头跟踪算法，但不能假设跨镜头自动可用；注意该项目、权重和依赖各自许可。 |
| [NVIDIA DeepStream](https://github.com/NVIDIA/DeepStream) / [Metropolis MTMC](https://docs.nvidia.com/mms/text/MDX_Multi_Camera_Tracking_App.html) | 存在 NVIDIA 多摄像头参考应用、SDK 和微服务；各部分授权不同，不能笼统称整个方案开源。 | 后续 NVIDIA PC 或规模化部署的参考；MVP 优先 Mac，暂不要求切换机器。应先确认 5060 Ti、操作系统、驱动、SDK 和许可兼容性。 |

没有把新候选当成经过本地验证的生产方案；仓库许可证不代表模型权重、训练数据和所有依赖拥有相同许可。

## 后续决策顺序

1. 先验证 RetailVision 常规流程和地面跟踪评估路径各自的输入/输出，以及 CITIC 的同步和坐标转换；仅编写确实缺失的适配，不复制现成跟踪器。
2. 如果要验证非 Ultralytics 方案，优先在 Mac 的隔离 uv 环境尝试 Open Model Zoo 官方 Demo 或 YOLOX + 原版 ByteTrack；固定版本和权重，先验证可用性，再比较实际数据，不将论文指标当成门店效果。
3. 区域和热力图优先比较 RetailVision、Retail Customer Tracking 与 Supervision 的现成能力；明确单摄像头像素坐标和公共平面坐标的区别。
4. 在可复现的真实观测与既有参考标注范围内评估，无法量化的部分保留未验证状态；验证成功后再接 ScreenFlows 事件导入。
