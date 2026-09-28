"""Curated NOVA company registry.

This file is deliberately separate from ranking. A company being present here, or
having a richer profile, never adds ranking score. It only supplies identity and
profile metadata after a result has already been discovered.
"""

def profile(organization, category, tagline="", description="", accent="#2563eb", links=None, tier="showcase", badge=None):
    if badge is None:
        badge = {
            "premium": "Profile Plus",
            "premium_demo": "Profile Plus Demo",
            "showcase": "NOVA Profile",
        }.get(tier, "")
    return {
        "organization": organization,
        "category": category,
        "tagline": tagline,
        "description": description,
        "profile_accent": accent,
        "profile_tier": tier,
        "profile_badge": badge,
        "links": links or {},
    }


REGISTRY = {
    "google.com": profile("Google", "Technology", "Интернет-сервисы и технологии", "Официальный домен Google.", "#4285f4", {"products":"https://about.google/products/","support":"https://support.google.com/","about":"https://about.google/","careers":"https://careers.google.com/","cloud":"https://cloud.google.com/"}),
    "youtube.com": profile("YouTube", "Media", "Видео и создатели", "Официальный домен YouTube.", "#ff0033", {"about":"https://about.youtube/"}),
    "github.com": profile("GitHub", "Developer Tools", "Платформа для совместной разработки", "Официальный домен GitHub.", "#24292f", {"docs":"https://docs.github.com/","pricing":"https://github.com/pricing","enterprise":"https://github.com/enterprise","about":"https://github.com/about","careers":"https://www.github.careers/"}),
    "microsoft.com": profile("Microsoft", "Technology", "Программное обеспечение, облако и AI", "Официальный домен Microsoft.", "#5e5e5e", {"products":"https://www.microsoft.com/en-us/microsoft-products-and-apps","support":"https://support.microsoft.com/","learn":"https://learn.microsoft.com/","about":"https://www.microsoft.com/about","careers":"https://careers.microsoft.com/"}),
    "apple.com": profile("Apple", "Technology", "Устройства, сервисы и программное обеспечение", "Официальный домен Apple.", "#111111", {"store":"https://www.apple.com/store","support":"https://support.apple.com/","newsroom":"https://www.apple.com/newsroom/","careers":"https://www.apple.com/careers/","developer":"https://developer.apple.com/"}),
    "openai.com": profile("OpenAI", "AI", "Исследования и продукты искусственного интеллекта", "Официальный домен OpenAI.", "#111111", {"research":"https://openai.com/research/","developers":"https://platform.openai.com/","docs":"https://platform.openai.com/docs/","about":"https://openai.com/about/","careers":"https://openai.com/careers/"}),
    "meta.com": profile("Meta", "Technology", "Социальные технологии и AI", "Официальный корпоративный домен Meta.", "#0866ff", {"about":"https://about.meta.com/","careers":"https://www.metacareers.com/"}),
    "facebook.com": profile("Facebook", "Social", "Социальная сеть", "Официальный домен Facebook.", "#1877f2"),
    "instagram.com": profile("Instagram", "Social", "Фото, видео и общение", "Официальный домен Instagram.", "#c13584"),
    "whatsapp.com": profile("WhatsApp", "Messaging", "Личные и бизнес-коммуникации", "Официальный домен WhatsApp.", "#25d366"),
    "linkedin.com": profile("LinkedIn", "Professional Network", "Профессиональная сеть", "Официальный домен LinkedIn.", "#0a66c2", {"about":"https://about.linkedin.com/"}),
    "reddit.com": profile("Reddit", "Community", "Сообщества и обсуждения", "Официальный домен Reddit.", "#ff4500"),
    "x.com": profile("X", "Social", "Публичные разговоры и обновления", "Официальный домен X.", "#111111"),
    "tiktok.com": profile("TikTok", "Social", "Короткие видео и сообщества", "Официальный домен TikTok.", "#111111"),
    "discord.com": profile("Discord", "Communication", "Сообщества, голос и сообщения", "Официальный домен Discord.", "#5865f2", {"download":"https://discord.com/download","support":"https://support.discord.com/","safety":"https://discord.com/safety","developer":"https://discord.com/developers","careers":"https://discord.com/careers"}),
    "spotify.com": profile("Spotify", "Media", "Музыка, подкасты и аудио", "Официальный домен Spotify.", "#1db954", {"music":"https://open.spotify.com/","podcasts":"https://open.spotify.com/genre/podcasts-web","support":"https://support.spotify.com/","about":"https://www.spotify.com/about-us/","jobs":"https://www.lifeatspotify.com/"}),
    "netflix.com": profile("Netflix", "Media", "Стриминговый сервис", "Официальный домен Netflix.", "#e50914", {"watch":"https://www.netflix.com/browse","help":"https://help.netflix.com/","about":"https://about.netflix.com/","newsroom":"https://about.netflix.com/en/newsroom","jobs":"https://jobs.netflix.com/"}),
    "amazon.com": profile("Amazon", "Commerce", "Онлайн-торговля и технологии", "Официальный глобальный домен Amazon.", "#ff9900", {"about":"https://www.aboutamazon.com/","jobs":"https://www.amazon.jobs/"}),
    "amazon.de": profile("Amazon", "Commerce", "Онлайн-торговля и технологии", "Официальный домен Amazon.", "#ff9900"),
    "ebay.com": profile("eBay", "Commerce", "Онлайн-маркетплейс", "Официальный домен eBay.", "#3665f3"),
    "paypal.com": profile("PayPal", "Fintech", "Цифровые платежи", "Официальный домен PayPal.", "#003087"),
    "stripe.com": profile("Stripe", "Fintech", "Платёжная инфраструктура для интернета", "Официальный домен Stripe.", "#635bff", {"products":"https://stripe.com/products","pricing":"https://stripe.com/pricing","docs":"https://docs.stripe.com/","support":"https://support.stripe.com/","about":"https://stripe.com/about"}),
    "shopify.com": profile("Shopify", "Commerce", "Платформа для интернет-магазинов", "Официальный домен Shopify.", "#5e8e3e", {"products":"https://www.shopify.com/solutions","pricing":"https://www.shopify.com/pricing","help":"https://help.shopify.com/","about":"https://www.shopify.com/about","careers":"https://www.shopify.com/careers"}),
    "cloudflare.com": profile("Cloudflare", "Internet Infrastructure", "Сеть, безопасность и производительность", "Официальный домен Cloudflare.", "#f48120", {"products":"https://www.cloudflare.com/plans/","docs":"https://developers.cloudflare.com/","learning":"https://www.cloudflare.com/learning/","about":"https://www.cloudflare.com/about-overview/","careers":"https://www.cloudflare.com/careers/"}),
    "nvidia.com": profile("NVIDIA", "Technology", "Вычисления, графика и AI", "Официальный домен NVIDIA.", "#76b900", {"products":"https://www.nvidia.com/en-us/","developer":"https://developer.nvidia.com/","drivers":"https://www.nvidia.com/Download/index.aspx","about":"https://www.nvidia.com/about-nvidia/","careers":"https://www.nvidia.com/en-us/about-nvidia/careers/"}),
    "intel.com": profile("Intel", "Semiconductors", "Полупроводники и вычислительные платформы", "Официальный домен Intel.", "#0068b5", {"products":"https://www.intel.com/content/www/us/en/products/overview.html","support":"https://www.intel.com/content/www/us/en/support.html","developer":"https://www.intel.com/content/www/us/en/developer/overview.html","careers":"https://jobs.intel.com/"}),
    "amd.com": profile("AMD", "Semiconductors", "Процессоры и графические технологии", "Официальный домен AMD.", "#ed1c24", {"products":"https://www.amd.com/en/products.html","support":"https://www.amd.com/en/support","developer":"https://www.amd.com/en/developer.html","careers":"https://careers.amd.com/"}),
    "adobe.com": profile("Adobe", "Software", "Креативные и документные продукты", "Официальный домен Adobe.", "#ff0000", {"products":"https://www.adobe.com/products/catalog.html","support":"https://helpx.adobe.com/support.html","learn":"https://helpx.adobe.com/creative-cloud/tutorials-explore.html","about":"https://www.adobe.com/about-adobe.html","careers":"https://careers.adobe.com/"}),
    "salesforce.com": profile("Salesforce", "Enterprise Software", "CRM и корпоративные облачные продукты", "Официальный домен Salesforce.", "#0d9dda", {"products":"https://www.salesforce.com/products/","help":"https://help.salesforce.com/","developer":"https://developer.salesforce.com/","about":"https://www.salesforce.com/company/","careers":"https://careers.salesforce.com/"}),
    "oracle.com": profile("Oracle", "Enterprise Software", "Базы данных и облачная инфраструктура", "Официальный домен Oracle.", "#c74634", {"products":"https://www.oracle.com/products/","cloud":"https://www.oracle.com/cloud/","docs":"https://docs.oracle.com/","support":"https://support.oracle.com/","careers":"https://www.oracle.com/careers/"}),
    "ibm.com": profile("IBM", "Technology", "Корпоративные технологии и AI", "Официальный домен IBM.", "#0f62fe", {"products":"https://www.ibm.com/products","consulting":"https://www.ibm.com/consulting","support":"https://www.ibm.com/support","research":"https://research.ibm.com/","careers":"https://www.ibm.com/careers"}),
    "notion.so": profile("Notion", "Productivity", "Рабочее пространство для заметок и команд", "Официальный домен Notion.", "#111111", {"product":"https://www.notion.com/product","templates":"https://www.notion.com/templates","help":"https://www.notion.com/help","pricing":"https://www.notion.com/pricing","careers":"https://www.notion.com/careers"}),
    "figma.com": profile("Figma", "Design", "Совместный дизайн интерфейсов", "Официальный домен Figma.", "#a259ff", {"products":"https://www.figma.com/products/","community":"https://www.figma.com/community","pricing":"https://www.figma.com/pricing/","about":"https://www.figma.com/about-us/","careers":"https://www.figma.com/careers/"}),
    "canva.com": profile("Canva", "Design", "Визуальная коммуникация и дизайн", "Официальный домен Canva.", "#7d2ae8", {"templates":"https://www.canva.com/templates/","products":"https://www.canva.com/visual-suite/","help":"https://www.canva.com/help/","about":"https://www.canva.com/about/","careers":"https://www.canva.com/careers/"}),
    "slack.com": profile("Slack", "Communication", "Командные коммуникации", "Официальный домен Slack.", "#611f69", {"help":"https://slack.com/help"}),
    "zoom.us": profile("Zoom", "Communication", "Видеосвязь и совместная работа", "Официальный домен Zoom.", "#2d8cff", {"products":"https://www.zoom.com/en/products/","support":"https://support.zoom.com/","developer":"https://developers.zoom.us/","about":"https://www.zoom.com/en/about/","careers":"https://careers.zoom.us/"}),
    "dropbox.com": profile("Dropbox", "Cloud Storage", "Хранение и совместная работа с файлами", "Официальный домен Dropbox.", "#0061ff", {"products":"https://www.dropbox.com/products","pricing":"https://www.dropbox.com/plans","help":"https://help.dropbox.com/","about":"https://www.dropbox.com/about","careers":"https://jobs.dropbox.com/"}),
    "atlassian.com": profile("Atlassian", "Developer Tools", "Инструменты для команд разработки и бизнеса", "Официальный домен Atlassian.", "#1868db", {"products":"https://www.atlassian.com/software","support":"https://support.atlassian.com/","developer":"https://developer.atlassian.com/","about":"https://www.atlassian.com/company","careers":"https://www.atlassian.com/company/careers"}),
    "steamcommunity.com": profile("Steam", "Games", "Игры, магазин и сообщество", "Официальный домен Steam.", "#1b2838"),
    "steampowered.com": profile("Steam", "Games", "Игры, магазин и сообщество", "Официальный домен Steam.", "#1b2838"),
    "epicgames.com": profile("Epic Games", "Games", "Игры и игровые технологии", "Официальный домен Epic Games.", "#111111", {"store":"https://store.epicgames.com/","games":"https://www.epicgames.com/site/en-US/home","developer":"https://dev.epicgames.com/","support":"https://www.epicgames.com/help/","careers":"https://www.epicgames.com/site/en-US/careers"}),
    "riotgames.com": profile("Riot Games", "Games", "Игры и киберспорт", "Официальный домен Riot Games.", "#d32936", {"games":"https://www.riotgames.com/en","support":"https://support.riotgames.com/","newsroom":"https://www.riotgames.com/en/news","careers":"https://www.riotgames.com/en/work-with-us"}),
    "ea.com": profile("Electronic Arts", "Games", "Видеоигры и интерактивные развлечения", "Официальный домен Electronic Arts.", "#ff4747"),
    "ubisoft.com": profile("Ubisoft", "Games", "Видеоигры", "Официальный домен Ubisoft.", "#0070ff"),
    "roblox.com": profile("Roblox", "Games", "Игровая и пользовательская платформа", "Официальный домен Roblox.", "#111111"),
    "sony.com": profile("Sony", "Technology", "Электроника и развлечения", "Официальный корпоративный домен Sony.", "#003791", {"products":"https://www.sony.com/electronics","support":"https://www.sony.com/electronics/support","newsroom":"https://www.sony.com/en/SonyInfo/News/","about":"https://www.sony.com/en/SonyInfo/CorporateInfo/","careers":"https://www.sony.com/en/SonyInfo/Careers/"}),
    "nintendo.com": profile("Nintendo", "Games", "Игровые устройства и игры", "Официальный домен Nintendo.", "#e60012", {"games":"https://www.nintendo.com/us/store/games/","newsroom":"https://www.nintendo.com/us/whatsnew/","support":"https://en-americas-support.nintendo.com/","about":"https://www.nintendo.co.jp/corporate/en/"}),
    "samsung.com": profile("Samsung", "Technology", "Электроника и устройства", "Официальный домен Samsung.", "#1428a0", {"products":"https://www.samsung.com/us/","support":"https://www.samsung.com/us/support/","newsroom":"https://news.samsung.com/global/","about":"https://www.samsung.com/global/about-us/","careers":"https://www.samsung.com/us/careers/"}),
    "tesla.com": profile("Tesla", "Automotive", "Электромобили и энергетика", "Официальный домен Tesla.", "#cc0000", {"vehicles":"https://www.tesla.com/","energy":"https://www.tesla.com/energy","charging":"https://www.tesla.com/charging","support":"https://www.tesla.com/support","careers":"https://www.tesla.com/careers"}),
    "bmw.com": profile("BMW", "Automotive", "Автомобили и мобильность", "Официальный глобальный домен BMW.", "#0066b1"),
    "mercedes-benz.com": profile("Mercedes-Benz", "Automotive", "Автомобили и мобильность", "Официальный домен Mercedes-Benz.", "#111111"),
    "volkswagen.com": profile("Volkswagen", "Automotive", "Автомобили и мобильность", "Официальный глобальный домен Volkswagen.", "#001e50"),
    "uber.com": profile("Uber", "Mobility", "Поездки, доставка и логистика", "Официальный домен Uber.", "#111111", {"ride":"https://www.uber.com/us/en/ride/","eats":"https://www.ubereats.com/","help":"https://help.uber.com/","about":"https://www.uber.com/newsroom/company-info/","careers":"https://www.uber.com/us/en/careers/"}),
    "airbnb.com": profile("Airbnb", "Travel", "Жильё и путешествия", "Официальный домен Airbnb.", "#ff385c", {"homes":"https://www.airbnb.com/","experiences":"https://www.airbnb.com/experiences","help":"https://www.airbnb.com/help","about":"https://news.airbnb.com/about-us/","careers":"https://careers.airbnb.com/"}),
    "booking.com": profile("Booking.com", "Travel", "Бронирование путешествий", "Официальный домен Booking.com.", "#003b95", {"stays":"https://www.booking.com/","flights":"https://www.booking.com/flights/","cars":"https://www.booking.com/cars/","attractions":"https://www.booking.com/attractions/","help":"https://secure.booking.com/help"}),
    "nike.com": profile("Nike", "Apparel", "Спортивная одежда и товары", "Официальный домен Nike.", "#111111", {"men":"https://www.nike.com/men","women":"https://www.nike.com/women","kids":"https://www.nike.com/kids","help":"https://www.nike.com/help","membership":"https://www.nike.com/membership"}),
    "adidas.com": profile("adidas", "Apparel", "Спортивная одежда и товары", "Официальный глобальный домен adidas.", "#111111", {"men":"https://www.adidas.com/us/men","women":"https://www.adidas.com/us/women","kids":"https://www.adidas.com/us/kids","help":"https://www.adidas.com/us/help","stories":"https://www.adidas.com/us/blog"}),
    # Russian companies and services. These profiles are presentation metadata only:
    # being listed here does not buy or guarantee a ranking position.
    "yandex.ru": profile("Яндекс", "Technology", "Поиск, карты, транспорт и цифровые сервисы", "Официальный домен сервисов Яндекса.", "#ffcc00", {"services":"https://yandex.ru/all","about":"https://yandex.ru/company/","careers":"https://yandex.ru/jobs/","support":"https://yandex.ru/support/"}),
    "vk.com": profile("VK", "Social", "Социальная сеть и коммуникации", "Официальный домен социальной сети VK.", "#0077ff", {"product":"https://vk.com/","about":"https://vk.company/ru/","support":"https://vk.com/support"}),
    "mail.ru": profile("Mail", "Communication", "Почта, новости и интернет-сервисы", "Официальный домен Mail.", "#005ff9", {"product":"https://mail.ru/","help":"https://help.mail.ru/","about":"https://vk.company/ru/"}),
    "sberbank.ru": profile("Сбер", "Fintech", "Банковские и цифровые сервисы", "Официальный домен Сбера.", "#21a038", {"personal":"https://www.sberbank.ru/ru/person","business":"https://www.sberbank.ru/ru/s_m_business","help":"https://www.sberbank.ru/ru/person/help","about":"https://www.sberbank.ru/ru/about"}),
    "tbank.ru": profile("Т-Банк", "Fintech", "Банковские, инвестиционные и бизнес-сервисы", "Официальный домен Т-Банка.", "#ffdd2d", {"products":"https://www.tbank.ru/","business":"https://www.tbank.ru/business/","investments":"https://www.tbank.ru/invest/","help":"https://www.tbank.ru/bank/help/"}),
    "ozon.ru": profile("Ozon", "Commerce", "Маркетплейс и цифровые сервисы", "Официальный домен Ozon.", "#005bff", {"shop":"https://www.ozon.ru/","sellers":"https://seller.ozon.ru/","careers":"https://job.ozon.ru/"}),
    "wildberries.ru": profile("Wildberries", "Commerce", "Онлайн-маркетплейс", "Официальный домен Wildberries.", "#a100ff", {"shop":"https://www.wildberries.ru/","sellers":"https://seller.wildberries.ru/","careers":"https://career.wb.ru/"}),
    "avito.ru": profile("Avito", "Marketplace", "Объявления, товары и услуги", "Официальный домен Avito.", "#00aaff", {"product":"https://www.avito.ru/","support":"https://support.avito.ru/","careers":"https://career.avito.com/"}),
    "kaspersky.ru": profile("Лаборатория Касперского", "Cybersecurity", "Кибербезопасность для частных лиц и бизнеса", "Официальный российский домен Лаборатории Касперского.", "#00a88e", {"products":"https://www.kaspersky.ru/","business":"https://www.kaspersky.ru/small-to-medium-business-security","support":"https://support.kaspersky.ru/","about":"https://www.kaspersky.ru/about"}),
    "2gis.ru": profile("2ГИС", "Maps", "Карты, справочник и навигация", "Официальный домен 2ГИС.", "#1f9d55", {"maps":"https://2gis.ru/","help":"https://help.2gis.ru/","business":"https://business.2gis.ru/"}),
    "hh.ru": profile("HeadHunter", "Professional Network", "Работа, вакансии и найм", "Официальный домен HeadHunter.", "#d6001c", {"jobs":"https://hh.ru/","employers":"https://hh.ru/employers","about":"https://hh.ru/article/28"}),
    "mts.ru": profile("МТС", "Telecom", "Мобильная связь, интернет и цифровые сервисы", "Официальный домен МТС.", "#e30611", {"products":"https://mts.ru/","support":"https://support.mts.ru/","business":"https://business.mts.ru/"}),
    "megafon.ru": profile("МегаФон", "Telecom", "Мобильная связь и цифровые сервисы", "Официальный домен МегаФона.", "#00b956", {"products":"https://megafon.ru/","support":"https://megafon.ru/help/","business":"https://business.megafon.ru/"}),
    "beeline.ru": profile("билайн", "Telecom", "Мобильная связь, домашний интернет и сервисы", "Официальный домен билайна.", "#ffd400", {"products":"https://beeline.ru/","support":"https://beeline.ru/customers/pomosh/","business":"https://beeline.ru/business/"}),
    "rt.ru": profile("Ростелеком", "Telecom", "Интернет, связь и цифровые услуги", "Официальный пользовательский домен Ростелекома.", "#7b2cff", {"products":"https://rt.ru/","support":"https://rt.ru/support","about":"https://www.company.rt.ru/about/info/","investors":"https://www.company.rt.ru/ir/"}),
    "alfa-bank.ru": profile("Альфа-Банк", "Fintech", "Банковские сервисы для частных лиц и бизнеса", "Официальный домен Альфа-Банка.", "#ef3124", {"personal":"https://alfabank.ru/","business":"https://alfabank.ru/sme/","help":"https://alfabank.ru/help/"}),
    "vtb.ru": profile("ВТБ", "Fintech", "Банковские сервисы для частных лиц и бизнеса", "Официальный домен ВТБ.", "#003f8f", {"personal":"https://www.vtb.ru/personal/","business":"https://www.vtb.ru/malyj-biznes/","about":"https://www.vtb.ru/about/"}),

    "kinopoisk.ru": profile("Кинопоиск", "Media", "Онлайн-кинотеатр, фильмы, сериалы и киноэнциклопедия", "Официальный домен Кинопоиска.", "#ff6600", {"watch":"https://www.kinopoisk.ru/"}),
    "rutube.ru": profile("RUTUBE", "Media", "Российская видеоплатформа", "Официальный домен RUTUBE.", "#100943", {"watch":"https://rutube.ru/","app":"https://rutube.ru/app/","legal":"https://rutube.ru/info/legal/"}),
    "rbc.ru": profile("РБК", "Media", "Деловые новости, аналитика и профессиональные материалы", "Официальный домен РБК.", "#1b6ac9", {"news":"https://www.rbc.ru/","business":"https://www.rbc.ru/rubric/business","subscription":"https://pro.rbc.ru/offers"}),
    "gazprombank.ru": profile("Газпромбанк", "Fintech", "Банковские услуги для частных лиц и бизнеса", "Официальный домен Газпромбанка.", "#00a5df", {"personal":"https://www.gazprombank.ru/","business":"https://www.gazprombank.ru/business/","investors":"https://www.gazprombank.ru/investors/","tariffs":"https://www.gazprombank.ru/documents-and-tariffs/","offices":"https://www.gazprombank.ru/offices/"}),
    "yota.ru": profile("Yota", "Telecom", "Мобильная связь, тарифы и цифровые сервисы", "Официальный домен оператора Yota.", "#00aeef", {"tariffs":"https://www.yota.ru/tariff","services":"https://www.yota.ru/services","support":"https://www.yota.ru/support","contacts":"https://www.yota.ru/contacts","business":"https://www.yota.ru/business"}),

    "puma.com": profile(
        "PUMA",
        "Apparel",
        "Forever. Faster. · спорт, performance и lifestyle",
        "Демонстрационная Profile Plus-карточка PUMA: быстрый доступ к ключевым продуктовым и корпоративным разделам официальной экосистемы бренда.",
        "#111111",
        {
            "shop":"https://eu.puma.com/de/en",
            "running":"https://eu.puma.com/de/en/men/sports/running",
            "football":"https://eu.puma.com/de/en/sports/football",
            "careers":"https://about.puma.com/en/careers",
            "investors":"https://about.puma.com/en/investor-relations",
            "sustainability":"https://about.puma.com/en/sustainability"
        },
        tier="premium_demo",
        badge="Profile Plus Demo"
    ),
    "ikea.com": profile("IKEA", "Retail", "Мебель и товары для дома", "Официальный глобальный домен IKEA.", "#0058a3"),
}

# Official PUMA surfaces share one presentation profile. Keeping aliases explicit makes
# the card work when search results land on regional commerce or corporate subdomains.
REGISTRY["eu.puma.com"] = REGISTRY["puma.com"]
REGISTRY["about.puma.com"] = REGISTRY["puma.com"]
