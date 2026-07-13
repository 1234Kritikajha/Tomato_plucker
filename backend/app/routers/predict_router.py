from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from backend.app.utils.api_errors import op_error
from backend.core.database import insert_prediction
from backend.core.tomato_detector import TomatoDetector


router = APIRouter()
logger = logging.getLogger(__name__)

UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "uploads"
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "models"
YOLO_MODEL_PATH = MODELS_DIR / "tomato_yolo.pt"

MAX_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
YOLO_CLASS_NAMES = {
    0: "Ripe, Healthy",
    1: "Ripe, Damaged",
    2: "Unripe, Healthy",
    3: "Unripe, Damaged",
    4: "Halfripe, Healthy",
    5: "Halfripe, Damaged",
}
_YOLO_MODEL = None
_YOLO_SOURCE = ""


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


def _load_yolo_model():
    global _YOLO_MODEL, _YOLO_SOURCE

    if _YOLO_MODEL is not None:
        return _YOLO_MODEL, _YOLO_SOURCE

    try:
        from ultralytics import YOLO
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=op_error(
                message=f"Ultralytics YOLO is not installed or unavailable: {exc}",
                status=503,
            ),
        ) from exc

    if YOLO_MODEL_PATH.exists():
        model_ref = str(YOLO_MODEL_PATH)
        _YOLO_SOURCE = "tomato_yolo.pt"
    else:
        model_ref = "yolov8n.pt"
        _YOLO_SOURCE = "yolov8n.pt"
        logger.warning(
            "Custom tomato YOLO weights not found at %s. Falling back to pretrained yolov8n.pt.",
            YOLO_MODEL_PATH,
        )

    try:
        _YOLO_MODEL = YOLO(model_ref)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=op_error(message=f"Failed to load YOLO model {model_ref}: {exc}", status=503),
        ) from exc

    return _YOLO_MODEL, _YOLO_SOURCE


def _decode_image_with_opencv(image_bytes: bytes):
    try:
        import cv2
        import numpy as np
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=op_error(
                message=f"OpenCV/numpy dependencies are unavailable: {exc}",
                status=503,
            ),
        ) from exc

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(
            status_code=400,
            detail=op_error(message="Unable to decode image", status=400),
        )

    return image


def _split_class_label(class_label: str) -> tuple[str, str]:
    ripeness, condition = [part.strip() for part in class_label.split(",", 1)]
    if ripeness == "Halfripe":
        ripeness = "Half-Ripe"
    return ripeness, condition


def _run_yolo_inference(image_bytes: bytes, confidence_threshold: float = 0.25) -> tuple[list[dict[str, Any]], str]:
    image = _decode_image_with_opencv(image_bytes)
    model, model_source = _load_yolo_model()

    results = model(image, conf=confidence_threshold, verbose=False)
    if not results:
        return [], model_source

    result = results[0]
    names = getattr(result, "names", {}) or {}
    detections: list[dict[str, Any]] = []

    for box in result.boxes:
        class_id = int(box.cls[0].item())
        confidence = float(box.conf[0].item())
        xyxy = box.xyxy[0].detach().cpu().tolist()
        xmin, ymin, xmax, ymax = [float(value) for value in xyxy]

        class_label = YOLO_CLASS_NAMES.get(class_id)
        if class_label is None:
            class_label = str(names.get(class_id, f"Class {class_id}"))
            logger.warning(
                "YOLO returned class id %s outside the TomatoPlucker 6-class matrix. Label=%s",
                class_id,
                class_label,
            )

        if "," in class_label:
            ripeness, condition = _split_class_label(class_label)
        else:
            ripeness, condition = class_label, "Unknown"

        detections.append(
            {
                "box": [xmin, ymin, xmax, ymax],
                "class_id": class_id,
                "class_label": class_label,
                "confidence": confidence * 100.0,
                "ripeness": ripeness,
                "condition": condition,
                "ripeness_conf": confidence,
                "condition_conf": confidence,
                "overall_conf": confidence,
                "pick": class_label == "Ripe, Healthy",
            }
        )

    return detections, model_source


def _pdf_escape(value: Any) -> str:
    text = str(value)
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_basic_pdf_report(
    pdf_path: Path,
    *,
    filename: str,
    summary: Dict[str, Any],
    detections: List[Dict[str, Any]],
) -> None:
    """Write a small valid PDF without optional reportlab dependency."""
    lines = [
        "Tomato Analysis Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Image: {filename}",
        "",
        "Analysis Summary",
        f"Total Tomatoes: {summary['total_tomatoes_detected']}",
        f"Should Pluck: {summary['plucking_decisions']['should_pluck']}",
        f"Should Not Pluck: {summary['plucking_decisions']['should_not_pluck']}",
        f"Pluckable Percentage: {summary['plucking_decisions']['pluckable_percentage']:.1f}%",
        f"Average Confidence: {summary['confidence_metrics']['average_overall_confidence'] * 100:.1f}%",
        "",
        "Ripeness Distribution",
    ]
    lines.extend(f"{key}: {value}" for key, value in summary["ripeness_distribution"].items())
    lines.append("")
    lines.append("Condition Distribution")
    lines.extend(f"{key}: {value}" for key, value in summary["condition_distribution"].items())
    lines.append("")
    lines.append("Detection Details")
    for detection in detections[:24]:
        classification = detection["classification"]
        pluckable = "Yes" if detection["plucking_decision"]["should_pluck"] else "No"
        confidence = classification["overall_confidence"] * 100
        lines.append(
            f"#{detection['id']} {classification['ripeness']} / "
            f"{classification['condition']} / {confidence:.1f}% / Pluckable: {pluckable}"
        )
    if len(detections) > 24:
        lines.append(f"... {len(detections) - 24} more detections")

    content_lines = ["BT", "/F1 12 Tf", "72 744 Td", "14 TL"]
    for index, line in enumerate(lines):
        if index:
            content_lines.append("T*")
        content_lines.append(f"({_pdf_escape(line)}) Tj")
    content_lines.append("ET")
    content = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
    ]

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(output)


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
    """Run YOLOv8 tomato detection using the 6-class ripeness/condition matrix."""
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
    detections, model_source = _run_yolo_inference(contents)

    ts = datetime.now(timezone.utc).isoformat()

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

    total_detected = len(detections)
    ripeness_counts = {
        "Ripe": 0,
        "Unripe": 0,
        "Half-Ripe": 0,
    }
    condition_counts = {
        "Healthy": 0,
        "Damaged": 0,
    }
    pluckable_count = 0
    not_pluckable_count = 0
    confidence_values = []

    for d in detections:
        if d["ripeness"] in ripeness_counts:
            ripeness_counts[d["ripeness"]] += 1
        if d["condition"] in condition_counts:
            condition_counts[d["condition"]] += 1

        if d["pick"]:
            pluckable_count += 1
        else:
            not_pluckable_count += 1

        confidence_values.append(d["overall_conf"])

    avg_conf = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0

    enhanced_detections = []
    for i, d in enumerate(detections):
        xmin, ymin, xmax, ymax = d["box"]
        width = max(0.0, xmax - xmin)
        height = max(0.0, ymax - ymin)

        enhanced_detections.append({
            "id": i + 1,
            "box": d["box"],
            "class_id": d["class_id"],
            "class_label": d["class_label"],
            "confidence": d["confidence"],
            "bounding_box": {
                "x": xmin,
                "y": ymin,
                "width": width,
                "height": height,
                "normalized": False,
                "label": d["class_label"],
            },
            "classification": {
                "ripeness": d["ripeness"],
                "ripeness_confidence": d["ripeness_conf"],
                "condition": d["condition"],
                "condition_confidence": d["condition_conf"],
                "overall_confidence": d["overall_conf"],
            },
            "plucking_decision": {
                "should_pluck": d["pick"],
                "reason": "Ripe and healthy" if d["pick"] else f"Not pluckable ({d['class_label']})",
                "confidence": d["overall_conf"],
            },
            "quality_score": {
                "overall": d["overall_conf"],
                "color_quality": d["ripeness_conf"],
                "health_quality": d["condition_conf"],
            },
        })

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
            "average_ripeness_confidence": avg_conf,
            "average_condition_confidence": avg_conf,
            "average_overall_confidence": avg_conf
        },
        "quality_assessment": {
            "high_quality_tomatoes": sum(1 for d in detections if d["overall_conf"] > 0.8),
            "medium_quality_tomatoes": sum(1 for d in detections if 0.6 < d["overall_conf"] <= 0.8),
            "low_quality_tomatoes": sum(1 for d in detections if d["overall_conf"] <= 0.6)
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
                "localization_source": "yolov8",
                "model_source": model_source,
                "model_loaded": YOLO_MODEL_PATH.exists(),
                "class_matrix": YOLO_CLASS_NAMES,
                "confidence_threshold": 0.25,
            }
        }
    )


@router.get("/predict/history")
async def get_prediction_history(limit: int = 10) -> JSONResponse:
    """Get recent prediction history from database"""
    try:
        from backend.core.database import get_recent_predictions
        
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
        pdf_path = UPLOADS_DIR / f"report_{int(time.time())}.pdf"
        _write_basic_pdf_report(
            pdf_path,
            filename=filename,
            summary=summary,
            detections=enhanced_detections,
        )
        return JSONResponse({
            "status": "success",
            "report_path": str(pdf_path.name),
            "download_url": f"/api/reports/download/{pdf_path.name}",
            "analysis": {
                "summary": summary,
                "detections": enhanced_detections
            },
            "pdf_engine": "basic"
        })
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
