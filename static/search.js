const base = new URL('../', document.currentScript.src);
window.addEventListener('DOMContentLoaded', () => {
  try {
    if (!window.PagefindUI) throw new Error('Pagefind UI fehlt');
    new PagefindUI({
      element: '#search',
      baseUrl: base.pathname,
      bundlePath: new URL('pagefind/', base).pathname,
      showImages: false,
      showSubResults: false,
      resetStyles: false,
      translations: {
        placeholder: 'Nachrichten oder Autoren suchen …',
        filter_label: 'Filter',
        clear_search: 'Suche löschen',
        load_more: 'Weitere Ergebnisse laden',
        zero_results: 'Keine Ergebnisse für [SEARCH_TERM]',
        many_results: '[COUNT] Ergebnisse für [SEARCH_TERM]',
        one_result: 'Ein Ergebnis für [SEARCH_TERM]',
        searching: 'Suche läuft …',
      },
    });
  } catch (error) {
    document.querySelector('#search-error').hidden = false;
    console.error(error);
  }
});
