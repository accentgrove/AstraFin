#!/usr/bin/env python3
"""Local-first personal trading radar. SQLite persistence, no third-party packages."""
import os,json,sqlite3,uuid,datetime as dt,time,re,hashlib,secrets,threading,urllib.request,urllib.parse,io,csv,base64
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from decimal import Decimal
import configuration as config
import engine
ROOT=Path(__file__).parent
DATA=Path(os.environ.get('RADAR_DATA',ROOT/'data'));DB=DATA/'radar.sqlite3'
VERSION='0.1.0';CSRF=secrets.token_urlsafe(32);TOKEN=os.environ.get('RADAR_TOKEN','');LOCK=threading.RLock()

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def initial():
 # Optional local bootstrap value; never commit actual account balances.
 raw=os.environ.get('RADAR_INITIAL_STOCK_CAPITAL','')
 capital=engine.number(raw) if raw else None
 if capital is not None and capital<0:raise ValueError('CAPITAL_REQUIRED')
 accounts={}
 for asset in ['stocks','crypto']:
  for mode in ['live','paper']:
   key=asset+'_'+mode
   accounts[key]=dict(asset=asset,mode=mode,capital=capital if key=='stocks_live' else None,events=[],marks={},paused=False,high=(capital or 0) if key=='stocks_live' else 0)
 return dict(version=1,config=config.initial(),accounts=accounts,datasets=[],plans=[],audit=[],alerts=[])
def connect():
 DATA.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(DB,timeout=20);db.execute('PRAGMA journal_mode=WAL');db.execute('CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)');db.execute('INSERT OR IGNORE INTO state VALUES(1,?)',(json.dumps(initial()),));db.commit();return db
def load():
 with connect() as db:return json.loads(db.execute('SELECT data FROM state WHERE id=1').fetchone()[0])
def positive(v,zero=False):
 n=engine.number(v)
 if n<0 or (n==0 and not zero):raise ValueError('POSITIVE')
 return n
def symbol(v):
 if not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9._:/-]{1,40}',v):raise ValueError('SYMBOL')
 return v.upper()
def position_key(market,sym,venue=''):
 return market+(':'+venue if market=='CRYPTO' else '')+'|'+sym

def portfolio(a):
 cash=engine.D(a['capital'] or 0);pos={};closed=[];flows=engine.D(a['capital'] or 0)
 for e in a['events']:
  if e['kind']=='flow':cash+=engine.D(e['amount']);flows+=engine.D(e['amount']);continue
  key=position_key(e['market'],e['symbol'],e.get('venue',''));q=engine.D(e['quantity']);price=engine.D(e['price']);fx=engine.D(e['fx']);fees=engine.D(e['fees'])*fx;cost=q*price*fx
  if e['side']=='buy':
   cash-=cost+fees
   if key not in pos:pos[key]=dict(symbol=e['symbol'],market=e['market'],venue=e.get('venue',''),currency=e['currency'],sector=e.get('sector',''),qty=Decimal(0),cost=Decimal(0),realized=Decimal(0),entry=e['time'],settings=e['settings'],strategy=e.get('strategy','manual'))
   p=pos[key];p['qty']+=q;p['cost']+=cost+fees
  else:
   if key not in pos or q>pos[key]['qty']:raise ValueError('OVERSELL')
   p=pos[key];basis=p['cost']*q/p['qty'];p['realized']+=cost-fees-basis;p['cost']-=basis;p['qty']-=q;cash+=cost-fees
   if p['qty']==0:
    closed.append(dict(symbol=p['symbol'],entry=p['entry'],exit=e['time'],net=float(p['realized']),strategy=p['strategy']));del pos[key]
 holdings=[];equity=cash;openrisk=Decimal(0);incomplete=False
 for key,p in pos.items():
  mark=a['marks'].get(key)
  if not mark:incomplete=True;price=p['cost']/p['qty'];fx=Decimal(1);stamp=None
  else:price=engine.D(mark['price']);fx=engine.D(mark['fx']);stamp=mark['time']
  value=p['qty']*price*fx;equity+=value;stop=engine.D(mark.get('stop',p['settings']['stop']) if mark else p['settings']['stop']);risk=max(Decimal(0),value-p['qty']*stop*fx);openrisk+=risk
  holdings.append(dict(key=key,symbol=p['symbol'],market=p['market'],venue=p.get('venue',''),sector=p['sector'],currency=p['currency'],quantity=str(p['qty']),cost=float(p['cost']),value=float(value),pnl=float(value-p['cost']),realized=float(p['realized']),price=float(price),fx=float(fx),mark_time=stamp,entry=p['entry'],settings=(dict(p['settings']) | ({'stop':mark['stop']} if mark and 'stop' in mark else {})),strategy=p['strategy'],risk=float(risk)))
 high=max(float(equity),a['high']);dd=max(0,(high-float(equity))/high*100) if high else 0
 return dict(cash=float(cash),equity=float(equity),high=high,drawdown=dd,positions=holdings,closed=closed,flows=float(flows),pnl=float(equity-flows),open_risk=float(openrisk),paused=a['paused'],configured=a['capital'] is not None,incomplete=incomplete)
def account(s,key):
 if key not in s['accounts']:raise ValueError('ACCOUNT')
 return s['accounts'][key]
def mutate(fn):
 with LOCK,connect() as db:
  db.execute('BEGIN IMMEDIATE');s=json.loads(db.execute('SELECT data FROM state WHERE id=1').fetchone()[0]);result=fn(s)
  for a in s['accounts'].values():
   p=portfolio(a);a['high']=max(a['high'],p['high']);c=s['config'][a['asset']]
   if p['drawdown']>=c['pause_pct']:a['paused']=True
  db.execute('UPDATE state SET data=? WHERE id=1',(json.dumps(s,ensure_ascii=False,allow_nan=False),));return result

def audit(s,action,detail):s['audit'].append(dict(time=now(),action=action,detail=detail))
def public_state(s):
 summaries={k:portfolio(v) for k,v in s['accounts'].items()}
 for key,pf in summaries.items():
  a=s['accounts'][key];c=s['config'][a['asset']]
  for h in pf['positions']:
   h['exit_review']=exit_review(s,a,h,c)
 return dict(version=VERSION,csrf=CSRF,config=s['config'],fields=config.FIELDS,groups=config.GROUPS,accounts=summaries,datasets=[{k:v for k,v in d.items() if k!='rows'}|{'count':len(d['rows'])} for d in s['datasets']],audit=s['audit'][-100:],plans=s['plans'][-50:],github_status='SOURCE_REPOSITORY_CONFIGURED',capabilities={'manual':True,'csv_scan':True,'kraken_adapter':True,'stock_live_feed':False,'broker_execution':False,'scheduler':False,'portfolio_backtest':False})
def exit_review(s,a,h,c):
 settings=h['settings'];mode=settings['mode'];reasons=[];stale=not h['mark_time'] or time.time()-engine.timestamp(h['mark_time'])>c['max_age_hours']*3600
 mark=a['marks'].get(h['key'],{});trailing=mark.get('peak',h['price'])*(1-settings['trailing_pct']/100)
 effective=max(settings['stop'],trailing) if mode in ['trailing','combined'] else settings['stop']
 if h['price']<=effective:reasons.append('STOP')
 # A partial target is only actionable until cumulative exits reach its original allocation.
 entries=[e for e in a['events'] if e['kind']=='trade' and e['symbol']==h['symbol'] and e['market']==h['market'] and (a['asset']=='stocks' or e.get('venue','')==h['venue']) and engine.timestamp(e['time'])>=engine.timestamp(h['entry'])]
 bought=sum(float(e['quantity']) for e in entries if e['side']=='buy');sold=sum(float(e['quantity']) for e in entries if e['side']=='sell')
 remaining_target=max(0,bought*settings['take_pct']/100-sold)
 if mode in ['fixed','combined'] and h['price']>=settings['target'] and (mode=='fixed' or remaining_target>0):reasons.append('TARGET')
 ds=[d for d in s['datasets'] if d['asset']==a['asset'] and d['symbol']==h['symbol'] and d['market']==h['market'] and d['currency']==h['currency'] and (a['asset']=='stocks' or d['venue']==h['venue'])]
 elapsed=None;signal_stale=True
 if ds:
  d=max(ds,key=lambda d:d['rows'][-1]['ts']);bars=[r for r in d['rows'] if r['complete'] and r['ts']<=time.time()]
  elapsed=sum(r['ts']>engine.timestamp(h['entry']) for r in bars)
  signal_stale=not bars or time.time()-bars[-1]['ts']>c['max_age_hours']*3600
  if mode=='period' and elapsed>=settings['holding_bars'] and not signal_stale:reasons.append('TIMEOUT')
  if mode=='radar' and len(bars)>=c['ema_slow']*3 and not signal_stale:
   prices=[r['close'] for r in bars]
   if engine.ema(prices,c['ema_fast'])[-1]<=engine.ema(prices,c['ema_slow'])[-1]:reasons.append('TREND_EXIT')
 qty=float(h['quantity']) if any(x in reasons for x in ['STOP','TIMEOUT','TREND_EXIT']) or mode=='fixed' else min(float(h['quantity']),remaining_target)
 return dict(reasons=reasons,stale=stale,effective_stop=effective,elapsed_bars=elapsed,signal_stale=signal_stale,suggested_exit_quantity=qty,manual_only=True)

def scoped(c,d):
 if d['asset']=='stocks':
  if d['market'] not in c['enabled_markets'].split(','):return False
  watch=c['watchlist'].upper().replace(' ','').split(',')
  sectors=[x.strip().lower() for x in c['sectors'].split(',') if x.strip()]
  if sectors and d.get('sector','').lower() not in sectors and d['symbol'] not in watch:return False
 else:watch=c['pairs'].upper().replace(' ','').split(',')
 if any(watch) and d['symbol'] not in watch:return False
 return d['symbol'] not in c['excluded'].upper().replace(' ','').split(',')
def scan(s,asset):
 c=s['config'][asset];results=[];covered=0
 for d in s['datasets']:
  if d['asset']!=asset or not scoped(c,d):continue
  covered+=1;r=engine.analyze(d['rows'],c,d['symbol'],d['source']);r.update(dataset=d['id'],symbol=d['symbol'],market=d['market'],venue=d['venue'],currency=d['currency'],timeframe=d['timeframe'],sector=d.get('sector',''))
  if r.get('ts'):r['stale']=(time.time()-r['ts'])>c['max_age_hours']*3600
  results.append(r)
 results.sort(key=lambda r:r.get('score',0),reverse=True)
 out={g:[r for r in results if g in r['groups']][:int(c['max_results'])] for g in ['golden','independent']}
 return dict(**out,all=results,coverage=covered,scanned_at=now(),revision=s['config']['revision'])

def action(path,p):
 if path=='/api/config':
  def save(s):
   candidate=p['config'];config.validate(candidate)
   if candidate['revision']!=s['config']['revision']:raise ValueError('REVISION')
   old=s['config'];candidate['revision']+=1;s['config']=candidate
   for plan in s['plans']:plan['status']='EXPIRED'
   audit(s,'CONFIG',{'old_revision':old['revision'],'new_revision':candidate['revision']});return {'revision':candidate['revision']}
  return mutate(save)
 if path=='/api/import':
  rows=engine.parse_csv(p['csv'])
  if any(r['complete'] and r['ts']>time.time() for r in rows):raise ValueError('FUTURE_CANDLE')
  asset=p['asset'];market=p['market'];sym=symbol(p['symbol']);venue=symbol(p['venue']);tf=p['timeframe'];currency=symbol(p['currency'])
  if asset not in ['stocks','crypto'] or market not in ['MY','US','HK','CN','JP','SG','TW','CRYPTO'] or tf not in ['1d','4h']:raise ValueError('MARKET')
  if (asset=='crypto')!=(market=='CRYPTO') or (asset=='stocks' and tf!='1d'):raise ValueError('TIMEFRAME')
  ident=hashlib.sha256(f'{asset}|{market}|{sym}|{venue}|{currency}|{tf}'.encode()).hexdigest()[:20]
  result=dict(id=ident,asset=asset,market=market,symbol=sym,venue=venue,currency=currency,timeframe=tf,sector=str(p.get('sector',''))[:80],source='CSV · '+str(p.get('source','user supplied'))[:80],rows=rows,imported=now())
  if p.get('preview'):return {'rows':len(rows),'first':rows[0],'last':rows[-1],'id':ident}
  def commit(s):
   s['datasets']=[d for d in s['datasets'] if d['id']!=ident]+[result];audit(s,'IMPORT',{'id':ident,'count':len(rows)});return {'rows':len(rows)}
  return mutate(commit)
 if path=='/api/scan':return scan(load(),p['asset'])
 if path=='/api/plan':
  def plan(s):
   a=account(s,p['account']);c=s['config'][a['asset']];pf=portfolio(a)
   if a['paused']:raise ValueError('PAUSED')
   if not pf['configured']:raise ValueError('CAPITAL_REQUIRED')
   d=next((d for d in s['datasets'] if d['id']==p['dataset']),None)
   if not d or d['asset']!=a['asset'] or not scoped(c,d):raise ValueError('DATASET')
   if a['asset']=='stocks' and a['mode']=='live' and d['market'] not in c['live_markets'].split(','):raise ValueError('LIVE_MARKET')
   r=engine.analyze(d['rows'],c,d['symbol'],d['source'])
   if not r.get('groups'):raise ValueError('NO_SIGNAL')
   if time.time()-r['ts']>c['max_age_hours']*3600:raise ValueError('STALE')
   if d['currency']!=c['fx_currency']:raise ValueError('FX_CURRENCY')
   if len(pf['positions'])>=c['max_positions'] and not any(x['symbol']==d['symbol'] and x['market']==d['market'] for x in pf['positions']):raise ValueError('POSITION_LIMIT')
   if any(x['symbol']==d['symbol'] and x['market']==d['market'] for x in pf['positions']):raise ValueError('EXISTING_POSITION')
   # Include liquidation fees and modeled slippage in the open-risk budget.
   risk=0
   for x in pf['positions']:
    if not x['mark_time'] or time.time()-engine.timestamp(x['mark_time'])>c['max_age_hours']*3600:raise ValueError('STALE_MARK')
    risk+=x['risk']+float(engine.fee(x['quantity'],x['settings']['stop'],c))*x['fx']+x['value']*c['slippage_bps']/10000
   entry=positive(p.get('entry',r['price']));stop=positive(p.get('stop',entry*(1-c['stop_pct']/100)));target=positive(p.get('target',entry+(entry-stop)*c['target_r']))
   size=engine.sizing(entry,stop,target,c,pf['equity'],pf['cash'],risk,pf['drawdown'],0,sum(x['value'] for x in pf['positions'] if x['sector']==d['sector']))
   item=dict(id=uuid.uuid4().hex,account=p['account'],symbol=d['symbol'],market=d['market'],currency=d['currency'],signal_id=r['id'],config_revision=s['config']['revision'],created=now(),status='MANUAL_PLAN',snapshot=c,**size)
   s['plans'].append(item);audit(s,'PLAN',item['id']);return item
  return mutate(plan)
 if path=='/api/flow':
  def flow(s):
   a=account(s,p['account']);amount=engine.number(p['amount']);before=portfolio(a)
   if not amount or (amount<0 and -amount>before['cash']):raise ValueError('CASH')
   if a['capital'] is None:
    if amount<=0:raise ValueError('CAPITAL_REQUIRED')
    a['capital']=0
   a['events'].append(dict(id=uuid.uuid4().hex,kind='flow',amount=amount,time=now(),note=str(p.get('note',''))[:200]))
   a['high']=a['high']*(before['equity']+amount)/before['equity'] if before['equity']>0 else max(0,amount)
   audit(s,'FLOW',{'account':p['account'],'amount':amount});return {'ok':True}
  return mutate(flow)
 if path=='/api/trade':
  def trade(s):
   a=account(s,p['account']);c=s['config'][a['asset']]
   if not c['manual']:raise ValueError('MANUAL_DISABLED')
   if a['capital'] is None:raise ValueError('CAPITAL_REQUIRED')
   eid=str(p['id'])
   if any(e['id']==eid for e in a['events']):return {'duplicate':True}
   sym=symbol(p['symbol']);market=p['market'];currency=symbol(p['currency']);venue=symbol(p.get('venue','BURSA' if market=='MY' else 'UNKNOWN'))
   if a['asset']=='crypto' and venue=='UNKNOWN':raise ValueError('VENUE_REQUIRED')
   if (a['asset']=='crypto' and market!='CRYPTO') or (a['asset']=='stocks' and market not in ['MY','US','HK','CN','JP','SG','TW']):raise ValueError('MARKET')
   if p['side'] not in ['buy','sell']:raise ValueError('SIDE')
   price=positive(p['price']);q=positive(p['quantity']);fx=positive(p['fx']);fees=positive(p['fees'],True);stamp=p['time'];engine.timestamp(stamp)
   if engine.timestamp(stamp)>time.time()+60:raise ValueError('FUTURE_FILL')
   prev=[e for e in a['events'] if e['kind']=='trade']
   if prev and engine.timestamp(stamp)<engine.timestamp(prev[-1]['time']):raise ValueError('FILL_ORDER')
   settings=dict(stop=positive(p['stop']),target=positive(p['target']),mode=p['mode'],holding_bars=int(p['holding_bars']),take_pct=positive(p['take_pct']),trailing_pct=positive(p['trailing_pct']))
   if settings['mode'] not in ['radar','period','fixed','trailing','combined'] or not 1<=settings['take_pct']<=100 or not 0<settings['trailing_pct']<100:raise ValueError('EXIT_CONFIG')
   if a['asset']=='stocks' and not 3<=settings['holding_bars']<=20:raise ValueError('EXIT_CONFIG')
   if p['side']=='buy' and not settings['stop']<price<settings['target']:raise ValueError('PRICE_ORDER')
   before=portfolio(a);warnings=[]
   if p['side']=='buy':
    if a['paused']:warnings.append('PAUSED')
    if a['asset']=='stocks' and a['mode']=='live' and market not in c['live_markets'].split(','):warnings.append('LIVE_MARKET')
    if price*q*fx+fees*fx>before['cash']:warnings.append('CASH')
    if (price-settings['stop'])*q*fx>=before['equity']*.02:warnings.append('TRADE_RISK')
    if len(before['positions'])>=c['max_positions']:warnings.append('POSITION_LIMIT')
   e=dict(id=eid,kind='trade',side=p['side'],symbol=sym,market=market,venue=venue,currency=currency,price=price,quantity=str(engine.D(p['quantity'])),fx=fx,fees=fees,time=stamp,sector=str(p.get('sector',''))[:80],settings=settings,strategy=str(p.get('strategy','manual'))[:60],config_revision=s['config']['revision'],warnings=warnings)
   a['events'].append(e);portfolio(a) # oversell rolls back transaction
   a['marks'][position_key(market,sym,venue)]=dict(price=price,fx=fx,time=stamp)
   audit(s,'FILL',{'account':p['account'],'id':eid,'warnings':warnings});return {'ok':True,'warnings':warnings}
  return mutate(trade)
 if path=='/api/mark':
  def mark(s):
   a=account(s,p['account']);pf=portfolio(a);h=next((h for h in pf['positions'] if h['key']==p['key']),None)
   if not h:raise ValueError('POSITION')
   price=positive(p['price']);fx=positive(p['fx']);stamp=p.get('time') or now();engine.timestamp(stamp)
   previous=a['marks'].get(p['key'],{});a['marks'][p['key']]=dict(price=price,fx=fx,time=stamp,peak=max(price,previous.get('peak',h['price'])))
   if 'stop' in previous:a['marks'][p['key']]['stop']=previous['stop']
   # Stop may only tighten. Applied to surviving entry lots through the settings shared by replay.
   if p.get('stop'):
    stop=positive(p['stop'])
    if stop<h['settings']['stop']:raise ValueError('STOP_LOOSEN')
    a['marks'][p['key']]['stop']=stop
   audit(s,'MARK',{'key':p['key'],'price':price,'fx':fx,'old_stop':h['settings']['stop'],'new_stop':a['marks'][p['key']].get('stop',h['settings']['stop'])});return {'ok':True}
  return mutate(mark)
 if path=='/api/resume':
  def resume(s):
   a=account(s,p['account']);pf=portfolio(a)
   if pf['drawdown']>=s['config'][a['asset']]['pause_pct']:raise ValueError('PAUSED')
   if not str(p.get('reason','')).strip():raise ValueError('REASON')
   a['paused']=False;audit(s,'RESUME',{'account':p['account'],'reason':p['reason']});return {'ok':True}
  return mutate(resume)
 if path=='/api/backtest':
  s=load();d=next(d for d in s['datasets'] if d['id']==p['dataset']);return engine.backtest(d['rows'],s['config'][d['asset']],p['start'])
 if path=='/api/kraken':
  pair=symbol(p['pair']);quote=symbol(p['currency'])
  if not pair.endswith(quote):raise ValueError('FX_CURRENCY')
  interval=240 if p['timeframe']=='4h' else 1440;s=load();url='https://api.kraken.com/0/public/OHLC?'+urllib.parse.urlencode({'pair':pair,'interval':interval})
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'PersonalRadar/0.1'}),timeout=s['config']['crypto']['timeout']) as r:data=json.loads(r.read(3_000_000))
  except Exception:raise ValueError('PROVIDER_UNREACHABLE')
  if data.get('error'):raise ValueError('PROVIDER_PAIR')
  key=next(k for k in data['result'] if k!='last');rows=data['result'][key][:-1]
  csvtext='time,open,high,low,close,volume,complete\n'+'\n'.join(','.join([dt.datetime.fromtimestamp(r[0]+interval*60,dt.timezone.utc).isoformat(),r[1],r[2],r[3],r[4],r[6],'true']) for r in rows)
  return action('/api/import',dict(csv=csvtext,asset='crypto',market='CRYPTO',symbol=pair,venue='KRAKEN',currency=p['currency'],timeframe=p['timeframe'],source='Kraken public OHLC (last incomplete bar removed)',sector='Crypto'))
 if path=='/api/restore':
  wrapper=p['backup'];raw=json.dumps(wrapper['state'],sort_keys=True,separators=(',',':'),ensure_ascii=False)
  if hashlib.sha256(raw.encode()).hexdigest()!=wrapper['sha256']:raise ValueError('BACKUP_HASH')
  candidate=wrapper['state'];config.validate(candidate['config'])
  if candidate['version']!=1 or set(candidate)!=set(initial()):raise ValueError('BACKUP_SCHEMA')
  if set(candidate['accounts'])!=set(initial()['accounts']):raise ValueError('BACKUP_SCHEMA')
  for a in candidate['accounts'].values():portfolio(a)
  def restore(s):
   # Keep a SQLite snapshot before applying the logical backup.
   for plan in candidate['plans']:plan['status']='EXPIRED'
   candidate['config']['stocks']['approval']=False;candidate['config']['crypto']['approval']=False
   candidate['config']['revision']=s['config']['revision']+1;s.clear();s.update(candidate);audit(s,'RESTORE','Verified checksum; all plans expired');return {'ok':True}
  with connect() as db,sqlite3.connect(DATA/('before-restore-'+str(int(time.time()))+'.sqlite3')) as backup:db.backup(backup)
  return mutate(restore)
 raise ValueError('NOT_FOUND')

class Handler(BaseHTTPRequestHandler):
 def log_message(self,fmt,*args):pass
 def send(self,code,data,content='application/json; charset=utf-8'):
  body=json.dumps(data,ensure_ascii=False,allow_nan=False).encode() if content.startswith('application/json') else data
  self.send_response(code);self.send_header('Content-Type',content);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'");self.end_headers();self.wfile.write(body)
 def allowed(self):
  host=self.headers.get('Host','').split(':')[0]
  allowed=os.environ.get('RADAR_ALLOWED_HOSTS','localhost,127.0.0.1').split(',')
  if host not in allowed:self.send(403,{'error':'HOST'});return False
  if TOKEN:
   token=self.headers.get('Authorization','').removeprefix('Bearer ')
   if not secrets.compare_digest(token,TOKEN):self.send(401,{'error':'AUTH'});return False
  return True
 def do_GET(self):
  path=urllib.parse.urlparse(self.path).path
  if path.startswith('/api/'):
   if not self.allowed():return
   try:
    s=load()
    if path=='/api/state':return self.send(200,public_state(s))
    if path=='/api/health':return self.send(200,{'ok':True,'version':VERSION})
    if path=='/api/backup':
     raw=json.dumps(s,sort_keys=True,separators=(',',':'),ensure_ascii=False);return self.send(200,{'state':s,'sha256':hashlib.sha256(raw.encode()).hexdigest(),'created':now()})
    if path=='/api/dataset':
     ident=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)['id'][0];d=next(d for d in s['datasets'] if d['id']==ident);return self.send(200,d)
    return self.send(404,{'error':'NOT_FOUND'})
   except Exception:return self.send(400,{'error':'REQUEST'})
  files={'/':'index.html','/app.js':'app.js','/style.css':'style.css','/favicon.svg':'favicon.svg'}
  if path not in files:return self.send(404,b'Not found','text/plain')
  p=ROOT/'static'/files[path];content={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml'}[p.suffix]
  self.send(200,p.read_bytes(),content)
 def do_POST(self):
  if not self.allowed():return
  origin=self.headers.get('Origin')
  if origin and urllib.parse.urlparse(origin).netloc!=self.headers.get('Host'):return self.send(403,{'error':'ORIGIN'})
  if self.headers.get('X-CSRF')!=CSRF:return self.send(403,{'error':'CSRF'})
  try:
   length=int(self.headers.get('Content-Length','0'))
   if not 0<length<=12_000_000:raise ValueError('SIZE')
   p=json.loads(self.rfile.read(length));result=action(self.path,p);self.send(200,result)
  except (ValueError,KeyError,StopIteration,TypeError) as e:self.send(400,{'error':str(e) if isinstance(e,ValueError) else 'REQUEST'})
  except Exception:self.send(500,{'error':'SERVER'})
if __name__=='__main__':
 host=os.environ.get('RADAR_HOST','127.0.0.1');port=int(os.environ.get('RADAR_PORT','8765'))
 if host not in ['127.0.0.1','localhost'] and not TOKEN:raise SystemExit('Set RADAR_TOKEN before binding a non-loopback address.')
 connect().close();print(f'Personal Radar {VERSION} · http://{host}:{port}',flush=True);ThreadingHTTPServer((host,port),Handler).serve_forever()
