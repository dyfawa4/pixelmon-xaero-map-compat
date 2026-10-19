"""Prepare own code + licensed ASM for local generation of the two native forks."""
from pathlib import Path
import hashlib,json,shutil,subprocess,urllib.request,zipfile,sys,uuid,os
r=Path(__file__).resolve().parents[1];out=r/'.cache/installer-payload';out.mkdir(parents=True,exist_ok=True)
if not (r/'dist/build-receipt.json').is_file():
    # Public checkouts can rebuild the desktop tool using the exact published
    # own-code payload, without redistributing game/Pixelmon compilation APIs.
    from payload_bundle import restore
    lock=json.loads((r/'config/payload.lock.json').read_text('utf8'))
    archive=r/'.cache'/('payload-download-'+uuid.uuid4().hex+'.zip')
    request=urllib.request.Request(lock['url'],headers={'User-Agent':'PixelmonMapAdapter-build/0.1.0'})
    with urllib.request.urlopen(request,timeout=60) as response:archive.write_bytes(response.read(5_000_001))
    restore(archive,out,lock['sha256']);archive.unlink()
    print('Restored verified published adapter payload');sys.exit(0)
receipt=json.loads((r/'dist/build-receipt.json').read_text('utf8'))
manifest={'format':1,'build':receipt['build'],'inputs':{},'outputs':receipt['outputs'],'patchTargets':receipt['patchTargets']}
for key,slug in [('minimap','xaeros-minimap'),('worldmap','xaeros-world-map'),('lib','xaerolib')]:
    reference=r/'evidence'/f'{slug}-download.json'
    if reference.is_file():
        data=json.loads(reference.read_text('utf8'))
        file=next(f for f in data['version']['files'] if f['filename']==receipt['inputs'][key]['file'])
        manifest['inputs'][key]={**receipt['inputs'][key],'url':file['url'],'project':'https://modrinth.com/mod/'+slug,'versionId':data['version']['id']}
    else:
        manifest['inputs'][key]=json.loads((r/'config/upstream.json').read_text('utf8'))['inputs'][key]
for name in ['asm-9.6.jar','asm-tree-9.6.jar']:shutil.copy2(r/'deps/build'/name,out/name)
classes=r/'.cache/installer-patcher';classes.mkdir(exist_ok=True)
cp=';'.join(str(out/name) for name in ['asm-9.6.jar','asm-tree-9.6.jar'])
javac=Path(os.environ['JAVA_HOME'])/'bin/javac.exe' if os.environ.get('JAVA_HOME') else shutil.which('javac') or r'C:\Program Files\Java\jdk-11\bin\javac.exe'
cmd=[str(javac),'--release','11','-encoding','UTF-8','-cp',cp,'-d',str(classes),str(r/'tools/NativePatcher.java')]
proc=subprocess.run(cmd,capture_output=True);assert proc.returncode==0,proc.stderr.decode('utf8','replace')
with zipfile.ZipFile(out/'adapter-payload.jar','w',zipfile.ZIP_DEFLATED) as own:
    own.write(classes/'NativePatcher.class','NativePatcher.class')
    for component,prefix in [('minimap','xaero/pixelmon/'),('worldmap','xaero/map/pixelmon/')]:
        with zipfile.ZipFile(r/'dist'/receipt['outputs'][component]['file']) as native:
            for name in native.namelist():
                if name.startswith(prefix) and name.endswith('.class'):own.writestr(component+'/'+name,native.read(name))
            own.writestr(component+'/META-INF/pixelmon-fork.json',native.read('META-INF/pixelmon-fork.json'))
        for f in (r/'resources'/component).rglob('*'):
            if f.is_file():own.write(f,component+'/'+f.relative_to(r/'resources'/component).as_posix())
license_path=r/'THIRD_PARTY_LICENSES/ASM-BSD-3-Clause.txt';license_path.parent.mkdir(exist_ok=True)
if not license_path.exists():
    with urllib.request.urlopen('https://asm.ow2.io/LICENSE.txt',timeout=30) as source:license_path.write_bytes(source.read())
shutil.copy2(license_path,out/license_path.name)
manifest['payloadHashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.name!='manifest.json' and p.is_file()}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf8')
config=r/'config';config.mkdir(exist_ok=True)
(config/'upstream.json').write_text(json.dumps({k:manifest[k] for k in ['format','build','inputs','outputs','patchTargets']},ensure_ascii=False,indent=2),'utf8')
print(json.dumps({'payload':str(out),'entries':manifest['payloadHashes']},ensure_ascii=False,indent=2))
