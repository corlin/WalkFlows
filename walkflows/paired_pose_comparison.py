"""Numerical summaries on already-paired model observations."""
import math
from statistics import median
from numbers import Real

def summarize_pairs(pairs):
 rows=list(pairs)
 for row in rows:
  if len(row)!=2 or any(isinstance(v,bool) or not isinstance(v,Real) or not math.isfinite(v) or v<0 for v in row):raise ValueError('invalid paired distances')
 return {'paired':len(rows),'nano_median':median(x[0] for x in rows) if rows else None,'small_median':median(x[1] for x in rows) if rows else None,'small_closer':sum(s<n for n,s in rows),'nano_closer':sum(n<s for n,s in rows),'ties':sum(n==s for n,s in rows)}
