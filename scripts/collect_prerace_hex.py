"""Collect timestamped public pre-race line/ability/SBH snapshots.
Respect robots.txt and access restrictions; never treat failed access as success.
No paid pages, bypasses, or post-start snapshots.
"""
import csv,json,re,time,urllib.request,urllib.parse,urllib.robotparser,urllib.error
from html.parser import HTMLParser
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

BASE="https://keirinhex.jp"
JST=ZoneInfo("Asia/Tokyo")
OUT=Path("snapshots");OUT.mkdir(exist_ok=True)
UA="KeirinResearchCollector/1.0 (public pages only; respectful rate limit)"
class Page(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag in ("script","style"):self.skip+=1
        if tag=="a" and d.get("href"):self.links.append(d["href"])
        if tag in ("tr","td","th","p","h1","h2","h3","li","br"):self.parts.append("\n")
    def handle_endtag(self,tag):
        if tag in ("script","style"):self.skip=max(0,self.skip-1)
        if tag in ("tr","p","li"):self.parts.append("\n")
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)
def fetch(url,robot):
    if not robot.can_fetch(UA,url):raise PermissionError("robots.txt disallows "+url)
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=25) as res:
                if res.status!=200:raise RuntimeError("HTTP "+str(res.status))
                if "html" not in res.headers.get("Content-Type",""):raise RuntimeError("not HTML")
                raw=res.read(2_000_001)
                if len(raw)>2_000_000:raise RuntimeError("page too large")
                charset=res.headers.get_content_charset() or "utf-8"
                return raw.decode(charset,errors="replace")
        except urllib.error.HTTPError as e:
            if e.code not in (429,500,502,503,504) or attempt==2:raise
            time.sleep(3*(attempt+1))
        except (urllib.error.URLError,TimeoutError,ConnectionError):
            if attempt==2:raise
            time.sleep(3*(attempt+1))
def main():
    now=datetime.now(JST)
    date=now.strftime("%Y%m%d")
    audit={"captured_jst":now.isoformat(),"date":date,"source":BASE,"visited":0,"snapshot_count":0,"errors":[]}
    robot=urllib.robotparser.RobotFileParser()
    try:
        robot.set_url(BASE+"/robots.txt");robot.read()
    except Exception as e:
        audit["errors"].append("robots unavailable: "+str(e));save_audit(date,audit);return
    try:
        index_html=fetch(BASE+"/races/"+date+"/",robot)
        index=Page();index.feed(index_html)
        links=sorted(set(urllib.parse.urljoin(BASE,x).split("?")[0] for x in index.links
                         if re.search(r"/races/"+date+r"/[0-9]+/?",x)))

        links=sorted(set(links)|{BASE+"/races/"+date+"/"+rid+"/" for rid in re.findall(r"/races/"+date+r"/([0-9]{8,20})/?",index_html)})
        cache_path=Path("results/race_start_cache")/(date+".json")
        try:
            start_cache=json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
        except (OSError,ValueError):
            start_cache={}
        def priority(url):
            rid=url.rstrip("/").split("/")[-1]
            try:
                t=datetime.fromisoformat(start_cache[rid])
                return (0,t.isoformat()) if t>datetime.now(JST) else (2,t.isoformat())
            except (KeyError,ValueError,TypeError):
                return (1,rid)
        links.sort(key=priority)
        audit["indexed_races"]=len(links)
        if not links:
            audit["errors"].append("no current-date race links found; do not infer 0 scheduled races")
        for url in links:
            try:
                race_id=url.rstrip("/").split("/")[-1]
                target=OUT/date/(race_id+".json")
                if target.exists():
                    try:
                        previous=json.loads(target.read_text(encoding="utf-8"))
                        if previous.get("verified_pre_race") and (previous.get("line_groups") or "ガールズ" in previous.get("page_text","")[:700]) and previous.get("captured_jst") and previous.get("start_jst") and datetime.fromisoformat(previous["captured_jst"]) < datetime.fromisoformat(previous["start_jst"]):
                            audit["already_saved"]=audit.get("already_saved",0)+1
                            continue
                    except (ValueError,OSError,TypeError,KeyError):
                        pass
                if race_id in start_cache:
                    try:
                        if datetime.fromisoformat(start_cache[race_id])<=datetime.now(JST):
                            audit["skipped_known_started"]=audit.get("skipped_known_started",0)+1
                            continue
                    except (ValueError,TypeError):pass
                time.sleep(1.5)
                page=Page();page.feed(fetch(url,robot));audit["visited"]+=1
                txt=re.sub(r"[ \t]+"," ","".join(page.parts))
                match=re.search(r"並び予想は\s*([0-9０-９/／\-－=\s]+)",txt)
                line_text=match.group(1).strip() if match else None
                groups=None
                if line_text:
                    normalized=line_text.translate(str.maketrans("０１２３４５６７８９／－","0123456789/-"))
                    pieces=[x.strip() for x in normalized.split("/")]
                    if all(re.fullmatch(r"[1-9](?:-[1-9])*",x) for x in pieces):
                        groups=[[int(n) for n in x.split("-")] for x in pieces]
                start=re.search(r"(?:発走(?:予定)?(?:時間)?|発走)\s*([0-2]?\d:[0-5]\d)",txt)
                # Do not label as pre-race unless start is visible and later than capture.
                start_dt=None
                if start:
                    start_dt=datetime.fromisoformat(now.strftime("%Y-%m-%d")+"T"+start.group(1)+":00").replace(tzinfo=JST)
                captured_at=datetime.now(JST)
                if start_dt is not None:
                    start_cache[race_id]=start_dt.isoformat()
                is_pre=start_dt is not None and captured_at<start_dt
                rec={"source_url":url,"captured_jst":captured_at.isoformat(),
                     "race_date":now.date().isoformat(),"start_jst":start_dt.isoformat() if start_dt else None,
                     "verified_pre_race":bool(is_pre),"line_groups":groups,
                     "lineup_raw":line_text,"page_text":txt[:30000],
                     "sbh_structured":False,"odds_structured":False,
                     "warning":"Raw page text is evidence, not yet structured SBH/odds; no post-start data as pre-race."}
                if not is_pre:
                    audit["errors"].append(url+": no verified future start time")
                    continue
                dest=OUT/date;dest.mkdir(parents=True,exist_ok=True)
                target=dest/(race_id+".json")
                # Keep earliest verified pre-start evidence immutable across hourly runs.
                if target.exists():
                    try:
                        previous=json.loads(target.read_text(encoding="utf-8"))
                        if previous.get("verified_pre_race") and (previous.get("line_groups") or "ガールズ" in previous.get("page_text","")[:700]):
                            audit["already_saved"]=audit.get("already_saved",0)+1
                            continue
                    except (ValueError,OSError):pass
                target.write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding="utf-8")
                audit["snapshot_count"]+=1
            except Exception as e:audit["errors"].append(url+": "+str(e))
        cache_path.parent.mkdir(parents=True,exist_ok=True)
        cache_path.write_text(json.dumps(start_cache,ensure_ascii=False,indent=2),encoding="utf-8")
    except Exception as e:audit["errors"].append("index: "+str(e))
    audit["verified_saved_total"]=sum(1 for p in (OUT/date).glob("*.json") if p.name!="collection_audit.json" and _verified_snapshot(p))
    audit["missing_verified_count"]=max(0,audit.get("indexed_races",0)-audit["verified_saved_total"])
    save_audit(date,audit)
def _verified_snapshot(path):
    try:
        d=json.loads(path.read_text(encoding="utf-8"))
        return bool(d.get("verified_pre_race") and datetime.fromisoformat(d["captured_jst"])<datetime.fromisoformat(d["start_jst"]))
    except (OSError,ValueError,TypeError,KeyError):return False
def save_audit(date,audit):
    dest=OUT/date;dest.mkdir(parents=True,exist_ok=True)
    (dest/"collection_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(audit,ensure_ascii=False))
if __name__=="__main__":main()
