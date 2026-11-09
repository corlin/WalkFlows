"""Conservative spatial weak labels, not independently verified identities."""
from walkflows.crossview import unique_pairs

def unique_position_pairs(predictions,references,max_distance):
 pairs=unique_pairs(predictions,references,max_distance=max_distance)
 by_pred={p['id']:p for p in predictions};by_ref={p['id']:p for p in references};result=[]
 for pair in pairs:
  p=by_pred[pair['left_id']];r=by_ref[pair['right_id']]
  result.append({'prediction_id':p['id'],'reference_id':r['id'],'input_x':p['x'],'input_y':p['y'],'target_x':r['x'],'target_y':r['y'],'distance':pair['distance'],'label_kind':'spatial_unique_proxy'})
 return result
