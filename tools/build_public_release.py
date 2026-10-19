"""Package the public generator/converter; excludes complete upstream map JARs."""
from pathlib import Path
import hashlib,io,json,shutil,subprocess,sys,zipfile
from payload_bundle import restore,FILES

r=Path(__file__).resolve().parents[1];version='0.1.0'
out=r/'dist'/('public-v'+version);out.mkdir(parents=True,exist_ok=True)
payload=r/'.cache/installer-payload'
payload_manifest=json.loads((payload/'manifest.json').read_text('utf8'))
for name,expected in payload_manifest['payloadHashes'].items():
    assert hashlib.sha256((payload/name).read_bytes()).hexdigest()==expected
with zipfile.ZipFile(payload/'adapter-payload.jar') as native:
    for name in native.namelist():
        assert name=='NativePatcher.class' or name.startswith(('minimap/xaero/pixelmon/','worldmap/xaero/map/pixelmon/')) or name in [
            'minimap/coremods/pixelmon_compass.js','minimap/META-INF/pixelmon-fork.json','worldmap/META-INF/pixelmon-fork.json'],name

def deterministic_zip(path,entries):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,blob in sorted(entries.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,19,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,blob)
    with zipfile.ZipFile(path) as z:assert z.testzip() is None

payload_zip=out/f'adapter-payload-v{version}.zip'
deterministic_zip(payload_zip,{name:(payload/name).read_bytes() for name in FILES})
payload_hash=hashlib.sha256(payload_zip.read_bytes()).hexdigest()
lock={'version':version,'url':f'https://github.com/dyfawa4/pixelmon-xaero-map-compat/releases/download/v{version}/{payload_zip.name}','sha256':payload_hash}
(r/'config/payload.lock.json').write_text(json.dumps(lock,ensure_ascii=False,indent=2)+'\n','utf8')
restore(payload_zip,r/'.cache/public-payload-verified',payload_hash)

exe=r/'dist/坐标迁移工具/地图坐标迁移.exe'
metadata=json.loads((exe.parent/'构建清单.json').read_text('utf8'))
assert hashlib.sha256(exe.read_bytes()).hexdigest()==metadata['sha256']
for name,digest in metadata['sourceHashes'].items():assert hashlib.sha256((r/'migration'/name).read_bytes()).hexdigest()==digest
subprocess.run([str(exe),'--self-test'],check=True,timeout=30)

guide='''# 宝可梦地图适配与坐标迁移 v0.1.0

双击“地图坐标迁移.exe”打开中文工具，无需安装 Python。

一、安装地图：点击右上角“安装 / 生成宝可梦地图组件…”，选 Java 11+ 和独立输出目录。
已有固定版本官方 JAR 时选其文件夹离线生成；留空时从作者官方 Modrinth 文件下载并校验。
生成后退出游戏，将两个定制地图 JAR 与 XaeroLib 放进实际游戏实例 mods，移走旧地图组件和 JourneyMap JAR。
保留 Pixelmon、本身需要的回迁模组，以及原 journeymap 数据目录。

二、迁移坐标：先用新地图进入对应世界一次，再退出游戏。选择旅行地图来源与 Xaero 目标，
核对世界/服务器及维度/子世界，生成预览后导入。转换功能始终可离线使用。

三、核对与回退：在 Xaero 默认路径点分组核对；重复导入去重，迁移前文件自动备份。
恢复入口在转换器内。迁移后若文件又有变化，工具会拒绝整体恢复，以免丢掉新增点位。

完整图示和步骤请读“迁移指南.md”。本版只迁移坐标点和历史死亡点，不转换已探索地形。
适用 Minecraft 1.16.5 / Forge 36.2.42，游戏已测 Java 11；小地图 26.6.0、世界地图 1.47.0、XaeroLib 1.7.3。
自制小智皮卡丘普通/异色已作图标专项检查，回迁物种经实体实际精灵图接口接入。

公开包附原创适配资源及生成器，不包含完整原版/修改版 Xaero JAR 或游戏/Pixelmon 资源。
最终在玩家本地生成两个定制原生地图，不额外增加兼容模组。原作者 Xaero96，官方入口：
https://modrinth.com/mod/xaeros-minimap
https://modrinth.com/mod/xaeros-world-map
https://modrinth.com/mod/xaerolib

项目：https://github.com/dyfawa4/pixelmon-xaero-map-compat
'''
entries={'地图坐标迁移.exe':exe.read_bytes(),'先读我.md':guide.encode('utf8'),
         '迁移指南.md':(r/'docs/迁移指南.md').read_bytes(),'验证记录.md':(r/'docs/验证记录.md').read_bytes(),
         'LICENSE':(r/'LICENSE').read_bytes(),'第三方许可/ASM-BSD-3-Clause.txt':(r/'THIRD_PARTY_LICENSES/ASM-BSD-3-Clause.txt').read_bytes()}
license_sources=[(Path(sys.base_prefix)/'LICENSE.txt','Python-LICENSE.txt'),
                (r/'.cache/migration-build-deps/pyinstaller-6.16.0.dist-info/licenses/COPYING.txt','PyInstaller-COPYING.txt')]
for root in [Path(sys.base_prefix)/'tcl',Path(sys.base_prefix)/'Lib/tkinter']:
    if root.is_dir():license_sources += [(p,p.parent.name+'-license.terms') for p in root.rglob('license.terms')]
for path,name in license_sources:
    if path.is_file():entries['第三方许可/'+name]=path.read_bytes()
manifest={'release':'v'+version,'mapBuild':payload_manifest['build'],'tool':metadata['tool'],
          'containsCompleteUpstreamMods':False,'files':{name:hashlib.sha256(blob).hexdigest() for name,blob in entries.items()}}
entries['文件校验清单.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf8')
bundle=out/f'Pixelmon-Xaero-Tools-v{version}.zip';deterministic_zip(bundle,entries)
checksums=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in [bundle,payload_zip])
(out/'SHA256SUMS.txt').write_text(checksums,'utf8')
notes='''首个公开版本：宝可梦地图适配生成器与中文坐标迁移工具。

- 大小地图读取宝可梦实际精灵图，覆盖重铸、回迁、普通/异色/形态；自制小智皮卡丘普通/异色已有专项检查。
- JourneyMap 坐标点与历史死亡点迁移，带维度分隔、预览、去重、备份及恢复。
- **不转换已探索地形**，保留原旅行地图目录。
- 详细安装与迁移教程在仓库 docs/迁移指南.md，也随工具包附带。

玩家请下载 **Pixelmon-Xaero-Tools-v0.1.0.zip**，解压运行“地图坐标迁移.exe”，无需 Python。
先用右上角入口从官方固定版本生成两个定制地图组件及 XaeroLib，再按教程迁移坐标。
已有官方原文件时可离线生成；坐标转换本身始终离线。公开包不包含完整修改版上游 JAR。

适用 Minecraft 1.16.5 / Forge 36.2.42；小地图 26.6.0 / 世界地图 1.47.0 / XaeroLib 1.7.3。
游戏实测 Java 11，回迁本轮基线 1.5.0。其他版本与复杂多人子世界尚未全部实机验证。

13 项转换回归、53 项游戏内迁移检查、9 项自制帽皮图标检查及 26 项原生修改检查已完成。
安装器的联网和离线输入方式生成结果与验收 JAR 哈希相同。原始坐标、存档与日志不公开。

adapter-payload-v0.1.0.zip 是给开发者重建桌面工具的原创适配资源包；普通玩家使用主工具包即可。
SHA256SUMS.txt 可核对两个下载附件。
'''
(out/'release-notes.md').write_text(notes,'utf8')
record={'version':'v'+version,'assets':[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [bundle,payload_zip,out/'SHA256SUMS.txt']],
        'noCompleteUpstreamMods':True,'payloadEntriesVerified':True,'exeSelfTestPassed':True}
(r/'evidence/public-release-verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(record,ensure_ascii=False,indent=2))
