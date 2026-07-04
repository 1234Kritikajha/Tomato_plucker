from __future__ import annotations

import asyncio
import hashlib
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.utils.api_errors import op_error
from core.database import insert_prediction
from core.tomato_detector import TomatoDetector


router = APIRouter()

UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "uploads"

MAX_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def _validate_magic_bytes(image_bytes: bytes) -> str:
    if len(image_bytes) < 12:
        raise HTTPException(
            status_code=400,
            detail=op_error(message="Invalid image", status=400),
        )

    # JPEG: FF D8 FF
    if image_bytes[0:3] == b"\xFF\xD8\xFF":
        return "image/jpeg"

    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if image_bytes[0:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"

    # WebP: RIFF....WEBP
    if image_bytes[0:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"

    raise HTTPException(
        status_code=400,
        detail=op_error(message="Unsupported image format", status=400),
    )


def _sanitize_filename(name: str) -> str:
    name = (name or "upload").strip()
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return name[:180]


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@router.post("/upload")
async def upload(file: UploadFile = File(...)) -> JSONResponse:
    if not file:
        raise HTTPException(
            status_code=400,
            detail=op_error(message="Missing file", status=400),
        )

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=415,
            detail=op_error(message="Unsupported file extension", status=415),
        )

    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=op_error(message="File too large (max 10MB)", status=413),
        )

    mime = _validate_magic_bytes(contents)

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_filename(file.filename or "upload")
    digest = _sha256(contents)[:16]
    out_name = f"{Path(safe_name).stem}_{digest}{ext}"
    out_path = UPLOADS_DIR / out_name
    out_path.write_bytes(contents)

    return JSONResponse(
        {
            "status": "success",
            "filename": out_name,
            "mime_type": mime,
        }
    )


@router.post("/predict")
async def predict(file: UploadFile = File(...)) -> JSONResponse:
    """Enhanced prediction endpoint with detailed analysis
    
    Provides:
    - Bounding boxes for all detected tomatoes
    - Ripeness classification (ripe, unripe, half_ripe)
    - Condition classification (healthy, damaged)
    - Confidence scores for each classification
    - Plucking decision (ripe + healthy = pluckable)
    - Detailed statistics and summary
    """

    if not file:
        raise HTTPException(
            status_code=400,
            detail=op_error(message="Missing file", status=400),
        )

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=415,
            detail=op_error(message="Unsupported file extension", status=415),
        )

    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=op_error(message="File too large (max 10MB)", status=413),
        )

    _validate_magic_bytes(contents)

    filename = file.filename or "upload"

    detector = TomatoDetector()
    detections = detector.detect_and_classify(contents, filename=filename)

    ts = datetime.now(timezone.utc).isoformat()

    # Store in database
    for d in detections:
        await asyncio.sleep(0)
        insert_prediction(
            filename=filename,
            timestamp_iso=ts,
            box_json=d["box"],
            ripeness=d["ripeness"],
            ripeness_conf=float(d["ripeness_conf"]),
            condition=d["condition"],
            condition_conf=float(d["condition_conf"]),
            pick=bool(d["pick"]),
        )

    # Calculate detailed statistics
    total_detected = len(detections)
    
    # Ripeness distribution
    ripeness_counts = {
        "Ripe": 0,
        "Unripe": 0,
        "Half-Ripe": 0
    }
    
    # Condition distribution
    condition_counts = {
        "Healthy": 0,
        "Damaged": 0
    }
    
    # Plucking decision counts
    pluckable_count = 0
    not_pluckable_count = 0
    
    # Average confidence scores
    ripeness_confidences = []
    condition_confidences = []
    
    for d in detections:
        ripeness_counts[d["ripeness"]] += 1
        condition_counts[d["condition"]] += 1
        
        if d["pick"]:
            pluckable_count += 1
        else:
            not_pluckable_count += 1
        
        ripeness_confidences.append(d["ripeness_conf"])
        condition_confidences.append(d["condition_conf"])
    
    # Calculate averages
    avg_ripeness_conf = sum(ripeness_confidences) / len(ripeness_confidences) if ripeness_confidences else 0
    avg_condition_conf = sum(condition_confidences) / len(condition_confidences) if condition_confidences else 0
    avg_overall_conf = (avg_ripeness_conf + avg_condition_conf) / 2 if total_detected > 0 else 0
    
    # Enhanced detection response with labels and detailed info
    enhanced_detections = []
    for i, d in enumerate(detections):
        enhanced_detections.append({
            "id": i + 1,
            "bounding_box": {
                "x": d["box"][0],
                "y": d["box"][1],
                "width": d["box"][2],
                "height": d["box"][3],
                "normalized": False,
                "label": f"Tomato #{i + 1}"
            },
            "classification": {
                "ripeness": d["ripeness"],
                "ripeness_confidence": d["ripeness_conf"],
                "condition": d["condition"],
                "condition_confidence": d["condition_conf"],
                "overall_confidence": (d["ripeness_conf"] + d["condition_conf"]) / 2
            },
            "plucking_decision": {
                "should_pluck": d["pick"],
                "reason": "Ripe and healthy" if d["pick"] else f"Not ripe or not healthy ({d['ripeness']}, {d['condition']})",
                "confidence": (d["ripeness_conf"] + d["condition_conf"]) / 2 if d["pick"] else 1 - ((d["ripeness_conf"] + d["condition_conf"]) / 2)
            },
            "quality_score": {
                "overall": (d["ripeness_conf"] + d["condition_conf"]) / 2,
                "color_quality": d["ripeness_conf"],
                "health_quality": d["condition_conf"]
            }
        })
    
    # Generate summary report
    summary = {
        "total_tomatoes_detected": total_detected,
        "ripeness_distribution": ripeness_counts,
        "condition_distribution": condition_counts,
        "plucking_decisions": {
            "should_pluck": pluckable_count,
            "should_not_pluck": not_pluckable_count,
            "pluckable_percentage": (pluckable_count / total_detected * 100) if total_detected > 0 else 0
        },
        "confidence_metrics": {
            "average_ripeness_confidence": avg_ripeness_conf,
            "average_condition_confidence": avg_condition_conf,
            "average_overall_confidence": avg_overall_conf
        },
        "quality_assessment": {
            "high_quality_tomatoes": sum(1 for d in detections if d["ripeness_conf"] > 0.8 and d["condition_conf"] > 0.8),
            "medium_quality_tomatoes": sum(1 for d in detections if 0.6 < d["ripeness_conf"] <= 0.8 or 0.6 < d["condition_conf"] <= 0.8),
            "low_quality_tomatoes": sum(1 for d in detections if d["ripeness_conf"] <= 0.6 or d["condition_conf"] <= 0.6)
        }
    }
    
    return JSONResponse(
        {
            "status": "success",
            "analysis_timestamp": ts,
            "image_info": {
                "filename": filename,
                "size_bytes": len(contents),
                "format": ext[1:].upper()
            },
            "detections": enhanced_detections,
            "summary": summary,
            "model_info": {
                "localization_source": detector.localization_source,
                "model_loaded": detector._primary_model_loaded,
                "confidence_threshold": detector.low_conf_threshold
            }
        }
    )


@router.get("/predict/history")
async def get_prediction_history(limit: int = 10) -> JSONResponse:
    """Get recent prediction history from database"""
    try:
        from core.database import get_recent_predictions
        
        predictions = get_recent_predictions(limit=limit)
        
        return JSONResponse({
            "status": "success",
            "predictions": predictions,
            "count": len(predictions)
        })
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to get prediction history: {e}", status=500),
        )


@router.post("/generate_report")
async def generate_report(file: UploadFile = File(...)) -> JSONResponse:
    """Generate PDF report for image analysis"""
    try:
        # First analyze the image
        if not file:
            raise HTTPException(
                status_code=400,
                detail=op_error(message="Missing file", status=400),
            )

        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXT:
            raise HTTPException(
                status_code=415,
                detail=op_error(message="Unsupported file extension", status=415),
            )

        contents = await file.read()
        if len(contents) > MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail=op_error(message="File too large (max 10MB)", status=413),
            )

        _validate_magic_bytes(contents)

        filename = file.filename or "upload"

        detector = TomatoDetector()
        detections = detector.detect_and_classify(contents, filename=filename)

        ts = datetime.now(timezone.utc).isoformat()

        # Store in database
        for d in detections:
            await asyncio.sleep(0)
            insert_prediction(
                filename=filename,
                timestamp_iso=ts,
                box_json=d["box"],
                ripeness=d["ripeness"],
                ripeness_conf=float(d["ripeness_conf"]),
                condition=d["condition"],
                condition_conf=float(d["condition_conf"]),
                pick=bool(d["pick"]),
            )

        # Calculate summary
        total_detected = len(detections)
        ripeness_counts = {"Ripe": 0, "Unripe": 0, "Half-Ripe": 0}
        condition_counts = {"Healthy": 0, "Damaged": 0}
        pluckable_count = 0
        not_pluckable_count = 0
        ripeness_confidences = []
        condition_confidences = []
        
        for d in detections:
            ripeness_counts[d["ripeness"]] += 1
            condition_counts[d["condition"]] += 1
            if d["pick"]:
                pluckable_count += 1
            else:
                not_pluckable_count += 1
            ripeness_confidences.append(d["ripeness_conf"])
            condition_confidences.append(d["condition_conf"])
        
        avg_ripeness_conf = sum(ripeness_confidences) / len(ripeness_confidences) if ripeness_confidences else 0
        avg_condition_conf = sum(condition_confidences) / len(condition_confidences) if condition_confidences else 0
        avg_overall_conf = (avg_ripeness_conf + avg_condition_conf) / 2 if total_detected > 0 else 0
        
        summary = {
            "total_tomatoes_detected": total_detected,
            "ripeness_distribution": ripeness_counts,
            "condition_distribution": condition_counts,
            "plucking_decisions": {
                "should_pluck": pluckable_count,
                "should_not_pluck": not_pluckable_count,
                "pluckable_percentage": (pluckable_count / total_detected * 100) if total_detected > 0 else 0
            },
            "confidence_metrics": {
                "average_ripeness_confidence": avg_ripeness_conf,
                "average_condition_confidence": avg_condition_conf,
                "average_overall_confidence": avg_overall_conf
            }
        }

        # Create enhanced detections
        enhanced_detections = []
        for i, d in enumerate(detections):
            enhanced_detections.append({
                "id": i + 1,
                "bounding_box": {
                    "x": d["box"][0],
                    "y": d["box"][1],
                    "width": d["box"][2],
                    "height": d["box"][3],
                    "normalized": False,
                    "label": f"Tomato #{i + 1}"
                },
                "classification": {
                    "ripeness": d["ripeness"],
                    "ripeness_confidence": d["ripeness_conf"],
                    "condition": d["condition"],
                    "condition_confidence": d["condition_conf"],
                    "overall_confidence": (d["ripeness_conf"] + d["condition_conf"]) / 2
                },
                "plucking_decision": {
                    "should_pluck": d["pick"],
                    "reason": "Ripe and healthy" if d["pick"] else f"Not ripe or not healthy ({d['ripeness']}, {d['condition']})",
                    "confidence": (d["ripeness_conf"] + d["condition_conf"]) / 2 if d["pick"] else 1 - ((d["ripeness_conf"] + d["condition_conf"]) / 2)
                }
            })

        # Generate PDF report
        import base64
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.pdfgen import canvas
        
        pdf_path = UPLOADS_DIR / f"report_{int(time.time())}.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        
        elements = []
        
        # Title
        title = Paragraph("Tomato Analysis Report", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Metadata
        metadata = f"""
        <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
        <b>Image:</b> {filename}<br/>
        <b>Analysis ID:</b> {int(time.time())}
        """
        elements.append(Paragraph(metadata, styles['Normal']))
        elements.append(Spacer(1, 12))
        
        # Summary Section
        elements.append(Paragraph("<b>Analysis Summary</b>", styles['Heading2']))
        elements.append(Spacer(1, 6))
        
        summary_data = [
            ['Metric', 'Value'],
            ['Total Tomatoes', str(summary['total_tomatoes_detected'])],
            ['Should Pluck', str(summary['plucking_decisions']['should_pluck'])],
            ['Should Not Pluck', str(summary['plucking_decisions']['should_not_pluck'])],
            ['Pluckable Percentage', f"{summary['plucking_decisions']['pluckable_percentage']:.1f}%"],
            ['Average Confidence', f"{summary['confidence_metrics']['average_overall_confidence']*100:.1f}%"]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
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
        elements.append(summary_table)
        elements.append(Spacer(1, 12))
        
        # Ripeness Distribution
        elements.append(Paragraph("<b>Ripeness Distribution</b>", styles['Heading2']))
        elements.append(Spacer(1, 6))
        
        ripeness_data = [['Ripeness', 'Count']]
        for key, value in summary['ripeness_distribution'].items():
            ripeness_data.append([key, str(value)])
        
        ripeness_table = Table(ripeness_data, colWidths=[2*inch, 2*inch])
        ripeness_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(ripeness_table)
        elements.append(Spacer(1, 12))
        
        # Condition Distribution
        elements.append(Paragraph("<b>Condition Distribution</b>", styles['Heading2']))
        elements.append(Spacer(1, 6))
        
        condition_data = [['Condition', 'Count']]
        for key, value in summary['condition_distribution'].items():
            condition_data.append([key, str(value)])
        
        condition_table = Table(condition_data, colWidths=[2*inch, 2*inch])
        condition_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(condition_table)
        elements.append(Spacer(1, 12))
        
        # Detection Details
        elements.append(Paragraph("<b>Detection Details</b>", styles['Heading2']))
        elements.append(Spacer(1, 6))
        
        detection_data = [['ID', 'Ripeness', 'Condition', 'Confidence', 'Pluckable']]
        for d in enhanced_detections:
            detection_data.append([
                str(d['id']),
                d['classification']['ripeness'],
                d['classification']['condition'],
                f"{d['classification']['overall_confidence']*100:.1f}%",
                'Yes' if d['plucking_decision']['should_pluck'] else 'No'
            ])
        
        detection_table = Table(detection_data, colWidths=[0.5*inch, 1*inch, 1*inch, 1*inch, 0.8*inch])
        detection_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(detection_table)
        
        doc.build(elements)
        
        return JSONResponse({
            "status": "success",
            "report_path": str(pdf_path.name),
            "download_url": f"/api/reports/download/{pdf_path.name}",
            "analysis": {
                "summary": summary,
                "detections": enhanced_detections
            }
        })
        
    except ImportError:
        return JSONResponse({
            "status": "error",
            "message": "PDF generation not available. Install reportlab: pip install reportlab"
        }, status_code=500)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=op_error(message=f"Failed to generate report: {e}", status=500),
        )


@router.get("/reports/download/{filename}")
async def download_report(filename: str):
    """Download generated PDF report"""
    from fastapi.responses import FileResponse
    
    file_path = UPLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=op_error(message="Report not found", status=404),
        )
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename
    )

