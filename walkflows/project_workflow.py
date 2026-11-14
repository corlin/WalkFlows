"""Single local workflow from camera paths to a review page."""
import json
import re
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from walkflows.multicamera_processing import file_sha256, run_project
from walkflows.multicamera_project import apply_offsets, build_project, create_config
from walkflows.multicamera_review import make_calibration_handler, serve as serve_review
from walkflows.plane_calibration import apply_calibration, apply_calibration_bundle


def local_path(path):
    text=str(path).strip().strip('"')
    match=re.match(r"^([A-Za-z]):[\\/](.*)$",text)
    if match:
        text="/mnt/"+match.group(1).lower()+"/"+match.group(2).replace(chr(92),"/")
    return str(Path(text).expanduser().resolve())


def prepare_project(name,cameras,workspace,*,mapping_config=None):
    workspace=Path(workspace).expanduser().resolve()
    workspace.mkdir(parents=True,exist_ok=False)
    entries=[{**camera,"path":local_path(camera["path"])} for camera in cameras]
    initial=workspace/"project.json"
    project=create_config(name,entries,initial)
    if mapping_config is None:return initial
    mapping_config=Path(local_path(mapping_config)).resolve(strict=True)
    mapping_hash=file_sha256(mapping_config)
    reference=build_project(mapping_config,allow_no_overlap=True)
    if file_sha256(mapping_config)!=mapping_hash:raise ValueError("mapping configuration changed")
    source={c["id"]:c for c in reference["cameras"]}
    if set(source)!={c["id"] for c in project["cameras"]}:
        raise ValueError("mapping camera IDs must exactly match project cameras")
    config=json.loads(initial.read_text(encoding="utf-8"))
    actual={c["id"]:c for c in project["cameras"]}
    for item in config["cameras"]:
        old=source[item["id"]];new=actual[item["id"]]
        if (old["video"]["width"],old["video"]["height"])!=(new["video"]["width"],new["video"]["height"]):
            raise ValueError("mapping camera dimensions differ: "+item["id"])
        if old["homography"] is not None:
            item["homography"]=old["homography"]
            if old.get("calibration_polygon") is not None:item["calibration_polygon"]=old["calibration_polygon"]
            item["calibration_provenance"]={"mapping_config_sha256":mapping_hash,
                "source":old.get("calibration_provenance"),
                "scope":"User-supplied calibration; matching IDs and dimensions do not verify the same physical setup."}
        if old.get("analysis_roi") is not None:item["analysis_roi"]=old["analysis_roi"]
    output=workspace/"mapped.json"
    with output.open("x",encoding="utf-8") as file:json.dump(config,file,indent=2,ensure_ascii=False,allow_nan=False);file.write(chr(10))
    build_project(output)
    return output


def configure_interactively(config,workspace,port,*,preview_dir=None):
    project=build_project(config,allow_no_overlap=True)
    base_handler=make_calibration_handler(project,preview_dir=preview_dir)
    class QuietHandler(base_handler):
        def log_message(self,format,*args):
            pass
    server=ThreadingHTTPServer(("127.0.0.1",port),QuietHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        print("时间和地面配置页面：http://127.0.0.1:"+str(server.server_port)+"/",flush=True)
        print("可在时间对齐页面下载偏移 JSON；可为每个相机选择地面点并下载 JSON。",flush=True)
        print("Windows 下载目录可输入 C:\\Users\\...，将自动转换为 WSL 路径。",flush=True)
        while True:
            offsets=input("偏移 JSON 路径（直接回车保留当前偏移）：").strip()
            if not offsets:break
            target=workspace/"timed-interactive.json"
            try:apply_offsets(config,local_path(offsets),target)
            except (ValueError,OSError,KeyError,TypeError) as error:
                print("偏移文件无效："+str(error)+"；请重试或回车跳过。",flush=True)
                continue
            config=target;break
        points=input("整组标定 JSON 路径（或输入 y 逐相机导入，回车跳过）：").strip()
        while points and points.lower()!="y":
            target=workspace/"mapped-bundle.json"
            try:apply_calibration_bundle(config,local_path(points),target)
            except (ValueError,OSError,KeyError,TypeError) as error:
                print("整组标定文件无效："+str(error)+"；请重试、输入 y 逐相机导入或回车跳过。",flush=True)
                points=input("整组标定 JSON 路径（或输入 y，回车跳过）：").strip()
                continue
            config=target;break
        if points.lower()=="y":
            for camera in project["cameras"]:
                while True:
                    path=input(camera["id"]+" 的点文件路径（回车跳过）：").strip()
                    if not path:break
                    target=workspace/("mapped-"+camera["id"]+".json")
                    try:apply_calibration(config,camera["id"],local_path(path),target)
                    except (ValueError,OSError,KeyError,TypeError) as error:
                        print("对应点文件无效："+str(error)+"；请重试或回车跳过。",flush=True)
                        continue
                    config=target;break
        return config
    finally:
        server.shutdown();server.server_close();thread.join()


def process_and_review(config,workspace,weights,device,port,*,no_serve=False,preview_dir=None):
    project=build_project(config)
    result=workspace/"result"
    stopped=threading.Event()
    def show_progress():
        state_path=result/"run.json";last=None
        while not stopped.wait(2):
            try:
                state=json.loads(state_path.read_text(encoding="utf-8"))
                entries=state.get("cameras",[])
                line=tuple((x.get("id"),x.get("status"),x.get("decoded_frames")) for x in entries)
                if line!=last:
                    completed=sum(x.get("status")=="completed" for x in entries)
                    current=next((x for x in entries if x.get("status")=="running"),None)
                    text="处理进度："+str(completed)+"/"+str(len(project["cameras"]))+" 路完成"
                    if current:text+=" · "+str(current.get("id"))+" 已解码 "+str(current.get("decoded_frames",0))+" 帧"
                    print(text,flush=True);last=line
            except (OSError,ValueError):pass
    monitor=threading.Thread(target=show_progress,daemon=True);monitor.start()
    try:run_project(project,result,weights,device)
    finally:stopped.set();monitor.join()
    print("处理完成："+str(result),flush=True)
    if not no_serve:
        print("结果页面服务运行中；按 Ctrl-C 停止。",flush=True)
        serve_review(result,port,preview_dir=preview_dir)
    return result


def run_workflow(name,cameras,workspace,weights,device,config_port,review_port,
                 *,mapping_config=None,offsets_file=None,non_interactive=False,no_serve=False,preview_dir=None):
    workspace=Path(workspace).expanduser().resolve()
    config=prepare_project(name,cameras,workspace,mapping_config=mapping_config)
    print("项目配置："+str(config),flush=True)
    for camera in build_project(config,allow_no_overlap=True)["cameras"]:
        video=camera["video"]
        print(camera["id"]+" · "+str(video["width"])+"×"+str(video["height"])+" · "+
              str(video["fps"])+" fps · "+format(video["duration_seconds"],".2f")+" 秒 · "+
              str(video.get("codec_fourcc") or "编码未知"),flush=True)
    print("时间偏移与地面映射须依据实际场地检查；默认零偏移不代表已同步。",flush=True)
    if mapping_config:
        print("已导入映射；相机同名和画面尺寸一致不证明设备位置或坐标系一致，请实际核验。",flush=True)
    if offsets_file:
        target=workspace/"timed.json"
        apply_offsets(config,local_path(offsets_file),target);config=target
    if not non_interactive:config=configure_interactively(config,workspace,config_port,preview_dir=preview_dir)
    print("将使用配置："+str(config),flush=True)
    final_project=build_project(config)
    missing=[camera["id"] for camera in final_project["cameras"] if camera["homography"] is None]
    if missing:
        print("未标定："+ "、".join(missing)+"；这些镜头仅显示单镜观察，不能生成平面候选。",flush=True)
    return process_and_review(config,workspace,weights,device,review_port,no_serve=no_serve,preview_dir=preview_dir)
