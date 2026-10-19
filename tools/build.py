"""Build native Xaero forks from official exact-version binary inputs and local source.

All generated artifacts stay inside this project. Original instances are read-only.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, zipfile, uuid

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0-dev3'
TARGETS = {
    'minimap': ['xaero/hud/minimap/radar/icon/cache/id/variant/RadarIconVariantHandler',
                'xaero/hud/minimap/radar/icon/definition/RadarIconDefinitionManager',
                'xaero/hud/minimap/radar/render/element/RadarRenderProvider',
                'xaero/common/settings/ModSettings'],
    'worldmap': ['xaero/map/mods/minimap/element/MinimapElementRendererWrapper'],
}

def run(args):
    result = subprocess.run([str(x) for x in args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:text = result.stdout.decode('utf-8')
    except UnicodeDecodeError:text=result.stdout.decode('gb18030',errors='replace')
    if result.returncode:
        raise RuntimeError(text)
    return text

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--jdk', type=Path, default=Path(r'C:\Program Files\Java\jdk-11'))
    p.add_argument('--base-build', type=Path, default=ROOT.parent/'重铸内容回迁/.cache/last-build.json')
    a=p.parse_args()
    javac, java = a.jdk/'bin/javac.exe', a.jdk/'bin/java.exe'
    assert 'javac 11.' in run([javac,'-version']), 'JDK 11 is required'
    # Bootstrap path is an existing, known SRG/Forge compile API, never a writable target.
    libraries=[]
    dependency_manifest=ROOT/'deps/build-manifest.json'
    if dependency_manifest.exists():
        frozen=json.loads(dependency_manifest.read_text('utf8'))
        for item in frozen:
            dst=ROOT/'deps/build'/item['file']
            assert dst.is_file() and digest(dst)==item['sha256'], 'Frozen build dependency missing/changed: '+str(dst)
            libraries.append(dst)
    else:
        base=json.loads(a.base_build.read_text('utf-8-sig'))
        frozen=[]
        for path in base['classpath'].split(';'):
            src=Path(path)
            if not src.is_file(): continue
            # Keep only the game/Forge/libraries; no unrelated gameplay addon dependencies.
            if '/mods/' in src.as_posix() and 'Pixelmon-1.16.5' not in src.name: continue
            dst=ROOT/'deps/build'/src.name
            dst.parent.mkdir(parents=True,exist_ok=True)
            if not dst.exists() or digest(src)!=digest(dst):shutil.copy2(src,dst)
            libraries.append(dst)
            frozen.append({'file':src.name,'sha256':digest(dst),'bootstrapSource':str(src)})
        dependency_manifest.write_text(json.dumps(frozen,ensure_ascii=False,indent=2),'utf8')
    upstreams={}
    for component, slug in [('minimap','xaeros-minimap'),('worldmap','xaeros-world-map'),('lib','xaerolib')]:
        reference=ROOT/'evidence'/f'{slug}-download.json'
        if reference.is_file():metadata=json.loads(reference.read_text('utf8'))
        else:
            locked=json.loads((ROOT/'config/upstream.json').read_text('utf8'))['inputs'][component]
            metadata={'sha256':locked['sha256'],'version':{'files':[{'filename':locked['file']}]}}
        file=next((f for f in metadata['version']['files'] if f.get('primary')),metadata['version']['files'][0])
        jar=ROOT/'deps'/file['filename']
        assert digest(jar)==metadata['sha256'], 'Official input hash mismatch'
        upstreams[component]=jar
    cp=';'.join(map(str,[*upstreams.values(),*libraries]))
    classes=ROOT/'.cache'/('build-'+uuid.uuid4().hex)/'classes';classes.mkdir(parents=True,exist_ok=True)
    srcs=sorted((ROOT/'src/minimap').rglob('*.java'))+sorted((ROOT/'src/worldmap').rglob('*.java'))
    argsfile=ROOT/'.cache/javac.args'
    # javac argument files use Java escaping; forward slashes avoid Windows escapes.
    args=['--release','11','-proc:none','-encoding','UTF-8','-classpath',cp,'-d',str(classes),*map(str,srcs),str(ROOT/'tools/NativePatcher.java')]
    argsfile.write_text('\n'.join('"'+s.replace('\\','/')+'"' for s in args),'utf8')
    print(run([javac,'@'+str(argsfile)]),end='')
    receipt={'build':VERSION,'inputs':{},'outputs':{},'patchTargets':TARGETS,'java':run([java,'-version']).strip()}
    for component, targets in TARGETS.items():
        upstream=upstreams[component]
        changed={}
        with zipfile.ZipFile(upstream) as z:
            for target in targets:
                name=target+'.class';source=ROOT/'.cache/upstream'/name;output=ROOT/'.cache/patched'/name
                source.parent.mkdir(parents=True,exist_ok=True);source.write_bytes(z.read(name))
                print(run([java,'-cp',str(classes)+';'+cp,'NativePatcher',source,output]).strip())
                changed[name]=output.read_bytes()
            for file in (classes/('xaero/pixelmon' if component=='minimap' else 'xaero/map/pixelmon')).rglob('*.class'):
                changed[file.relative_to(classes).as_posix()]=file.read_bytes()
            for file in (ROOT/'resources'/component).rglob('*'):
                if file.is_file():changed[file.relative_to(ROOT/'resources'/component).as_posix()]=file.read_bytes()
            if component=='minimap':
                coremods=json.loads(z.read('META-INF/coremods.json')) if 'META-INF/coremods.json' in z.namelist() else {}
                assert 'pixelmon_compass' not in coremods
                coremods['pixelmon_compass']='coremods/pixelmon_compass.js'
                changed['META-INF/coremods.json']=json.dumps(coremods,indent=2).encode()
            changed['META-INF/pixelmon-fork.json']=json.dumps({'build':VERSION,'component':component,'upstreamSha256':digest(upstream),'source':'src/'+component,'originalApiVersionPreserved':True},indent=2).encode()
            dest=ROOT/'dist'/(upstream.stem+'-pixelmon-'+VERSION+'.jar')
            dest.parent.mkdir(exist_ok=True)
            with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as out:
                for info in z.infolist():
                    name=info.filename
                    if name in changed:continue
                    assert not name.upper().endswith(('.SF','.RSA','.DSA')), 'Signed upstream requires a different local build procedure'
                    out.writestr(info,z.read(info))
                for name,blob in sorted(changed.items()):
                    info=zipfile.ZipInfo(name,date_time=(2026,10,17,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                    out.writestr(info,blob)
        with zipfile.ZipFile(dest) as z:assert z.testzip() is None
        receipt['inputs'][component]={'file':upstream.name,'sha256':digest(upstream)}
        receipt['outputs'][component]={'file':dest.name,'sha256':digest(dest),'changedEntries':list(changed)}
    receipt['inputs']['lib']={'file':upstreams['lib'].name,'sha256':digest(upstreams['lib'])}
    (ROOT/'dist/build-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(receipt['outputs'],ensure_ascii=False,indent=2))

if __name__=='__main__':main()
