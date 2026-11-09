import csv, itertools, math, random, re, statistics
from collections import defaultdict
from pathlib import Path

ROOT=Path('keirin_data'); OUT=Path('results'); OUT.mkdir(exist_ok=True)
FIELDS=['race_id','venue_slug','date','race_no','lineup','ni_sha_tan','san_ren_tan','san_ren_fuku','banum','player_name','pref','age','term','player_class','running_style','gear','race_score','rank','agari','finish_type','margin','win_lose']

def num(v,default=None):
 try:return float(str(v).replace(',',''))
 except:return default

def parse_payout(s,order,unordered=False):
 if not s:return None
 s=str(s).replace('－','-').replace('ー','-').replace('−','-')
 for m in re.finditer(r'(?<!\d)(\d)\s*[-=]\s*(\d)(?:\s*[-=]\s*(\d))?\s+([\d,]+)\s*円',s):
  parts=tuple(int(x) for x in m.groups()[:3] if x is not None)
  if (sorted(parts)==sorted(order) if unordered else parts==tuple(order)):
   return int(m.group(4).replace(',',''))
 return None

def load():
 races=defaultdict(list); files=sorted(ROOT.glob('????_??_keirin.csv'))
 for f in files:
  with f.open(encoding='utf-8-sig',newline='') as h:
   for r in csv.DictReader(h):
    if r.get('race_id') and r.get('date'):
     races[(r['date'],r['race_id'])].append(r)
 return races,files

def rank_feature(p,h,mode):
 name=p.get('player_name','').strip(); hist=h[name]; n,w,t2,t3=hist
 score=num(p.get('race_score'),80) or 80
 age=num(p.get('age'),35) or 35
 gear=num(p.get('gear'),3.9) or 3.9
 style=p.get('running_style','')
 prior=(w+1)/(n+7); top=(t3+3)/(n+9)
 if mode==0:return score
 if mode==1:return prior
 if mode==2:return .65*score/100+.35*prior
 if mode==3:return .45*score/100+.35*prior+.20*top
 if mode==4:return .65*score/100+.35*top
 if mode==5:return .45*score/100+.55*prior
 if mode==6:return score/100+.04*('逃' in style)-.02*('追' in style)
 if mode==7:return score/100+.04*('追' in style)-.02*('逃' in style)
 if mode==8:return score/100+.01*(40-age)/20
 if mode==9:return score/100+.02*(3.9-gear)
 return score/100

def make_candidates(players,h,mode,kind,depth):
 ranked=sorted(players,key=lambda p:rank_feature(p,h,mode),reverse=True)
 nums=[]
 for p in ranked:
  v=num(p.get('banum'))
  if v is not None and int(v) not in nums:nums.append(int(v))
 nums=nums[:depth]
 if len(nums)<3:return []
 if kind=='trifecta':return list(itertools.permutations(nums,3))
 if kind=='trio':return list(itertools.combinations(sorted(nums),3))
 if kind=='exacta':return list(itertools.permutations(nums,2))
 return []

def actual_order(players):
 finish=[]
 for p in players:
  n=num(p.get('banum')); r=num(p.get('rank'))
  if n is not None and r is not None and r>0:finish.append((r,int(n)))
 finish.sort()
 if len(finish)<3 or len(set(x[0] for x in finish[:3]))!=3:return None
 return tuple(n for _,n in finish[:3])

def evaluate_one(players,picks,kind,stake):
 actual=actual_order(players)
 if not actual:return None
 target=actual[:2] if kind=='exacta' else actual
 if kind=='trio':target=tuple(sorted(target))
 hit=target in picks
 # Payoffs are recorded per 100 yen ticket, not odds.
 field={'trifecta':'san_ren_tan','trio':'san_ren_fuku','exacta':'ni_sha_tan'}[kind]
 payout=parse_payout(players[0].get(field,''),target,kind=='trio') if hit else 0
 # If hit but the payout is unparseable, mark the race unverifiable.
 if hit and payout is None:return None
 return {'stake':len(picks)*stake,'return':payout*(stake/100) if hit else 0,'hit':int(hit),'bets':len(picks)}

def stats(records):
 if not records:return {'n':0,'roi':None,'profit':None,'hit_rate':None,'max_drawdown':None}
 stake=sum(x['stake'] for x in records); returned=sum(x['return'] for x in records)
 equity=peak=dd=0
 for x in records:
  equity+=x['return']-x['stake'];peak=max(peak,equity);dd=max(dd,peak-equity)
 return {'n':len(records),'roi':returned/stake if stake else None,'profit':round(returned-stake),'hit_rate':sum(x['hit'] for x in records)/len(records),'max_drawdown':round(dd),'stake':round(stake),'returned':round(returned)}

def main():
 races,files=load(); print('Files:',len(files),'Races:',len(races))
 if not races:raise SystemExit('No monthly CSV files in keirin_data/')
 dates=sorted(set(d for d,_ in races)); n=len(dates)
 if n<30:raise SystemExit('Need at least 30 distinct racing dates for time-separated evaluation')
 train_end=dates[max(0,int(n*.6)-1)]; val_end=dates[max(0,int(n*.8)-1)]
 hist=defaultdict(lambda:[0,0,0,0]); entries=[]
 for date in dates:
  daily=[(key,players) for key,players in races.items() if key[0]==date]
  for (d,rid),players in daily:
   if not actual_order(players):continue
   entries.append((date,rid,players,{mode:sorted(players,key=lambda p:rank_feature(p,hist,mode),reverse=True) for mode in range(10)}))
  # update only AFTER all predictions for a date, avoiding same-day leakage
  for _,players in daily:
   for p in players:
    name=p.get('player_name','').strip();rank=num(p.get('rank'))
    if name and rank is not None and rank>0:
     h=hist[name];h[0]+=1;h[1]+=rank==1;h[2]+=rank<=2;h[3]+=rank<=3
 del hist
 strategies=[]
 # 10 scoring modes x 3 ticket types x 4 depths x 2 budget caps = 240 scenarios
 for mode,kind,depth,cap in itertools.product(range(10),('trifecta','trio','exacta'),(3,4,5,6),(1000,3000)):
  strategies.append((mode,kind,depth,cap))
 outputs=[]; splits={'train':[],'validation':[],'test':[]}
 for date,rid,players,ranked in entries:
  split='train' if date<=train_end else 'validation' if date<=val_end else 'test'
  splits[split].append((date,rid,players,ranked))
 print('Chronological date splits:',len(splits['train']),len(splits['validation']),len(splits['test']))
 def run(strategy,part):
  mode,kind,depth,cap=strategy; rec=[]; missing=0
  for date,rid,players,ranked in splits[part]:
   nums=[]
   for p in ranked[mode][:depth]:
    x=num(p.get('banum'))
    if x is not None and int(x) not in nums:nums.append(int(x))
   if len(nums)<depth:continue
   picks=(list(itertools.permutations(nums,3)) if kind=='trifecta' else list(itertools.combinations(sorted(nums),3)) if kind=='trio' else list(itertools.permutations(nums,2)))
   if len(picks)*100>cap:continue
   x=evaluate_one(players,picks,kind,100)
   if x is None:missing+=1;continue
   rec.append(x)
  return stats(rec),missing
 # select only using training; validation checks selection, test remains untouched
 train=[]
 for s in strategies:
  st,miss=run(s,'train')
  if st['n']>=30:train.append((s,st,miss))
 train.sort(key=lambda x:(x[1]['roi'] if x[1]['roi'] is not None else -1),reverse=True)
 candidates=train[:min(20,len(train))]
 validated=[]
 for s,t,miss in candidates:
  v,vm=run(s,'validation')
  if v['n']>=10:validated.append((s,t,v,miss,vm))
 validated.sort(key=lambda x:(x[2]['roi'] if x[2]['roi'] is not None else -1),reverse=True)
 chosen=validated[0] if validated else None
 with (OUT/'optimization_summary.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['mode','ticket','depth','budget_cap','train_n','train_roi','validation_n','validation_roi','test_n','test_roi','test_profit','test_hit_rate','test_max_drawdown','unverifiable_hits'])
  for s,t,v,tm,vm in validated:
   test,miss=run(s,'test') if chosen and s==chosen[0] else ({},0)
   w.writerow([*s,t['n'],t['roi'],v['n'],v['roi'],test.get('n',''),test.get('roi',''),test.get('profit',''),test.get('hit_rate',''),test.get('max_drawdown',''),tm+vm+miss])
 print('Scenarios:',len(strategies),'train eligible:',len(train),'validation eligible:',len(validated))
 if chosen:
  s,t,v,_,_=chosen; test,miss=run(s,'test')
  print('SELECTED using validation:',s,'TRAIN:',t,'VALIDATION:',v,'UNTOUCHED TEST:',test,'missing payouts:',miss)
 else:print('INSUFFICIENT VERIFIED DATA: cannot select a reliable strategy')
 print('Output: results/optimization_summary.csv')

if __name__=='__main__':main()
