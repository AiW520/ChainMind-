"""
文档上传路由 v2.0
支持分片上传、进度跟踪、异步处理
"""
import os
import uuid
import asyncio
from pathlib import Path
from typing import List, Optional, Dict
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..services.document_processor import process_document
from ..services.vector_store import get_vector_store

router = APIRouter(prefix="/upload", tags=["文档上传"])

# 支持的文件类型
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".html"}

# 分片上传状态存储
upload_states: Dict[str, dict] = {}


class ChunkUploadRequest(BaseModel):
    """分片上传请求"""
    file_id: str
    chunk_index: int
    total_chunks: int
    filename: str
    chunk: bytes


class ChunkUploadResponse(BaseModel):
    """分片上传响应"""
    file_id: str
    chunk_index: int
    status: str
    message: str


def get_upload_dir() -> Path:
    """获取上传目录"""
    base_dir = Path(__file__).parent.parent.parent
    data_dir = base_dir / "data"
    upload_dir = data_dir / "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def get_chunk_dir(file_id: str) -> Path:
    """获取分片临时目录"""
    upload_dir = get_upload_dir()
    chunk_dir = upload_dir / f".chunks_{file_id}"
    os.makedirs(chunk_dir, exist_ok=True)
    return chunk_dir


async def process_file_background(file_id: str, file_path: str, filename: str):
    """后台处理文件"""
    try:
        # 更新状态
        upload_states[file_id] = {
            "status": "processing",
            "progress": 0,
            "message": "正在解析文档..."
        }

        # 处理文档
        result = process_document(file_path)

        # 更新进度
        upload_states[file_id] = {
            "status": "processing",
            "progress": 50,
            "message": "正在向量化..."
        }

        # 添加到向量库
        if result.get("chunks"):
            vector_store = get_vector_store()
            vector_store.add_documents(result["chunks"], filename)

        # 完成
        upload_states[file_id] = {
            "status": "completed",
            "progress": 100,
            "message": "处理完成",
            "result": result
        }

    except Exception as e:
        upload_states[file_id] = {
            "status": "failed",
            "progress": 0,
            "message": f"处理失败: {str(e)}",
            "error": str(e)
        }


@router.post("/chunk")
async def upload_chunk(
    file_id: str,
    chunk_index: int,
    total_chunks: int,
    filename: str,
    chunk: UploadFile = File(...)
):
    """
    分片上传接口
    客户端将大文件分成多个chunk依次上传
    """
    # 验证文件类型
    file_extension = Path(filename).suffix.lower()
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_extension}"
        )

    # 初始化上传状态
    if file_id not in upload_states:
        upload_states[file_id] = {
            "file_id": file_id,
            "filename": filename,
            "total_chunks": total_chunks,
            "received_chunks": [],
            "status": "uploading",
            "progress": 0
        }

    # 保存分片
    chunk_dir = get_chunk_dir(file_id)
    chunk_path = chunk_dir / f"chunk_{chunk_index}"

    contents = await chunk.read()
    with open(chunk_path, "wb") as f:
        f.write(contents)

    # 更新状态
    upload_states[file_id]["received_chunks"].append(chunk_index)
    upload_states[file_id]["progress"] = int(
        len(upload_states[file_id]["received_chunks"]) / total_chunks * 80
    )

    # 检查是否所有分片都已上传
    if len(upload_states[file_id]["received_chunks"]) == total_chunks:
        # 合并分片
        upload_dir = get_upload_dir()
        final_path = upload_dir / filename

        with open(final_path, "wb") as output:
            for i in range(total_chunks):
                chunk_path = chunk_dir / f"chunk_{i}"
                with open(chunk_path, "rb") as input_chunk:
                    output.write(input_chunk.read())

        # 清理分片目录
        import shutil
        shutil.rmtree(chunk_dir)

        # 启动后台处理
        asyncio.create_task(
            process_file_background(file_id, str(final_path), filename)
        )

        return ChunkUploadResponse(
            file_id=file_id,
            chunk_index=chunk_index,
            status="completed",
            message="所有分片已上传，开始处理"
        )

    return ChunkUploadResponse(
        file_id=file_id,
        chunk_index=chunk_index,
        status="uploading",
        message=f"分片 {chunk_index + 1}/{total_chunks} 已上传"
    )


@router.get("/status/{file_id}")
async def get_upload_status(file_id: str):
    """获取上传状态"""
    if file_id not in upload_states:
        raise HTTPException(status_code=404, detail="上传任务不存在")

    return upload_states[file_id]


@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    单文件上传接口（小于10MB的文件）
    """
    # 检查文件扩展名
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_extension}，仅支持: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    # 检查文件大小
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小超过 10MB，请使用分片上传")

    # 保存文件
    upload_dir = get_upload_dir()
    file_path = upload_dir / file.filename

    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    # 后台处理
    asyncio.create_task(
        process_file_background(
            f"sync_{file.filename}",
            str(file_path),
            file.filename
        )
    )

    return {
        "status": "processing",
        "file_name": file.filename,
        "message": "文件已上传，正在后台处理"
    }


@router.post("/files")
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    """批量上传文件"""
    results = []
    upload_dir = get_upload_dir()

    for file in files:
        # 检查文件类型
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in SUPPORTED_EXTENSIONS:
            results.append({
                "file_name": file.filename,
                "status": "error",
                "error": f"不支持的文件类型: {file_extension}"
            })
            continue

        # 保存文件
        contents = await file.read()
        file_path = upload_dir / file.filename

        try:
            with open(file_path, "wb") as buffer:
                buffer.write(contents)

            # 后台处理
            asyncio.create_task(
                process_file_background(
                    f"async_{file.filename}",
                    str(file_path),
                    file.filename
                )
            )

            results.append({
                "file_name": file.filename,
                "status": "processing",
                "message": "文件已上传，正在后台处理"
            })
        except Exception as e:
            results.append({
                "file_name": file.filename,
                "status": "error",
                "error": str(e)
            })

    return {
        "total": len(files),
        "results": results
    }


@router.get("/list")
async def list_uploaded_files():
    """列出已上传的文件"""
    files = []
    upload_dir = get_upload_dir()

    for file_path in upload_dir.iterdir():
        if file_path.is_file() and not file_path.name.startswith("."):
            stat = file_path.stat()
            files.append({
                "name": file_path.name,
                "size": stat.st_size,
                "extension": file_path.suffix,
                "size_formatted": _format_size(stat.st_size)
            })

    return {"files": files}


@router.delete("/{filename}")
async def delete_file(filename: str):
    """删除文件"""
    upload_dir = get_upload_dir()
    file_path = upload_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    # 从向量库中删除
    vector_store = get_vector_store()
    vector_store.delete_by_filename(filename)

    # 删除文件
    file_path.unlink()

    return {"status": "deleted", "filename": filename}


def _format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
