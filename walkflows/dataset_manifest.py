"""Validate a pinned Hugging Face file inventory before local download."""
import re
from pathlib import PurePosixPath

def parse_manifest(payload,revision):
 if not isinstance(payload,dict) or payload.get('sha')!=revision or not re.fullmatch('[0-9a-f]{40}',revision) or not isinstance(payload.get('siblings'),list):raise ValueError('invalid dataset revision')
 entries=[];seen=set()
 for item in payload['siblings']:
  if not isinstance(item,dict):raise ValueError('invalid entry')
  name=item.get('rfilename');size=item.get('size');blob=item.get('blobId')
  if not isinstance(name,str) or not name or '\\' in name or name.startswith('/') or any(x in ('','.','..') for x in name.split('/')) or str(PurePosixPath(name))!=name or name in seen:raise ValueError('invalid path')
  if type(size) is not int or size<0 or not isinstance(blob,str) or not re.fullmatch('[0-9a-f]{40}',blob):raise ValueError('invalid file metadata')
  lfs=item.get('lfs')
  if lfs is not None:
   if not isinstance(lfs,dict) or lfs.get('size')!=size or not isinstance(lfs.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',lfs['sha256']):raise ValueError('invalid lfs metadata')
   kind='sha256';digest=lfs['sha256']
  else:kind='git';digest=blob
  seen.add(name);entries.append({'path':name,'size':size,'kind':kind,'digest':digest})
 if not entries:raise ValueError('empty inventory')
 return sorted(entries,key=lambda x:x['path'])
