# 通用区域流转候选与参考轨迹的条件性对照

2026-11-13。复用既有研究中的示意 north/south 矩形，而非真实门店分区；坐标见 [示例区域](../configs/site03-example-zones.json)。对 site03 006 和 007 的左视角 ROI 结果，以及同一参考轨迹应用相同的单镜区域边界规则：只连接连续有效帧、无同帧边界冲突的离开→进入，最长间隔固定 30 秒。条件对照只看方向相同、离开和到达时间均在参考事件前后 1 秒内；不建立一对一身份，也不将时间邻近当作真阳性。两个片段和区域均曾用于开发，不是独立盲测。

| 录像 | 输入尺寸 | 参考流转 | 单镜候选 | 与参考时间邻近的候选 |
|---|---:|---:|---:|---:|
| 006 | 640 | 1 | 2 | 1 |
| 006 | 1280 | 1 | 1 | 1 |
| 007 | 640 | 1 | 0 | 0 |
| 007 | 1280 | 1 | 0 | 0 |

006 的参考 north→south 时间为 6.27→7.07 秒；640 的 C0001056 局部轨迹候选为 5.73→6.67 秒，属于所设时间邻近范围，另一个候选没有邻近参考。007 的参考事件为 23.53→23.87 秒，两种设置均未生成候选。参考的可见性、完整性、时间同步和身份均未独立证明；不同摄像头可能重复观察，候选和参考数量不能当作人数、精确率或召回率。这套规则没有过去研究脚本的停留阈值与边界余量，结果不能与先前不同规则的事件数直接比较。

针对 007 失败事件，事后检查参考轨迹 ID 1 的 343–368 帧，共 26 帧有参考位置：在 0.5 场景单位内，640 和 1280 均仅在 C0001056 的第 358、359 帧各出现一条邻近投影；640 两条均无局部 ID，1280 两条均带 ID 30。该窗口是发现失败后选择的探索性诊断，不能单独判断漏检原因或证明身份，但说明严格连续流转缺少足够邻近支撑。

复现：`scripts.evaluate_generic_zone_events` 接受已完成运行、参考文件、区域 JSON、最长间隔、时间容差和明确的对齐假设；它校验视频及 CSV 哈希并输出每路候选和参考邻近列表。示例命令：

```bash
.venv/bin/python -m scripts.evaluate_generic_zone_events \
  --run data/processed/site03-006-roi-v1/result \
  --reference data/raw/multiview/006_site03_tracks/ground-truth.json \
  --zones configs/site03-example-zones.json --max-duration 30 --time-tolerance 1 \
  --assume-aligned --output /path/to/new-zone-eval.json
```

`scripts.audit_generic_reference_window` 用于事后窗口诊断；四份最终事件报告位于本地忽略的 `data/processed/site03-006-roi-v1/zone-eval-v3*.json` 和 `data/processed/site03-007-roi-v1/zone-eval-v3*.json`，窗口报告位于后者的 `window-audit*.json`。代码测试覆盖缺帧、重复编号、时间限制、歧义候选以及 Python 与浏览器规则在合成样本上的一致性。

下一步应优先改善有参考位置但单镜轨迹稀疏的片段，分析检测框、遮挡与 tracker 状态，并在包含逐镜可见性标注的独立数据上检验，避免放宽规则制造连续性。
