"""Download the pinned XFeat checkpoint without changing the Python environment."""
import hashlib
import os
import tempfile
from pathlib import Path
from urllib.request import urlopen

URL=("https://raw.githubusercontent.com/verlab/accelerated_features/"
     "e92685f57f8318b18725c5c8c0bd28c7fe188d9a/weights/xfeat.pt")
EXPECTED="0f5187fd7bedd26c7fe6acc9685444493a165a35ecc087b33c2db3627f3ea10b"
DESTINATION=Path(__file__).resolve().parents[1]/"data"/"models"/"xfeat.pt"


def main():
    DESTINATION.parent.mkdir(parents=True,exist_ok=True)
    if DESTINATION.exists():
        if hashlib.sha256(DESTINATION.read_bytes()).hexdigest()!=EXPECTED:
            raise ValueError("existing checkpoint has unexpected hash; it was not changed")
        print("XFeat checkpoint already verified:",DESTINATION);return
    fd,name=tempfile.mkstemp(prefix=".xfeat-",dir=DESTINATION.parent)
    try:
        with os.fdopen(fd,"wb") as output, urlopen(URL,timeout=60) as source:
            digest=hashlib.sha256()
            while True:
                chunk=source.read(1024*1024)
                if not chunk:break
                digest.update(chunk);output.write(chunk)
        if digest.hexdigest()!=EXPECTED:raise ValueError("downloaded checkpoint hash mismatch")
        # Create the destination atomically without replacing an existing file.
        os.link(name,DESTINATION)
        print("XFeat checkpoint downloaded and verified:",DESTINATION)
    finally:
        Path(name).unlink(missing_ok=True)


if __name__=="__main__":
    main()
