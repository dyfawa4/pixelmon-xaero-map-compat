"""Generate native forks locally; payload contains only own code and BSD ASM."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,urllib.request,uuid,zipfile

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def payload_path():
    return Path(sys._MEIPASS)/'payload' if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]/'.cache/installer-payload'
def run(args):
    proc=subprocess.run(list(map(str,args)),capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,timeout=90)
    text=proc.stdout.decode('utf8','replace')+proc.stderr.decode('utf8','replace')
    if proc.returncode:raise RuntimeError(text[-5000:])
    return text
def java_major(java):
    text=run([java,'-version']);match=re.search(r'version "(\d+)(?:\.(\d+))?',text)
    if not match:raise ValueError('无法识别 Java 版本：'+text[:300])
    return int(match[2]) if match[1]=='1' else int(match[1])
def find_java():
    candidates=[]
    if os.environ.get('JAVA_HOME'):candidates.append(Path(os.environ['JAVA_HOME'])/'bin/java.exe')
    if shutil.which('java'):candidates.append(Path(shutil.which('java')))
    if os.name=='nt':
        for base in [Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'Java',Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'Eclipse Adoptium']:
            if base.is_dir():candidates+=sorted(base.glob('*/bin/java.exe'),reverse=True)
    for java in candidates:
        try:
            if java.is_file() and java_major(java)>=11:return java
        except Exception:pass
    return None

def install(output:Path,java:Path,originals:Path|None=None,progress=lambda text:None):
    output=output.expanduser().resolve()
    if output.name.lower()=='mods':raise ValueError('请选择单独的输出文件夹，不要直接写入游戏 mods。生成成功后再替换组件。')
    if java_major(java)<11:raise ValueError('生成组件需要 Java 11 或更高版本；游戏推荐使用 Java 11。')
    payload=payload_path();manifest=json.loads((payload/'manifest.json').read_text('utf8'))
    for name,digest in manifest['payloadHashes'].items():
        path=(payload/name).resolve()
        if not path.is_relative_to(payload.resolve()) or sha(path)!=digest:raise RuntimeError('安装器资源校验失败：'+name)
    output.mkdir(parents=True,exist_ok=True)
    work=output/('.build-'+uuid.uuid4().hex);work.mkdir()
    cache=output/'官方原版';cache.mkdir(exist_ok=True)
    inputs={}
    for component,entry in manifest['inputs'].items():
        progress('准备官方原版：'+entry['file'])
        path=(originals/entry['file']) if originals else cache/entry['file']
        if not path.is_file() and originals:raise ValueError('所选原版文件夹缺少：'+entry['file'])
        if not path.is_file():
            url=entry['url']
            if not url.startswith('https://cdn.modrinth.com/'):raise ValueError('非预期的原版来源')
            temporary=path.with_suffix('.download-'+uuid.uuid4().hex)
            try:
                request=urllib.request.Request(url,headers={'User-Agent':'PixelmonMapAdapter/1.0.0'})
                with urllib.request.urlopen(request,timeout=60) as source,temporary.open('xb') as dest:
                    total=0
                    while True:
                        block=source.read(256*1024)
                        if not block:break
                        total+=len(block)
                        if total>30_000_000:raise ValueError('下载超出预期大小')
                        dest.write(block)
                if sha(temporary)!=entry['sha256']:raise ValueError('官方原文件 SHA-256 不匹配，已停止：'+entry['file'])
                os.replace(temporary,path)
            finally:
                if temporary.exists():temporary.unlink()
        if sha(path)!=entry['sha256']:raise ValueError('原版版本或 SHA-256 不匹配，不能套用此补丁：'+path.name)
        inputs[component]=path
    native=payload/'adapter-payload.jar'
    classpath=os.pathsep.join(str(payload/n) for n in ['adapter-payload.jar','asm-9.6.jar','asm-tree-9.6.jar'])
    prepared=[]
    with zipfile.ZipFile(native) as own:
        for component in ['minimap','worldmap']:
            progress('生成定制原生组件：'+component);changes={}
            with zipfile.ZipFile(inputs[component]) as upstream:
                for target in manifest['patchTargets'][component]:
                    name=target+'.class';src=work/'upstream'/name;dst=work/'patched'/name
                    src.parent.mkdir(parents=True,exist_ok=True);src.write_bytes(upstream.read(name))
                    run([java,'-Dfile.encoding=UTF-8','-cp',classpath,'NativePatcher',src,dst]);changes[name]=dst.read_bytes()
                for name in own.namelist():
                    if name.startswith(component+'/'):changes[name[len(component)+1:]]=own.read(name)
                if component=='minimap':
                    coremods=json.loads(upstream.read('META-INF/coremods.json')) if 'META-INF/coremods.json' in upstream.namelist() else {}
                    if 'pixelmon_compass' in coremods:raise ValueError('所选文件已包含本项目补丁')
                    coremods['pixelmon_compass']='coremods/pixelmon_compass.js'
                    changes['META-INF/coremods.json']=json.dumps(coremods,indent=2).encode()
                entry=manifest['outputs'][component];destination=work/entry['file']
                with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dest:
                    for info in upstream.infolist():
                        if info.filename in changes:continue
                        if info.filename.upper().endswith(('.SF','.RSA','.DSA')):raise ValueError('不支持重签名的原版文件')
                        dest.writestr(info,upstream.read(info))
                    for name,data in sorted(changes.items()):
                        info=zipfile.ZipInfo(name,date_time=(2026,10,17,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;dest.writestr(info,data)
                if sha(destination)!=entry['sha256']:raise RuntimeError('输出未通过预期 SHA-256 校验：'+destination.name)
                prepared.append(destination)
    lib=work/inputs['lib'].name;shutil.copy2(inputs['lib'],lib);prepared.append(lib)
    for src in prepared:
        dst=output/src.name
        if dst.exists() and sha(dst)!=sha(src):raise ValueError('输出目录已有不同内容的同名文件，请选择新的空目录：'+dst.name)
    for src in prepared:shutil.copy2(src,output/src.name)
    receipt={'build':manifest['build'],'officialSources':manifest['inputs'],'outputs':[{'file':p.name,'sha256':sha(p)} for p in prepared]}
    (output/'组件生成清单.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),'utf8')
    progress('完成：两个定制原生地图组件及 XaeroLib，全部通过哈希校验。')
    return {'output':str(output),'files':[p.name for p in prepared]}
