#!/usr/bin/env python3
"""그룹웨어(Bizbox) 공유일정에서 읽은 연차·휴가·출장을 data.json absences로 바꿔 넣기.
입력: JSON [{name, title, sda, eda}]  (name 예: "마이(Mild)", title 예: "[연차]Day off (10/11/26)")
사용: python3 gw_absences.py events.json data.json [--from 2026-11-16]
- 그룹웨어에서 온 항목(src:"gw")은 매번 새로 덮어쓰고, 손으로 넣은 항목은 그대로 둬요.
- 보건휴가는 '병가(ลาป่วย)'로 표시하되, 일정 제목에 적힌 사유는 넣지 않아요.
"""
import json, sys, re, datetime as dt
NAME = {"제이":"jay","핸":"hand","마이":"mild","맛":"mud","억":"ox","애":"aey","킵":"keep","삔":"pin","블루":"blue","네임":"name","쫑":"jong","비":"bee","찻":"chat"}
KIND = {
 "연차":    ("leave","연차","ลาพักร้อน"),
 "오전반차": ("leave","오전 반차","ลาครึ่งวันเช้า"),
 "오후반차": ("leave","오후 반차","ลาครึ่งวันบ่าย"),
 "보건휴가": ("leave","병가","ลาป่วย"),
 "휴가":    ("leave","휴가","ลาพักร้อน"),
 "국내출장": ("trip","출장","ไปทำงานต่างจังหวัด"),
 "해외출장": ("trip","해외 출장","ไปทำงานต่างประเทศ"),
}
def nextwork(d):
    d += dt.timedelta(days=1)
    while d.weekday() >= 5: d += dt.timedelta(days=1)
    return d
evs = json.load(open(sys.argv[1])); path = sys.argv[2]
since = sys.argv[sys.argv.index("--from")+1] if "--from" in sys.argv else "0000"
D = json.load(open(path))
keep = [a for a in D.get("absences", []) if a.get("src") != "gw"]
old_where = {a["id"]: a for a in D.get("absences", []) if a.get("type") == "trip"}
out = []
for e in evs:
    m = re.match(r"\[(.+?)\]", e["title"]); k = m.group(1) if m else ""
    if k not in KIND: continue
    nick = re.match(r"([^\(]+)", e["name"]).group(1).strip(); sid = NAME.get(nick)
    if not sid: continue
    a, b = e["sda"][:10], e["eda"][:10]
    if b < since: continue
    typ, ko, th = KIND[k]
    to = dt.date.fromisoformat(b)
    back = to if (k == "오전반차" or typ == "trip") else nextwork(to)   # 출장은 끝나는 날이 복귀일(그날 자리는 비움)
    item = {"id": sid, "from": a, "to": b, "type": typ, "ko": ko, "th": th, "back": back.isoformat(), "src": "gw"}
    if k in ("오전반차", "오후반차"): item["half"] = "am" if k == "오전반차" else "pm"   # 대시보드가 시간대에 맞춰 표시
    if typ == "trip" and sid in old_where and old_where[sid].get("where"):
        item["where"] = old_where[sid]["where"]; item["where_th"] = old_where[sid].get("where_th", "")
    out.append(item)
# 같은 사람의 같은 종류 일정이 주말만 끼고 이어지면 하나로 합치기 (복귀일이 맞게 나오도록)
out.sort(key=lambda a: (a["id"], a["from"]))
merged = []
for a in out:
    p = merged[-1] if merged else None
    if p and p["id"] == a["id"] and p["ko"] == a["ko"] and not a.get("half") and a["from"] <= nextwork(dt.date.fromisoformat(p["to"])).isoformat():
        p["to"] = max(p["to"], a["to"]); p["back"] = a["back"] if a["to"] >= p["to"] else p["back"]
    else: merged.append(dict(a))
out = merged
# 손으로 넣은 항목 중 그룹웨어와 같은 사람·기간이 겹치는 건 그룹웨어 쪽을 우선
def overlap(x, y): return x["id"] == y["id"] and not (x["to"] < y["from"] or y["to"] < x["from"])
keep = [a for a in keep if not any(overlap(a, g) for g in out)]
D["absences"] = sorted(keep + out, key=lambda a: (a["from"], a["id"]))
json.dump(D, open(path, "w"), ensure_ascii=False, indent=1)
for a in D["absences"]: print(a["id"], a["from"], a["to"], a["ko"], "→", a["back"], a.get("src",""))
