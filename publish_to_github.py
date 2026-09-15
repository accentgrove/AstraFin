#!/usr/bin/env python3
"""Prepare a review branch; --push explicitly publishes it using local Git credentials."""
import argparse,json,pathlib,shutil,subprocess,datetime,sys
ROOT=pathlib.Path(__file__).resolve().parent
REPO='https://github.com/accentgrove/AstraFin.git'
def run(*args,cwd=None):return subprocess.run(args,cwd=cwd,check=True,text=True)
def out(*args,cwd=None):return subprocess.check_output(args,cwd=cwd,text=True).strip()
def main():
 parser=argparse.ArgumentParser(description='Prepare the AstraFin review branch. Requires locally authenticated Git.')
 parser.add_argument('--push',action='store_true',help='Push the prepared review branch. Never merges into main.')
 parser.add_argument('--directory',default='AstraFin-review',help='New destination checkout directory.')
 args=parser.parse_args();dest=pathlib.Path(args.directory).resolve()
 if dest.exists():raise SystemExit('Destination exists; choose a new --directory. / 目标已存在，请选择新目录。')
 if not shutil.which('git'):raise SystemExit('Install Git first. / 请先安装Git。')
 run('git','clone',REPO,str(dest));branch='codex/astrafin-v0.1.0-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
 run('git','switch','-c',branch,cwd=dest)
 manifest=json.loads((ROOT/'source-manifest.json').read_text())
 # Refuse to overwrite newly added remote work. Existing repository baseline is preserved.
 for item in manifest:
  src=ROOT/item;target=dest/item
  if target.exists() and target.read_bytes()!=src.read_bytes():
   if item=='.gitignore':continue
   if item=='README.md' and target.read_text().strip()=='# AstraFin':continue
   raise SystemExit('Existing remote file requires review: '+item)
 for item in manifest:
  src=ROOT/item;target=dest/item;target.parent.mkdir(parents=True,exist_ok=True)
  if item=='.gitignore' and target.exists():
   current=target.read_text();target.write_text(current+'\n# AstraFin application exclusions\n'+src.read_text())
  else:shutil.copy2(src,target)
 run(sys.executable,'-m','unittest','discover','-s','tests','-v',cwd=dest)
 run('git','add','--',*manifest,cwd=dest)
 run('git','diff','--cached','--stat',cwd=dest)
 if not out('git','config','user.name',cwd=dest) or not out('git','config','user.email',cwd=dest):raise SystemExit('Configure your local Git author name/email, then commit. / 请先设置本地Git作者信息。')
 run('git','commit','-m','Add AstraFin bilingual stock and crypto radar initial release',cwd=dest)
 if args.push:
  run('git','push','-u','origin',branch,cwd=dest)
  print('Pushed review branch:',branch)
  print('Open a pull request in accentgrove/AstraFin; main was not modified.')
 else:
  print('Prepared locally:',dest)
  print('To publish after reviewing: git -C',str(dest),'push -u origin',branch)
 print('No credentials are read from this package or stored in it. / 本包不包含或保存登录凭据。')
if __name__=='__main__':main()
