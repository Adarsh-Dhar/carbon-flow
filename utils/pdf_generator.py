"""
PDF Report Generator for Accountability Reports

This module generates production-ready PDF reports from accountability agent
output suitable for CAQM submission.
"""

from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


def generate_accountability_pdf(report_data: dict[str, Any] | str) -> bytes:
    """
    Generate a professional PDF report from accountability agent output.
    
    Args:
        report_data: Accountability report as dict or JSON string
        
    Returns:
        PDF file as bytes
        
    Raises:
        ValueError: If report_data cannot be parsed
    """
    # Parse input data
    if isinstance(report_data, str):
        try:
            report_data = json.loads(report_data)
        except json.JSONDecodeError:
            # If it's not JSON, treat as raw text report
            report_data = {"raw_report": report_data}
    elif not isinstance(report_data, dict):
        raise ValueError("report_data must be dict or JSON string")
    
    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    # Container for PDF elements
    story = []
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=1,  # Center
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=20,
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=10,
        spaceBefore=15,
    )
    
    normal_style = styles['Normal']
    normal_style.fontSize = 11
    normal_style.leading = 14
    
    # Cover Page
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("Commission for Air Quality Management", title_style))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("Inter-State Pollution Accountability Report", styles['Heading2']))
    story.append(Spacer(1, 1*inch))
    
    # Report metadata
    report_id = report_data.get("report_id", "N/A")
    timestamp = report_data.get("timestamp", datetime.now().isoformat())
    
    # Format timestamp
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        formatted_time = dt.strftime("%B %d, %Y at %I:%M %p UTC")
    except Exception:
        formatted_time = timestamp
    
    metadata_data = [
        ["Report ID:", report_id],
        ["Generated:", formatted_time],
    ]
    
    metadata_table = Table(metadata_data, colWidths=[2*inch, 4*inch])
    metadata_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
    ]))
    story.append(metadata_table)
    story.append(PageBreak())
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))
    executive_summary = report_data.get("executive_summary", report_data.get("raw_report", "No summary available."))
    if isinstance(executive_summary, dict):
        executive_summary = str(executive_summary)
    story.append(Paragraph(str(executive_summary), normal_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Surge Details
    story.append(Paragraph("Pollution Surge Details", heading_style))
    surge_details = report_data.get("surge_details", {})
    
    if surge_details:
        if isinstance(surge_details, dict):
            surge_data = []
            for key, value in surge_details.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, indent=2)
                surge_data.append([key.replace("_", " ").title() + ":", str(value)])
            
            if surge_data:
                surge_table = Table(surge_data, colWidths=[2.5*inch, 4.5*inch])
                surge_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('PADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(surge_table)
        else:
            story.append(Paragraph(str(surge_details), normal_style))
    else:
        story.append(Paragraph("No surge details available.", normal_style))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Fire Correlation Analysis
    story.append(Paragraph("Fire Event Correlation Analysis", heading_style))
    fire_correlation = report_data.get("fire_correlation", {})
    
    if fire_correlation:
        if isinstance(fire_correlation, dict):
            # Extract key information
            fire_data = []
            if "fire_count" in fire_correlation:
                fire_data.append(["Total Fire Events:", str(fire_correlation["fire_count"])])
            if "states" in fire_correlation:
                states = fire_correlation["states"]
                if isinstance(states, dict):
                    for state, count in states.items():
                        fire_data.append([f"Fires in {state}:", str(count)])
                elif isinstance(states, list):
                    fire_data.append(["Affected States:", ", ".join(str(s) for s in states)])
            
            if fire_data:
                fire_table = Table(fire_data, colWidths=[3*inch, 4*inch])
                fire_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#fff3cd')),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('PADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(fire_table)
        else:
            story.append(Paragraph(str(fire_correlation), normal_style))
    else:
        story.append(Paragraph("No fire correlation data available.", normal_style))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Stubble Burning Contribution
    story.append(Paragraph("Stubble Burning Contribution", subheading_style))
    stubble_pct = report_data.get("stubble_burning_percent", report_data.get("stubble_burning_contribution"))
    if stubble_pct is not None:
        story.append(Paragraph(f"Stubble burning contributes <b>{stubble_pct}%</b> to current pollution levels.", normal_style))
    else:
        story.append(Paragraph("Stubble burning contribution data not available.", normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Reasoning Statement
    story.append(Paragraph("Correlation Reasoning", subheading_style))
    reasoning = report_data.get("reasoning", report_data.get("raw_report", "No reasoning provided."))
    if isinstance(reasoning, dict):
        reasoning = json.dumps(reasoning, indent=2)
    story.append(Paragraph(str(reasoning), normal_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Confidence Score
    story.append(Paragraph("Confidence Assessment", subheading_style))
    confidence = report_data.get("confidence_score", report_data.get("confidence_level"))
    if confidence is not None:
        confidence_text = f"Report confidence level: <b>{confidence}%</b>"
        story.append(Paragraph(confidence_text, normal_style))
    else:
        story.append(Paragraph("Confidence score not available.", normal_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Data Quality
    story.append(Paragraph("Data Quality Assessment", subheading_style))
    data_quality = report_data.get("data_quality", {})
    if isinstance(data_quality, dict):
        quality_data = []
        for key, value in data_quality.items():
            quality_data.append([key.replace("_", " ").title() + ":", str(value)])
        
        if quality_data:
            quality_table = Table(quality_data, colWidths=[3*inch, 4*inch])
            quality_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(quality_table)
    else:
        story.append(Paragraph("Data quality assessment not available.", normal_style))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Legal Citations
    story.append(Paragraph("Legal Citations", heading_style))
    legal_citations = report_data.get("legal_citations", {})
    
    if isinstance(legal_citations, dict):
        citations_text = []
        if "caqm_direction" in legal_citations:
            citations_text.append(f"<b>CAQM Direction:</b> {legal_citations['caqm_direction']}")
        if "enforcement_authority" in legal_citations:
            citations_text.append(f"<b>Enforcement Authority:</b> {legal_citations['enforcement_authority']}")
        if "enforcement_request" in legal_citations:
            citations_text.append(f"<b>Enforcement Request:</b> {legal_citations['enforcement_request']}")
        
        if citations_text:
            story.append(Paragraph("<br/>".join(citations_text), normal_style))
        else:
            # Default citations
            story.append(Paragraph(
                "<b>CAQM Direction No. 95:</b> This confirms non-compliance with CAQM Direction No. 95.<br/>"
                "<b>Section 12 of the CAQM Act, 2021:</b> Requesting immediate enforcement action as per Section 12 of the CAQM Act.",
                normal_style
            ))
    else:
        # Default citations if not provided
        story.append(Paragraph(
            "<b>CAQM Direction No. 95:</b> This confirms non-compliance with CAQM Direction No. 95.<br/>"
            "<b>Section 12 of the CAQM Act, 2021:</b> Requesting immediate enforcement action as per Section 12 of the CAQM Act.",
            normal_style
        ))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Recommendations
    story.append(Paragraph("Recommendations", heading_style))
    recommendations = report_data.get("recommendations", [])
    
    if isinstance(recommendations, list) and recommendations:
        for i, rec in enumerate(recommendations, 1):
            story.append(Paragraph(f"{i}. {rec}", normal_style))
    elif isinstance(recommendations, str):
        story.append(Paragraph(recommendations, normal_style))
    else:
        story.append(Paragraph(
            "1. Immediate enforcement action required in neighboring states to reduce stubble burning.<br/>"
            "2. Enhanced monitoring at border stations to track cross-border pollution.<br/>"
            "3. Coordination with state governments for compliance with CAQM directives.",
            normal_style
        ))
    
    story.append(Spacer(1, 0.5*inch))
    
    # Footer
    story.append(Paragraph(
        "<i>This report was generated automatically by the CarbonFlow Autonomous Governance Platform.</i>",
        ParagraphStyle('Footer', parent=normal_style, fontSize=9, textColor=colors.grey, alignment=1)
    ))
    
    # Build PDF
    doc.build(story)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes

