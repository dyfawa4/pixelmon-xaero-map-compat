"""JourneyMap 5.x JSON -> Xaero 26.6 native waypoint files. Standard library only.

The source is read-only. Plans are reviewed before apply; every target change is
staged, hashed and backed up. Restore refuses to erase changes made since import.
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass, field
from contextlib import contextmanager
from datetime import datetime
import hashlib, json, os, re, uuid

VERSION = '1.0.0'
HEADER = '# JourneyMap 坐标点迁移工具 1.0.0\n# 原旅行地图数据未修改\n'
PALETTE = [0x000000,0x0000aa,0x00aa00,0x00aaaa,0xaa0000,0xaa00aa,
           0xffaa00,0xaaaaaa,0x555555,0x5555ff,0x55ff55,0x55ffff,
           0xff0000,0xff55ff,0xffff55,0xffffff,0xc74ebd,0x3ab3da,
           0x80c71f,0xf38baa,0x835432]
ALIASES = {'0':'minecraft:overworld','overworld':'minecraft:overworld',
           '-1':'minecraft:the_nether','the_nether':'minecraft:the_nether',
           'DIM-1':'minecraft:the_nether','1':'minecraft:the_end',
           'the_end':'minecraft:the_end','DIM1':'minecraft:the_end',
           'ultra_space':'pixelmon:ultra_space'}
RESOURCE = re.compile(r'^[a-z0-9_.-]+:[a-z0-9_./-]+$')

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def fingerprint(path: Path) -> str | None:
    return sha(path.read_bytes()) if path.is_file() else None

def contained(path: Path, root: Path) -> Path:
    path, root = path.resolve(), root.resolve()
    if not path.is_relative_to(root):
        raise ValueError('路径超出所选目录：' + str(path))
    return path

def dimension_id(value) -> str:
    text = str(value)
    text = ALIASES.get(text, text)
    if not RESOURCE.fullmatch(text) or '..' in text or '/' in text:
        raise ValueError('无法安全识别维度，请检查源文件 dimensions 字段：' + str(value))
    return text

def dim_folder(dim: str) -> str:
    dim = dimension_id(dim)
    known = {'minecraft:overworld':'dim%0','minecraft:the_nether':'dim%-1','minecraft:the_end':'dim%1'}
    return known.get(dim, 'dim%' + dim.replace(':', '$'))

def coordinate(value, optional=False):
    if value is None and optional: return '~'
    if isinstance(value, bool) or not re.fullmatch(r'-?\d+', str(value)):
        raise ValueError('坐标必须是整数：' + str(value))
    number = int(value)
    if not -2147483648 <= number <= 2147483647: raise ValueError('坐标超出整数范围')
    return str(number)

def clean_name(value) -> str:
    text = str(value).replace('§§', '§ §')
    return ''.join(c if c >= ' ' and c not in '\x7f\u2028\u2029' else ' ' for c in text).strip() or '未命名坐标点'

def escape(text: str) -> str:
    return text.replace(':', '§§')

@dataclass(frozen=True)
class Point:
    source: str
    dimension: str
    name: str
    x: str
    y: str
    z: str
    color: int
    disabled: bool
    death: bool

    @property
    def key(self): return (self.name, self.x, self.y, self.z, self.death)

    def line(self):
        # OLD_DEATH preserves every historical death without making it the active target.
        return ':'.join(['waypoint', escape(self.name), escape(self.name[0]), self.x,self.y,self.z,
                         str(self.color),str(self.disabled).lower(),'2' if self.death else '0',
                         'gui.xaero_default','false','0','GLOBAL' if self.death else 'LOCAL','false'])

def read_point(path: Path) -> list[Point]:
    if path.stat().st_size > 2_000_000: raise ValueError('坐标点 JSON 过大')
    data = json.loads(path.read_text('utf-8-sig'))
    if not isinstance(data, dict): raise ValueError('需要 JourneyMap 单个坐标点 JSON 对象')
    dims = data.get('dimensions')
    if not isinstance(dims, list) or not dims: raise ValueError('缺少非空 dimensions 数组，不能猜测世界维度')
    dims = sorted({dimension_id(d) for d in dims})
    rgb = []
    for c in 'rgb':
        v = data.get(c,255)
        if isinstance(v,bool) or not isinstance(v,int) or not 0 <= v <= 255: raise ValueError('颜色必须是 0–255 整数')
        rgb.append(v)
    color = min(range(len(PALETTE)), key=lambda n:sum((rgb[i]-((PALETTE[n]>>(16-8*i))&255))**2 for i in range(3)))
    kind = str(data.get('type','Normal')).lower()
    death = kind in ('death','deathpoint','death_point') or 'death' in str(data.get('icon','')).lower()
    if kind not in ('normal','death','deathpoint','death_point') and not death: raise ValueError('未知坐标点类型：' + kind)
    enabled = data.get('enable',True)
    if not isinstance(enabled,bool): raise ValueError('enable 必须为 true/false')
    name = clean_name(data.get('name',path.stem))
    xyz = [coordinate(data.get(k),k=='y') for k in 'xyz']
    return [Point(str(path),d,name,*xyz,color,not enabled,death) for d in dims]

def source_files(world: Path) -> list[Path]:
    folder = world if world.name == 'waypoints' else world/'waypoints'
    if not folder.is_dir(): raise ValueError('所选旅行地图世界没有 waypoints 文件夹')
    files = sorted(folder.glob('*.json'))
    for f in files: contained(f,folder)
    return files

def discover_sources(root: Path) -> list[Path]:
    root = root.expanduser().resolve()
    if root.name == 'waypoints' and root.is_dir(): return [root.parent]
    if (root/'waypoints').is_dir(): return [root]
    bases = [root,root/'.minecraft']
    for base in list(bases):
        if (base/'versions').is_dir(): bases += [p for p in (base/'versions').iterdir() if p.is_dir()]
    results = set()
    for base in bases:
        for data in [base/'journeymap/data',base/'data',base]:
            for mode in ['sp','mp']:
                if not (data/mode).is_dir(): continue
                for waypoints in (data/mode).glob('*/waypoints'):
                    if waypoints.is_dir(): results.add(waypoints.parent.resolve())
    return sorted(results)

def validate_target(target: Path) -> Path:
    target = target.resolve()
    if target.parent.name != 'minimap' or target.parent.parent.name != 'xaero' or not target.is_dir():
        raise ValueError('目标必须是本定制版已生成的 xaero/minimap/<世界或服务器> 目录。请先进入对应世界一次，再退出游戏。')
    if target.is_symlink(): raise ValueError('目标不能是符号链接')
    return target

def discover_targets(root: Path) -> list[Path]:
    root = root.expanduser().resolve()
    if root.parent.name == 'minimap' and root.parent.parent.name == 'xaero' and root.is_dir(): return [root]
    bases = [root,root/'.minecraft']
    for base in list(bases):
        if (base/'versions').is_dir(): bases += [p for p in (base/'versions').iterdir() if p.is_dir()]
    results = set()
    for base in bases:
        for data in [base/'xaero/minimap',base if base.name=='minimap' else base/'__no_candidate__']:
            if not data.is_dir(): continue
            for world in data.iterdir():
                if world.is_dir() and world.name != 'backup' and ((world/'config.txt').is_file() or any(world.glob('dim%*'))): results.add(world.resolve())
    return sorted(results)

def destinations(target: Path, dim: str) -> list[str]:
    folder = target/dim_folder(dim)
    # Existing subworlds are explicit options, never selected by guessing a server.
    values = {str(p.relative_to(target).as_posix()) for p in folder.rglob('waypoints.txt')} if folder.exists() else set()
    values.add(dim_folder(dim)+'/waypoints.txt')
    return sorted(values)

def existing_keys(blob: bytes) -> set[tuple]:
    text = blob.decode('utf-8-sig')
    keys=set()
    for no,line in enumerate(text.splitlines(),1):
        if not line.lower().startswith('waypoint:'): continue
        a=line.split(':')
        if len(a)<10: raise ValueError('目标路径点文件格式错误，第 '+str(no)+' 行；停止写入')
        x,y,z=coordinate(a[3]),coordinate(a[4],True) if a[4]!='~' else '~',coordinate(a[5])
        typ=int(a[8])
        if typ not in range(4): raise ValueError('目标路径点类型超出范围')
        keys.add((a[1].replace('§§',':'),x,y,z,typ in (1,2)))
    return keys

@dataclass
class Plan:
    source: Path
    target: Path
    points: list[Point]
    rows: list[dict]
    issues: list[str]
    sources: dict[str,str]
    before: dict[str,str|None]
    writes: dict[str,bytes]
    mappings: dict[str,str]

    def summary(self):
        return {'tool':VERSION,'source':str(self.source),'target':str(self.target),
                'add':sum(r['status']=='新增' for r in self.rows),
                'duplicates':sum(r['status']=='已存在' for r in self.rows),
                'excluded':sum(r['status']=='不导入' for r in self.rows),
                'deathpoints':sum(r['status']=='新增' and r['death'] for r in self.rows),
                'filesToChange':len(self.writes),'issues':self.issues,'mappings':self.mappings,'rows':self.rows}

def make_plan(source: Path, target: Path, mappings: dict[str,str]|None=None, include_death=True) -> Plan:
    source,target=source.resolve(),validate_target(target)
    points=[];issues=[];sources={}
    for f in source_files(source):
        sources[str(f)]=fingerprint(f)
        try: points.extend(read_point(f))
        except (ValueError,UnicodeError,KeyError,TypeError) as error: issues.append(f.name+'：'+str(error))
    mappings=dict(mappings or {})
    for dim in sorted({p.dimension for p in points}):
        if dim not in mappings:
            choices=destinations(target,dim)
            if len(choices)>1: raise ValueError(dim+' 存在多个 Xaero 子世界，请在维度对应中明确选择目标')
            mappings[dim]=choices[0]
    before={};writes={};texts={};keys={};rows=[];used={}
    for dim,rel in mappings.items():
        if rel == '': continue
        path=contained(target/rel,target)
        if path.name!='waypoints.txt' or path.relative_to(target).parts[0]!=dim_folder(dim):
            raise ValueError('维度目标必须在 '+dim_folder(dim)+' 内，且文件名为 waypoints.txt')
        rel=path.relative_to(target).as_posix();mappings[dim]=rel
        if rel in used and used[rel]!=dim: raise ValueError('不同维度不能写入同一目标')
        used[rel]=dim
        blob=path.read_bytes() if path.is_file() else b''
        before[rel]=fingerprint(path);texts[rel]=blob;keys[rel]=existing_keys(blob)
    for p in points:
        rel=mappings[p.dimension]
        status='不导入' if not rel or (p.death and not include_death) else '已存在' if p.key in keys[rel] else '新增'
        rows.append({'name':p.name,'dimension':p.dimension,'x':p.x,'y':p.y,'z':p.z,'death':p.death,'disabled':p.disabled,'status':status,'target':rel,'source':p.source})
        if status=='新增':
            keys[rel].add(p.key)
            blob=writes.get(rel,texts[rel])
            if not blob: blob=HEADER.encode('utf8')
            if not blob.endswith(b'\n'): blob+=b'\n'
            writes[rel]=blob+(p.line()+'\n').encode('utf8')
    return Plan(source,target,points,rows,issues,sources,before,writes,mappings)

@contextmanager
def target_locks(target: Path):
    """Xaero holds .lock files while the selected map is open. Deny shared access."""
    handles=[]
    try:
        if os.name=='nt':
            import ctypes
            from ctypes import wintypes
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
            kernel.CreateFileW.restype=wintypes.HANDLE
            kernel.CloseHandle.argtypes=[wintypes.HANDLE]
            maproot=target.parent.parent/'world-map'/target.name
            locks=list(target.rglob('.lock'))+(list(maproot.rglob('.lock')) if maproot.is_dir() else [])
            # Serialize independent converter processes, including a fresh world.
            locks.insert(0,target/'.journeymap-migration.lock')
            for path in locks:
                own_guard=path.name=='.journeymap-migration.lock'
                h=kernel.CreateFileW(str(path),0xC0000000 if own_guard else 0x80000000,0,None,4 if own_guard else 3,0x80,None)
                if h==ctypes.c_void_p(-1).value: raise RuntimeError('目标地图正在使用或被其他程序占用，请完全退出目标游戏后重试：'+str(path))
                handles.append((kernel,h))
        yield
    finally:
        for kernel,h in handles: kernel.CloseHandle(h)

def atomic_write(path: Path, blob: bytes):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.migration-'+uuid.uuid4().hex+'.tmp')
    try:
        with tmp.open('xb') as stream: stream.write(blob);stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists(): tmp.unlink()

def save_json(path: Path, data): atomic_write(path,json.dumps(data,ensure_ascii=False,indent=2).encode('utf8'))

def backup_root(target: Path) -> Path:
    return target.parent.parent.parent/'xaero-migration-backups'

def apply_plan(plan: Plan) -> dict:
    target=validate_target(plan.target)
    with target_locks(target):
        current={str(p):fingerprint(p) for p in source_files(plan.source)}
        if current!=plan.sources: raise RuntimeError('源坐标点在预览后发生变化，请重新预览')
        for rel,expected in plan.before.items():
            if fingerprint(contained(target/rel,target))!=expected: raise RuntimeError('目标文件在预览后发生变化，请重新预览：'+rel)
        if not plan.writes: return {'status':'nothing_to_do','add':0,'backup':None}
        folder=backup_root(target)/(datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
        folder.mkdir(parents=True)
        entries=[]
        for rel,blob in plan.writes.items():
            path=contained(target/rel,target)
            before=path.read_bytes() if path.is_file() else None
            if before is not None: atomic_write(folder/'before'/rel,before)
            atomic_write(folder/'after'/rel,blob)
            entries.append({'path':rel,'before':sha(before) if before is not None else None,'after':sha(blob)})
        manifest={'format':1,'tool':VERSION,'status':'prepared','target':str(target),'entries':entries,'sourceHashes':plan.sources,'summary':plan.summary()}
        save_json(folder/'manifest.json',manifest)
        try:
            # Validate every path again immediately before replacing it.
            for entry in entries:
                dst=contained(target/entry['path'],target)
                if fingerprint(dst)!=entry['before']: raise RuntimeError('目标被其他程序修改：'+entry['path'])
                atomic_write(dst,(folder/'after'/entry['path']).read_bytes())
                if fingerprint(dst)!=entry['after']: raise RuntimeError('写入校验失败')
            manifest['status']='complete';save_json(folder/'manifest.json',manifest)
        except BaseException:
            for entry in entries:
                dst=contained(target/entry['path'],target)
                if fingerprint(dst)==entry['after']:
                    if entry['before'] is None: dst.unlink()
                    else: atomic_write(dst,(folder/'before'/entry['path']).read_bytes())
            manifest['status']='rolled_back';save_json(folder/'manifest.json',manifest)
            raise
        return {'status':'complete','add':plan.summary()['add'],'backup':str(folder)}

def restore_backup(folder: Path) -> dict:
    folder=folder.resolve()
    manifest=json.loads((folder/'manifest.json').read_text('utf8'))
    if manifest.get('format')!=1 or manifest.get('status') not in ('complete','prepared'):
        raise ValueError('此备份已恢复、已回滚或格式不受支持')
    target=validate_target(Path(manifest['target']))
    contained(folder,backup_root(target))
    entries=manifest['entries']
    with target_locks(target):
        # Preflight all files: never erase waypoints created after the migration.
        for entry in entries:
            dst=contained(target/entry['path'],target)
            if dst.name!='waypoints.txt': raise ValueError('备份目标不是路径点文件')
            if fingerprint(dst)!=entry['after']: raise RuntimeError('迁移后文件已改变，不能整体恢复以免丢失新坐标点：'+entry['path']+'。迁移前副本在备份 before 目录。')
            for kind in ['before','after']:
                if entry[kind] is not None:
                    src=contained(folder/kind/entry['path'],folder/kind)
                    if fingerprint(src)!=entry[kind]: raise RuntimeError('备份校验失败：'+str(src))
        restored=[]
        try:
            for entry in entries:
                dst=contained(target/entry['path'],target)
                if entry['before'] is None: dst.unlink()
                else: atomic_write(dst,(folder/'before'/entry['path']).read_bytes())
                restored.append(entry)
            manifest['status']='restored';save_json(folder/'manifest.json',manifest)
        except BaseException:
            for entry in restored: atomic_write(contained(target/entry['path'],target),(folder/'after'/entry['path']).read_bytes())
            raise
    return {'status':'restored','files':len(entries),'target':str(target)}
