from typing import List, Dict, Optional, Any
from fastapi import APIRouter, Query, HTTPException, Request
from pydantic import BaseModel
from pathlib import Path

from app.services import file_service
from app.core.config import CHECKPOINT_DIR

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/checkpoint-folders")
async def get_checkpoint_folder_list() -> List[str]:
    try:
        return file_service.get_checkpoint_folder_list()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/checkpoint-files")
async def get_checkpoint_file_list(folder: str = Query(default="")) -> List[str]:
    try:
        return file_service.get_checkpoint_file_list(folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ChatDataRequest(BaseModel):
    folder: str
    model: str
    params: Dict[str, Any] = {}
    dialogue_content: List[Dict[str, str]] = []


@router.post("/chat-data")
async def save_chat_data(req: ChatDataRequest) -> Dict:
    try:
        result = file_service.save_chat_data(req.folder, req.model, req.params)
        return {"message": "保存成功", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/chat-data")
async def update_chat_params(req: ChatDataRequest) -> Dict:
    try:
        result = file_service.save_chat_data(req.folder, req.model, req.params)
        return {"message": "更新成功", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat-data")
async def delete_chat_data(folder: str = Query(...), model: str = Query(...)) -> Dict:
    try:
        file_service.delete_chat_data(folder, model)
        return {"message": "删除成功"}
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat-data")
async def get_chat_data_endpoint(folder: str = Query(...), model: str = Query(...)) -> Dict:
    try:
        return file_service.get_chat_data(folder, model)
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/chat-data/dialogue")
async def update_dialogue_content(req: ChatDataRequest) -> Dict:
    try:
        result = file_service.update_dialogue_content(req.folder, req.model, req.dialogue_content or [])
        return {"message": "对话内容已更新", "data": result}
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/temp-txt")
async def get_temp_txt(folder: str = Query(...)) -> Dict:
    try:
        temp_file_path = CHECKPOINT_DIR / folder / "chat-data" / "temp.txt"
        if temp_file_path.exists():
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                return {"content": f.read()}
        return {"content": ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat-models")
async def get_chat_model_list() -> List[Dict[str, Any]]:
    try:
        return file_service.get_chat_model_list()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/base-models")
async def get_base_model_list() -> List[str]:
    try:
        return file_service.get_base_model_list()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MergeRequest(BaseModel):
    source_files: List[Dict[str, str]]
    shuffle: bool = True
    new_name: str
    counts: Dict[str, int]
    folder: str = "out"


@router.get("/folders")
async def get_folder_list() -> List[str]:
    try:
        return file_service.get_folder_list()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files")
async def get_file_list(folder: str = Query(default="")) -> List[str]:
    try:
        return file_service.get_file_list(folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/stats")
async def get_files_stats(
    files: str = Query(..., description="逗号分隔的文件名列表"),
    folders: str = Query(default="", description="逗号分隔的文件夹列表")
) -> List[Dict]:
    try:
        filenames = [f.strip() for f in files.split(',') if f.strip()]
        folder_list = [f.strip() for f in folders.split(',')] if folders else []
        if len(folder_list) == 0:
            folder_list = [''] * len(filenames)
        return file_service.get_files_stats(filenames, folder_list)
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{filename}/stats")
async def get_file_stats(filename: str, folder: str = Query(default="")) -> Dict:
    try:
        return file_service.get_file_stats(filename, folder)
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{filename}")
async def get_file_data(
    filename: str,
    folder: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    rounds_filter: str = Query(default="all")
):
    try:
        return file_service.read_jsonl(filename, folder, page, size, rounds_filter)
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/files/{filename}/{row_id}")
async def update_row(filename: str, row_id: int, folder: str = Query(default=""), request: Request = None):
    try:
        new_text = (await request.body()).decode('utf-8')
        file_service.update_row(filename, folder, row_id, new_text)
        return {"message": "更新成功"}
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except file_service.RowNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{filename}/{row_id}")
async def delete_row(filename: str, row_id: int, folder: str = Query(default="")):
    try:
        file_service.delete_row(filename, folder, row_id)
        return {"message": "删除成功"}
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except file_service.RowNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{filename}")
async def delete_whole_file(filename: str, folder: str = Query(default="")):
    try:
        file_service.delete_file(filename, folder)
        return {"message": f"文件 {filename} 已删除"}
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/merge")
async def merge_files(req: MergeRequest):
    try:
        result = file_service.merge_files_with_ratio(
            source_files=req.source_files,
            shuffle=req.shuffle,
            new_name=req.new_name,
            counts=req.counts,
            folder=req.folder
        )
        folder_path = req.folder or ''
        path_note = f"workspace/data/{folder_path}/{result['filename']}" if folder_path else f"workspace/data/{result['filename']}"
        return {
            "message": f"合并成功: {result['filename']}",
            "filename": result['filename'],
            "folder": result['folder'],
            "path": path_note,
            "total_lines": result['total_lines'],
            "original_lines": result['original_lines']
        }
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
