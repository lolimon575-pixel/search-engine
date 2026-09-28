/* NOVA UI stabilization layer */
(function(){
  function keepIndependentPanels(){
    window.novaUIState = window.novaUIState || {
      historyExpanded:false,
      frequentExpanded:false,
      activeModal:null
    };
  }

  function improveModalBehavior(){
    document.addEventListener('keydown', function(e){
      if(e.key !== 'Escape') return;
      document.querySelectorAll('.modal.open,.dialog-wrap.open').forEach(function(el){
        el.classList.remove('open');
      });
    });
  }

  function markPremiumCards(){
    document.querySelectorAll('.featured-official').forEach(function(card){
      card.classList.add('nova-premium-card');
    });
  }

  keepIndependentPanels();
  improveModalBehavior();
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', markPremiumCards);
  } else {
    markPremiumCards();
  }
})();
