(function(){
  function safePost(type){
    try{
      window.parent.postMessage({ type }, window.location.origin);
    }catch(e){
      try{ window.parent.postMessage({ type }, '*'); }catch(e2){}
    }
  }
  if (typeof window.post === "undefined") window.post = safePost;
  window.postIntro = safePost;
})();