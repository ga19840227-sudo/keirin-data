"""Join archived actual line/SBH pages with settled historical CSV races by date, venue and race number."""
import csv,glob,json,re,collections
from pathlib import Path
VENUES={"前橋":"maebashi","松戸":"matsudo","小倉":"kokura","川崎":"kawasaki","立川":"tachikawa","京王閣":"keiokaku","玉野":"tamano","弥彦":"yahiko","静岡":"shizuoka","防府":"hofu","四日市":"yokkaichi","宇都宮":"utsunomiya","平塚":"hiratsuka","大宮":"omiya","西武園":"seibuen","取手":"toride","高松":"takamatsu","岸和田":"kishiwada","奈良":"nara","向日町":"mukomachi","豊橋":"toyohashi","名古屋":"nagoya","岐阜":"gifu","大垣":"ogaki","富山":"toyama","福井":"fukui","松阪":"matsusaka","和歌山":"wakayama","広島":"hiroshima","小松島":"komatsushima","高知":"kochi","松山":"matsuyama","久留米":"kurume","武雄":"takeo","佐世保":"sasebo","別府":"beppu","熊本":"kumamoto","函館":"hakodate","青森":"aomori","いわき平":"iwakitaira","福島":"iwakitaira","伊東":"ito","千葉":"chiba"}
lookup=collections.defaultdict(list)
for path in sorted(glob.glob("historical_hex/20*/*.json")):
 if path.endswith("day_archive.json"):continue
 d=json.loads(Path(path).read_text(encoding="utf-8"))
 m=re.search(r"([^\s]+?)競輪\s*(\d+)R",d.get("page_text","")[:1200])
 if not m:continue
 venue=VENUES.get(m.group(1))
 if not venue:continue
 key=(d["race_date"],venue,str(int(m.group(2))))
 lookup[key].append((path,d))
race=collections.defaultdict(list)
for path in sorted(glob.glob("keirin_data/*_keirin.csv")):
 with open(path,encoding="utf-8-sig",newline="") as f:
  for row in csv.DictReader(f):
   key=(row.get("date",""),row.get("venue_slug",""),str(row.get("race_no","")).split(".")[0])
   if key in lookup:race[key].append(row)
report={"archive_races_with_venue":sum(map(len,lookup.values())),"matched_races":0,"complete_line_sbh_and_results":0,"examples":[],"unmatched_keys":[]}
out=Path("results/historical_joined");out.mkdir(parents=True,exist_ok=True)
for key,ds in lookup.items():
 rows=race.get(key,[])
 if not rows:
  report["unmatched_keys"].append(key)
  continue
 report["matched_races"]+=1
 for path,d in ds:
  if not d.get("line_and_sbh_complete"):continue
  ranks={str(r.get("rank","")).strip() for r in rows}
  if not {"1","2","3"}<=ranks:continue
  report["complete_line_sbh_and_results"]+=1
  payload={"key":key,"source":d["source_url"],"verified_pre_race":False,"line_groups":d["line_groups"],"riders":d["riders"],"results":[{"banum":r.get("banum"),"rank":r.get("rank"),"san_ren_tan":r.get("san_ren_tan")} for r in rows]}
  dest=out/(Path(path).stem+".json")
  dest.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
  if len(report["examples"])<8:report["examples"].append({"key":key,"file":str(dest)})
Path("results/historical_line_join_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False))
