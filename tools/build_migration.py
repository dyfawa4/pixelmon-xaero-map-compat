"""Build a portable Windows GUI with dependencies isolated inside this project."""
from pathlib import Path
import hashlib,json,os,subprocess,sys

r=Path(__file__).resolve().parents[1]
deps=r/'.cache/migration-build-deps'
env=os.environ.copy();env['PYTHONPATH']=str(deps);env['PIP_CACHE_DIR']=str(r/'.cache/pip')
def run(args):
    p=subprocess.run(list(map(str,args)),env=env,cwd=r,capture_output=True)
    if p.returncode:raise RuntimeError(p.stdout.decode('utf8','replace')+p.stderr.decode('utf8','replace'))
    print(p.stdout.decode('utf8','replace')[-1600:])
if not (deps/'PyInstaller').is_dir():
    run([sys.executable,'-m','pip','install','--target',deps,'--disable-pip-version-check','pyinstaller==6.16.0'])
run([sys.executable,r/'tools/prepare_installer.py'])
out=r/'dist/坐标迁移工具';out.mkdir(parents=True,exist_ok=True)
run([sys.executable,'-m','PyInstaller','--noconfirm','--onefile','--windowed',
     '--name','地图坐标迁移','--distpath',out,'--workpath',r/'.cache/migration-pyinstaller',
     '--specpath',r/'.cache','--paths',r/'migration','--paths',r/'installer',
     '--add-data',str(r/'.cache/installer-payload')+';payload',r/'migration/地图坐标迁移.py'])
exe=out/'地图坐标迁移.exe'
run([exe,'--self-test'])
(out/'使用说明.md').write_bytes((r/'migration/使用说明.md').read_bytes())
record={'tool':'1.0.0','file':exe.name,'bytes':exe.stat().st_size,'sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
        'guiSelfTest':True,'python':sys.version,'pyinstaller':'6.16.0','sourceHashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (r/'migration').glob('*.py')}}
(out/'构建清单.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(record,ensure_ascii=False,indent=2))
