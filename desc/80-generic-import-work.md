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
