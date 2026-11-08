"""Exploratory appearance-conflict gate for gaps, not verified identity."""
import math

def normalize(values):
 if values is None:return None
 if not values or any(not isinstance(x,(int,float)) or isinstance(x,bool) or not math.isfinite(x) or x<0 for x in values):raise ValueError('invalid histogram')
 total=sum(values)
 if total<=0:raise ValueError('empty histogram')
 return [x/total for x in values]

def distance(a,b):
 if a is None or b is None:return None
 if len(a)!=len(b):raise ValueError('inconsistent histogram shape')
 return math.sqrt(max(0.,1.-min(1.,sum(math.sqrt(x*y) for x,y in zip(a,b)))))

def segment_track(rows,threshold):
 if not isinstance(threshold,(int,float)) or isinstance(threshold,bool) or not math.isfinite(threshold) or not 0<=threshold<=1:raise ValueError('invalid threshold')
 segment=0;previous=None;out=[]
 for row in rows:
  frame=row['frame'];feature=normalize(row['feature'])
  if type(frame) is not int or frame<0:raise ValueError('invalid frame')
  if previous:
   prev_frame,prev_feature=previous
   if frame<=prev_frame:raise ValueError('frames not strictly ordered')
   d=distance(prev_feature,feature)
   if frame>prev_frame+1 and (d is None or d>threshold):segment+=1
  out.append(segment);previous=(frame,feature)
 return out
