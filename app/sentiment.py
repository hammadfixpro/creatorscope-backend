POSITIVE = set("good great amazing awesome excellent love loved best fantastic brilliant helpful thanks thank wonderful superb nice cool perfect interesting informative clear easy fun happy glad enjoy enjoyed wow incredible outstanding quality favourite favorite super".split())
NEGATIVE = set("bad terrible awful worst hate hated boring poor disappointing useless waste slow broken wrong annoying stupid horrible disgusting fake scam low sad angry difficult confusing".split())

def analyze_sentiment(texts):
    pos = neg = neu = 0
    for t in texts or []:
        words = set((t or "").lower().split())
        p, n = len(words & POSITIVE), len(words & NEGATIVE)
        if p > n: pos += 1
        elif n > p: neg += 1
        else: neu += 1
    total = max(pos + neg + neu, 1)
    return {"positive": round(pos/total, 3), "negative": round(neg/total, 3),
            "neutral": round(neu/total, 3),
            "score": round((pos - neg)/total, 3), "sample_size": pos+neg+neu}
