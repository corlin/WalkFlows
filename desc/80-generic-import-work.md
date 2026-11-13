# Generic multicamera import: implementation work

2026-11-13. The next-stage objective remains the complete 5-6-camera input-to-result workflow in desc/79, not merely a configuration importer. The existing local CLI is hardwired to site03 assets.

The first implementation slice defines a reusable project manifest: camera IDs, local file paths, signed start offsets, probed video metadata and optional image-to-plane homographies. Relative paths resolve against the configuration file, camera IDs are unique and safe, offsets and matrices must be finite, and files must actually decode. The shared timeline is the overlap of each video interval after offsets. Missing calibration is explicitly represented as absent; there is no invented plane projection or identity. The importer records content hashes and fails on invalid inputs or no common time. The validation command prints a manifest and does not write or overwrite an existing project. Tests use real small video files where the environment supports video encoding.

Subsequent required slices include actual per-camera inference, isolated tracker state, time-aligned review, explicit calibration and cross-view candidates, task progress and recovery, general-scene UI, and end-to-end verification using at least two distinct 5-6-view groups. Existing site03 review remains available. Do not claim this first slice alone meets the MVP.

## Current implementation

Run `.venv/bin/python -m walkflows project-validate --config /path/to/cameras.json`.
The config is JSON, for example:

```json
{"name":"Room","cameras":[{"id":"front","path":"front.mp4","offset_seconds":0},{"id":"back","path":"back.mp4","offset_seconds":0.2,"homography":[[1,0,0],[0,1,0],[0,0,1]]}]}
```

Paths are relative to the config. Offset is the start of each video on the shared timeline; the reported overlap is based on container metadata, which is an estimate, not proven frame synchronization. Homographies are optional; their numerical invertibility does not prove calibration correctness. Validation decodes the first frame and computes SHA-256; it does not guarantee every later frame is readable, perform inference, or render results.

## Generic local processing (2026-11-13)

Run `.venv/bin/python -m walkflows project-run --config /path/to/cameras.json --output /path/to/new-output --device cpu`; use `--device 0` for a working CUDA device and `--weights` to select local weights. The output path must not already exist. Cameras are processed sequentially with independent ByteTrack state; each CSV contains frame-based timestamps, local detections and IDs, bounding boxes, and bottom-center footpoint estimates. If a homography is provided it maps those footpoints to the configured plane. No homography produces blank plane coordinates. IDs are camera-local, projections and timestamps are unvalidated estimates, and zero observations is a valid visible result, not proof of absence.

run.json records running/completed/failed status, progress by camera, hashes of inputs, model and CSVs, parameters and package versions. A hard termination can leave status running; this does not prove the process remains live. Per-camera resume and status inspection were added later; frame-level checkpointing and complete result review remain required. Frame count differences are reported rather than interpreted as synchronized coverage.

A local smoke test used six site03 006 videos, each cropped to its first camera image, resized to 448x336 and shortened to eight frames. CPU processing completed 8 frames per camera with observation counts 8, 1, 0, 0, 1, 0. This only verifies the generic input-to-CSV execution path on short clips: it is not a tracking accuracy assessment, real-scene acceptance, a second independent scenario or an end-to-end UI. Source and outputs remain in ignored local data/processed/generic-six-camera-smoke.

## Generic review (2026-11-13)

Run `.venv/bin/python -m walkflows project-review --output /path/to/completed-output --port 8768`, then open http://127.0.0.1:8768/. The loopback server checks source video and observations hashes before startup, serves only declared assets and supports byte ranges for seeking. It exposes a scrubber, approximate synchronized playback and camera-local detection boxes; it does not implement cross-view candidates, track trails, regions or an end-to-end import UI. Video paths remain server-side and are not sent to the browser.

A browser check confirmed that the six generated MJPEG AVI smoke clips are not playable in the tested browser, while the original H.264 MP4 for site03 camera C0001056_v2 was processed (400 frames, 854 observations) and displayed with boxes; pressing play advanced the timeline. The video route returned HTTP 206 for browser range requests. These are one-camera playback and address checks, not multi-camera sync or accuracy acceptance. Unsupported codecs show a playback error; no automatic transcoding is implemented. Results and frame-overlay timing remain approximate, especially with variable-frame-rate videos.

## 平面映射与六路验证（2026-11-13）

对于用户自己的场地，先确定统一平面坐标系和单位，选择至少四组不共线的地面对应点。每路相机分别准备 JSON，例如：

```json
{"image_points": [[0,0],[100,0],[100,100],[0,100]], "plane_points": [[0,0],[2,0],[2,2],[0,2]]}
```

执行 `.venv/bin/python -m walkflows project-calibrate --points /path/to/points.json`，把输出的 `homography` 和 `calibration_polygon` 加入该相机的项目配置。此误差只针对参与拟合的点，必须用额外未参与拟合的点检查；四个点的拟合误差很小并不能证明准确。仅平面区域可用，遮挡、镜头畸变、拍摄移动、不同视角使用不同坐标系均可能导致错误。

对现有 site03 006 样本，`scripts/derive_site03_plane_mapping.py` 将已有 sensor0 非线性标定模型在左侧 896×672 图像的有效地面范围内近似为单应映射，采用交错网格划分拟合和留出点。六路留出点的 95% 误差为 0.0059–0.0091 场景单位，代表对原模型的近似误差，并非现实定位误差；网格点高度相关，也不能证明模型本身正确。有效多边形是样本网格凸包近似，映射不适用于左右拼接画面的右半部分或边界之外。脚点是检测框底部中心，仍需物理验证。六路偏移暂设为零，不代表已验证同步。

本机生成的配置和报告分别位于 `data/processed/site03-generic-plane/config.json` 与 `calibration-report.json`，处理结果位于 `result/`；均为本地忽略文件。用上述配置实际处理六路各 400 帧，浏览器验证视频、共同时间轴及平面散点可显示；场景图是自动缩放的坐标散点，不是建筑平面图，也未做跨镜去重或身份匹配。浏览器回放是近似同步，尚未完成逐帧时间对齐验证。

## 视频选点界面（2026-11-13）

在运行推理前，可以执行 `.venv/bin/python -m walkflows project-calibration-ui --config /path/to/cameras.json --port 8769`，在本机打开 http://127.0.0.1:8769/ 。选择相机和视频时间，点击图中地面固定点，输入同一坐标系的平面 X、Y，至少记录四组后下载对应点 JSON。页面内切换相机保留尚未下载的点，关闭页面则不会保留；下载位置由浏览器决定。随后使用 `project-calibrate --points ...` 计算矩阵并加入项目配置。相机切换、视频地址和坐标选取在真实 MP4 样本中检查过；测试所填数值是交互用例，不是标定真值。当前仍需用户准备统一地面坐标；可用下述命令生成新配置，尚未实现通过界面保存项目或自动标定。

### 将标定写入新配置

导出对应点后，可执行 `.venv/bin/python -m walkflows project-apply-calibration --config /path/to/project.json --camera camera1 --points /path/to/camera1-points.json --output /path/to/new-project.json`。命令计算映射并创建新配置，不覆盖已有文件，其他相机路径会按原配置位置解析成绝对路径。需要为多路相机依次生成新的配置；输出中的残差仅针对拟合点，仍须用独立点和现场数据核查。若浏览器运行在 Windows，下载文件可能需要通过 WSL 的 /mnt 路径访问。

### 局部轨迹与跨镜候选（2026-11-13）

共同平面视图可显示最近最多三秒、连续帧的单镜局部轨迹；缺帧会断开轨迹，不跨镜拼接。用户自行输入正的距离阈值后，在当前时间按每对相机计算双向唯一的邻近候选，并统计存在竞争的候选边；同一对象在多相机间可能有多个候选。这是空间邻近启发式，不是身份确认、全局去重或准确率。阈值单位取决于用户坐标系，时间偏差、标定和脚点误差直接影响结果；不支持的观测保留为空。

浏览器交互测试使用 site03 006 样本、10 秒和人为输入的 0.5 场景单位，显示 1 对候选；这只是功能演示，不能当作正确匹配的证据。候选每帧独立计算，尚未进行连续时间支持、跨镜冲突消解或与真值的评估。

### 创建项目与区域（2026-11-13）

可通过命令创建项目而不手写 JSON：`.venv/bin/python -m walkflows project-create --name Room --camera front=/path/front.mp4 --camera back=/path/back.mp4 --offset back=0.2 --output /path/project.json`。可重复传入 5–6 个 `--camera`；偏移未提供时为零，必须由用户根据录像确定。命令检查视频、共同时间范围和重复 ID，并拒绝覆盖已有项目。实际用 007 六路 MP4 验证了创建项目，报告共同时间范围 0–33.33 秒。

对同一 site03 的另一组 007 录像，通用处理按六路各 500 帧完成，并使用已有同场地标定生成估计平面坐标。这是不同录像的功能验证，仍不是不同场景的泛化或完整准确率验收。

结果页可在自动缩放的坐标视图绘制多边形区域，显示当前各镜落入区域的投影观察条数，支持导出及导入区域 JSON。结果是原始各镜观测，不是去重人数；位置和区域边界依赖所用坐标和标定。导入时需自行核对坐标系，区域数据在页面内存中，刷新前请导出。区域进入/离开事件、跨镜去重和统计准确性验证仍未完成。浏览器使用示例视频验证了绘制、完成与观察数显示；自动测试覆盖点在多边形内外及边界。

### 热度与区域边界候选（2026-11-13）

结果页可选择显示全时段的投影观察热度网格；它累计每帧各相机的有效投影，受帧率、不同视角重复、遮挡与检测错误影响，不能解释为去重人数或停留时间。

用户画好区域后，系统仅对同一相机、同一局部编号在连续两帧由区域内外发生变化的记录生成进入/离开候选；轨迹开始时处于区域内、丢帧后的变化或同帧重复编号均不推断事件。事件不是已确认真实行为，同一人可能在多个镜头产生重复事件。页面按当前时间显示，导出包含全时段事件、区域、源视频和观察文件指纹、时间偏移、映射矩阵及模型参数；不含本地视频路径。

浏览器用 site03 006 临时绘制的测试区域检查了热度显示和一条离开候选，仅为功能检查，不是事件准确率。自动测试覆盖首次出现、断帧、同帧重复、边界及网格累计。仍需要用真值检验事件质量、时间对齐和跨镜去重。

### 任务状态与按相机续跑（2026-11-13）

`project-status --output /path/to/run` 显示日志和锁状态；持锁可证实运行中，而无锁且原进程不存在时标记为中断或遗弃，无法判定时显示 unknown。失败或中断后，可对相同配置执行 `project-run --config /path/to/project.json --output /path/to/run --device cpu --resume`。续跑要求项目、视频、模型、设备参数、依赖版本、处理代码和 tracker 配置一致，并重新核验已完成相机 CSV 的哈希；通过后只重跑未完成的相机。运行锁防止同一目录并发写入。

结果先写临时文件，再以不覆盖现有文件的方式发布；意外崩溃可能留下 .part 文件或未登记 CSV，这类未确认文件不会被自动覆盖，需保留现场并另选输出目录处理。仅支持相机粒度续跑，不恢复单路视频中的帧级 tracker 状态。此前版本创建且缺少必要版本或进程信息的运行可能不能安全续跑。测试覆盖失败后复用、锁竞争、结果篡改、配置变化及不明文件保护；已有输出或校验失败不会被当作可靠缓存。

### 处理前的时间对齐预览（2026-11-13）

启动 `project-calibration-ui --config /path/project.json --port 8769` 后，在标定页面进入“时间对齐预览”，或打开 http://127.0.0.1:8769/sync 。各路偏移表示视频首帧在共同时间轴上的秒数；共同范围为各路区间的交集。页面可调整偏移、拖动共同时间和近似同步播放；无共同范围时禁止播放及下载。下载的 JSON 可通过 `project-apply-offsets --config /path/project.json --offsets /path/walkflows-offsets.json --output /path/timed-project.json` 写入新配置，命令重新验证视频和交集，不覆盖已有文件。即使原配置无重叠，也允许打开预览以调整，但不能用于直接处理。

六路样本浏览器检查了偏移 1.25 秒时的共同范围、100 秒导致无交集的提示和恢复播放；使用一份 0.2 秒测试偏移验证了六路新配置生成。上述数值仅用于测试，不是样本实际校正。视频时长来自帧数与标称帧率；变帧率、视频解码延迟及浏览器时钟可能使画面不同步，预览不证明曝光或帧级同步。需要用户通过共同可见事件验证，并为实际录像确定偏移。

### 浏览器预览与结果缓存（2026-11-13）

部分 AVI 等录像可以由处理引擎解码，但浏览器不能直接播放。可安装可选依赖 `uv pip install --python .venv/bin/python '.[preview]'`（或使用已有 FFmpeg），然后在处理之前创建播放副本：

```bash
.venv/bin/python -m walkflows project-preview-videos --config /path/project.json --destination /path/new-preview
.venv/bin/python -m walkflows project-calibration-ui --config /path/project.json --preview-dir /path/new-preview
.venv/bin/python -m walkflows project-run --config /path/project.json --output /path/new-run --device cpu
.venv/bin/python -m walkflows project-review --output /path/new-run --preview-dir /path/new-preview
```

也可对已完成的运行使用 `project-preview-videos --output /path/new-run --destination /path/new-preview`。副本目录必须不存在，失败可能留下部分文件和状态记录供检查；不会覆盖原视频。预览转为 H.264、无音轨，校验源文件和副本哈希、解码帧数、尺寸及标称帧率；**未逐帧核对时间戳**，变帧率或转码时间变化可能影响对齐与叠框，须对照原片核验。处理和推理仍使用原片；不保证所有输入均可转换或所有浏览器均可播放。预览清单和状态均完成且校验通过才可使用。可选 imageio-ffmpeg 提供的 FFmpeg 二进制及其编码器具有各自许可，参见 [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) 和 [FFmpeg 许可说明](https://ffmpeg.org/legal.html)。

复用同一浏览器地址查看不同运行时，旧视频或观察数据可能被条件缓存复用。现服务端禁用缓存和条件 304，并在视频与观察地址加入内容版本；未标定相机的平面坐标也在界面侧清空。浏览器在同一端口先后打开已标定与未标定样本，后者显示无平面坐标。此检查证明修正后的组合行为，不足以单独证明此前某次显示异常的具体根因。早前依赖浏览器界面观察的演示应在新版本重新核验；独立离线文件计算不因浏览器缓存自动失效。

### 单镜轨迹方向（2026-11-13）

通用结果页对当前帧之前最多 3 秒的连续单镜局部投影绘制轨迹；仅当轨迹至少持续半秒且起终点在画布上相距至少 8 像素时，绘制首尾位移方向箭头。缺帧、同帧重复局部编号或无有效投影会中断轨迹，不跨镜连接；短期抖动、误跟踪、映射误差或回转仍可能使箭头误导，不能视为真实身份或行为。屏幕像素阈值随缩放变化，不是物理速度或停止判定。

在 site03 006 本地结果复核了页面及 10 秒时刻；检测到当前按所有投影自动缩放，正常点高度集中，方向在该画面难以辨认。这次不将截图作为方向效果或准确率通过的证据；需要进一步处理异常坐标、视图缩放与基于真值的方向评估。

针对上述缩放问题，结果页增加“聚焦当前投影”和“显示全部范围”。聚焦使用所选时间各镜有效投影的边界，固定视野直至用户再次选择，范围外的轨迹和区域可能被裁切；无投影时保留原视野并提示。热度按当前视野重新计算，仅显示视野内的观察，因此不同视野的颜色深浅不宜直接比较。site03 006 的 10 秒时刻经浏览器检查，聚焦后可辨认轨迹，仍未评估方向的真实性或精度。

### 独立检查点与平面映射（2026-11-13）

拟合后可用未参与拟合的地面对应点检查映射。使用标定页面另选点并下载 JSON，或自行准备 `image_points` 和 `plane_points` 两组等长坐标，然后执行：

```bash
.venv/bin/python -m walkflows project-check-calibration --config /path/mapped-project.json --camera front --points /path/check-points.json
```

命令输出每点预测、给定坐标、距离误差和是否在标定多边形内（无多边形时为 null），以及 RMSE、最大误差、项目配置和检查文件的 SHA-256。若拟合时记录过对应点文件哈希，`same_file_as_fit` 可发现逐字节重复使用；false 或 null 均不能证明点真正独立。应选择覆盖实际活动区域的多个留出点，确认坐标单位、测量质量和误差是否满足用途；标定范围外的结果是外推，不能靠拟合残差保证。该命令不会修改配置、视频或映射，也不会替代实地测量。

本地以 site03 C0001056 的既有标定模型生成三个原拟合网格中留出的检查点，命令得到 RMSE 约 0.0070、最大误差约 0.0077 场景单位，三点均在多边形内。两者来自同一传感器模型且样本很少，仅说明映射近似模型的计算路径可运行；不是独立现场定位误差、也不是方向或跨镜身份准确率。检查输入保存在忽略目录 `data/processed/site03-006-roi-v1/check-model-holdout.json`。

### 平面投影的矩阵尺度修正（2026-11-13）

单应矩阵与其任意非零倍数表示同一个映射。旧处理代码用绝对分母阈值 1e-9 判断无效，因而外部导入的等价小尺度矩阵可能让所有投影为空。现先归一化矩阵，再用相对阈值排除接近投影地平线的点；仍按标定多边形排除范围外的脚点。该修正不改变原视频和已有结果：已有运行不会自动重算，若受影响需创建新的处理输出；处理代码哈希变化后，旧版本中断任务不能用新代码续跑，以免混用结果。

回归测试验证正负缩放及地平线情况。对 site03 006 既有 916 条观察中的 739 条有效投影，分别用原矩阵及其 1e-12 倍重算，与既有 CSV 的最大数值差约 2.9e-15 场景单位；这是计算等价性检查，不是定位精度或跨场景效果评估。

### 处理后的共同时间范围（2026-11-13）

复核页现在以各相机实际解码帧数、标称帧率及配置偏移重新计算共同时间交集。解码帧数和视频元数据不一致时，对应相机显示提示；若实际解码范围无交集，复核服务明确拒绝启动并提示无共同时间。处理日志与输入配置不被修改，标称帧率仍不等于逐帧时间戳；变帧率、损坏或浏览器解码差异需要进一步检查。

用合成运行日志测试了元数据范围到 10 秒、实际相交到 2 秒以及无交集的情况；另用复制的 site03 结果和人为修改的帧数状态检查了浏览器提示。该例专门用于模拟错误，不代表原始 site03 视频存在损坏。

### site04 另一段录像的负面结果（2026-11-13）

对 site04 046 按既定六路配置完成了 640 / 1280 通用处理、条件参考对照和浏览器回放检查。仅一台相机有投影，640 为 88 条、1280 为 14 条，均无 0.5 场景单位内参考邻近；检测首帧存在疑似误检但未经人工标注确认。详情、选择偏差及复现材料见 [site04 046 诊断](87-site04-046-diagnostic.md)。该结果说明流程可运行，不支持宣称跨场景检测或定位效果达标。

### 官方 WILDTRACK 六镜单帧检查（2026-11-13）

官方归档现可从 WSL 访问；选择性提取首帧的六路官方图像与参考框后，按 0.5 IoU 做单镜一对一条件对照。126 个逐镜参考框、83 个检测框中有 44 对匹配，结果仅为单帧开发诊断，户外数据不能替代零售验证；详见 [官方数据检查](88-wildtrack-official-sixview-probe.md)。

### 检查录像与预览逐帧时间（2026-11-13）

`project-check-timing` 使用已有系统 FFmpeg 或同一虚拟环境的可选 `imageio-ffmpeg`，完整解码首个视频流，通过 [FFmpeg showinfo](https://ffmpeg.org/ffmpeg-filters.html#showinfo) 的帧序号、整数 PTS 和时间基准计算每帧相对首帧的时间。命令只检查，不更改视频：

```bash
.venv/bin/python -m walkflows project-check-timing --video /path/original.mp4 --preview /path/playback-copy.mp4 --report /path/new-timing-report.json
```

`--preview` 和 `--report` 可省略；报告文件不得已存在。输出最大偏离标称帧率时间的秒数与帧数，并在提供副本时输出同序帧间最大相对 PTS 差异。时间戳缺失、非严格递增、帧数不一致或 FFmpeg 解码失败会报错，而不是声称对齐；报告记录源、副本和 FFmpeg 的 SHA-256。该检查需完整解码全部帧，长视频可能耗时和占用内存。误差是否可接受取决于应用，程序不设自动通过阈值。

局限：这只对 FFmpeg 解码出来的帧进行相对时间检查，不证明浏览器显示帧与解码帧一一对应、不同相机时间同步或视频内容一致，也不自动修正变帧率。处理与复核主路径目前仍以标称帧率计算时间：若最大偏差显著，轨迹、跨镜候选与事件时间可能错位，需另行处理并核验，不能将报告视作自动对齐或准确性证明。

本机用 8 帧 MJPG 原片及生成的 H.264 预览检查，最大相对 PTS 偏差为 0；这是短合成样本。另用 12 帧的合成变帧率录像，对比相同帧数及 10 fps 标称帧率的匀速副本，最大偏差为 0.4 秒（4 帧），证明只核验帧数及标称帧率不够；不代表任意编码或浏览器均已验证。

### 将不规则帧时间转为恒帧率分析输入（2026-11-13）

当 `project-check-timing` 显示明显偏差时，可选择为每路单独创建新的恒帧率分析文件，再用这些文件创建项目：

```bash
.venv/bin/python -m walkflows project-normalize-video --video /path/original.mp4 --fps 15 --destination /path/new-camera1
.venv/bin/python -m walkflows project-create --name Room --camera camera1=/path/new-camera1/normalized.mp4 --camera camera2=/path/new-camera2/normalized.mp4 --output /path/new-project.json
```

每路需根据录像选择目标帧率并分别执行，目标目录必须不存在。转码用 FFmpeg 的 `setpts=PTS-STARTPTS,fps:round=near`，输出 H.264 无音轨，**可能复制或丢弃帧**；它改变了分析输入和首帧时间，不是无损修复，也不自动同步相机。应重新核验每路偏移、画面、标定和业务结果；源视频保持不变。若保留原项目的空间映射，需确认实际画面尺寸、方向及坐标对应没有变化。用户须确认 FFmpeg 及编码器许可。

每个目录包含 `normalized.mp4`、`manifest.json` 和状态日志，记录原片及输出哈希、帧数、时间偏差、尺寸、FFmpeg 哈希和参数；可用输出哈希与运行记录中的输入哈希关联原片。已验证输出尺寸、标称帧率和逐帧相对时间；这不证明视觉内容、浏览器解码或跨镜时序准确。失败可能留下部分文件与 failed 状态，不会覆盖已有目录；请检查后另选新目录。

在六路 8 帧合成变帧率短片上，首版归一化各生成 11 帧，源与标称时间最大偏差约 0.205 秒，输出检查为 0；随后使用这些副本创建项目、执行 GPU 检测并在浏览器打开六路回放，未设置空间标定。其后增加尺寸和输出哈希核验，用最终版本对其中一路重新运行得到 448×336、8→11 帧及 0 的输出时间偏差。该短片仅为功能验证，不证明真实变帧率素材普遍有效、人员身份或坐标准确。

### 将重采样来源带入项目（2026-11-13）

创建项目时可直接传入归一化目录，使原片与分析输入的指纹自动进入运行和导出来源：

```bash
.venv/bin/python -m walkflows project-create --name Room \
  --normalized-camera camera1=/path/new-camera1 \
  --normalized-camera camera2=/path/new-camera2 \
  --output /path/new-project.json
```

可与普通 `--camera ID=PATH` 混用；相机 ID 必须唯一。创建或验证项目时检查归一化状态、输出文件、帧数、帧率和清单中的哈希；异常或不完整的目录不会被当作有效来源。项目、运行记录和复核导出中的 `normalization` 包含原片、输出、归一化清单、FFmpeg 的 SHA-256 和目标帧率。结果页及标定 / 时间预览提示分析输入经过重采样。校准和偏移配置导出会保留清单路径；若移动项目或归一化目录，需更新配置并重新验证。

来源信息反映本地归一化清单与输入哈希的一致性，不证明清单真实来源或原片仍存在；项目验证不会读取原片重新比对。直接以普通 `--camera` 指定 `normalized.mp4` 仍可运行，但不会自动关联其旁边的清单。重采样可能复制或丢帧、重置首帧时间，仍须重新核验相机时间对齐。

六路合成短片已使用 `--normalized-camera` 创建项目并完成 GPU 处理，运行和复核清单中均保留六路原片 / 输入哈希；浏览器逐路显示重采样提示。自动测试覆盖不完整状态、输出哈希不符，以及配置迁移时相对清单路径的保留。该检查不证明实际录像的同步、映射或人员识别准确性。

### 批量准备多路恒帧率项目（2026-11-13）

已有项目可一次按同一目标帧率顺序转换全部摄像头，并生成新项目：

```bash
.venv/bin/python -m walkflows project-normalize-project --config /path/source-project.json --fps 15 --destination /path/new-batch
.venv/bin/python -m walkflows project-calibration-ui --config /path/new-batch/project.json
.venv/bin/python -m walkflows project-run --config /path/new-batch/project.json --output /path/new-run --device 0
```

源项目的相机顺序、偏移、映射及 ROI 会被保留，源文件不覆盖；每路保留原片和输出哈希及独立归一化清单，新项目关联这些清单。原偏移仅作为待复核初值：每路重采样会重置首帧时间、可能复制或丢帧，必须结合实际画面重新核验时间对齐；映射和 ROI 也应结合画面复核。命令当前对所有相机使用同一显式帧率，不会自动选择最佳值；已含重采样来源的项目会拒绝再次批量转换，避免丢失上游来源链。

批次目录必须不存在，按相机串行处理。每路完成后写状态；只有全部转换、源配置和文件哈希复核、新项目验证均完成后，才发布 `project.json`。失败时保留日志和可能存在的部分输出，未发布的新项目不可使用；当前不支持自动续跑，应检查后另选目录重试。原始配置无时间交集时允许创建供后续调偏移的配置，但不能直接运行需共同时间的处理。

六路 8 帧合成变帧率片段通过该命令各生成 11 帧，随后完成六路 GPU 检测，复核服务验证了六条来源链。自动测试覆盖保留相机配置、来源哈希、拒绝重复转换及第二路失败时不发布项目。这是短片功能检查，不代表真实录像时间同步、标定或识别准确。
