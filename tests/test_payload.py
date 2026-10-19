from pathlib import Path
import hashlib,json,sys,tempfile,unittest,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from payload_bundle import FILES,restore

class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='adapter-payload-')
        self.root=Path(self.temp.name);self.archive=self.root/'payload.zip';self.target=self.root/'restored'
    def tearDown(self):self.temp.cleanup()
    def package(self,extra=None,corrupt=False):
        entries={name:('fixture '+name).encode() for name in FILES if name!='manifest.json'}
        hashes={name:hashlib.sha256(blob).hexdigest() for name,blob in entries.items()}
        if corrupt:hashes['adapter-payload.jar']='0'*64
        entries['manifest.json']=json.dumps({'payloadHashes':hashes}).encode()
        if extra:entries.update(extra)
        with zipfile.ZipFile(self.archive,'w') as z:
            for name,blob in entries.items():z.writestr(name,blob)
        return hashlib.sha256(self.archive.read_bytes()).hexdigest()
    def test_verified_archive_restores_exact_files(self):
        digest=self.package();restore(self.archive,self.target,digest)
        self.assertEqual({p.name for p in self.target.iterdir()},FILES)
        self.assertEqual((self.target/'adapter-payload.jar').read_bytes(),b'fixture adapter-payload.jar')
    def test_wrong_download_hash_never_creates_destination(self):
        self.package()
        with self.assertRaises(ValueError):restore(self.archive,self.target,'0'*64)
        self.assertFalse(self.target.exists())
    def test_extra_traversal_entry_never_writes(self):
        digest=self.package({'../outside.txt':b'no'})
        with self.assertRaises(ValueError):restore(self.archive,self.target,digest)
        self.assertFalse(self.target.exists());self.assertFalse((self.root/'outside.txt').exists())
    def test_entry_hash_mismatch_never_writes(self):
        digest=self.package(corrupt=True)
        with self.assertRaises(ValueError):restore(self.archive,self.target,digest)
        self.assertFalse(self.target.exists())

if __name__=='__main__':unittest.main(verbosity=2)
