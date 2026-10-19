"""Validate the redistributable own-code/ASM payload without unpacking arbitrary paths."""
from pathlib import Path
import hashlib,json,zipfile

FILES={'adapter-payload.jar','asm-9.6.jar','asm-tree-9.6.jar','ASM-BSD-3-Clause.txt','manifest.json'}

def restore(archive:Path,destination:Path,expected:str):
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:
        raise ValueError('Adapter payload SHA-256 mismatch')
    with zipfile.ZipFile(archive) as z:
        if len(z.infolist())!=len(FILES) or set(z.namelist())!=FILES:
            raise ValueError('Unexpected adapter payload entries')
        if sum(i.file_size for i in z.infolist())>5_000_000:
            raise ValueError('Adapter payload exceeds expected size')
        blobs={name:z.read(name) for name in FILES}
    manifest=json.loads(blobs['manifest.json'])
    if set(manifest['payloadHashes'])!=FILES-{'manifest.json'}:
        raise ValueError('Unexpected payload hash manifest')
    for name,digest in manifest['payloadHashes'].items():
        if hashlib.sha256(blobs[name]).hexdigest()!=digest:raise ValueError('Payload entry hash mismatch: '+name)
    destination.mkdir(parents=True,exist_ok=True)
    for name,blob in blobs.items():(destination/name).write_bytes(blob)
    return manifest
