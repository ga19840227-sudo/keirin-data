"""Post-race settlement collector. Never use results as prediction inputs."""
import json,re,urllib.request,urllib.robotparser
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from html.parser import HTMLParser
JST=ZoneInfo("Asia/Tokyo")
UA="KeirinResearchCollector/1.0 (public pages only; respectful rate limit)"
class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ("script","style"):self.skip+=1
  if tag in ("p","tr","td","li","br","h2","h3"):self.parts.append("\n")
 def handle_endtag(self,tag):
  if tag in ("script","style"):self.skip=max(0,self.skip-1)
  if tag in ("p","tr","li"):self.parts.append("\n")
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)
def fetch(url,robot):
 if not robot.can_fetch(UA,url):raise PermissionError("robots disallow")
 req=urllib.request.Request(url,headers={"User-Agent":UA})
 with urllib.request.urlopen(req,timeout=20) as res:
  if res.status!=200:raise RuntimeError("HTTP "+str(res.status))
  if "html" not in res.headers.get("Content-Type",""):raise ValueError("not html")
  data=res.read(2000001)
  if len(data)>2000000:raise ValueError("too large")
  p=Text();p.feed(data.decode(res.headers.get_content_charset() or "utf-8",errors="replace"))
  return re.sub(r"[ \t]+"," ","".join(p.parts))
def order(text):
 # Only explicit final classification 1着3 / 2着5 / 3着2; no rider-number guessing
 m=re.search(r"結果\s*1着\s*は[^\n]*",text)
 anchor=text.find("結果",max(0,text.find("結果印並び")))
 for segment in [text[anchor:anchor+1800] if anchor>=0 else "",text]:
  matches=re.findall(r"(?:^|\n)\s*([123])着\s*([1-9])(?=[^0-9]|$)",segment)
  vals={}
  for rank,num in matches:
   if rank not in vals:vals[rank]=int(num)
  if len(vals)==3 and len(set(vals.values()))==3:return [vals[str(i)] for i in (1,2,3)]
 return None
def main():
 now=datetime.now(JST); root=Path("snapshots");out=Path("results/auto_settlement");out.mkdir(parents=True,exist_ok=True)
 robot=urllib.robotparser.RobotFileParser();robot.set_url("https://keirinhex.jp/robots.txt")
 audit={"checked_at_jst":now.isoformat(),"checked":0,"settled":0,"pending":[],"errors":[],"payout_missing":[]}
 try:robot.read()
 except Exception as e:
  audit["errors"].append("robots: "+str(e));(out/"latest_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2));return
 for day in [(now-timedelta(days=i)).strftime("%Y%m%d") for i in range(3)]:
  for path in sorted((root/day).glob("*.json")):
   if path.name=="collection_audit.json":continue
   try:
    d=json.loads(path.read_text());start=d.get("start_jst")
    if not start or datetime.fromisoformat(start)>now:continue
    dest=out/(path.stem+".json")
    if dest.exists() and json.loads(dest.read_text()).get("status")=="result_confirmed":continue
    url=d.get("source_url","")
    if not re.fullmatch(r"https://keirinhex\.jp/races/\d{8}/\d+/?",url):continue
    audit["checked"]+=1
    text=fetch(url,robot);actual=order(text)
    if not actual:audit["pending"].append(path.stem);continue
    # HEX provides result order but often no official payout. Never substitute odds.
    rec={"race_id":path.stem,"source_url":url,"result_retrieved_jst":datetime.now(JST).isoformat(),"status":"result_confirmed","actual_first_second_third":actual,"official_trifecta_payout_per_100_yen":None,"payout_status":"unverified","prerace_snapshot":str(path)}
    dest.write_text(json.dumps(rec,ensure_ascii=False,indent=2));audit["settled"]+=1;audit["payout_missing"].append(path.stem)
   except Exception as e:audit["errors"].append({"race":path.stem,"error":str(e)[:220]})
 (out/"latest_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2));print(json.dumps(audit,ensure_ascii=False))
if __name__=="__main__":main()
