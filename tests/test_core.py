import unittest,tempfile,copy,datetime as dt,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app,configuration,engine

class CoreTests(unittest.TestCase):
 def setUp(self):
  self.previous_capital=app.os.environ.get('RADAR_INITIAL_STOCK_CAPITAL')
  app.os.environ['RADAR_INITIAL_STOCK_CAPITAL']='30000' # synthetic test fixture
  self.tmp=tempfile.TemporaryDirectory();app.DATA=Path(self.tmp.name);app.DB=app.DATA/'test.db';self.c=copy.deepcopy(configuration.DEFAULT)
 def tearDown(self):
  self.tmp.cleanup()
  if self.previous_capital is None:app.os.environ.pop('RADAR_INITIAL_STOCK_CAPITAL',None)
  else:app.os.environ['RADAR_INITIAL_STOCK_CAPITAL']=self.previous_capital
 def trade(self,side,q,price,id,account='stocks_live'):
  return app.action('/api/trade',dict(account=account,id=id,side=side,quantity=q,price=price,fees=1,fx=1,time='2026-01-01T00:00:00+00:00',symbol='TEST',market='MY',currency='MYR',stop=8,target=15,mode='fixed',holding_bars=10,take_pct=50,trailing_pct=5))
 def test_config_rejects_two_percent(self):
  c=configuration.initial();c['stocks']['risk_pct']=2
  with self.assertRaises(ValueError):configuration.validate(c)
 def test_config_rejects_unimplemented(self):
  c=configuration.initial();c['stocks']['approval']=True
  with self.assertRaisesRegex(ValueError,'UNSUPPORTED'):configuration.validate(c)
 def test_config_revision(self):
  c=app.load()['config'];app.action('/api/config',{'config':copy.deepcopy(c)})
  with self.assertRaisesRegex(ValueError,'REVISION'):app.action('/api/config',{'config':c})
 def test_sizing_budget_and_cash(self):
  self.c.update(fees_verified=True,fee_source='test',fee_min=8,lot=100)
  r=engine.sizing(10,9.5,11.5,self.c,30000,30000)
  self.assertLessEqual(r['risk'],150);self.assertLessEqual(r['cost'],10500);self.assertGreater(r['rr'],1.5)
  self.assertEqual(engine.D(r['quantity'])%100,0)
 def test_unverified_fees_block(self):
  with self.assertRaisesRegex(ValueError,'FEES_UNVERIFIED'):engine.sizing(10,9,12,self.c,30000,30000)
 def test_crypto_default_risk_unconfirmed(self):self.assertFalse(configuration.initial()['crypto']['risk_confirmed'])
 def test_zero_capital_not_invented(self):self.assertIsNone(app.load()['accounts']['crypto_live']['capital'])
 def test_isolated_ledgers_partial_exits(self):
  self.trade('buy',100,10,'1');self.trade('sell',40,12,'2')
  s=app.load();p=app.portfolio(s['accounts']['stocks_live']);self.assertEqual(len(p['closed']),0);self.assertEqual(p['positions'][0]['quantity'],'60')
  self.assertEqual(app.portfolio(s['accounts']['stocks_paper'])['cash'],0)
  self.trade('sell',60,11,'3');p=app.portfolio(app.load()['accounts']['stocks_live'])
  self.assertEqual(len(p['closed']),1);self.assertAlmostEqual(p['closed'][0]['net'],137);self.assertAlmostEqual(p['cash'],30137)
 def test_idempotent_fill(self):
  self.trade('buy',100,10,'same');self.trade('buy',100,10,'same')
  self.assertEqual(len(app.load()['accounts']['stocks_live']['events']),1)
 def test_oversell_rollback(self):
  self.trade('buy',100,10,'1')
  with self.assertRaisesRegex(ValueError,'OVERSELL'):self.trade('sell',101,12,'2')
  self.assertEqual(len(app.load()['accounts']['stocks_live']['events']),1)
 def test_deposit_not_profit_or_drawdown(self):
  app.action('/api/flow',dict(account='stocks_live',amount=10000));p=app.portfolio(app.load()['accounts']['stocks_live']);self.assertEqual(p['pnl'],0);self.assertEqual(p['drawdown'],0)
 def test_drawdown_pause(self):
  self.trade('buy',1000,10,'1');app.action('/api/mark',dict(account='stocks_live',key='MY|TEST',price=8,fx=1))
  p=app.portfolio(app.load()['accounts']['stocks_live']);self.assertTrue(p['paused']);self.assertGreater(p['drawdown'],5)
 def test_csv_validation(self):
  good='time,open,high,low,close,volume,complete\n2026-01-01,10,11,9,10,100,true\n2026-01-02,10,12,9,11,100,false'
  self.assertEqual(len(engine.parse_csv(good)),2)
  with self.assertRaisesRegex(ValueError,'OHLC'):engine.parse_csv(good.replace('10,11,9,10','10,8,9,10'))
 def test_breakout_excludes_current_bar(self):
  rows=[]
  for i in range(100):rows.append(dict(time=(dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(days=i)).isoformat(),ts=1735689600+i*86400,open=10,high=10.5,low=9.5,close=10,volume=100,complete=True))
  rows[-1].update(open=10,high=13,low=9.5,close=12,volume=200)
  self.c.update(min_rvol=0,min_score=0,macd_enabled=False,ema_enabled=False,pullback_enabled=False)
  result=engine.analyze(rows,self.c,'T','test');self.assertIn('independent',result['groups'])
  rows[-1]['complete']=False;result=engine.analyze(rows,self.c,'T','test');self.assertNotIn('independent',result['groups'])
 def test_backup_hash_rejection(self):
  with self.assertRaisesRegex(ValueError,'BACKUP_HASH'):app.action('/api/restore',{'backup':{'state':app.load(),'sha256':'wrong'}})
 def test_restore_roundtrip(self):
  self.trade('buy',100,10,'1');s=app.load();raw=app.json.dumps(s,sort_keys=True,separators=(',',':'),ensure_ascii=False);wrapped={'state':s,'sha256':app.hashlib.sha256(raw.encode()).hexdigest()}
  app.action('/api/flow',{'account':'stocks_live','amount':100});app.action('/api/restore',{'backup':wrapped});self.assertEqual(app.portfolio(app.load()['accounts']['stocks_live'])['cash'],28999)
if __name__=='__main__':unittest.main()
