"""Clearly-labeled DEMO dataset. Sample data ONLY -- never live research.
Used when no YouTube API key is configured or ?demo=1 is passed."""
from datetime import datetime, timezone

def _v(id_, title, ch, views, likes, comments, days_ago, dur, kw):
    return {"id": id_, "title": title, "channel_id": ch[0], "channel_title": ch[1],
            "thumbnail_url": f"https://i.ytimg.com/vi/{id_}/hqdefault.jpg",
            "published_at": f"2026-10-{max(1, 23-days_ago):02d}T12:00:00Z",
            "views": views, "likes": likes, "comments": comments,
            "duration_seconds": dur, "is_short": dur <= 60,
            "url": f"https://www.youtube.com/watch?v={id_}",
            "channel_subscribers": ch[2], "_keywords": kw,
            "_days_ago": days_ago}

CH_FIN = ("UCdemoFinance01", "Wealth In Plain English", 82000)
CH_AI = ("UCdemoAITools02", "AI Workflow Lab", 45000)
CH_HIST = ("UCdemoHistory03", "History They Forgot", 12500)
CH_FIT = ("UCdemoFitness04", "Home Strength Daily", 210000)
CH_COOK = ("UCdemoCooking05", "15 Minute Kitchen", 67000)
CH_TECH = ("UCdemoTech006", "Gadget Verdict", 34000)
CH_TRAVEL = ("UCdemoTravel07", "Budget Backroads", 9800)
CH_PETS = ("UCdemoPets008", "Senior Dog Care HQ", 15800)
CH_GAME = ("UCdemoGaming09", "Lore Explained Fast", 150000)
CH_STUDY = ("UCdemoStudy010", "Focus Formula", 27000)

CHANNELS = [
 {"id": c[0], "title": c[1], "subscribers": c[2], "hidden_subscriber_count": False,
  "total_views": tv, "video_count": vc, "created_at": ca,
  "thumbnail_url": f"https://yt3.googleusercontent.com/demo-{c[0]}",
  "banner_url": None, "url": f"https://www.youtube.com/channel/{c[0]}",
  "description": "Demo channel (sample data)."}
 for c, tv, vc, ca in [
  (CH_FIN, 4800000, 142, "2021-03-14T00:00:00Z"), (CH_AI, 2100000, 98, "2022-06-01T00:00:00Z"),
  (CH_HIST, 890000, 57, "2025-08-19T00:00:00Z"), (CH_FIT, 15200000, 310, "2019-11-02T00:00:00Z"),
  (CH_COOK, 3900000, 188, "2020-05-23T00:00:00Z"), (CH_TECH, 1700000, 121, "2021-09-30T00:00:00Z"),
  (CH_TRAVEL, 640000, 74, "2023-04-11T00:00:00Z"), (CH_PETS, 980000, 89, "2022-01-17T00:00:00Z"),
  (CH_GAME, 11400000, 264, "2018-07-08T00:00:00Z"), (CH_STUDY, 1350000, 66, "2023-10-05T00:00:00Z")]]

VIDEOS = [
 _v("demoVid001", "Why Rich People Use Debt Differently", CH_FIN, 184000, 7200, 640, 3, 742, "personal finance debt investing"),
 _v("demoVid002", "Index Funds Explained in 11 Minutes", CH_FIN, 42000, 1900, 150, 10, 660, "personal finance index funds investing"),
 _v("demoVid003", "The Budget Rule Nobody Follows", CH_FIN, 38000, 1500, 121, 17, 590, "personal finance budget money"),
 _v("demoVid004", "I Automated My Whole Job With AI Tools", CH_AI, 296000, 11400, 980, 2, 905, "ai tools automation workflow"),
 _v("demoVid005", "5 AI Tools That Replace a $500/mo Stack", CH_AI, 61000, 2600, 210, 9, 640, "ai tools software productivity"),
 _v("demoVid006", "Build an AI Agent in 20 Minutes", CH_AI, 54000, 2300, 189, 15, 1180, "ai agents tutorial automation"),
 _v("demoVid007", "The Roman Soldier Who Retired Rich", CH_HIST, 412000, 15800, 1320, 4, 1020, "ancient rome history soldiers"),
 _v("demoVid008", "A Day in a Medieval Village", CH_HIST, 29000, 1100, 88, 11, 940, "medieval history village life"),
 _v("demoVid009", "Why Ancient Armies Starved", CH_HIST, 34000, 1300, 104, 19, 880, "ancient history army logistics"),
 _v("demoVid010", "20 Minute Home Workout, No Equipment", CH_FIT, 520000, 19800, 870, 6, 1210, "home workout fitness no equipment"),
 _v("demoVid011", "Fix Your Posture in 7 Days", CH_FIT, 238000, 9100, 402, 13, 540, "posture fitness health"),
 _v("demoVid012", "60 Second Morning Mobility", CH_FIT, 88000, 3400, 96, 1, 45, "mobility shorts fitness morning"),
 _v("demoVid013", "3 Ingredients, 15 Minutes, Full Dinner", CH_COOK, 167000, 6800, 311, 5, 780, "quick cooking dinner recipes"),
 _v("demoVid014", "Why Your Rice Is Always Mushy", CH_COOK, 45000, 1800, 240, 12, 430, "cooking rice tips kitchen"),
 _v("demoVid015", "The $2 Breakfast That Tastes Expensive", CH_COOK, 39000, 1500, 132, 20, 390, "budget cooking breakfast recipes"),
 _v("demoVid016", "I Tested 7 Cheap Earbuds So You Don't Have To", CH_TECH, 92000, 3700, 519, 7, 690, "tech gadgets earbuds review"),
 _v("demoVid017", "This $40 Gadget Replaced My Laptop Dock", CH_TECH, 31000, 1200, 148, 14, 520, "tech gadgets laptop usb"),
 _v("demoVid018", "30 Second Phone Trick", CH_TECH, 64000, 2100, 77, 2, 32, "phone trick shorts tech"),
 _v("demoVid019", "The Cheapest Country to Travel in 2026", CH_TRAVEL, 78000, 3200, 286, 8, 830, "budget travel cheapest country"),
 _v("demoVid020", "7 Days in the Mountains for $210", CH_TRAVEL, 11500, 480, 61, 16, 760, "budget travel mountains trip"),
 _v("demoVid021", "Senior Dog Care: 5 Signs to Never Ignore", CH_PETS, 134000, 5900, 733, 4, 615, "senior dog care pets health"),
 _v("demoVid022", "Best Food for Older Dogs", CH_PETS, 21000, 870, 119, 13, 480, "dog food senior pets care"),
 _v("demoVid023", "The Hidden Lore Behind the Final Boss", CH_GAME, 388000, 14900, 1240, 3, 970, "gaming lore boss story"),
 _v("demoVid024", "How to Study 6 Hours Without Burning Out", CH_STUDY, 201000, 8600, 654, 9, 810, "study productivity focus exam"),
 _v("demoVid025", "The 25 Minute Focus Method, Tested", CH_STUDY, 33000, 1400, 98, 18, 560, "focus pomodoro study productivity"),
 _v("demoVid026", "45 Second Study Hack", CH_STUDY, 47000, 1900, 54, 1, 48, "study hack shorts focus"),
]

COMMENTS = [
 {"author": "demo_user_1", "text": "Great video, this was really helpful and clear. Thanks!", "likes": 42, "published_at": "2026-10-22T09:00:00Z"},
 {"author": "demo_user_2", "text": "Amazing breakdown, best explanation I have seen.", "likes": 18, "published_at": "2026-10-22T11:30:00Z"},
 {"author": "demo_user_3", "text": "Good points but a bit slow in the middle.", "likes": 5, "published_at": "2026-10-22T14:05:00Z"},
 {"author": "demo_user_4", "text": "This was boring and confusing, poor pacing.", "likes": 2, "published_at": "2026-10-22T16:40:00Z"},
 {"author": "demo_user_5", "text": "Interesting topic, I enjoyed it.", "likes": 9, "published_at": "2026-10-23T08:15:00Z"},
]

def all_videos(): return [dict(v) for v in VIDEOS]
def all_channels(): return [dict(c) for c in CHANNELS]
def get_channel(cid):
    for c in CHANNELS:
        if c["id"] == cid: return dict(c)
    return None
def get_video(vid):
    for v in VIDEOS:
        if v["id"] == vid: return dict(v)
    return None
