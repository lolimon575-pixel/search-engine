(() => {
  const dictionaries = {
    ru: {
      language: 'Язык',
      search: 'Найти',
      searchPlaceholder: 'Введите запрос',
      history: 'История поиска',
      popular: 'Популярные запросы',
      details: 'Подробнее',
      verification: 'Проверка NOVA',
      officialSite: 'Официальный сайт'
    },
    en: {
      language: 'Language',
      search: 'Search',
      searchPlaceholder: 'Enter query',
      history: 'Search history',
      popular: 'Popular searches',
      details: 'Details',
      verification: 'NOVA Verification',
      officialSite: 'Official website'
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
