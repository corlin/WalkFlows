"use strict";
async function playAvailable(cards) {
  const attempts=cards.map(card=>{
    try{return Promise.resolve(card.video.play());}
    catch(error){return Promise.reject(error);}
  });
  const outcomes=await Promise.allSettled(attempts);
  const playing=[],failed=[];
  outcomes.forEach((outcome,index)=>(outcome.status==="fulfilled"?playing:failed).push(cards[index]));
  return {playing,failed};
}
if(typeof module!=="undefined")module.exports={playAvailable};
