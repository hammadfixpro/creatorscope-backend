"""Scored similar-channel matching (v2) — transparent, documented, never invented.

Similarity score (0-100) for a candidate channel vs a seed channel:
    score = 0.45 * keyword_component
          + 0.15 * topic_component
          + 0.20 * subscriber_component
          + 0.20 * views_component

    keyword_component   = min(100, 20 * number_of_shared_keywords)
                          (5+ shared keywords saturate this component)
    topic_component     = 100 if seed and candidate share a YouTube topic
                          category, else 0. Topic categories come from the
                          channels.list topicDetails part (public data).
    subscriber_component = 100 * (1 - min(1, |log10(seed_subs)
                          - log10(candidate_subs)| / 3)) — channels within
                          one order of magnitude score >= ~67. Hidden or
                          missing subscriber counts score a neutral 50.
    views_component     = same log-closeness formula applied to average
                          views (recent sample where affordable, otherwise
                          lifetime total_views / video_count). Missing
                          averages score a neutral 50.

Keywords are extracted from the seed channel's title + description +
recent video titles/tags, lowercased, stopword-filtered, frequency-ranked
(top 12 kept). Candidates with NEITHER a shared keyword NOR a shared topic
category are excluded: subscriber/view size closeness alone is not
similarity, and surfacing such channels as "similar" would be misleading.
Live quota note: the similar-channels endpoint spends
up to 3 search.list calls (100 units each) + 1 batched channels.list
(1 unit) + up to 10 candidate recent-video samples (3 units each:
channels contentDetails + playlistItems + videos.list) = ~334 units
worst case per uncached call; all provider calls are cached 3600s, so a
repeat within the hour costs 0 fresh units.
"""
import math
import re
from statistics import mean

STOPWORDS = set(
    "a an the and or of to in on for with from by at is are was were be been "
    "this that these those it its you your we our they their he she his her "
    "how what when where why who which do does did can could will would should "
    "i me my me myself about into over under after before between through during "
    "video videos channel new best top get make made watch watching today now "
    "part episode official full free tips tricks guide tutorial review reviews "
    "youtube shorts short vlog daily life real world time day year years".split()
)

def extract_keywords(texts, limit=12):
    """texts: iterable of strings -> ordered list of top keywords."""
    counts = {}
    for text in texts or []:
        for tok in re.findall(r"[a-z0-9]+", (text or "").lower()):
            if len(tok) < 3 or tok in STOPWORDS:
                continue
            counts[tok] = counts.get(tok, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [k for k, _ in ranked[:limit]]

def _log_closeness(a, b):
    """100 when equal, ~67 within 1 order of magnitude, 0 at >=3 orders."""
    if not a or not b or a <= 0 or b <= 0:
        return 50.0
    diff = abs(math.log10(float(a)) - math.log10(float(b)))
    return max(0.0, 100.0 * (1.0 - min(1.0, diff / 3.0)))

def similarity_score(seed_keywords, cand_keywords, seed_topics, cand_topics,
                     seed_subs, cand_subs, seed_avg_views, cand_avg_views):
    """Return (score 0-100, matched_keywords list). Pure function, unit-tested."""
    seed_set, cand_set = set(seed_keywords or []), set(cand_keywords or [])
    matched = sorted(seed_set & cand_set)
    kw = min(100.0, 20.0 * len(matched))
    topic = 100.0 if (set(seed_topics or []) & set(cand_topics or [])) else 0.0
    subs = _log_closeness(seed_subs, cand_subs)
    views = _log_closeness(seed_avg_views, cand_avg_views)
    score = round(0.45 * kw + 0.15 * topic + 0.20 * subs + 0.20 * views, 1)
    return max(0.0, min(100.0, score)), matched

def lifetime_avg_views(channel):
    vc = channel.get("video_count") or 0
    tv = channel.get("total_views") or 0
    return (tv / vc) if vc else None

def uploads_per_week(videos):
    """videos: list with published_at ISO strings. 0.0 when uncomputable."""
    if len(videos or []) < 2:
        return 0.0
    try:
        from datetime import datetime
        dates = sorted(v["published_at"] for v in videos if v.get("published_at"))
        if len(dates) < 2:
            return 0.0
        span = max((datetime.fromisoformat(dates[-1].replace("Z", "+00:00"))
                    - datetime.fromisoformat(dates[0].replace("Z", "+00:00"))).days, 1)
        return round(len(dates) / (span / 7.0), 2)
    except Exception:
        return 0.0

def mean_views(videos):
    vals = [v["views"] for v in (videos or []) if v.get("views") is not None]
    return round(mean(vals), 1) if vals else None
