# 本机预训练模型基线

更新：2026-11-06｜状态：短片段已运行，跨镜头尚未验证

## 方案与复现

- 用途：内部研究，公开 CITIC capture1 大厅两路前 10 秒；不采集、不标注、不训练。每路独立跟踪，输出的 ID 仅在该路范围内有效。
- 本机：Apple M1 Pro、16 GB 内存；uv 管理的 Python 3.12.9，Ultralytics 8.3.162、YOLO11n 预训练权重、ByteTrack、MPS。锁文件固定依赖；这个组合是实验基线，不表示已证明最稳定或选定最终供应商。
- 权重来自 [Ultralytics 官方 v8.3.0 资源](https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt)，SHA-256 `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`。保存在不入库的 `data/models/yolo11n.pt`。使用和再分发前核查权重与代码许可。
- 依赖安装：`uv sync --locked`。样本和标定文件放入 `data/raw/citic/` 后，执行 `uv run --locked python -m walkflows.run_baseline --seconds 10 --device mps`；执行 `uv run --locked python -m walkflows.candidates` 生成同帧空间候选；测试为 `uv run --locked python -m unittest discover -s tests`。
- 每路输出标注回放、观测 CSV；`run.json` 记录权重哈希、设备与运行摘要；`candidate_pairs.json` 仅列空间候选，不合并 ID。结果保存在 `data/processed/baseline/`，不入库。

## 首次运行结果

| 摄像头 | 处理帧 | 观测行数 | 局部轨迹 ID 数 | 耗时 |
| --- | ---: | ---: | ---: | ---: |
| HallSeg | 250 | 250 | 2 | 31.89 秒 |
| HallWide | 250 | 127 | 5 | 6.50 秒 |

耗时包含逐帧推理、标注及视频写入，首路包含首次运行预热；不含模型加载，不能用于严格的设备速度对比。观测行数是检测到轨迹的帧数总和，局部 ID 数可能因误检、遮挡、切换或重复而偏离实际人数；以上数字不代表准确率。回放视频可解码且均为 250 帧。

依据假设两路同帧同步，在未校准精度验证的地面坐标上以 1 米作探索阈值，出现多个空间候选。例如 HallSeg ID 2 与 HallWide ID 12 有 65 帧候选，距离中位数 0.438 米；ID 2 与 HallWide ID 1 和 6 也产生候选。阈值仅用于探索，候选可重叠、非一对一，不能证明身份、同步或定位精度，也不能直接汇总为整店去重客流。

## 待完成

1. 沿连续视频检查同帧是否同步、轨迹是否为同一人及投影误差；数据集现有参考为路点插值且缺少检测框，不额外造标注或声称检测准确率。
2. 检查短轨迹和明显不可见脚点造成的异常，设计保守的过滤与未匹配状态，不能直接强行跨镜头拼接。
3. 对照 [YOLOX](https://github.com/Megvii-BaseDetection/YOLOX) 等非 Ultralytics 模型，固定版本、同样片段及设置，比较运行、检测与依赖许可。YOLOX 仓库代码采用 Apache-2.0，原始 [ByteTrack](https://github.com/FoundationVision/ByteTrack) 仓库代码采用 MIT；预训练权重和其他依赖需单独核验。当前使用的是 Ultralytics 的 ByteTrack 集成，其许可不能按原始仓库直接推定。
4. 确认可复现的数据下载方式和干净环境，选择可量化的验证场景后，再进入区域事件、热力图和产品层。
