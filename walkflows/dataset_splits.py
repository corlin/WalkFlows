"""Fixed site-level partition; entries are not labels or training samples."""
import re

SITE_SPLITS={'site01':'train','site02':'train','site03':'train','site04':'train','site05':'train','site08':'train','site06':'validation','site07':'test'}

def build_splits(entries):
 if not isinstance(entries,list):raise ValueError('invalid inventory')
 result={name:[] for name in ('train','validation','test','shared')};seen=set()
 for entry in entries:
  if not isinstance(entry,dict) or not isinstance(entry.get('path'),str) or type(entry.get('size')) is not int or entry['size']<0:raise ValueError('invalid inventory entry')
  path=entry['path'];parts=path.split('/')
  if path in seen or any(x in ('','.','..') for x in parts) or path.startswith('/') or '\\' in path:raise ValueError('invalid or duplicate path')
  seen.add(path)
  if path=='unlabeled/index.json':split='shared'
  elif parts[0] in ('testcases','unlabeled'):
   if len(parts)<3:raise ValueError('invalid scenario path')
   found=re.findall(r'site\d{2}',parts[1])
   if len(found)!=1 or found[0] not in SITE_SPLITS:raise ValueError('unknown or ambiguous site')
   split=SITE_SPLITS[found[0]]
  else:split='shared'
  result[split].append(dict(entry))
 return result
