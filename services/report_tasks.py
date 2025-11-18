"""
Celery tasks for asynchronous report generation.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from uuid import UUID
from celery import Task
from services.celery_app import celery_app
from models.scan import ScanResult
from models.report import Report, ReportFormat
from analytics.report_generator import ReportGenerator
from database.connection import get_db_connection
from core.config import get_config, init_config

logger = logging.getLogger(__name__)


class ReportTask(Task):
    """Base task class for report tasks with error handling."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 60
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=ReportTask,
    name='generate_report_async'
)
def generate_report_async(
    self,
    scan_id: str,
    format: str = 'pdf'
) -> Dict[str, Any]:
    """
    Generate compliance report asynchronously via Celery.
    
    Args:
        scan_id: Scan ID to generate report for
        format: Report format (pdf, html, json)
        
    Returns:
        Result dictionary with report details
    """
    try:
        # Initialize config if not already done
        try:
            get_config()
        except RuntimeError:
            init_config()
        
        logger.info(f"Starting async report generation for scan {scan_id}, format: {format}")
        
        # Convert format string to enum
        try:
            report_format = ReportFormat(format.lower())
        except ValueError:
            raise ValueError(f"Invalid report format: {format}. Must be one of: pdf, html, json")
        
        # Fetch scan result from database
        scan_result = _fetch_scan_result(scan_id)
        if not scan_result:
            raise ValueError(f"Scan result not found: {scan_id}")
        
        # Generate report
        report_generator = ReportGenerator()
        report = report_generator.generate_compliance_report(scan_result, report_format)
        
        # Store report metadata in database (if needed)
        _store_report_metadata(report)
        
        result = {
            'report_id': str(report.report_id),
            'scan_id': str(report.scan_id),
            'format': report.format.value,
            'file_path': report.file_path,
            'file_size': report.file_size,
            'generated_at': report.generated_at.isoformat(),
            'status': 'completed'
        }
        
        logger.info(
            f"Async report generation completed: {report.report_id}, "
            f"file: {report.file_path}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_report_async task: {e}", exc_info=True)
        # Re-raise to trigger Celery retry
        raise


@celery_app.task(
    bind=True,
    base=ReportTask,
    name='generate_multiple_reports_async'
)
def generate_multiple_reports_async(
    self,
    scan_id: str,
    formats: list[str] = None
) -> Dict[str, Any]:
    """
    Generate multiple report formats for a scan asynchronously.
    
    Args:
        scan_id: Scan ID to generate reports for
        formats: List of report formats (defaults to all formats)
        
    Returns:
        Result dictionary with all generated reports
    """
    try:
        # Initialize config if not already done
        try:
            get_config()
        except RuntimeError:
            init_config()
        
        if formats is None:
            formats = ['pdf', 'html', 'json']
        
        logger.info(
            f"Starting async multi-format report generation for scan {scan_id}, "
            f"formats: {formats}"
        )
        
        # Fetch scan result once
        scan_result = _fetch_scan_result(scan_id)
        if not scan_result:
            raise ValueError(f"Scan result not found: {scan_id}")
        
        # Generate all reports
        report_generator = ReportGenerator()
        reports = []
        
        for format_str in formats:
            try:
                report_format = ReportFormat(format_str.lower())
                report = report_generator.generate_compliance_report(scan_result, report_format)
                _store_report_metadata(report)
                reports.append({
                    'report_id': str(report.report_id),
                    'format': report.format.value,
                    'file_path': report.file_path,
                    'file_size': report.file_size,
                    'status': 'completed'
                })
            except Exception as e:
                logger.error(f"Failed to generate {format_str} report: {e}")
                reports.append({
                    'format': format_str,
                    'status': 'failed',
                    'error': str(e)
                })
        
        result = {
            'scan_id': scan_id,
            'reports': reports,
            'total_generated': len([r for r in reports if r.get('status') == 'completed']),
            'total_failed': len([r for r in reports if r.get('status') == 'failed'])
        }
        
        logger.info(
            f"Async multi-format report generation completed: {scan_id}, "
            f"generated {result['total_generated']}/{len(formats)} reports"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_multiple_reports_async task: {e}", exc_info=True)
        raise


@celery_app.task(
    bind=True,
    base=ReportTask,
    name='export_scan_to_csv_async'
)
def export_scan_to_csv_async(
    self,
    scan_id: str
) -> Dict[str, Any]:
    """
    Export scan cookies to CSV format asynchronously.
    
    Args:
        scan_id: Scan ID to export
        
    Returns:
        Result dictionary with export details
    """
    try:
        # Initialize config if not already done
        try:
            get_config()
        except RuntimeError:
            init_config()
        
        logger.info(f"Starting async CSV export for scan {scan_id}")
        
        # Fetch scan result
        scan_result = _fetch_scan_result(scan_id)
        if not scan_result:
            raise ValueError(f"Scan result not found: {scan_id}")
        
        # Export to CSV
        report_generator = ReportGenerator()
        file_path = report_generator.export_to_csv(scan_result)
        
        result = {
            'scan_id': scan_id,
            'file_path': file_path,
            'format': 'csv',
            'status': 'completed'
        }
        
        logger.info(f"Async CSV export completed: {file_path}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in export_scan_to_csv_async task: {e}", exc_info=True)
        raise


@celery_app.task(name='cleanup_old_reports')
def cleanup_old_reports(days: int = 30) -> Dict[str, Any]:
    """
    Clean up old report files (placeholder for future implementation).
    
    Args:
        days: Number of days to keep reports
        
    Returns:
        Result dictionary with cleanup summary
    """
    try:
        # TODO: Implement cleanup logic when report persistence is added
        logger.info(f"Cleanup task executed for reports older than {days} days")
        
        return {
            'status': 'completed',
            'days': days,
            'deleted_count': 0  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_reports task: {e}", exc_info=True)
        raise


# Helper functions

def _fetch_scan_result(scan_id: str) -> Optional[ScanResult]:
    """
    Fetch scan result from database.
    
    Args:
        scan_id: Scan ID to fetch
        
    Returns:
        ScanResult object or None if not found
    """
    try:
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch scan result
        cursor.execute(
            """
            SELECT 
                scan_id, domain_config_id, domain, scan_mode, 
                timestamp_utc, status, duration_seconds, total_cookies,
                page_count, error, params
            FROM scan_results
            WHERE scan_id = %s
            """,
            (scan_id,)
        )
        
        row = cursor.fetchone()
        if not row:
            logger.warning(f"Scan result not found: {scan_id}")
            return None
        
        # Fetch cookies for this scan
        cursor.execute(
            """
            SELECT 
                name, domain, path, hashed_value, category, vendor,
                cookie_type, set_after_accept, metadata
            FROM cookies
            WHERE scan_id = %s
            """,
            (scan_id,)
        )
        
        cookie_rows = cursor.fetchall()
        
        # Construct ScanResult object
        from models.scan import Cookie, ScanMode, ScanStatus
        import json
        
        cookies = []
        for cookie_row in cookie_rows:
            metadata = cookie_row[8] if cookie_row[8] else {}
            cookie = Cookie(
                name=cookie_row[0],
                domain=cookie_row[1],
                path=cookie_row[2],
                hashed_value=cookie_row[3],
                category=cookie_row[4],
                vendor=cookie_row[5],
                cookie_type=cookie_row[6],
                set_after_accept=cookie_row[7],
                cookie_duration=metadata.get('cookie_duration'),
                size=metadata.get('size'),
                http_only=metadata.get('http_only', False),
                secure=metadata.get('secure', False),
                same_site=metadata.get('same_site'),
                iab_purposes=metadata.get('iab_purposes', []),
                description=metadata.get('description'),
                source=metadata.get('source')
            )
            cookies.append(cookie)
        
        scan_result = ScanResult(
            scan_id=UUID(row[0]),
            domain_config_id=UUID(row[1]) if row[1] else None,
            domain=row[2],
            scan_mode=ScanMode(row[3]) if row[3] else ScanMode.QUICK,
            timestamp_utc=row[4],
            status=ScanStatus(row[5]) if row[5] else ScanStatus.COMPLETED,
            duration_seconds=row[6],
            total_cookies=row[7],
            page_count=row[8],
            cookies=cookies,
            pages_visited=[],
            storages={},
            params=row[10] if row[10] else {},
            error=row[9]
        )
        
        cursor.close()
        conn.close()
        
        logger.info(f"Fetched scan result: {scan_id} with {len(cookies)} cookies")
        return scan_result
        
    except Exception as e:
        logger.error(f"Error fetching scan result {scan_id}: {e}", exc_info=True)
        return None


def _store_report_metadata(report: Report):
    """
    Store report metadata in database.
    
    Args:
        report: Report object to store
    """
    try:
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert report metadata
        cursor.execute(
            """
            INSERT INTO reports (
                report_id, scan_id, report_type, format,
                generated_at, data, file_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (report_id) DO UPDATE SET
                generated_at = EXCLUDED.generated_at,
                file_path = EXCLUDED.file_path
            """,
            (
                str(report.report_id),
                str(report.scan_id),
                report.report_type.value,
                report.format.value,
                report.generated_at,
                report.data,
                report.file_path
            )
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Stored report metadata: {report.report_id}")
        
    except Exception as e:
        logger.error(f"Error storing report metadata: {e}", exc_info=True)
        # Don't raise - report file is already generated
