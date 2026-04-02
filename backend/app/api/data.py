from typing import List, Dict, Optional
from fastapi import APIRouter, Query, HTTPException, Request
from pydantic import BaseModel

from app.services import file_service

router = APIRouter(prefix="/api/data", tags=["data"])


class MergeRequest(BaseModel):
    source_files: List[str]
    shuffle: bool = True
    new_name: str
    counts: Dict[str, int]


@router.get("/files")
async def get_file_list() -> List[str]:
    try:
        return file_service.get_file_list()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/stats")
async def get_files_stats(
    files: str = Query(..., description="逗号分隔的文件名列表")
) -> List[Dict]:
    try:
        filenames = [f.strip() for f in files.split(',') if f.strip()]
        return file_service.get_files_stats(filenames)
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{filename}/stats")
async def get_file_stats(filename: str) -> Dict:
    try:
        return file_service.get_file_stats(filename)
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{filename}")
async def get_file_data(
    filename: str,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100)
):
    try:
        return file_service.read_jsonl(filename, page, size)
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/files/{filename}/{row_id}")
async def update_row(filename: str, row_id: int, request: Request):
    try:
        new_text = (await request.body()).decode('utf-8')
        file_service.update_row(filename, row_id, new_text)
        return {"message": "更新成功"}
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except file_service.RowNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{filename}/{row_id}")
async def delete_row(filename: str, row_id: int):
    try:
        file_service.delete_row(filename, row_id)
        return {"message": "删除成功"}
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except file_service.RowNotFoundError as e:
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
            counts=req.counts
        )
        return {
            "message": f"合并成功: {result['filename']}",
            "filename": result['filename'],
            "total_lines": result['total_lines'],
            "original_lines": result['original_lines']
        }
    except file_service.FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
