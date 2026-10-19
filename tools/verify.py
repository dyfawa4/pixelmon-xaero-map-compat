from pathlib import Path
import hashlib,json,subprocess,zipfile

r=Path(__file__).resolve().parents[1]
receipt=json.loads((r/'dist/build-receipt.json').read_text('utf8'))
outputs=[r/'dist'/receipt['outputs'][k]['file'] for k in ['minimap','worldmap']]
cp=';'.join(map(str,[*outputs,*(r/'deps/build').glob('asm*-9.6.jar'),*[p for p in (r/'deps').glob('*.jar') if not p.name.startswith(('xaerominimap-','xaeroworldmap-'))],*(r/'deps/build').glob('*.jar')]))
classes=r/'.cache/verification';classes.mkdir(exist_ok=True)
jdk=Path(r'C:\Program Files\Java\jdk-11\bin')
def run(args):
 p=subprocess.run(list(map(str,args)),capture_output=True);text=p.stdout.decode('utf8','replace')+p.stderr.decode('utf8','replace')
 if p.returncode:raise RuntimeError(text)
 return text
args=r/'.cache/verify-javac.args'
args.write_text('\n'.join('"'+str(s).replace('\\','/')+'"' for s in ['--release','11','-proc:none','-encoding','UTF-8','-classpath',cp,'-d',classes,r/'tests/BytecodeVerification.java']),'utf8')
print(run([jdk/'javac.exe','@'+str(args)]))
compass=next((r/'deps').glob('*ExplorersCompass*.jar'))
nature=next((r/'deps').glob('*NaturesCompass*.jar'))
result=run([jdk/'java.exe','-Xverify:all','-cp',str(classes)+';'+cp,'BytecodeVerification',*outputs,compass,nature])
print(result)
for component,out in zip(['minimap','worldmap'],outputs):
 assert hashlib.sha256(out.read_bytes()).hexdigest()==receipt['outputs'][component]['sha256']
 with zipfile.ZipFile(r/'deps'/receipt['inputs'][component]['file']) as original,zipfile.ZipFile(out) as modified:
  approved=set(receipt['outputs'][component]['changedEntries'])
  actual={n for n in modified.namelist() if n not in original.namelist() or modified.read(n)!=original.read(n)}
  assert approved==actual,(approved^actual)
  assert set(original.namelist())<=set(modified.namelist())
  assert len(modified.namelist())==len(set(modified.namelist()))
  assert modified.testzip() is None
(r/'evidence/offline-verification.json').write_text(json.dumps({'passed':True,'javaChecks':result.strip(),'approvedEntriesOnly':True,'allOriginalFilesRetained':True,'noDuplicateEntries':True,'crcsVerified':True,'outputs':receipt['outputs']},ensure_ascii=False,indent=2),'utf8')
print('PASS native fork entry boundaries, original retention, hashes and ZIP CRCs')
