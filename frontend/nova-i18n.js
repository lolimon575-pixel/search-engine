(() => {
  const dictionaries = {
    ru: {
      language: 'Язык',
      russian: 'Русский',
      english: 'English',
      search: 'Найти',
      searchPlaceholder: 'Введите запрос',
      history: 'История поиска',
      popular: 'Популярные запросы',
      details: 'Подробнее',
      verification: 'Проверка NOVA',
      officialSite: 'Официальный сайт',
      close: 'Закрыть',
      loading: 'Проверка...',
      verified: 'Проверено',
      company: 'Компания',
      source: 'Источник',
      score: 'Оценка',
      clear: 'Очистить',
      more: 'Больше',
      results: 'Результаты',
      noResults: 'Ничего не найдено',
      footerLanguage: 'Язык'
    },
    en: {
      language: 'Language',
      russian: 'Русский',
      english: 'English',
      search: 'Search',
      searchPlaceholder: 'Enter query',
      history: 'Search history',
      popular: 'Popular searches',
      details: 'Details',
      verification: 'NOVA Verification',
      officialSite: 'Official website',
      close: 'Close',
      loading: 'Checking...',
      verified: 'Verified',
      company: 'Company',
      source: 'Source',
      score: 'Score',
      clear: 'Clear',
      more: 'More',
      results: 'Results',
      noResults: 'No results found',
      footerLanguage: 'Language'
    }
  };

  const KEY = 'novaLanguage';
  let current = localStorage.getItem(KEY) || (navigator.language.startsWith('ru') ? 'ru' : 'en');

  function translate(key) {
    return dictionaries[current]?.[key] || dictionaries.en[key] || key;
  }

  function applyLanguage() {
    document.documentElement.lang = current;
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.dataset.i18n;
      el.textContent = translate(key);
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      el.placeholder = translate(el.dataset.i18nPlaceholder);
    });
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      el.title = translate(el.dataset.i18nTitle);
    });
    window.dispatchEvent(new CustomEvent('nova-language-change', {detail:{language: current}}));
  }

  function setLanguage(lang) {
    if (!dictionaries[lang]) return;
    current = lang;
    localStorage.setItem(KEY, lang);
    applyLanguage();
  }

  window.NOVA_I18N = { setLanguage, getLanguage: () => current, translate, applyLanguage };
  window.addEventListener('DOMContentLoaded', applyLanguage);
})();
