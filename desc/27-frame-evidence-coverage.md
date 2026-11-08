# 逐帧证据覆盖

2026-11-08。scripts/report_site02_coverage.py 按相机和帧关联质量台账与姿态证据；逐帧数量不匹配、缺帧或乱序时停止。输出 data/processed/site02-coverage/frame_coverage.csv 与 summary.json，记录输入哈希。

第一路218帧中：213帧仅研究候选、2帧无轨迹输出、3帧只有硬排除观测。第二路：144帧仅研究候选、74帧无轨迹输出。两路共418条观测均能分解到姿态分数或未匹配/歧义状态。

这些是处理结果覆盖，不是实际人数、召回率或可见性。无轨迹输出代表未知，不能当作无人；0.25只用于描述模型分数，不自动改变质量状态。没有生成区域事件或跨镜头身份。

复现：先运行 scripts/export_site02_quality.py 和 scripts/export_pose_evidence.py，再运行 scripts/report_site02_coverage.py。验收：436帧、418观测、逐帧证据分解一致；15项现有单元测试通过。
