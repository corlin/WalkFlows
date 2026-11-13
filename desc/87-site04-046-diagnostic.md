# site04 第二段六路录像的覆盖与参考诊断

2026-11-13。对已纳入训练分区的公开数据 `046_site04_sitting_3` 做开发诊断，不用于最终盲测或模型选择。此前 045 场景的前六路几乎没有投影，补充相机 C0001035 在高分辨率下曾有少量参考邻近。为检验另一段录像，运行前固定选择清单后六路 C0001030、1031、1034、1035、1036、1058，选择依据包含此前覆盖诊断，不能视为随机或无偏相机样本。其他镜头没有运行；site07 保留测试未使用。

六路均为左右拼接画面，按原始标定使用左半幅 ROI 与近似平面映射，采用清单时间偏移（未独立验证同步）。每路解码 150 帧，视频 15 fps；参考含 149 帧、两条轨迹，参考可见性、身份和完整性未独立证明。模型使用固定 YOLO11n、ByteTrack、0.25 阈值和同一 GPU，先运行 640，再按之前 site04 诊断的 1280 输入做对照。两个运行使用相同权重及当前代码；观测不能当作独立人数。

| 模型输入 | 六路观察 | 有效投影 | 0.5 场景单位内参考邻近 | 单次耗时 |
|---|---:|---:|---:|---:|
| 640 | 88 | 88 | 0 | 35.2 秒 |
| 1280 | 14 | 14 | 0 | 37.1 秒 |

所有观察来自 C0001035，另外五路均无观察。640 的 88 条观察在参考帧中的最近参考距离约 0.583–0.673、中位约 0.657 场景单位；这是事后诊断，假定参考同坐标和同步，不是定位误差真值。只抽查该镜头首帧，框覆盖疑似衣物或遮挡区域，是否为人无法仅凭该画面确定；不能将连续观察当作确认人员或用轨迹连续性排除误检。1280 减少观察，未在固定距离门限内产生邻近，不能认为分辨率提高改善该样本。耗时是一次运行含初始化和散列，不是性能基准。

浏览器用 640 运行打开六路页面并启动播放，页面显示每路观察数量及未验证提示；这是功能检查，不证明定位、关联或事件准确。配置、输入散列、模型、观察及报告保存在本机忽略目录 `data/processed/site04-046-selected-six/`；公开数据及校准来源和许可参见 [数据记录](03-data-and-licenses.md)。条件性对照报告为 `reference-report.json` 和 `reference-report-1280.json`，首帧复核图为 `diagnostic-frame0.jpg`。

此证据支持维持默认 640，不支持通过简单放宽距离或一味增加分辨率解决问题。后续应结合可验证的逐镜可见性与脚点标注，区分检测误报、遮挡、坐姿参考定义和映射误差；避免根据本片段调整最终阈值或将数据集参考当作现场测量。

复核入口（已生成配置及结果时）：

```bash
.venv/bin/python -m walkflows project-review --output data/processed/site04-046-selected-six/result
.venv/bin/python -m walkflows project-evaluate-reference --output data/processed/site04-046-selected-six/result --reference data/raw/multiview/full-dataset/testcases/046_site04_sitting_3/ground-truth.json --distance 0.5 --assume-aligned --report /path/to/new-report.json
```

从输入重新处理可用上述目录的 `config.json`，分别执行 `project-run --config ... --output NEW_DIR --weights data/models/yolo11n.pt --device 0 --image-size 640 --confidence 0.25` 与 `--image-size 1280`；输出目录必须不同且不存在。
