# attendance_bot/api/routers/reports.py
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.middlewares.auth import get_current_user, require_role
from models import User, UserRole
from services.report_service import ReportService

router = APIRouter()


class ReportRequest(BaseModel):
    report_type: str  # monthly, yearly, department
    year: int
    month: Optional[int] = None
    department_id: Optional[int] = None
    user_id: Optional[int] = None
    format: str = "excel"  # excel, pdf


@router.post("/generate")
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db)
):
    service = ReportService(db)

    if request.format == "excel":
        file_path = await service.generate_excel_report(
            report_type=request.report_type,
            year=request.year,
            month=request.month,
            department_id=request.department_id,
            user_id=request.user_id,
        )
    elif request.format == "pdf":
        file_path = await service.generate_pdf_report(
            report_type=request.report_type,
            year=request.year,
            month=request.month,
            department_id=request.department_id,
            user_id=request.user_id,
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

    return {
        "message": "Report generated successfully",
        "file_path": file_path,
        "download_url": f"/api/v1/reports/download?path={file_path}"
    }


@router.get("/download")
async def download_report(
    path: str,
    current_user: User = Depends(require_role(UserRole.MANAGER))
):
    import os
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report file not found")

    filename = os.path.basename(path)
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"         if filename.endswith(".xlsx") else "application/pdf"

    return FileResponse(
        path=path,
        filename=filename,
        media_type=media_type
    )
