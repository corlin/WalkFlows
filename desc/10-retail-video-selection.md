# 真实门店视频筛选

更新：2026-11-07｜状态：已下载少量候选，待上游工具兼容验证

## 选择依据

用户明确优先选择真实门店、画面清晰；此前 CITIC Showroom 暗且更像展示厅，保留为技术验证，不再作为主要演示样片。

## 首个候选：PRCV Labs multiview retail tracking

来源：[数据集说明](https://huggingface.co/datasets/prcvlabs/multiview-retail-tracking)，读取时数据集版本 `6cf0e1066653f7efe1d0aae5c49860b19ef9a6e5`。发布者说明录自真实零售场景，已模糊人脸及标识，数据许可为 CC BY-NC 4.0，仅用于非商业研究与教育；不得尝试识别人物或地点。代码和数据许可证不同，商业用途须另行核实。

已下载 `testcases/002_site02_gaze` 的两个视频、manifest 与参考轨迹，共约 8.1 MiB，位于本地忽略目录 `data/raw/multiview/002_site02_gaze/`。两个文件均可解码，218 帧、15 fps、约 14.5 秒；画面为 1792×672 的左右并排双目，每只眼 896×672。人工查看 0、3、6 秒画面可见明亮的零售陈列及人员活动；画面为高位视角，颜色存在偏色、人物与店招经过隐私模糊，清晰度与展示效果仍应请用户实际查看。该片段较短，无法单凭它说明能覆盖完整进店到离店的旅程。

| 文件 | SHA-256 |
| --- | --- |
| `C0001001_v10.mp4` | `9926ccdd05358cab83c292d9a62f2196961de9439e97857c592a75d2993d5276` |
| `C0001011_v10.mp4` | `1d9b0ff0cbf92d9d107cfb7b197fe393fea5937f1245e5bc99b852e7137c694d` |

manifest 声明两路使用同一相对起点和 15 fps；其时间为 1970-01-01 的占位值，不代表真实拍摄时间。两路同步精度、地面坐标与参考轨迹格式尚未在本地验证。

### 参考轨迹与标定核查（2026-11-07）

- 配套 multiview 源码检出版本 `7e334db96ca7ab685628365a2eaa2d5e8117eac3`。仓库内的 `site02_scene01_v1.json` 包含两台双目摄像头配置、场景边界、入口区域和三维变换；还需结合各传感器畸变与双目标定，不能直接当作现成的单应矩阵。
- 本例 `ground-truth.json` 的 `track_results` 声明 218 帧、帧时长约 1/15 秒，以及原始 `start-frame=4702`；其中一条参考轨迹有 218 个点，点内帧号为 0–217。根据上游 `track-point.cpp`，点数组前几项分别是 x、y、帧号、方向；其余字段不应误当作顾客属性。真实事件时间仍不可从占位日期推断。
- 上游 `floor-histogram.hpp` 定义网格到空间坐标为 `x = grid_x × hist_sz + top_left_x`、`y = grid_y × hist_sz + top_left_y`；本例 `hist_sz=0.1`、`top-left=[-0.75,-2.5]`。这是源码层面的格式解释，参考轨迹与视频、场景轴方向及标定精度尚未做独立对齐验证；不能仅凭回环计算声称位置准确。
- 该样本只有一条参考轨迹，适合先检查坐标和单人路径，不足以评估多人交叉、相互遮挡或整店去重；评估这些情况应另选公开的多人场景，不自行标注。

## 复用边界与下一步

- 上游数据集配套 [multiview](https://github.com/prcvlabs/multiview) 开源系统，针对双目、畸变及其标定格式；优先阅读和验证其已有处理/输出接口，不把左右眼分别算成两个顾客或未经标定就拼接。
- 上游 README 的构建步骤面向 Linux x86_64，使用 micromamba/C++，完整姿态检测还需单独配置 HyperPose/TensorRT；不应承诺可直接在 Apple Silicon 或 uv Python 环境运行。先在 Mac 上做数据和格式检查；如最终确定该上游是必要依赖，再评估 PC 的 Linux 环境与 GPU 兼容性，按用户要求不要提前切机。
- 检查配套标定资源、参考轨迹及上游在 macOS 的可运行性，再决定能否直接使用或是否需要最小格式适配。不要直接沿用 CITIC 单应矩阵或 Showroom 区域配置。
- 数据集说明强模糊会降低部分跟踪模型的召回率；不能将隐私处理后的表现当作清晰原视频的模型基准。
- [RetailAction](https://huggingface.co/datasets/standard-cognition/RetailAction) 是另一套真实店铺多视角数据，但偏商品交互、单片段帧数有限，且采用单独许可；本次未下载，不默认用于长轨迹评估。

### Mac 实测（2026-11-07）

- 配套 multiview 项目在 Apple Silicon 上做 CMake CPU 配置尝试，关闭 CUDA、AWS、HyperPose 后在 `find_package(OpenCV)` 阶段停止：本机缺少 C++ OpenCV 开发包及其 CMake 配置。上游安装脚本针对 Linux x86，完整姿态检测依赖 TensorRT；目前只确认上述配置失败，不能据此断定所有 Mac 原生构建均不可行。未运行上游安装脚本，也未更改系统环境。
- 在临时 uv 环境直接调用 Retail Customer Tracking 的现有 `PersonTracker`，对两台摄像头视频的左眼各处理前 75 帧（5 秒），复用预训练 YOLO11n/ByteTrack。C0001001 产生 75 条观测、2 个局部 ID、耗时 3.92 秒；C0001011 产生 8 条观测、2 个局部 ID、耗时 2.63 秒。耗时不含模型构造、解码以外的产品功能，也没有严格区分设备和预热，只是一次可运行性试验。
- 两路均有输出，但第二路观测明显较少，不能仅凭次数判断原因或准确率；局部 ID 数不等于人数，左右眼未参与双目深度，多摄像头身份及空间定位未验证。这个实验复用上游单镜头组件，没有调用其 Showroom 区域配置。
- 进一步逐秒抽查 0–4 秒：第二路画面可见人物，0、1、4 秒无跟踪框，2、3 秒出现跟踪框；至少存在检测或跟踪间断，不能简单解释为无人。样本是稀疏人工观察而非完整帧标注，不据此计算召回率。
- 按用户要求继续尝试原生构建：使用隔离临时目录安装 C++ 依赖（conda-forge，Python 项目环境仍由 uv 管理），关闭 CUDA、AWS、HyperPose 后 CMake 配置成功，OpenCV 4.12 等依赖可找到。随后 `multiview-cli` 编译失败，上游内置 range-v3 与 AppleClang/libc++ 的标准库声明冲突（如 `unordered_multimap` 重定义）。没有修改上游代码、系统环境或宣称编译成功；日志位于临时文件 `/tmp/walkflows-multiview-build.log`。即使解决编译冲突，关闭 HyperPose 的构建也不能代表完整姿态跟踪可运行。
- 后续仅在 `/tmp` 的上游副本继续尝试：将内置 range-v3 临时替换为 0.12.0，设置 `META_NO_STD_FORWARD_DECLARATIONS` 和 `_LIBCPP_ENABLE_CXX20_REMOVED_TYPE_TRAITS`，临时添加 macOS 字节序兼容头、关闭整数收窄错误，以及在入口代码用 `std::filesystem` 代替 Linux `basename`。CPU、无 CUDA/AWS/HyperPose 的 `multiview-cli` 最终编译并可显示帮助。以上属于未审核的可移植性试验，不是正式依赖方案；整数收窄抑制可能改变边界行为，必须审查而不能直接交付。上游项目副本已修改，WalkFlows 产品源码未改。
- CLI 可读取 site02 双目视频及上游标定资产，生成默认参数并运行两帧。进程返回 0，但日志明确提示 HyperPose 未编译，输出 `track_results.frames=2`、`tracks=[]`；不能当作行人跟踪成功。日志摘要另报告 217 帧，与输出元数据不一致，需进一步核对该字段的含义，不能用其计算吞吐。试验输出在 `data/processed/multiview_mac_probe/`，未纳入版本管理。
- 按用户要求尝试启用 HyperPose：以 `MULTIVIEW_WITH_CUDA=ON`、`MULTIVIEW_WITH_HYPERPOSE=ON` 在独立构建目录进行 CMake 配置，失败于 `Failed to find nvcc`，尚未进入 HyperPose 的实际编译。上游 CMake 明确要求 CUDA、TensorRT 的 `nvinfer` 和 ONNX parser；[TensorRT 10 安装要求](https://docs.nvidia.com/deeplearning/tensorrt/10.x.x/installing-tensorrt/prerequisites.html)要求 NVIDIA GPU。M1 Pro 无 NVIDIA GPU，当前这条上游 HyperPose/TensorRT 路线不能在本机直接运行。HyperPose 项目也提及 CPU/GPU 混合调度，但不能据此认定 multiview 的 TensorRT 接口存在可直接启用的 Mac CPU 后端；未验证其他实现。

## 第二个候选：site03 多轨迹场景

已从同一数据集固定版本下载 `testcases/006_site03_tracks` 的两路视频、manifest 与参考轨迹。场景共六路，目前只取其中两路用于小样检查；两路视频报告 400 帧、15 fps，参考文件报告 399 帧、13 条轨迹。13 条是参考轨迹数量，不能直接认定为 13 位不同顾客。视频与参考帧数相差一帧，原因和对齐规则待验证，且只看两路不能验证完整六路轨迹。抽查第 5 秒画面明亮、展示货品清楚，但这两路当时未看到清晰的完整人物，需进一步筛查活动时间及其他摄像头再决定是否适合演示。
