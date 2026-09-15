"""Deterministic signals and Decimal sizing; no model-generated market data."""
import csv,io,math,hashlib,datetime as dt
from decimal import Decimal, ROUND_FLOOR
UTC=dt.timezone.utc
def number(v):
 n=float(v)
 if not math.isfinite(n): raise ValueError('FINITE_REQUIRED')
 return n
def timestamp(v):
 try:
  t=dt.datetime.fromisoformat(str(v).replace('Z','+00:00'))
  if t.tzinfo is None: t=t.replace(tzinfo=UTC)
  return t.timestamp()
 except Exception: raise ValueError('TIMESTAMP')
def parse_csv(content):
 reader=csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
 if not reader.fieldnames or not {'time','open','high','low','close','volume','complete'}<=set(reader.fieldnames): raise ValueError('CSV_COLUMNS')
 rows=[]
 for r in reader:
  bar={k:number(r[k]) for k in ['open','high','low','close','volume']}
  bar['time']=str(r['time']);bar['ts']=timestamp(r['time'])
  if min(bar[k] for k in ['open','high','low','close'])<=0 or bar['volume']<0 or bar['high']<max(bar['open'],bar['close'],bar['low']) or bar['low']>min(bar['open'],bar['close']): raise ValueError('OHLC')
  if r['complete'].lower() not in ['true','false','1','0']: raise ValueError('COMPLETE')
  bar['complete']=r['complete'].lower() in ['true','1'];rows.append(bar)
 if not 2<=len(rows)<=10000: raise ValueError('CSV_SIZE')
 if any(rows[i]['ts']>=rows[i+1]['ts'] for i in range(len(rows)-1)): raise ValueError('CSV_ORDER')
 return rows

def ema(vals,n):
 n=int(n);out=[];p=vals[0];a=2/(n+1)
 for x in vals: p=a*x+(1-a)*p;out.append(p)
 return out

def analyze(rows,c,symbol,source,now=None):
 now=now or dt.datetime.now(UTC).timestamp()
 bars=[r for r in rows if r['complete'] and r['ts']<=now]
 needed=max(c['history_min'],c['ema_slow']*3,c['macd_slow']*3,c['breakout_length']+2,c['volume_length']+2,c['trend_length'] if c['trend_filter'] else 0)
 if len(bars)<needed:return {'status':'INSUFFICIENT','needed':needed,'bars':len(bars),'groups':[]}
 vals=[r['close'] for r in bars];i=len(vals)-1;b=bars[-1]
 fast=ema(vals,c['ema_fast']);slow=ema(vals,c['ema_slow']);mf=ema(vals,c['macd_fast']);ms=ema(vals,c['macd_slow']);macd=[a-b for a,b in zip(mf,ms)];sig=ema(macd,c['macd_signal'])
 prior=bars[-int(c['volume_length'])-1:-1];av=sum(r['volume'] for r in prior)/len(prior);rv=b['volume']/av if av else 0
 turn=sum(r['volume']*r['close'] for r in prior)/len(prior)
 golden=[]
 for name,a,z,on in [('EMA',fast,slow,c['ema_enabled']),('MACD',macd,sig,c['macd_enabled'])]:
  if on and a[-1]>z[-1]:
   for j in range(i,max(0,i-int(c['fresh_bars'])),-1):
    if a[j]>z[j] and a[j-1]<=z[j-1]:golden.append({'model':name,'age':i-j});break
 independent=[]
 highest=max(r['high'] for r in bars[-int(c['breakout_length'])-1:-1])
 if c['breakout_enabled'] and b['close']>highest*(1+c['breakout_buffer']/100):independent.append({'model':'BREAKOUT','age':0})
 prev=bars[-2]
 if c['pullback_enabled'] and fast[-1]>slow[-1] and prev['low']<=slow[-2]*(1+c['pullback_tolerance']/100) and prev['close']>=slow[-2]*(1-c['pullback_tolerance']/100) and b['close']>prev['high']:independent.append({'model':'PULLBACK','age':0})
 trend=(not c['trend_filter']) or b['close']>sum(vals[-int(c['trend_length']):])/c['trend_length']
 score=min(100,round(30+(20 if fast[-1]>slow[-1] else 0)+min(rv,3)/3*30+(20 if golden and independent else 0)))
 reasons=[]
 if rv<c['min_rvol']:reasons.append('VOLUME_FILTER')
 if turn<c['min_turnover']:reasons.append('TURNOVER_FILTER')
 if not trend:reasons.append('TREND_FILTER')
 if score<c['min_score']:reasons.append('SCORE_FILTER')
 if c['win_gate']:reasons.append('UNVALIDATED')
 groups=[]
 if not reasons:
  if golden:groups.append('golden')
  if independent:groups.append('independent')
 ident=hashlib.sha256(f'{symbol}|{source}|{b["time"]}|{c}'.encode()).hexdigest()[:20]
 return dict(id=ident,status='CONFIRMED' if groups else 'NO_SIGNAL',groups=groups,models=golden+independent,score=score,rvol=round(rv,2),price=b['close'],time=b['time'],ts=b['ts'],bars=len(bars),reasons=reasons,fast=fast[-1],slow=slow[-1],macd=macd[-1],resonance=bool(golden and independent),validation='UNVALIDATED',source=source)

def D(n):return Decimal(str(n))
def fee(q,p,c):
 value=D(q)*D(p)
 return max(D(c['fee_min']),value*D(c['fee_rate'])/100)+value*D(c['levy_rate'])/100

def sizing(entry,stop,target,c,equity,cash,open_risk=0,drawdown=0,allocated=0,sector_allocated=0):
 entry,stop,target=map(D,[entry,stop,target])
 if not 0<stop<entry<target:raise ValueError('PRICE_ORDER')
 if not c['fees_verified']:raise ValueError('FEES_UNVERIFIED')
 if not c['risk_confirmed']:raise ValueError('RISK_UNCONFIRMED')
 if drawdown>=c['pause_pct']:raise ValueError('PAUSED')
 fx=D(c['fx_to_myr']);eq=D(equity);cash=D(cash);lot=D(c['lot']);slip=D(c['slippage_bps'])/10000
 risk=eq*D(c['risk_pct'])/100
 if drawdown>=c['warning_pct']:risk*=D(c['warning_multiplier'])
 remaining_dd=max(D(0),eq/(1-D(drawdown)/100)*(D(c['pause_pct'])-D(drawdown))/100)
 budget=max(D(0),min(risk,eq*D(c['total_risk_pct'])/100-D(open_risk),remaining_dd-D(open_risk)))
 cap=max(D(0),min(cash-eq*D(c['cash_reserve_pct'])/100,eq*D(c['concentration_pct'])/100-D(allocated),eq*D(c['sector_pct'])/100-D(sector_allocated)))
 def metrics(q):
  buy=q*entry*(1+slip)+fee(q,entry,c);sell=q*stop*(1-slip)-fee(q,stop,c);take=q*target*(1-slip)-fee(q,target,c)
  return buy*fx,(buy-sell)*fx,(take-buy)*fx
 hi=int((cap/(entry*fx*lot)).to_integral_value(rounding=ROUND_FLOOR)) if cap else 0;lo=0
 while lo<hi:
  mid=(lo+hi+1)//2;cost,loss,profit=metrics(lot*mid)
  if cost<=cap and loss<=budget:lo=mid
  else:hi=mid-1
 q=lot*lo
 if q<=0 or q*entry<D(c['min_notional']):raise ValueError('NO_SIZE')
 cost,loss,profit=metrics(q);rr=profit/loss if loss else D(0)
 if rr<=D(c['min_rr']):raise ValueError('RR_FILTER')
 return dict(quantity=str(q),cost=float(cost),risk=float(loss),profit=float(profit),rr=float(rr),budget=float(budget),entry=float(entry),stop=float(stop),target=float(target))

def backtest(rows,c,start):
 bars=[r for r in rows if r['complete'] and r['ts']<=dt.datetime.now(UTC).timestamp()];start_ts=timestamp(start);trades=[];position=None
 for i in range(1,len(bars)):
  b=bars[i]
  if position:
   p=position;reason=None;exitp=None
   if b['open']<=p['stop']:exitp=b['open'];reason='GAP_STOP'
   elif b['low']<=p['stop']:exitp=p['stop'];reason='STOP'
   elif b['open']>=p['target']:exitp=b['open'];reason='TARGET'
   elif b['high']>=p['target']:exitp=p['target'];reason='TARGET'
   elif i-p['index']>=c['holding_bars']:exitp=b['close'];reason='TIMEOUT'
   if exitp is not None:
    q=D(c['lot']);slip=D(c['slippage_bps'])/10000
    net=q*(D(exitp)*(1-slip)-D(p['entry'])*(1+slip))-fee(q,exitp,c)-fee(q,p['entry'],c)
    trades.append({'entry_time':p['time'],'exit_time':b['time'],'net':float(net),'reason':reason});position=None
   continue
  if b['ts']<start_ts:continue
  signal=analyze(bars[:i],c,'backtest','import')
  if signal['groups']:
   entry=b['open'];stop=entry*(1-c['stop_pct']/100);target=entry+(entry-stop)*c['target_r'];position=dict(entry=entry,stop=stop,target=target,time=b['time'],index=i)
   # Entry bar conflicts must also be resolved stop-first.
   if b['low']<=stop or b['high']>=target:
    exitp=stop if b['low']<=stop else target;q=D(c['lot']);slip=D(c['slippage_bps'])/10000
    net=q*(D(exitp)*(1-slip)-D(entry)*(1+slip))-fee(q,exitp,c)-fee(q,entry,c)
    trades.append(dict(entry_time=b['time'],exit_time=b['time'],net=float(net),reason='STOP' if b['low']<=stop else 'TARGET'));position=None
 wins=sum(t['net']>0 for t in trades);n=len(trades);z=1.96
 if n:
  p=wins/n;center=(p+z*z/(2*n))/(1+z*z/n);half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n);ci=[100*(center-half),100*(center+half)]
 else:ci=None
 return dict(trades=trades,count=n,win_rate=100*wins/n if n else None,confidence=ci,sufficient=n>=c['minimum_samples'],open_trade=position,net=sum(t['net'] for t in trades),fees_verified=c['fees_verified'],method='Fixed quantity / next open / stop-first / fixed target; not a portfolio backtest')
