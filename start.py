#!/usr/bin/env python3
"""One-command local startup; browser opens only on the local loopback URL."""
import os,sys,subprocess,time,urllib.request,webbrowser
from pathlib import Path
root=Path(__file__).resolve().parent
port=os.environ.get('RADAR_PORT','8765')
proc=subprocess.Popen([sys.executable,str(root/'app.py')],cwd=root)
try:
 for _ in range(40):
  if proc.poll() is not None:raise SystemExit(proc.returncode)
  try:
   request=urllib.request.Request('http://127.0.0.1:'+port+'/api/health')
   token=os.environ.get('RADAR_TOKEN','')
   if token:request.add_header('Authorization','Bearer '+token)
   with urllib.request.urlopen(request,timeout=.5):break
  except Exception:time.sleep(.1)
 webbrowser.open('http://127.0.0.1:'+port+'/')
 print('Close this terminal or press Ctrl+C to stop. / 按 Ctrl+C 停止。',flush=True)
 proc.wait()
except KeyboardInterrupt:proc.terminate();proc.wait(timeout=5)
