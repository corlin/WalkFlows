"""Content-checked cache records; absent or interrupted outputs are cache misses."""
from pathlib import Path
import hashlib,json,os

def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

def cache_valid(record,contract,directory,required):
    try:
        data=json.loads(Path(record).read_text());expected=data['artifacts']
        if data['contract']!=contract or not isinstance(expected,dict) or set(expected)!=set(required):return False
        for name in required:
            if not isinstance(name,str) or Path(name).name!=name or not isinstance(expected[name],str) or sha256(Path(directory)/name)!=expected[name]:return False
        return True
    except (OSError,ValueError,TypeError,KeyError):return False


def adopt_verified_part(part,destination,validator):
    """Atomically adopt a complete verified download, including after interruption."""
    part=Path(part);destination=Path(destination)
    if not part.is_file() or not validator(part):return False
    os.replace(part,destination);return True
