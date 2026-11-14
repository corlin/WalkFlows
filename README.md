# WalkFlows

WalkFlows 是一个定位开源、非商业化的线下空间客流与匿名轨迹离线原型。项目使用公开多摄像头录像、已有标定和位置参考，探索人员检测、单镜头跟踪、地面投影、跨镜头关联、区域事件、热图和路径分析。

**当前状态：研究原型，尚未完成业务验收。** 轨迹关联、位置和区域事件均为研究候选，不能直接作为去重顾客人数、真实咨询、成交或布局效果结论。公开参考的可见性和覆盖也未独立确认。

## 当前可以查看

- 六路零售样本的双视角视频回放、局部检测框、实验投影和公开参考点。
- 在坐标平面配置矩形区域或点位，查看候选进入、离开、停留、区域转移、热图与路径；布局保存在当前浏览器，可导入导出。
- 比较原基线与公开参考；准备可选实验后，也可查看直接姿态检测的轨迹和视频框，并在同一布局与时段下对照参考。
- 导出带来源、时段、布局和候选明细的研究分析 JSON。

当前 site03 的公开标定没有指定实际平面底图，界面使用坐标网格；示例分区不代表真实门店布局。局部 ID、研究轨迹数和参考轨迹数都不是已验证的顾客人数。

## 本机使用

当前研发环境为 WSL2 的 Ubuntu20.04，项目位于 /home/corlin/WalkFlows，使用 corlin 用户和已有的唯一项目虚拟环境 .venv。从 Windows 进入：

~~~powershell
wsl -d Ubuntu20.04 -u corlin
~~~

在 WSL 中：

~~~bash
cd ~/WalkFlows
.venv/bin/python -m walkflows status
.venv/bin/python -m walkflows prepare --cross-scene
.venv/bin/python -m walkflows serve --port 8767
~~~

浏览器打开 [本地研究页面](http://127.0.0.1:8767/)。服务在前台运行，用 Ctrl-C 停止；如果已有服务占用该端口，直接打开现有页面即可。源码或数据重新准备后，刷新页面查看更新。

prepare --cross-scene 需要本机已有 site02 的数据和缓存；只准备 site03 可省略 --cross-scene。固定 site03 输入缺失时可使用 .venv/bin/python -m walkflows prepare --fetch 下载并校验；该选项不安装环境依赖，也不获取 site02 数据。流程需要项目现有 Python 3.12 虚拟环境、Node.js、g++ 和可用的 CUDA/PyTorch 环境。不要以 root 用户直接运行，也不需要新建第二套虚拟环境。详见 [本地流程](desc/43-local-pipeline.md)。

status 显示输入与回放包的来源状态，不执行 GPU 健康检查。bundle_current 只表示复现产物与来源一致，不代表定位、身份或业务指标已验收。

## 通用多摄像头流程（开发中）

推荐从统一入口开始，以下为两路示例；目标店铺可能只有 1–3 路或 3–5 路，需要更多镜头时继续添加 `--camera ID=路径`：

~~~bash
.venv/bin/python -m walkflows project-workflow --name Room \
  --workspace /home/corlin/WalkFlows/data/processed/my-room \
  --camera 'front=/path/front.mp4' --camera 'back=/path/back.mp4' --device 0
~~~

工作目录必须不存在。命令显示每路录像信息并启动配置页面（默认 http://127.0.0.1:8769/sync）；按提示可填写页面下载的偏移 JSON，以及逐路下载的平面对应点 JSON 路径，也可跳过。输入完成后自动处理并启动结果页（默认 http://127.0.0.1:8768/），Ctrl-C 停止服务。终端可填写 WSL 路径或带引号的 Windows 盘符路径。GPU 不可用时使用 `--device cpu`。

已有同场地映射可用 `--mapping-config /path/project.json` 导入，要求相机 ID 和尺寸一致，原配置指向的视频仍须可访问；尺寸相同并不能证明相机位置或坐标系一致。若已有经校验的播放副本，可传 `--preview-dir /path/preview`。自动处理可加 `--non-interactive --no-serve`；处理中断后可依据终端打印的最终配置，用 `project-run --config <最终配置> --output <工作目录>/result --device <原设备> --resume` 恢复，再运行 `project-review --output <工作目录>/result`。

平面标定页可对已测量的地面矩形使用四角引导，宽高和坐标方向仍需现场核验。录像偏移和真实平面对应点仍需按现场设置，跳过平面标定只能查看单镜观察；个别视频播放失败时其他可播放画面继续。 结果页可在共同平面中直接开启全时段观察热度，区域及跨镜候选在“分析工具”中展开。两组既有场地录像的操作与局限见 [验收记录](desc/91-workflow-acceptance.md)。

也可以使用以下分步命令：

~~~bash
.venv/bin/python -m walkflows project-create --name Room \
  --camera front=/path/front.mp4 --camera back=/path/back.mp4 \
  --offset back=0.2 --output /path/project.json
.venv/bin/python -m walkflows project-calibration-ui --config /path/project.json --port 8769
# 在页面为 front 和 back 选择对应点并下载到 WSL 可访问的路径，按 Ctrl-C 停止标定服务后：
.venv/bin/python -m walkflows project-apply-calibration --config /path/project.json --camera front --points /path/front-points.json --output /path/front-mapped.json
.venv/bin/python -m walkflows project-apply-calibration --config /path/front-mapped.json --camera back --points /path/back-points.json --output /path/mapped-project.json
.venv/bin/python -m walkflows project-run --config /path/mapped-project.json --output /path/run --device cpu
.venv/bin/python -m walkflows project-status --output /path/run
.venv/bin/python -m walkflows project-review --output /path/run --port 8768
~~~

下载到 Windows 的对应点文件须先使用 WSL 可访问的路径，例如 `/mnt/c/Users/.../Downloads/...`；不要把示例坐标当作实际场地。录像偏移、平面坐标和对应点须根据实际场地确定；没有标定时仍可查看单镜观察。结果包含近邻候选、区域事件和观察热度，但跨镜身份、去重人数及事件准确率尚未验证。浏览器不支持的编码可能无法播放。续跑和标定方法见 [通用流程](desc/80-generic-import-work.md)，参考邻近对照见 [评估记录](desc/82-generic-reference-evaluation.md)。已有操作验收使用两组六路样本；1、3、5 路的代表性操作验收尚待完成。该流程尚未完成下一阶段 MVP 的全部验收。

## 可选：直接姿态跟踪实验

该实验使用额外的已固定权重，并在两路主要摄像头上直接进行姿态检测和局部跟踪；其余视角沿用原基线。已准备好常规 site03 结果后运行：

~~~bash
.venv/bin/python scripts/fetch_site03_pose_s.py
.venv/bin/python scripts/probe_site03_pose_direct.py --camera C0001055_v4
.venv/bin/python scripts/probe_site03_pose_direct.py --camera C0001056_v2
.venv/bin/python scripts/evaluate_site03_direct_pose_journeys.py
node scripts/compare_site03_direct_pose_events.js
.venv/bin/python -m walkflows prepare --cross-scene
~~~

若本机没有 site02 数据，最后一行可省略 --cross-scene。构建时只有通过来源校验的实验产物才会出现在页面中；普通准备流程不会自动下载该可选模型或运行实验。视频中的基线框与蓝色虚线实验框使用不同局部 ID，不可直接视为同一身份。详情见 [多镜实验](desc/65-direct-pose-multiview.md) 和 [界面说明](desc/67-direct-pose-review.md)。

六路直接姿态研究模式可在依次处理六个相机后，执行 .venv/bin/python scripts/evaluate_site03_direct_pose_journeys.py --all-cameras，再运行 prepare 重新生成页面。页面可分别选择两路混合或六路实验轨迹、叠加对应视频框，并在相同区域与时段对照参考。实验来源仍未验证身份或顾客人数，原有默认模式不变。详见 [六路实验](desc/77-six-camera-direct-pose.md)。


## 浏览器无法播放的视频

若原视频可被处理但浏览器无法播放，可安装可选预览依赖（`uv pip install --python .venv/bin/python '.[preview]'`），或使用已有 FFmpeg。先执行 `project-preview-videos --config /path/project.json --destination /path/new-preview`，再为 `project-calibration-ui` 和 `project-review` 传入 `--preview-dir /path/new-preview`。推理仍读取原视频，副本仅用于播放。副本校验帧数、尺寸和标称帧率，但未校验逐帧时间戳；时间对齐和叠框需结合原片核验。具体流程、失败处理和依赖许可见 [通用导入工作记录](desc/80-generic-import-work.md)。


处理前还可使用 `project-check-timing --video /path/original --preview /path/playback-copy` 完整检查帧时间；无预览时可省略后一个参数。项目仍使用标称帧率，时间不规则时需特别核验，详见 [时间检查说明](desc/80-generic-import-work.md)。


若需为现有恒帧率处理链准备输入，可显式运行 `project-normalize-video --video /path/original --fps 15 --destination /path/new-camera`，再通过 `project-create --normalized-camera camera1=/path/new-camera` 创建项目并保留来源指纹；帧率仅为示例。该操作可能复制或丢弃帧，并重置起始时间，需要重新核对相机偏移与画面，原视频不会被覆盖。完整流程和溯源说明见 [通用导入工作记录](desc/80-generic-import-work.md)。


已有多路项目可使用 `project-normalize-project --config /path/source-project.json --fps 15 --destination /path/new-batch` 批量生成新项目；所有相机共用所指定帧率，原偏移必须重新核验。详见 [批量转换说明](desc/80-generic-import-work.md)。

## 数据与许可

当前主要研究样本来自 [PRCV Labs multiview retail tracking 数据集](https://huggingface.co/datasets/prcvlabs/multiview-retail-tracking)，固定数据修订及校验信息见 [样本获取脚本](scripts/fetch_site03_sample.py)。该数据集标注为 CC BY-NC 4.0，用于非商业研究和教育；数据、模型、代码及其依赖的许可应分别核验，不能据此默认商业使用。视频、模型和生成结果保存在忽略的 data/ 目录，不提交到仓库。其他资源及许可边界见 [数据清单](desc/03-data-and-licenses.md)。

## 文档与验证

- [产品目标和 MVP 范围](desc/01-product.md)
- [技术方案和数据契约](desc/02-architecture.md)
- [实施路线与验收原则](desc/04-roadmap.md)
- [文档索引](desc/README.md)
- [跨场景姿态实验](desc/66-direct-pose-cross-scene.md)
- [训练方向和数据清单](desc/69-training-direction.md)
- [首次弱监督训练试验](desc/72-weak-localizer-pilot.md)
- [轨迹与行进方向](desc/71-motion-direction.md)

常规复现入口为 .venv/bin/python -m walkflows prepare --cross-scene；它检查固定输入，运行或复用经过校验的缓存，并执行 Python 与 JavaScript 检查。验证报告和日志位于 data/processed/site03-verification/ 和 data/processed/local-pipeline/。通过这些检查仅说明当前研究链可复现，不等于完成全项目验收。

已用部分公开数据运行首个弱监督训练试验；部分验证摄像头退化，尚未接入默认流程。固定版本全量数据已下载并完成校验；更广泛的训练和评估仍在推进。仓库尚未添加项目代码的 LICENSE 文件，不应根据非商业化定位推定具体授权条款。
