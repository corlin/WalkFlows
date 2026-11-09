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
