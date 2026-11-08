/* Side-by-side research comparison; not an identity or accuracy metric. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.WalkflowsSourceComparison=factory()})(globalThis,function(){
 'use strict';
 function compareSources(model,reference,zones,window,options,analytics,transitions){
  if(!Array.isArray(model)||!Array.isArray(reference)||!Array.isArray(zones)||!window||!Number.isSafeInteger(window.start)||!Number.isSafeInteger(window.end)||!Number.isSafeInteger(window.referenceFrames)||window.start<0||window.end<window.start||window.referenceFrames<1||!options||!analytics||!transitions)throw Error('invalid source comparison');
  const end=Math.min(window.end,window.referenceFrames-1),coverage={requested_start:window.start,requested_end:window.end,compared_start:window.start<=end?window.start:null,compared_end:window.start<=end?end:null,excluded_reference_missing_frames:window.end-Math.max(window.start,window.referenceFrames)+1};coverage.excluded_reference_missing_frames=Math.max(0,coverage.excluded_reference_missing_frames);
  if(window.start>end)return {status:'no_reference_coverage',scope:'research_comparison_not_accuracy_or_people',coverage};
  function build(source){const h=analytics.sliceHypotheses(source,window.start,end);return {areas:zones.map(z=>({zone_id:z.id,name:z.name,...analytics.summarizeArea(h,z,options)})),transitions:transitions.summarize(h,zones,options,analytics)}}
  return {status:'ok',scope:'research_comparison_not_accuracy_or_people',coverage,model:build(model),reference:build(reference)};
 }
 return {compareSources};
});
