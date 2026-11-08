# site03 本地研究流程

在 WSL 中以 corlin 用户进入 `/home/corlin/WalkFlows`，使用已有的唯一项目虚拟环境 `.venv`；入口拒绝直接以 root 运行。

```bash
cd ~/WalkFlows
.venv/bin/python -m walkflows status
.venv/bin/python -m walkflows prepare --cross-scene
.venv/bin/python -m walkflows serve --port 8767
```

浏览器访问 http://127.0.0.1:8767/ 。服务在前台运行，Ctrl-C 结束。已有 site02 数据用于跨场景验证；不加 `--cross-scene` 时只验证 site03。`prepare --fetch` 可获取缺失的固定 site03 输入并校验哈希，不安装虚拟环境依赖，也不获取 site02 数据。准备完成后可附加 `--serve` 启动服务。

`status --json` 显示输入、环境、上次准备和产物来源状态；状态检查不测试 GPU。准备流程检查固定输入和模型，运行或复用校验过的逐相机结果，再验证并构建回放包。日志位于 `data/processed/local-pipeline/runs/`；最新状态及成功记录分别保存在同目录 `state.json` 和 `manifest.json`。源码、依赖版本、输入或产物变化会使当前标记失效。中断会终止流程启动的子进程；重新准备时可复用有效缓存。

使用上述服务时，单个 HTTP 请求与准备流程使用读写锁协调；准备期间请求返回 503。此保护不保证页面跨多个请求的快照一致，也不保证准备失败后的中间产物完整，应检查 status 后再使用。`bundle_current` 仅表示来源和验证报告一致，并非定位、跨镜身份、客流或业务指标已通过验收。
