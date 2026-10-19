from pathlib import Path
import json, sys, tempfile, unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration'))
import migrate_core as m

class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='mapmigration-中文-')
        self.root=Path(self.tmp.name);self.source=self.root/'原实例/journeymap/data/sp/中文世界'
        (self.source/'waypoints').mkdir(parents=True)
        self.target=self.root/'新实例/xaero/minimap/中文世界';self.target.mkdir(parents=True)
        (self.target/'config.txt').write_text('original config\n','utf8')
    def tearDown(self):self.tmp.cleanup()
    def point(self,name='家',file='home',**updates):
        data={'name':name,'x':-10,'y':64,'z':123,'r':255,'g':0,'b':0,'enable':True,'type':'Normal','dimensions':['minecraft:overworld']};data.update(updates)
        path=self.source/'waypoints'/f'{file}.json';path.write_text(json.dumps(data,ensure_ascii=False),'utf8');return path
    def test_preview_merge_idempotency_restore(self):
        self.point();dst=self.target/'dim%0/waypoints.txt';dst.parent.mkdir()
        original=b'sets:MySet:gui.xaero_default\n# keep exact original bytes\r\nwaypoint:Existing:E:1:2:3:6:false:0:MySet:false:0:LOCAL:false\r\n';dst.write_bytes(original)
        before=list(self.root.rglob('*'));p=m.make_plan(self.source,self.target)
        self.assertEqual(p.summary()['add'],1);self.assertEqual(dst.read_bytes(),original);self.assertEqual(before,list(self.root.rglob('*')))
        r=m.apply_plan(p);self.assertTrue(dst.read_bytes().startswith(original));self.assertIn(b':12:false:0:gui.xaero_default:',dst.read_bytes())
        p2=m.make_plan(self.source,self.target);self.assertEqual(p2.summary()['duplicates'],1);self.assertFalse(p2.writes)
        self.assertEqual(m.apply_plan(p2)['status'],'nothing_to_do')
        m.restore_backup(Path(r['backup']));self.assertEqual(dst.read_bytes(),original)
    def test_death_disabled_names_and_dimensions(self):
        self.point('家:中文\n😀',enable=False,type='Death',dimensions=['minecraft:overworld','pixelmon:ultra_space'])
        p=m.make_plan(self.source,self.target);self.assertEqual(p.summary()['deathpoints'],2)
        self.assertEqual(set(p.writes),{'dim%0/waypoints.txt','dim%pixelmon$ultra_space/waypoints.txt'})
        for blob in p.writes.values():
            line=blob.decode('utf8').splitlines()[-1];self.assertEqual(len(line.split(':')),14)
            self.assertIn('家§§中文 😀',line);self.assertIn(':true:2:gui.xaero_default:',line);self.assertIn(':GLOBAL:false',line)
        self.assertFalse(m.make_plan(self.source,self.target,include_death=False).writes)
    def test_invalid_json_missing_dimension_and_coordinate_rejected(self):
        self.point();self.point(file='invalid',dimensions=[]);self.point(file='fraction',x=12.5)
        (self.source/'waypoints/broken.json').write_text('{','utf8')
        p=m.make_plan(self.source,self.target);self.assertEqual(p.summary()['add'],1);self.assertEqual(len(p.issues),3)
    def test_no_world_guessing_and_safe_target(self):
        self.point(dimensions=['../../evil'])
        self.assertEqual(len(m.make_plan(self.source,self.target).issues),1)
        with self.assertRaises(ValueError):m.make_plan(self.source,self.root)
        self.point()
        for rel in ['../../escape/waypoints.txt','dim%-1/waypoints.txt','dim%0/other.txt']:
            with self.assertRaises(ValueError):m.make_plan(self.source,self.target,{'minecraft:overworld':rel})
    def test_changes_after_preview_abort(self):
        src=self.point();p=m.make_plan(self.source,self.target);src.write_text('{}','utf8')
        with self.assertRaises(RuntimeError):m.apply_plan(p)
        self.point();p=m.make_plan(self.source,self.target);dst=self.target/'dim%0/waypoints.txt';dst.parent.mkdir();dst.write_text('# new\n','utf8')
        with self.assertRaises(RuntimeError):m.apply_plan(p)
        self.assertFalse(m.backup_root(self.target).exists())
    def test_restore_refuses_post_import_edit_and_corrupt_backup(self):
        self.point();p=m.make_plan(self.source,self.target);r=m.apply_plan(p);folder=Path(r['backup']);dst=self.target/'dim%0/waypoints.txt';after=dst.read_bytes();dst.write_bytes(after+b'# newer user change\n')
        with self.assertRaises(RuntimeError):m.restore_backup(folder)
        dst.write_bytes(after);(folder/'after/dim%0/waypoints.txt').write_bytes(b'corrupt')
        with self.assertRaises(RuntimeError):m.restore_backup(folder)
        self.assertEqual(dst.read_bytes(),after)
    def test_restore_removes_only_created_file(self):
        self.point();p=m.make_plan(self.source,self.target);r=m.apply_plan(p);dst=self.target/'dim%0/waypoints.txt';self.assertTrue(dst.exists())
        m.restore_backup(Path(r['backup']));self.assertFalse(dst.exists());self.assertTrue((self.target/'config.txt').is_file())
    def test_transaction_rolls_back_after_second_write_fails(self):
        self.point(dimensions=['minecraft:overworld','pixelmon:ultra_space']);p=m.make_plan(self.source,self.target)
        original=m.atomic_write;count=0
        def flaky(path,blob):
            nonlocal count
            # Hosted Windows temp roots may use an 8.3 alias (RUNNER~1).
            # The converter canonicalizes destinations before writing them.
            if path.resolve().is_relative_to(self.target.resolve()):
                count+=1
                if count==2:raise OSError('simulated disk failure')
            return original(path,blob)
        with patch.object(m,'atomic_write',side_effect=flaky):
            with self.assertRaises(OSError):m.apply_plan(p)
        self.assertFalse(list(self.target.rglob('waypoints.txt')))
        manifest=next(m.backup_root(self.target).glob('*/manifest.json'));self.assertEqual(json.loads(manifest.read_text('utf8'))['status'],'rolled_back')
    def test_multiple_subworlds_require_explicit_choice(self):
        self.point();folder=self.target/'dim%0/mw$server';folder.mkdir(parents=True);(folder/'waypoints.txt').write_text('# existing\n','utf8')
        with self.assertRaises(ValueError):m.make_plan(self.source,self.target)
        p=m.make_plan(self.source,self.target,{'minecraft:overworld':'dim%0/mw$server/waypoints.txt'});self.assertEqual(p.summary()['add'],1)
    def test_existing_malformed_target_is_never_overwritten(self):
        self.point();dst=self.target/'dim%0/waypoints.txt';dst.parent.mkdir();dst.write_text('waypoint:broken\n','utf8')
        with self.assertRaises(ValueError):m.make_plan(self.source,self.target)
    def test_discovery_and_dimension_aliases(self):
        self.point(dimensions=['0','-1','1','ultra_space'])
        self.assertEqual(len(m.make_plan(self.source,self.target).points),4)
        self.assertEqual(m.discover_sources(self.root/'原实例'),[self.source.resolve()])
        self.assertEqual(m.discover_sources(self.source/'waypoints'),[self.source.resolve()])
        self.assertEqual(m.discover_targets(self.root/'新实例'),[self.target.resolve()])
    def test_duplicate_in_source_and_y_omitted(self):
        self.point(y=None);self.point(file='same',y=None)
        p=m.make_plan(self.source,self.target);self.assertEqual(p.summary()['add'],1);self.assertEqual(p.summary()['duplicates'],1)
        self.assertIn(b':-10:~:123:',next(iter(p.writes.values())))
    @unittest.skipUnless(m.os.name=='nt','Windows sharing mode')
    def test_concurrent_converter_is_blocked(self):
        with m.target_locks(self.target):
            with self.assertRaises(RuntimeError):
                with m.target_locks(self.target):pass

if __name__=='__main__':unittest.main(verbosity=2)
