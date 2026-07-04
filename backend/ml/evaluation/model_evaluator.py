from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np


RIPENESS_CLASSES: Sequence[str] = ("Ripe", "Unripe", "Half-Ripe")
CONDITION_CLASSES: Sequence[str] = ("Healthy", "Damaged")


def _as_1d_int_array(x: Sequence[Any], *, name: str) -> np.ndarray:
    arr = np.asarray(x)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be a 1D sequence of class indices or labels; got shape {arr.shape}")
    return arr


def _label_to_index(labels: Sequence[Any], classes: Sequence[str]) -> np.ndarray:
    """Convert labels (strings or indices) into integer indices."""
    idx_map = {c: i for i, c in enumerate(classes)}

    out = []
    for v in labels:
        if isinstance(v, (int, np.integer)):
            out.append(int(v))
        else:
            s = str(v)
            if s not in idx_map:
                raise ValueError(f"Unknown label '{s}'. Expected one of: {list(classes)}")
            out.append(idx_map[s])
    return np.asarray(out, dtype=np.int64)


def _confusion_from_indices(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> np.ndarray:
    if y_true.shape != y_pred.shape:
        raise ValueError(f"y_true and y_pred must have same shape; got {y_true.shape} vs {y_pred.shape}")
    if y_true.ndim != 1:
        raise ValueError(f"y_true/y_pred must be 1D; got {y_true.ndim}D")

    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for t, p in zip(y_true.tolist(), y_pred.tolist()):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            cm[int(t), int(p)] += 1
        else:
            raise ValueError(f"Class index out of range. y_true={t}, y_pred={p}, num_classes={num_classes}")
    return cm


@dataclass(frozen=True)
class _PRF:
    precision: float
    recall: float
    f1: float
    support: int


def _prf_from_cm(cm: np.ndarray, class_index: int) -> _PRF:
    """Binary one-vs-rest PRF from multi-class confusion matrix."""
    tp = int(cm[class_index, class_index])
    fp = int(cm[:, class_index].sum() - tp)
    fn = int(cm[class_index, :].sum() - tp)

    support = int(cm[class_index, :].sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return _PRF(precision=precision, recall=recall, f1=f1, support=support)


def compute_comprehensive_metrics(
    y_true_ripeness: Sequence[Any],
    y_pred_ripeness: Sequence[Any],
    y_true_condition: Sequence[Any],
    y_pred_condition: Sequence[Any],
) -> Dict[str, Any]:
    """Compute multi-label (two-head) per-class precision/recall/F1 plus aggregates.

    Returns a nested dictionary that can be serialized directly to JSON.
    """

    yt_r = _label_to_index(y_true_ripeness, RIPENESS_CLASSES)
    yp_r = _label_to_index(y_pred_ripeness, RIPENESS_CLASSES)
    yt_c = _label_to_index(y_true_condition, CONDITION_CLASSES)
    yp_c = _label_to_index(y_pred_condition, CONDITION_CLASSES)

    if len(yt_r) != len(yp_r) or len(yt_c) != len(yp_c):
        raise ValueError("Prediction arrays must match their corresponding true arrays in length")
    if len(yt_r) != len(yt_c):
        raise ValueError("Ripeness and condition arrays must have the same number of samples")

    cm_r = _confusion_from_indices(yt_r, yp_r, num_classes=len(RIPENESS_CLASSES))
    cm_c = _confusion_from_indices(yt_c, yp_c, num_classes=len(CONDITION_CLASSES))

    ripeness_per_class: List[Dict[str, Any]] = []
    for i, name in enumerate(RIPENESS_CLASSES):
        prf = _prf_from_cm(cm_r, i)
        ripeness_per_class.append(
            {
                "class": name,
                "precision": prf.precision,
                "recall": prf.recall,
                "f1": prf.f1,
                "support": prf.support,
            }
        )

    condition_per_class: List[Dict[str, Any]] = []
    for i, name in enumerate(CONDITION_CLASSES):
        prf = _prf_from_cm(cm_c, i)
        condition_per_class.append(
            {
                "class": name,
                "precision": prf.precision,
                "recall": prf.recall,
                "f1": prf.f1,
                "support": prf.support,
            }
        )

    # Macro averages (simple mean over classes)
    ripeness_macro = {
        "precision": float(np.mean([x["precision"] for x in ripeness_per_class])),
        "recall": float(np.mean([x["recall"] for x in ripeness_per_class])),
        "f1": float(np.mean([x["f1"] for x in ripeness_per_class])),
    }
    condition_macro = {
        "precision": float(np.mean([x["precision"] for x in condition_per_class])),
        "recall": float(np.mean([x["recall"] for x in condition_per_class])),
        "f1": float(np.mean([x["f1"] for x in condition_per_class])),
    }

    # Micro averages (compute over aggregated TP/FP/FN for one-vs-rest)
    def _micro_from_cm(cm: np.ndarray) -> Dict[str, float]:
        num_classes = cm.shape[0]
        tp_sum = 0
        fp_sum = 0
        fn_sum = 0
        for i in range(num_classes):
            tp = cm[i, i]
            fp = cm[:, i].sum() - tp
            fn = cm[i, :].sum() - tp
            tp_sum += tp
            fp_sum += fp
            fn_sum += fn
        precision = tp_sum / (tp_sum + fp_sum) if (tp_sum + fp_sum) > 0 else 0.0
        recall = tp_sum / (tp_sum + fn_sum) if (tp_sum + fn_sum) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        return {"precision": float(precision), "recall": float(recall), "f1": float(f1)}

    ripeness_micro = _micro_from_cm(cm_r)
    condition_micro = _micro_from_cm(cm_c)

    # Convert confusion matrices to nested lists for JSON-ability
    report: Dict[str, Any] = {
        "ripeness": {
            "classes": list(RIPENESS_CLASSES),
            "confusion_matrix": cm_r.tolist(),
            "per_class": ripeness_per_class,
            "macro": ripeness_macro,
            "micro": ripeness_micro,
        },
        "condition": {
            "classes": list(CONDITION_CLASSES),
            "confusion_matrix": cm_c.tolist(),
            "per_class": condition_per_class,
            "macro": condition_macro,
            "micro": condition_micro,
        },
    }

    return report


def get_evaluation_report(metrics: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalize compute_comprehensive_metrics output for frontend telemetry.

    Expected consumers (front-end bar charts) typically want:
    - per-class precision/recall/f1 series
    - macro/micro aggregate points
    - optional confusion matrix for deeper inspection
    """

    if not isinstance(metrics, Mapping):
        raise ValueError("metrics must be a mapping")
    if "ripeness" not in metrics or "condition" not in metrics:
        raise ValueError("metrics must contain 'ripeness' and 'condition' fields")

    def _extract_head(head: str, expected_classes: Sequence[str]) -> Dict[str, Any]:
        head_obj = metrics.get(head, {})
        per_class = head_obj.get("per_class", [])
        if not isinstance(per_class, list):
            raise ValueError(f"metrics['{head}']['per_class'] must be a list")

        class_order = [x.get("class") for x in per_class]
        if any(c is None for c in class_order):
            # fallback to expected order
            class_order = list(expected_classes)

        precision = [float(x.get("precision", 0.0)) for x in per_class]
        recall = [float(x.get("recall", 0.0)) for x in per_class]
        f1 = [float(x.get("f1", 0.0)) for x in per_class]
        support = [int(x.get("support", 0)) for x in per_class]

        return {
            "classes": class_order,
            "precision_series": precision,
            "recall_series": recall,
            "f1_series": f1,
            "support_series": support,
            "macro": head_obj.get("macro", {}),
            "micro": head_obj.get("micro", {}),
            "confusion_matrix": head_obj.get("confusion_matrix", None),
        }

    return {
        "ripeness": _extract_head("ripeness", RIPENESS_CLASSES),
        "condition": _extract_head("condition", CONDITION_CLASSES),
        "raw": metrics,
    }

