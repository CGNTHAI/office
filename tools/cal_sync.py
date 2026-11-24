#!/usr/bin/env python3
"""구글 'CGN Thai' 캘린더 일정 → calendar.json (장비렌탈 '회사 일정' 탭이 읽음)
usage: python3 cal_sync.py events.json calendar.json
events.json: Google Calendar list_events 의 events 배열(또는 그걸 담은 객체, 여러 개면 배열의 배열)
- 직원 개인 연차(day off 등)는 빼요 — 오피스 대시보드에 이미 나와요.
- 건강검진 같은 회사 일정은 그대로 넣어요.
"""
import json, re, sys, datetime as dt
OFF = re.compile(r"day\s*-?\s*off|dayoff|\bleave\b|ลางาน|ลาพักร้อน|ลาป่วย|ลากิจ|연차|휴가|병가", re.I)
src, out = sys.argv[1], sys.argv[2]
raw = json.load(open(src))
def flat(x):
    if isinstance(x, dict): return x.get("events", [x] if "start" in x else [])
    r = []
    for y in x: r += flat(y) if isinstance(y, (list, dict)) and not (isinstance(y, dict) and "start" in y) else [y]
    return r
evs, seen = [], set()
for e in flat(raw):
    if e.get("status") == "cancelled" or e.get("id") in seen: continue
    seen.add(e.get("id"))
    title = (e.get("summary") or "").strip()
    if not title or OFF.search(title): continue
    s, en = e["start"], e["end"]
    if "date" in s:
        a = s["date"]; b = (dt.date.fromisoformat(en["date"]) - dt.timedelta(days=1)).isoformat()
        evs.append({"t": title, "d": a, "d2": b, "all": 1})
    else:
        a, b = s["dateTime"][:16], en["dateTime"][:16]
        evs.append({"t": title, "d": a[:10], "d2": b[:10], "s": a[11:], "e": b[11:]})
    if e.get("location"): evs[-1]["loc"] = e["location"].split("\n")[0][:80]
    if e.get("colorId"): evs[-1]["c"] = e["colorId"]
evs.sort(key=lambda x: (x["d"], x.get("s", "")))
new = {"updated": dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).strftime("%Y-%m-%d %H:%M"), "events": evs}
try:
    old = json.load(open(out))
    if old.get("events") == evs: print("변경 없음"); sys.exit(0)
except Exception: pass
json.dump(new, open(out, "w"), ensure_ascii=False, indent=0)
print(f"{len(evs)}개 저장")
