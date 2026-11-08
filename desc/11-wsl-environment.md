# WSL2 environment and CUDA repair

2026-11-07. User: corlin. Workspace: /home/corlin/WalkFlows.
Python 3.12.11, dual RTX 5060 Ti 16 GB, Windows driver 580.97.

Torch 2.15.0+cu132 imports and executes CPU operations but reproducibly segfaults in torch.cuda.is_available(). cuInit(0) succeeds and cuda.bindings enumerates both GPUs. Changing LD_LIBRARY_PATH and NVML detection did not repair execution.

An isolated torch 2.9.1+cu128 / torchvision 0.24.1 experiment succeeded. These versions are now pinned in pyproject.toml and uv.lock. Both GPUs pass matrix multiplication and torchvision CUDA NMS; all four existing unit tests pass. Ultralytics 8.3.162 imports. Exact native crash function remains unknown; driver incompatibility alone has not been proven. System CUDA and Windows drivers were not changed.

Install: `uv sync --locked --default-index https://mirrors.aliyun.com/pypi/simple`.
No actual video inference was verified at this stage.
