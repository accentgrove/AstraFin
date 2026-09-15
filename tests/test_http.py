"""HTTP integration with synthetic fixtures, isolated from the user's ledger."""
import unittest,tempfile,threading,urllib.request,urllib.error,json,datetime as dt,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
class HTTPTests(unittest.TestCase):
 def setUp(self):
  self.previous_capital=app.os.environ.get('RADAR_INITIAL_STOCK_CAPITAL')
  app.os.environ['RADAR_INITIAL_STOCK_CAPITAL']='30000' # synthetic test fixture
  self.tmp=tempfile.TemporaryDirectory();app.DATA=Path(self.tmp.name);app.DB=app.DATA/'state.db';self.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.base='http://127.0.0.1:'+str(self.server.server_address[1])
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.tmp.cleanup()
  if self.previous_capital is None:app.os.environ.pop('RADAR_INITIAL_STOCK_CAPITAL',None)
  else:app.os.environ['RADAR_INITIAL_STOCK_CAPITAL']=self.previous_capital
 def request(self,path,data=None,csrf=True):
  headers={'Content-Type':'application/json'}
  if csrf:headers['X-CSRF']=app.CSRF
  req=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data else None,headers=headers)
  with urllib.request.urlopen(req) as r:return json.load(r)
 def test_csrf_required(self):
  with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/flow',{'account':'stocks_paper','amount':1000},False)
  self.assertEqual(e.exception.code,403)
 def test_full_paper_workflow(self):
  s=self.request('/api/state');c=s['config'];c['stocks'].update(sectors='',min_rvol=0,min_score=0,fees_verified=True,fee_source='SYNTHETIC TEST ONLY',fee_min=1)
  self.request('/api/config',{'config':c});self.request('/api/flow',{'account':'stocks_paper','amount':30000})
  lines=['time,open,high,low,close,volume,complete'];today=dt.datetime.now(dt.timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)
  for i in range(100):
   stamp=(today-dt.timedelta(days=99-i)).isoformat();last=i==99;lines.append(f'{stamp},10,{13 if last else 10.5},9.5,{12 if last else 10},{200 if last else 100},true')
  data=dict(asset='stocks',market='MY',symbol='QA.TEST',venue='SYNTHETIC',currency='MYR',timeframe='1d',csv='\n'.join(lines),sector='TEST',source='SYNTHETIC TEST ONLY')
  self.assertEqual(self.request('/api/import',data|{'preview':True})['rows'],100)
  self.assertEqual(len(self.request('/api/state')['datasets']),0)
  self.request('/api/import',data);scan=self.request('/api/scan',{'asset':'stocks'});self.assertEqual(scan['coverage'],1);self.assertEqual(len(scan['independent']),1)
  ident=scan['independent'][0]['dataset'];plan=self.request('/api/plan',{'account':'stocks_paper','dataset':ident,'entry':12,'stop':11.4,'target':13.8});self.assertGreater(float(plan['quantity']),0)
  trade=dict(account='stocks_paper',id='http-test',symbol='QA.TEST',market='MY',currency='MYR',side='buy',quantity=100,price=12,fees=1,fx=1,time=app.now(),stop=11.4,target=13.8,mode='combined',holding_bars=10,take_pct=50,trailing_pct=5)
  self.request('/api/trade',trade);self.request('/api/trade',trade)
  s=self.request('/api/state');self.assertEqual(len(s['accounts']['stocks_paper']['positions']),1);self.assertEqual(s['accounts']['stocks_live']['equity'],30000)
  self.request('/api/mark',{'account':'stocks_paper','key':'MY|QA.TEST','price':14,'fx':1,'stop':12.5})
  s=self.request('/api/state');h=s['accounts']['stocks_paper']['positions'][0];self.assertIn('TARGET',h['exit_review']['reasons']);self.assertEqual(h['exit_review']['suggested_exit_quantity'],50)
  backup=self.request('/api/backup');self.request('/api/restore',{'backup':backup});self.assertEqual(self.request('/api/state')['plans'][0]['status'],'EXPIRED')
  test=self.request('/api/backtest',{'dataset':ident,'start':(today-dt.timedelta(days=30)).date().isoformat()});self.assertFalse(test['sufficient'])
 def test_page_assets(self):
  for path in ['/','/app.js','/style.css','/favicon.svg']:
   with urllib.request.urlopen(self.base+path) as r:self.assertEqual(r.status,200);self.assertGreater(len(r.read()),100)
if __name__=='__main__':unittest.main()
