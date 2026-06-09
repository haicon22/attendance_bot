# attendance_bot/tasks/report_tasks.py
import logging

from tasks.celery_app import celery_app
from core.database import AsyncSessionLocal
from services.report_service import ReportService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def generate_monthly_report(self, year: int, month: int, department_id: int = None):
    """Generate monthly attendance report asynchronously."""
    import asyncio

    async def _generate():
        async with AsyncSessionLocal() as session:
            service = ReportService(session)
            file_path = await service.generate_excel_report(
                report_type="monthly",
                year=year,
                month=month,
                department_id=department_id,
            )
            return file_path

    try:
        file_path = asyncio.run(_generate())
        logger.info(f"Generated monthly report: {file_path}")
        return {"status": "success", "file_path": file_path}
    except Exception as exc:
        logger.error(f"Failed to generate report: {exc}")
        raise self.retry(exc=exc, countdown=300)


@celery_app.task
def cleanup_old_reports(days: int = 30):
    """Clean up report files older than specified days."""
    import os
    from datetime import datetime, timedelta

    reports_dir = "/app/reports"
    cutoff = datetime.now() - timedelta(days=days)

    cleaned = 0
    for filename in os.listdir(reports_dir):
        filepath = os.path.join(reports_dir, filename)
        if os.path.getmtime(filepath) < cutoff.timestamp():
            os.remove(filepath)
            cleaned += 1

    logger.info(f"Cleaned up {cleaned} old report files")
    return {"cleaned": cleaned}
