"""
文档上传路由
功能：接收用户上传的文档，保存到服务器，并调用文档处理服务
"""
import os
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from ..services.document_processor import process_document
from ..services.vector_store import get_vector_store

from pathlib import Path
import os

router = APIRouter(prefix="/upload", tags=["文档上传"])

# 支持的文件类型
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}

def get_upload_dir():
    """获取上传目录的绝对路径"""
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    upload_dir = data_dir / "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

@router.post("/file")
async def upload_file(file: UploadFile = File(...)):
    """
    上传单个文档
    
    - **file**: 要上传的文件（支持 .txt, .md, .pdf）
    
    Returns:
        文档处理结果，包含文件名、页数、切割块数等
    """
    # 检查文件扩展名
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_extension}，仅支持: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    
    # 检查文件大小（限制 10MB）
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        # raise 语句用于主动触发异常
        raise HTTPException(status_code=400, detail="文件大小超过 10MB 限制")
    
    # 保存文件
    upload_dir = get_upload_dir()
    file_path = upload_dir / file.filename
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    
    # 处理文档
    try:
        result = process_document(str(file_path))
        result["status"] = "success"
        
        # ✅ 自动将 chunks 添加到向量库
        if result.get("chunks"):
            vector_store = get_vector_store()
            vector_store.add_documents(result["chunks"], file.filename)
            result["vector_stored"] = True
        
        return result
    except Exception as e:
        # 处理失败，删除已上传的文件
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")

@router.post("/files")
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    """
    批量上传文档
    
    - files: 要上传的文件列表
    
    Returns:
        所有文档的处理结果
    """
    results = []
    uploaded_files = []
    
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
        upload_dir = get_upload_dir()
        file_path = upload_dir / file.filename
        
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(contents)
            uploaded_files.append(file_path)
            
            # 处理文档
            result = process_document(str(file_path))
            result["status"] = "success"
            
            # ✅ 自动将 chunks 添加到向量库
            if result.get("chunks"):
                vector_store = get_vector_store()
                vector_store.add_documents(result["chunks"], file.filename)
                result["vector_stored"] = True
            
            results.append(result)
        except Exception as e:
            results.append({
                "file_name": file.filename,
                "status": "error",
                "error": str(e)
            })
            # 清理已上传的文件
            if file_path.exists():
                file_path.unlink()
    
    return {
        "total": len(files),
        "success_count": sum(1 for r in results if r["status"] == "success"),
        "results": results
    }

@router.get("/list")
async def list_uploaded_files():
    """
    列出已上传的所有文档
    """
    files = []
    upload_dir = get_upload_dir()
    for file_path in upload_dir.iterdir():
        if file_path.is_file():
            files.append({
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "extension": file_path.suffix
            })
    return {"files": files}

@router.delete("/{filename}")
async def delete_file(filename: str):
    """
    删除指定的已上传文件
    """
    upload_dir = get_upload_dir()
    file_path = upload_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_path.unlink()
    return {"status": "deleted", "filename": filename}
