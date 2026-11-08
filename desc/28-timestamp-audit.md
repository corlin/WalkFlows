# site02 文件时间戳审计

2026-11-08。使用项目唯一的 .venv 和 OpenCV 4.11 解码固定哈希的两路 site02 视频；每路218帧、15 fps。逐帧读取 CAP_PROP_POS_MSEC 和 CAP_PROP_PTS：两路时间戳严格递增，0–14466.667 ms，对应帧时间差为0。原始CSV及哈希保存在 data/processed/site02-timestamp-audit。

这是解码后文件时间轴一致，不是摄像头真实曝光同步的证据。公开 manifest 的零起点是占位；ground-truth 内历史配置的约20.666ms差异不能直接应用到发布短片。脚本不选择或修正偏移，W06仍未验收。ffprobe在当前环境未找到，本次结果来自OpenCV解码器，不代表独立容器级校验。

复现：.venv/bin/python scripts/audit_site02_timestamps.py。脚本验证视频哈希、帧数、时间单调性和逐帧差值。
