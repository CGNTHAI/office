#!/usr/bin/env python3
"""cgn-rental 의 오피스 컬렉션을 cgn-office 로 복사 (한 번 쓰는 도구).
usage: python3 migrate.py [--since ISO]   --since: 그 이후에 바뀐 문서만 다시 복사"""
import json, sys, urllib.request
OLD = "https://firestore.googleapis.com/v1/projects/cgn-rental/databases/(default)/documents/"
NEW = "https://firestore.googleapis.com/v1/projects/cgn-office/databases/(default)/documents/"
COLS = ["office_reports", "office_events", "office_server", "office_projects"]
since = sys.argv[sys.argv.index("--since")+1] if "--since" in sys.argv else ""
def call(url, data=None, method="GET"):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)
tot = 0
for c in COLS:
    tok, n = "", 0
    while True:
        d = call(OLD + c + "?pageSize=300" + (f"&pageToken={tok}" if tok else ""))
        for doc in d.get("documents", []):
            if since and doc.get("updateTime", "") < since: continue
            did = doc["name"].rsplit("/", 1)[1]
            call(NEW + c + "/" + did, {"fields": doc.get("fields", {})}, "PATCH"); n += 1
        tok = d.get("nextPageToken", "")
        if not tok: break
    print(c, n); tot += n
print("total", tot)
