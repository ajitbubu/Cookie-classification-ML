"""
Report generator for cookie compliance reports.

Supports multiple formats:
- PDF reports using ReportLab
- HTML reports with templates
- JSON reports for API consumption
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image as RLImage
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from src.models.scan import ScanResult
from src.models.report import Report, ReportType, ReportFormat, ComplianceMetrics
from src.analytics.metrics_calculator import MetricsCalculator

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate compliance reports in multiple formats."""
    
    def __init__(
        self,
        output_dir: str = "results/reports",
        metrics_calculator: Optional[MetricsCalculator] = None
    ):
        """
        Initialize report generator.
        
        Args:
            output_dir: Directory to save generated reports
            metrics_calculator: Metrics calculator instance (creates new if None)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_calculator = metrics_calculator or MetricsCalculator()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        logger.info(f"ReportGenerator initialized with output_dir: {output_dir}")
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles for PDF reports."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            spaceBefore=12
        ))
        
        # Score style
        self.styles.add(ParagraphStyle(
            name='ScoreStyle',
            parent=self.styles['Normal'],
            fontSize=36,
            textColor=colors.HexColor('#2e7d32'),
            alignment=TA_CENTER,
            spaceAfter=20
        ))
    
    def generate_compliance_report(
        self,
        scan_result: ScanResult,
        format: ReportFormat = ReportFormat.PDF
    ) -> Report:
        """
        Generate a compliance report for a scan result.
        
        Args:
            scan_result: Scan result to generate report for
            format: Report format (PDF, HTML, or JSON)
            
        Returns:
            Report object with generated report data
        """
        logger.info(
            f"Generating {format.value} compliance report for scan {scan_result.scan_id}"
        )
        
        # Calculate metrics
        metrics = self.metrics_calculator.calculate_comprehensive_metrics(scan_result)
        
        # Generate report based on format
        if format == ReportFormat.PDF:
            file_path = self._generate_pdf_report(scan_result, metrics)
        elif format == ReportFormat.HTML:
            file_path = self._generate_html_report(scan_result, metrics)
        elif format == ReportFormat.JSON:
            file_path = self._generate_json_report(scan_result, metrics)
        else:
            raise ValueError(f"Unsupported report format: {format}")
        
        # Get file size
        file_size = Path(file_path).stat().st_size if file_path else None
        
        # Create report object
        report = Report(
            scan_id=scan_result.scan_id,
            report_type=ReportType.COMPLIANCE,
            format=format,
            generated_at=datetime.utcnow(),
            data=metrics.dict(),
            file_path=file_path,
            file_size=file_size
        )
        
        logger.info(
            f"Report generated successfully: {file_path} ({file_size} bytes)"
        )
        
        return report
    
    def _generate_pdf_report(
        self,
        scan_result: ScanResult,
        metrics: ComplianceMetrics
    ) -> str:
        """Generate PDF compliance report."""
        filename = f"compliance_report_{scan_result.scan_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path = self.output_dir / filename
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build content
        story = []
        
        # Title
        story.append(Paragraph(
            "Cookie Compliance Report",
            self.styles['CustomTitle']
        ))
        story.append(Spacer(1, 12))
        
        # Domain and timestamp
        scan_mode_value = scan_result.scan_mode.value if hasattr(scan_result.scan_mode, 'value') else str(scan_result.scan_mode)
        
        story.append(Paragraph(
            f"<b>Domain:</b> {scan_result.domain}",
            self.styles['Normal']
        ))
        story.append(Paragraph(
            f"<b>Scan Date:</b> {scan_result.timestamp_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            self.styles['Normal']
        ))
        story.append(Paragraph(
            f"<b>Scan Mode:</b> {scan_mode_value}",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 20))
        
        # Compliance Score
        story.append(Paragraph(
            "Compliance Score",
            self.styles['CustomSubtitle']
        ))
        
        score_color = self._get_score_color(metrics.compliance_score)
        story.append(Paragraph(
            f'<font color="{score_color}">{metrics.compliance_score:.1f}/100</font>',
            self.styles['ScoreStyle']
        ))
        story.append(Spacer(1, 20))
        
        # Summary Statistics
        story.append(Paragraph(
            "Summary Statistics",
            self.styles['CustomSubtitle']
        ))
        
        summary_data = [
            ['Metric', 'Value'],
            ['Total Cookies', str(metrics.total_cookies)],
            ['Third-Party Ratio', f'{metrics.third_party_ratio:.1%}'],
            ['Cookies After Consent', str(metrics.cookies_set_after_accept)],
            ['Cookies Before Consent', str(metrics.cookies_set_before_accept)],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Cookie Distribution by Category
        if metrics.cookies_by_category:
            story.append(Paragraph(
                "Cookie Distribution by Category",
                self.styles['CustomSubtitle']
            ))
            
            category_data = [['Category', 'Count', 'Percentage']]
            for category, count in sorted(
                metrics.cookies_by_category.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                percentage = (count / metrics.total_cookies * 100) if metrics.total_cookies > 0 else 0
                category_data.append([
                    category,
                    str(count),
                    f'{percentage:.1f}%'
                ])
            
            category_table = Table(category_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
            category_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(category_table)
            story.append(Spacer(1, 20))
        
        # Cookie Distribution by Type
        if metrics.cookies_by_type:
            story.append(Paragraph(
                "Cookie Distribution by Type",
                self.styles['CustomSubtitle']
            ))
            
            type_data = [['Type', 'Count', 'Percentage']]
            for cookie_type, count in metrics.cookies_by_type.items():
                if count > 0:  # Only show types with cookies
                    percentage = (count / metrics.total_cookies * 100) if metrics.total_cookies > 0 else 0
                    type_data.append([
                        cookie_type,
                        str(count),
                        f'{percentage:.1f}%'
                    ])
            
            type_table = Table(type_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
            type_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(type_table)
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"PDF report generated: {file_path}")
        return str(file_path)
    
    def _generate_html_report(
        self,
        scan_result: ScanResult,
        metrics: ComplianceMetrics
    ) -> str:
        """Generate HTML compliance report."""
        filename = f"compliance_report_{scan_result.scan_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
        file_path = self.output_dir / filename
        
        score_color = self._get_score_color(metrics.compliance_score)
        scan_mode_value = scan_result.scan_mode.value if hasattr(scan_result.scan_mode, 'value') else str(scan_result.scan_mode)
        
        # Build HTML content
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cookie Compliance Report - {scan_result.domain}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1a1a1a;
            text-align: center;
            border-bottom: 3px solid #2e7d32;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #333;
            margin-top: 30px;
            border-bottom: 2px solid #ddd;
            padding-bottom: 5px;
        }}
        .score {{
            text-align: center;
            font-size: 48px;
            font-weight: bold;
            color: {score_color};
            margin: 20px 0;
        }}
        .metadata {{
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .metadata p {{
            margin: 5px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border: 1px solid #ddd;
        }}
        th {{
            background-color: #666;
            color: white;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Cookie Compliance Report</h1>
        
        <div class="metadata">
            <p><strong>Domain:</strong> {scan_result.domain}</p>
            <p><strong>Scan Date:</strong> {scan_result.timestamp_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p><strong>Scan Mode:</strong> {scan_mode_value}</p>
            <p><strong>Scan ID:</strong> {scan_result.scan_id}</p>
        </div>
        
        <h2>Compliance Score</h2>
        <div class="score">{metrics.compliance_score:.1f}/100</div>
        
        <h2>Summary Statistics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Total Cookies</td>
                <td>{metrics.total_cookies}</td>
            </tr>
            <tr>
                <td>Third-Party Ratio</td>
                <td>{metrics.third_party_ratio:.1%}</td>
            </tr>
            <tr>
                <td>Cookies After Consent</td>
                <td>{metrics.cookies_set_after_accept}</td>
            </tr>
            <tr>
                <td>Cookies Before Consent</td>
                <td>{metrics.cookies_set_before_accept}</td>
            </tr>
        </table>
        
        <h2>Cookie Distribution by Category</h2>
        <table>
            <tr>
                <th>Category</th>
                <th>Count</th>
                <th>Percentage</th>
            </tr>
"""
        
        # Add category rows
        for category, count in sorted(
            metrics.cookies_by_category.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            percentage = (count / metrics.total_cookies * 100) if metrics.total_cookies > 0 else 0
            html_content += f"""
            <tr>
                <td>{category}</td>
                <td>{count}</td>
                <td>{percentage:.1f}%</td>
            </tr>
"""
        
        html_content += """
        </table>
        
        <h2>Cookie Distribution by Type</h2>
        <table>
            <tr>
                <th>Type</th>
                <th>Count</th>
                <th>Percentage</th>
            </tr>
"""
        
        # Add type rows
        for cookie_type, count in metrics.cookies_by_type.items():
            if count > 0:
                percentage = (count / metrics.total_cookies * 100) if metrics.total_cookies > 0 else 0
                html_content += f"""
            <tr>
                <td>{cookie_type}</td>
                <td>{count}</td>
                <td>{percentage:.1f}%</td>
            </tr>
"""
        
        html_content += f"""
        </table>
        
        <div class="footer">
            <p>Generated by Cookie Scanner Platform on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Write HTML file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated: {file_path}")
        return str(file_path)
    
    def _generate_json_report(
        self,
        scan_result: ScanResult,
        metrics: ComplianceMetrics
    ) -> str:
        """Generate JSON compliance report."""
        filename = f"compliance_report_{scan_result.scan_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = self.output_dir / filename
        
        # Build JSON structure
        scan_mode_value = scan_result.scan_mode.value if hasattr(scan_result.scan_mode, 'value') else str(scan_result.scan_mode)
        
        report_data = {
            'report_type': 'compliance',
            'generated_at': datetime.utcnow().isoformat(),
            'scan_info': {
                'scan_id': str(scan_result.scan_id),
                'domain': scan_result.domain,
                'scan_mode': scan_mode_value,
                'timestamp_utc': scan_result.timestamp_utc.isoformat(),
                'duration_seconds': scan_result.duration_seconds,
                'pages_visited': scan_result.page_count
            },
            'metrics': metrics.dict(),
            'cookies': [
                {
                    'name': cookie.name,
                    'domain': cookie.domain,
                    'category': cookie.category,
                    'cookie_type': cookie.cookie_type.value if hasattr(cookie.cookie_type, 'value') else str(cookie.cookie_type) if cookie.cookie_type else None,
                    'vendor': cookie.vendor,
                    'set_after_accept': cookie.set_after_accept,
                    'duration': cookie.cookie_duration
                }
                for cookie in scan_result.cookies
            ]
        }
        
        # Write JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON report generated: {file_path}")
        return str(file_path)
    
    def _get_score_color(self, score: float) -> str:
        """Get color based on compliance score."""
        if score >= 80:
            return '#2e7d32'  # Green
        elif score >= 60:
            return '#f57c00'  # Orange
        else:
            return '#c62828'  # Red
    
    def export_to_csv(self, scan_result: ScanResult) -> str:
        """
        Export scan result cookies to CSV format.
        
        Args:
            scan_result: Scan result to export
            
        Returns:
            Path to generated CSV file
        """
        import csv
        
        filename = f"cookies_export_{scan_result.scan_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = self.output_dir / filename
        
        # Define CSV headers
        headers = [
            'Name', 'Domain', 'Path', 'Category', 'Type', 'Vendor',
            'Duration', 'Size', 'HttpOnly', 'Secure', 'SameSite',
            'Set After Accept', 'Description'
        ]
        
        # Write CSV
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for cookie in scan_result.cookies:
                cookie_type_value = ''
                if cookie.cookie_type:
                    cookie_type_value = cookie.cookie_type.value if hasattr(cookie.cookie_type, 'value') else str(cookie.cookie_type)
                
                writer.writerow([
                    cookie.name,
                    cookie.domain,
                    cookie.path,
                    cookie.category or '',
                    cookie_type_value,
                    cookie.vendor or '',
                    cookie.cookie_duration or '',
                    cookie.size or '',
                    cookie.http_only,
                    cookie.secure,
                    cookie.same_site or '',
                    cookie.set_after_accept,
                    cookie.description or ''
                ])
        
        logger.info(f"CSV export generated: {file_path}")
        return str(file_path)
