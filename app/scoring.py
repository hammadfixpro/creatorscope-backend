"""Transparent scoring formulas for CreatorScope AI.

Outlier score:
    outlier_score = video_views / baseline_views
    baseline_views = median views of OTHER recent videos from the same channel
    (the current video is always excluded from its own baseline).

Confidence (from sample size = number of other videos in the baseline):
    sample_size >= 8  -> "high"
    3 <= sample_size <= 7 -> "medium"
    1 <= sample_size <= 2 -> "low"
    sample_size == 0  -> "low" and the score falls back to views_per_sub
                         (a weak signal only -- NOT proof of virality).

Opportunity score (0-100, niches):
    opportunity = 0.45 * demand_component + 0.35 * outlier_component
                + 0.20 * competition_component
    demand_component      = min(100, log10(max(avg_views,1)) / 6 * 100)
    outlier_component     = min(100, (avg_outlier - 1) / 9 * 100) clamped >= 0
    competition_component = {low: 100, medium: 60, high: 25}[competition_level]

Revenue estimate:
    revenue = monthly_views / 1000 * assumed_rpm   (low/mid/high scenarios)
"""
import math
from statistics import median as _median

def median(values):
    vals = [float(v) for v in values if v is not None]
    return float(_median(vals)) if vals else 0.0

def outlier_score(views, baseline_views):
    if not baseline_views or baseline_views <= 0:
        return None
    return round(float(views) / float(baseline_views), 3)

def confidence_for_sample(sample_size):
    if sample_size >= 8: return "high"
    if sample_size >= 3: return "medium"
    return "low"

def compute_outlier(video_views, other_video_views, channel_subscribers=None):
    """Return dict(baseline_views, sample_size, outlier_score, views_per_sub, confidence)."""
    others = [v for v in (other_video_views or []) if v is not None]
    sample = len(others)
    baseline = median(others) if others else 0.0
    vps = round(video_views / channel_subscribers, 3) if channel_subscribers else None
    score = outlier_score(video_views, baseline) if baseline > 0 else None
    if score is None:
        # Weak fallback: views/sub ratio, explicitly low confidence.
        score = vps
    return {"baseline_views": baseline if baseline > 0 else None,
            "sample_size": sample, "outlier_score": score,
            "views_per_sub": vps, "confidence": confidence_for_sample(sample)}

def opportunity_score(avg_views, avg_outlier, competition_level):
    demand = min(100.0, (math.log10(max(float(avg_views or 0), 1.0)) / 6.0) * 100.0)
    outlier_c = max(0.0, min(100.0, ((float(avg_outlier or 1) - 1.0) / 9.0) * 100.0))
    comp = {"low": 100.0, "medium": 60.0, "high": 25.0}.get(competition_level, 60.0)
    return round(0.45 * demand + 0.35 * outlier_c + 0.20 * comp, 2)

def revenue_estimate(monthly_views, rpm_low, rpm_mid, rpm_high):
    mv = float(monthly_views or 0)
    return {"low": round(mv / 1000.0 * float(rpm_low), 2),
            "mid": round(mv / 1000.0 * float(rpm_mid), 2),
            "high": round(mv / 1000.0 * float(rpm_high), 2),
            "formula": "revenue = monthly_views / 1000 * assumed_rpm"}
