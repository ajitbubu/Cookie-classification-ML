"""
Analytics service for retrieving and processing scan data.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

import asyncpg

from src.models.scan import ScanResult, Cookie, CookieType, ScanMode
from src.models.report import Report, ReportFormat, ReportType, TrendData
from src.analytics.report_generator import ReportGenerator
from src.analytics.metrics_calculator import MetricsCalculator
from src.analytics.trend_analyzer import TrendAnalyzer

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics operations."""
    
    def __init__(
        self,
        db_pool: asyncpg.Pool,
        redis_client=None
    ):
        """Initialize analytics service."""
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.report_generator = ReportGenerator()
        self.metrics_calculator = MetricsCalculator()
        self.trend_analyzer = TrendAnalyzer(self.metrics_calculator)
        logger.info("AnalyticsService initialized")
    
    async def get_scan_result(self, scan_id: UUID) -> Optional[ScanResult]:
        """
        Get scan result by ID.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            ScanResult or None if not found
        """
        async with self.db_pool.acquire() as conn:
            # Get scan result
            row = await conn.fetchrow(
                """
                SELECT scan_id, domain_config_id, domain, scan_mode,
                       timestamp_utc, status, duration_seconds, total_cookies,
                       page_count, error, params, created_at, updated_at
                FROM scan_results
                WHERE scan_id = $1
                """,
                scan_id
            )
            
            if not row:
                return None
            
            # Get cookies for this scan
            cookie_rows = await conn.fetch(
                """
                SELECT cookie_id, name, domain, path, hashed_value,
                       category, vendor, cookie_type, set_after_accept,
                       metadata
                FROM cookies
                WHERE scan_id = $1
                """,
                scan_id
            )
            
            # Build cookie objects
            cookies = []
            for cookie_row in cookie_rows:
                metadata = cookie_row['metadata'] or {}
                cookies.append(Cookie(
                    cookie_id=cookie_row['cookie_id'],
                    name=cookie_row['name'],
                    domain=cookie_row['domain'],
                    path=cookie_row['path'],
                    hashed_value=cookie_row['hashed_value'],
                    category=cookie_row['category'],
                    vendor=cookie_row['vendor'],
                    cookie_type=CookieType(cookie_row['cookie_type']) if cookie_row['cookie_type'] else None,
                    set_after_accept=cookie_row['set_after_accept'],
                    cookie_duration=metadata.get('cookie_duration'),
                    size=metadata.get('size'),
                    http_only=metadata.get('http_only', False),
                    secure=metadata.get('secure', False),
                    same_site=metadata.get('same_site'),
                    description=metadata.get('description'),
                    iab_purposes=metadata.get('iab_purposes', []),
                    source=metadata.get('source')
                ))
            
            # Build scan result
            scan_result = ScanResult(
                scan_id=row['scan_id'],
                domain_config_id=row['domain_config_id'],
                domain=row['domain'],
                scan_mode=ScanMode(row['scan_mode']),
                timestamp_utc=row['timestamp_utc'],
                status=row['status'],
                duration_seconds=row['duration_seconds'],
                page_count=row['page_count'],
                cookies=cookies,
                storages={},  # Not stored in DB currently
                params=row['params'],
                error=row['error']
            )
            
            return scan_result
    
    async def list_scan_results(
        self,
        domain: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ScanResult]:
        """
        List scan results with optional filtering.
        
        Args:
            domain: Filter by domain
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            List of ScanResult objects
        """
        query = """
            SELECT scan_id, domain_config_id, domain, scan_mode,
                   timestamp_utc, status, duration_seconds, total_cookies,
                   page_count, error, params, created_at, updated_at
            FROM scan_results
            WHERE 1=1
        """
        params = []
        param_count = 1
        
        if domain:
            query += f" AND domain = ${param_count}"
            params.append(domain)
            param_count += 1
        
        if start_date:
            query += f" AND timestamp_utc >= ${param_count}"
            params.append(start_date)
            param_count += 1
        
        if end_date:
            query += f" AND timestamp_utc <= ${param_count}"
            params.append(end_date)
            param_count += 1
        
        query += f" ORDER BY timestamp_utc DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
        params.extend([limit, offset])
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            scan_results = []
            for row in rows:
                # Get cookies for each scan
                cookie_rows = await conn.fetch(
                    """
                    SELECT cookie_id, name, domain, path, hashed_value,
                           category, vendor, cookie_type, set_after_accept,
                           metadata
                    FROM cookies
                    WHERE scan_id = $1
                    """,
                    row['scan_id']
                )
                
                cookies = []
                for cookie_row in cookie_rows:
                    metadata = cookie_row['metadata'] or {}
                    cookies.append(Cookie(
                        cookie_id=cookie_row['cookie_id'],
                        name=cookie_row['name'],
                        domain=cookie_row['domain'],
                        path=cookie_row['path'],
                        hashed_value=cookie_row['hashed_value'],
                        category=cookie_row['category'],
                        vendor=cookie_row['vendor'],
                        cookie_type=CookieType(cookie_row['cookie_type']) if cookie_row['cookie_type'] else None,
                        set_after_accept=cookie_row['set_after_accept'],
                        cookie_duration=metadata.get('cookie_duration'),
                        size=metadata.get('size'),
                        http_only=metadata.get('http_only', False),
                        secure=metadata.get('secure', False),
                        same_site=metadata.get('same_site'),
                        description=metadata.get('description'),
                        iab_purposes=metadata.get('iab_purposes', []),
                        source=metadata.get('source')
                    ))
                
                scan_results.append(ScanResult(
                    scan_id=row['scan_id'],
                    domain_config_id=row['domain_config_id'],
                    domain=row['domain'],
                    scan_mode=ScanMode(row['scan_mode']),
                    timestamp_utc=row['timestamp_utc'],
                    status=row['status'],
                    duration_seconds=row['duration_seconds'],
                    page_count=row['page_count'],
                    cookies=cookies,
                    storages={},
                    params=row['params'],
                    error=row['error']
                ))
            
            return scan_results
    
    async def generate_report(
        self,
        scan_id: UUID,
        format: ReportFormat = ReportFormat.JSON
    ) -> Report:
        """
        Generate a compliance report for a scan.
        
        Args:
            scan_id: Scan ID
            format: Report format
            
        Returns:
            Report object
        """
        # Get scan result
        scan_result = await self.get_scan_result(scan_id)
        if not scan_result:
            raise ValueError(f"Scan {scan_id} not found")
        
        # Generate report
        report = self.report_generator.generate_compliance_report(
            scan_result, format
        )
        
        # Save report to database
        async with self.db_pool.acquire() as conn:
            report_id = await conn.fetchval(
                """
                INSERT INTO reports (
                    scan_id, report_type, format, generated_at,
                    data, file_path
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING report_id
                """,
                scan_id,
                report.report_type,
                report.format,
                report.generated_at,
                report.data,
                report.file_path
            )
            report.report_id = report_id
        
        logger.info(f"Report {report_id} generated for scan {scan_id}")
        return report
    
    async def get_trend_data(
        self,
        domain: str,
        metric: str = 'total_cookies',
        days: int = 30
    ) -> TrendData:
        """
        Get trend data for a domain.
        
        Args:
            domain: Domain to analyze
            metric: Metric to analyze
            days: Number of days to look back
            
        Returns:
            TrendData object
        """
        # Get historical scan results
        start_date = datetime.utcnow() - timedelta(days=days)
        scan_results = await self.list_scan_results(
            domain=domain,
            start_date=start_date,
            limit=1000
        )
        
        if not scan_results:
            raise ValueError(f"No scan results found for domain {domain}")
        
        # Analyze trends
        trend_data = self.trend_analyzer.analyze_trends(
            domain, scan_results, metric
        )
        
        return trend_data
    
    async def get_metrics_summary(
        self,
        domain: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get metrics summary for recent scans.
        
        Args:
            domain: Optional domain filter
            days: Number of days to look back
            
        Returns:
            Dictionary with metrics summary
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        scan_results = await self.list_scan_results(
            domain=domain,
            start_date=start_date,
            limit=1000
        )
        
        if not scan_results:
            return {
                'total_scans': 0,
                'domains_scanned': 0,
                'total_cookies_found': 0,
                'average_compliance_score': 0.0,
                'average_scan_duration': 0.0
            }
        
        # Calculate summary metrics
        total_scans = len(scan_results)
        domains = set(sr.domain for sr in scan_results)
        total_cookies = sum(len(sr.cookies) for sr in scan_results)
        
        # Calculate average compliance score
        compliance_scores = [
            self.metrics_calculator.calculate_compliance_score(sr)
            for sr in scan_results
        ]
        avg_compliance = sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0.0
        
        # Calculate average duration
        durations = [sr.duration_seconds for sr in scan_results if sr.duration_seconds]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        # Get category distribution across all scans
        all_categories = {}
        for sr in scan_results:
            dist = self.metrics_calculator.calculate_cookie_distribution(sr)
            for category, count in dist.items():
                all_categories[category] = all_categories.get(category, 0) + count
        
        return {
            'total_scans': total_scans,
            'domains_scanned': len(domains),
            'total_cookies_found': total_cookies,
            'average_compliance_score': round(avg_compliance, 2),
            'average_scan_duration': round(avg_duration, 2),
            'cookie_distribution': all_categories,
            'time_range': {
                'start': start_date.isoformat(),
                'end': datetime.utcnow().isoformat()
            }
        }
