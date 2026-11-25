#!/usr/bin/env python3
"""CGN Thai office: list staff entries that still need Korean, and write translations back.
  python3 tr.py list            -> JSON [{doc, i, f, th}] : f="ko" task text, f="n" progress note, still untranslated
  python3 tr.py apply FILE.json -> FILE = [{doc, i, f, ko}] ; writes the Korean into field f (default "ko")
"""
import json, re, sys, urllib.request
BASE = "https://firestore.googleapis.com/v1/projects/cgn-rental/databases/(default)/documents/office_reports"
THAI = re.compile(r"[฀-๿]")

def get(url):
    with urllib.request.urlopen(url, timeout=30) as r: return json.load(r)

def docs():
    """오늘(방콕) 업무와 이번 주 목표 문서만 읽어요 (Firestore 하루 무료 읽기 50,000회 절약)."""
    import datetime as dt
    today = (dt.datetime.utcnow() + dt.timedelta(hours=7)).date()
    mon = today - dt.timedelta(days=today.weekday())
    vals = [{"stringValue": today.isoformat()}] + ([{"stringValue": mon.isoformat()}] if mon != today else [])
    q = {"structuredQuery": {"from": [{"collectionId": "office_reports"}],
         "where": {"fieldFilter": {"field": {"fieldPath": "date"}, "op": "IN", "value": {"arrayValue": {"values": vals}}}}}}
    req = urllib.request.Request(BASE.rsplit("/", 1)[0] + ":runQuery", data=json.dumps(q).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r: res = json.load(r)
    out = [x["document"] for x in res if "document" in x]
    # 월요일 날짜의 일일 업무 문서(YYYY-MM-DD_id)는 오늘이 월요일이 아니면 빼요 — 주간 목표(week_…)만 남김
    if mon != today: out = [d for d in out if not (d["name"].rsplit("/",1)[1].startswith(mon.isoformat()))]
    return out

def tasks_of(doc):
    return doc.get("fields", {}).get("tasks", {}).get("arrayValue", {}).get("values", []) or []

def sv(m, k): return m.get("mapValue", {}).get("fields", {}).get(k, {}).get("stringValue", "")

if sys.argv[1] == "list":
    pend = []
    for d in docs():
        name = d["name"].rsplit("/", 1)[1]
        for i, t in enumerate(tasks_of(d)):
            th, ko = sv(t, "th"), sv(t, "ko")
            if th and THAI.search(th) and (not ko or ko == th):
                pend.append({"doc": name, "i": i, "f": "ko", "th": th})
            nth, n = sv(t, "nth"), sv(t, "n")
            if nth and THAI.search(nth) and (not n or n == nth):
                pend.append({"doc": name, "i": i, "f": "n", "th": nth})
    print(json.dumps(pend, ensure_ascii=False, indent=1))
elif sys.argv[1] == "apply":
    items = json.load(open(sys.argv[2]))
    by = {}
    for it in items: by.setdefault(it["doc"], {}).setdefault(it["i"], {})[it.get("f", "ko")] = it["ko"]
    for name, m in by.items():
        d = get(f"{BASE}/{name}")
        vals = tasks_of(d)
        for i, fs in m.items():
            if i < len(vals):
                for f, ko in fs.items(): vals[i]["mapValue"]["fields"][f] = {"stringValue": ko}
        body = json.dumps({"fields": {"tasks": {"arrayValue": {"values": vals}}}}).encode()
        req = urllib.request.Request(f"{BASE}/{name}?updateMask.fieldPaths=tasks&currentDocument.updateTime={d['updateTime']}",
                                     data=body, method="PATCH", headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=30); print("ok", name, len(m))
        except urllib.error.HTTPError as e:
            print("skip", name, e.code, "(changed meanwhile or denied)")
