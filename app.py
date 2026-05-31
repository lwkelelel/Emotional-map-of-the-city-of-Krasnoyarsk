from flask import Flask, render_template, request, redirect, flash, url_for, jsonify, send_file, session
import re
import requests
import hashlib
from datetime import datetime
from functools import wraps
from pathlib import Path
from urllib.parse import quote, urljoin

from sqlalchemy import func

from database import engine, db_session, Base
from models import Category, Place, Admin, Vote, Complaint
from collections import Counter

app = Flask(__name__)
app.secret_key = "emotional-map-secret-key-2026"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Пожалуйста, войдите в систему", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function


def clean_value(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def geocode_address(address):
    try:
        api_key = "ed1e5987-d728-476b-a522-01190c8d6679"
        response = requests.get(
            "https://geocode-maps.yandex.ru/1.x/",
            params={"apikey": api_key, "geocode": address, "format": "json"},
            timeout=6
        )
        data = response.json()
        pos = data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["Point"]["pos"]
        lon, lat = map(float, pos.split())
        return lat, lon
    except Exception:
        return 56.0106, 92.8526



def init_categories():
    categories_data = [
        {"name": "Восторг", "icon": "😍", "color": "#FF6B6B"},
        {"name": "Гордость за город", "icon": "🏆", "color": "#FFD93D"},
        {"name": "Удивление", "icon": "😲", "color": "#6BCF7F"},
        {"name": "Хорошая грусть", "icon": "😔", "color": "#4D9DE0"},
        {"name": "Беспокойные места", "icon": "😰", "color": "#E15554"},
        {"name": "Весёлые места", "icon": "😂", "color": "#FFB347"},
        {"name": "Вкусные места", "icon": "🍜", "color": "#FF6B35"},
        {"name": "Воодушевляющие места", "icon": "✨", "color": "#9B59B6"},
        {"name": "Мистические места", "icon": "🔮", "color": "#2C3E50"},
        {"name": "Одухотворённые места", "icon": "🕊️", "color": "#A8E6CF"},
        {"name": "Романтические места", "icon": "💕", "color": "#FF8DA1"},
        {"name": "Спокойные места", "icon": "😌", "color": "#88D4AB"},
        {"name": "Страшные места", "icon": "👻", "color": "#4A4A4A"},
        {"name": "Умилительные места", "icon": "🥹", "color": "#FFB7B2"},
        {"name": "Умиротворяющие места", "icon": "🌿", "color": "#6B8E6B"},
    ]

    for cat_data in categories_data:
        existing = db_session.query(Category).filter(Category.name == cat_data["name"]).first()
        if not existing:
            db_session.add(Category(**cat_data))
    db_session.commit()

WIKI_TITLE_OVERRIDES = {'Красноярские Столбы': 'Красноярские Столбы',
 'Часовня Параскевы Пятницы': 'Часовня Параскевы Пятницы',
 'Коммунальный мост': 'Коммунальный мост (Красноярск)',
 'Красноярская ГЭС': 'Красноярская гидроэлектростанция',
 'Фанпарк «Бобровый лог»': 'Бобровый лог',
 'Остров Татышев': 'Татышев',
 'Виноградовский мост': 'Виноградовский мост',
 'Роев ручей': 'Роев ручей',
 'Николаевская сопка': 'Николаевская сопка',
 'Красноярский краеведческий музей': 'Красноярский краевой краеведческий музей',
 'Красноярский театр оперы и балета': 'Красноярский театр оперы и балета',
 'Музей-усадьба В. И. Сурикова': 'Музей-усадьба В. И. Сурикова',
 'Красноярский художественный музей имени В. И. Сурикова': 'Красноярский художественный музей имени В. И. Сурикова',
 'Сибирский федеральный университет': 'Сибирский федеральный университет',
 'Покровский кафедральный собор': 'Покровский собор (Красноярск)',
 'Красноярская краевая филармония': 'Красноярская краевая филармония',
 'Красноярский драматический театр имени А. С. Пушкина': 'Красноярский драматический театр имени А. С. Пушкина',
 'Торгашинский хребет': 'Торгашинский хребет',
 'Чёрная сопка': 'Чёрная сопка',
 'Музей-пароход «Святитель Николай»': 'Святитель Николай (пароход)',
 'Храм Преображения Господня': 'Храм Преображения Господня (Красноярск)',
 'Памятник «Царь-рыба»': None,
 'Литературный музей имени В. П. Астафьева': 'Литературный музей (Красноярск)',
 'Троицкое кладбище': 'Троицкое кладбище (Красноярск)',
 'Караульная гора': 'Караульная гора',
 'Центральный парк Красноярска': 'Центральный парк имени М. Горького (Красноярск)',
 'Красноярский музыкальный театр': 'Красноярский музыкальный театр',
 'Театральная площадь': None,
 'Красноярский театр юного зрителя': 'Красноярский театр юного зрителя',
 'Красноярский цирк': 'Красноярский цирк',
 'Красноярск': 'Красноярск',
 'Центральный район Красноярска': 'Центральный район (Красноярск)',
 'Речной вокзал Красноярска': 'Красноярский речной вокзал',
 'Институт гастрономии СФУ': None,
 'Проспект Мира': 'Проспект Мира (Красноярск)',
 'Центральная набережная Красноярска': None,
 'Скала Перья': 'Скала Перья (Красноярск)',
 'Скала Дед': 'Скала Дед (Красноярск)',
 'Красноярский театр кукол': 'Красноярский театр кукол',
 'Красноярский краевой театр кукол': 'Красноярский краевой театр кукол',
 'Литературный музей Астафьева': 'Литературный музей (Красноярск)',
 'Памятник А. П. Чехову': None,
 'Памятник Чехову': None,
 'Фонтан «Реки Сибири»': None,
 'Красноярский речной вокзал': 'Красноярский речной вокзал',
 'Площадь Революции': 'Площадь Революции (Красноярск)',
 'Октябрьский мост': 'Октябрьский мост (Красноярск)',
 'Железнодорожный мост через Енисей': 'Железнодорожный мост через Енисей (Красноярск)',
 'Скала Ермак': 'Красноярские Столбы',
 'Скала Львиные Ворота': 'Красноярские Столбы',
 'Благовещенский монастырь': 'Благовещенский монастырь (Красноярск)',
 'Свято-Успенский мужской монастырь': 'Свято-Успенский мужской монастырь (Красноярск)',
 'Детская железная дорога': 'Красноярская детская железная дорога'}

BAD_WIKI_TITLES = {'Антон Павлович Чехов',
 'Енисей',
 'Красноярск',
 'Красноярский край',
 'Памятник А. П. Чехову',
 'Памятник Чехову',
 'Пушкин, Александр Сергеевич',
 'Россия',
 'Театр кукол',
 'Центральный парк',
 'Чехов, Антон Павлович'}

GASTRO_PLACES = {'Булгаков Bar',
 'Гастробар Tunguska',
 'Институт гастрономии СФУ',
 'Кафе Green Villa Pizza',
 'Кафе Traveler’s Coffee',
 'Кофейня Академия кофе',
 'Ресторан 0.75 Please',
 'Ресторан Bangkok',
 'Хозяин тайги',
 'Центральный рынок Красноярска'}

FORCE_EXTERNAL_PLACES = {'Булгаков Bar',
 'Гастробар Tunguska',
 'Кафе Green Villa Pizza',
 'Кафе Traveler’s Coffee',
 'Кофейня Академия кофе',
 'Памятник А. П. Чехову',
 'Памятник Чехову',
 'Ресторан 0.75 Please',
 'Ресторан Bangkok',
 'Театральная площадь',
 "Институт гастрономии СФУ",
 'Фонтан «Реки Сибири»',
 'Хозяин тайги',
 'Памятник «Царь-рыба»',
 'Центральная набережная Красноярска',
 'Центральный рынок Красноярска'}

EXTERNAL_ARTICLES = {'Памятник А. П. Чехову': {'title': 'Памятник А. П. Чехову в Красноярске',
                           'extract': 'Памятник Антону Павловичу Чехову расположен в Красноярске и посвящён известному русскому писателю. '
                                      'Монумент связан с историей путешествия Чехова по Сибири и является одной из городских скульптур, '
                                      'которые напоминают о литературной памяти города. Это место подходит для прогулки по центральной '
                                      'части Красноярска и знакомства с культурными деталями городской среды.',
                           'url': 'http://kraskompas.ru/nash-gorod/pamyatniki-i-skulptury/pamyatniki/item/279-pamyatnik-a-p-chekhovu.html',
                           'thumbnail': 'https://commons.wikimedia.org/wiki/Special:FilePath/%D0%9A%D1%80%D0%B0%D1%81%D0%BD%D0%BE%D1%8F%D1%80%D1%81%D0%BA.%20%D0%9F%D0%B0%D0%BC%D1%8F%D1%82%D0%BD%D0%B8%D0%BA%20%D0%A7%D0%B5%D1%85%D0%BE%D0%B2%D1%83.jpg'},
 'Памятник Чехову': {'title': 'Памятник А. П. Чехову в Красноярске',
                     'extract': 'Памятник Антону Павловичу Чехову расположен в Красноярске и посвящён известному русскому писателю. '
                                'Монумент связан с историей путешествия Чехова по Сибири и является одной из городских скульптур, которые '
                                'напоминают о литературной памяти города. Это место подходит для прогулки по центральной части Красноярска '
                                'и знакомства с культурными деталями городской среды.',
                     'url': 'http://kraskompas.ru/nash-gorod/pamyatniki-i-skulptury/pamyatniki/item/279-pamyatnik-a-p-chekhovu.html',
                     'thumbnail': 'https://commons.wikimedia.org/wiki/Special:FilePath/%D0%9A%D1%80%D0%B0%D1%81%D0%BD%D0%BE%D1%8F%D1%80%D1%81%D0%BA.%20%D0%9F%D0%B0%D0%BC%D1%8F%D1%82%D0%BD%D0%B8%D0%BA%20%D0%A7%D0%B5%D1%85%D0%BE%D0%B2%D1%83.jpg'},
"Институт гастрономии СФУ": {
                        "title": "Институт гастрономии СФУ",
                        "extract": "Институт гастрономии СФУ — образовательный центр в Красноярске, созданный совместно с французской школой Institut Lyfe (ранее Paul Bocuse). Здесь готовят специалистов в области гастрономии, ресторанного бизнеса и гостиничного сервиса. Институт стал одним из ключевых проектов развития гастрономической культуры Сибири.",
                        "url": "https://gastronomyinstitute.ru/",
                        "thumbnail": ""
                    },
 'Фонтан «Реки Сибири»': {'title': 'Фонтан «Реки Сибири» в Красноярске',
                          'extract': 'Фонтан «Реки Сибири» расположен на Театральной площади Красноярска и является заметной частью '
                                     'центрального городского пространства. Композиция посвящена образу сибирских рек и хорошо подходит '
                                     'для прогулок, фотографий и знакомства с центром города. Рядом находятся театр оперы и балета, '
                                     'городская набережная и другие популярные места Красноярска.',
                          'url': 'https://www.kraskompas.ru/nash-gorod/dostoprimechatelnosti/fontany/item/143-reki-sibiri.html',
                          'thumbnail': ''},
 'Центральная набережная Красноярска': {'title': 'Центральная набережная Красноярска',
                                        'extract': 'Центральная набережная Красноярска — прогулочная зона у Енисея с видами на реку, мосты '
                                                   'и центральную часть города. Это место подходит для спокойных прогулок, свиданий, '
                                                   'фотографий и отдыха после посещения музеев или театров. Набережная помогает '
                                                   'почувствовать связь Красноярска с Енисеем.',
                                        'url': 'https://krasgorpark.ru/parki/levoberezhnaya-naberezhnaya',
                                        'thumbnail': ''},
 'Театральная площадь': {'title': 'Театральная площадь Красноярска',
                         'extract': 'Театральная площадь — одно из центральных общественных пространств Красноярска. Рядом находятся театр '
                                    'оперы и балета, фонтан «Реки Сибири», прогулочные зоны и городская набережная. Площадь воспринимается '
                                    'как место встреч, прогулок, городских событий и культурных маршрутов.',
                         'url': '',
                         'thumbnail': ''},
 'Скала Перья': {'title': 'Скала Перья',
                 'extract': 'Скала Перья — одна из самых узнаваемых скальных групп национального парка «Красноярские Столбы». Место '
                            'известно необычной формой скал и связано с туристическими маршрутами, природными видами и атмосферой '
                            'настоящей сибирской природы.',
                 'url': '',
                 'thumbnail': ''},
 'Скала Дед': {'title': 'Скала Дед',
               'extract': 'Скала Дед находится в районе Красноярских Столбов и получила название из-за выразительного силуэта. Это место '
                          'связано с прогулками по природным маршрутам, внимательным рассматриванием скальных форм и легендарной '
                          'атмосферой Столбов.',
               'url': '',
               'thumbnail': ''},
 'Центральный рынок Красноярска': {'title': 'Центральный рынок Красноярска',
                                   'extract': 'Центральный рынок Красноярска связан с повседневной гастрономией города, местными '
                                              'продуктами, торговой атмосферой и живым ритмом центра. Это не музейная '
                                              'достопримечательность, а место, где можно почувствовать обычную городскую жизнь через '
                                              'запахи, вкусы, покупки и общение.',
                                   'url': '',
                                   'thumbnail': ''},
 'Ресторан 0.75 Please': {'title': 'Ресторан 0.75 Please',
                          'extract': '0.75 Please — известный красноярский ресторан современной кухни. Заведение связано с '
                                     'гастрономическим образом города, локальными продуктами, авторской подачей и атмосферой вечернего '
                                     'центра. Это место подходит для маршрута, где еда становится частью городского впечатления.',
                          'url': 'https://075please.ru/about',
                          'thumbnail': ''},
 'Булгаков Bar': {'title': 'Булгаков Bar',
                  'extract': 'Булгаков Bar — городское пространство для встреч, ужинов и вечернего отдыха. Заведение воспринимается как '
                             'часть гастрономической культуры центра Красноярска, где еда, напитки, интерьер и общение соединяются в один '
                             'городской сценарий.',
                  'url': 'https://siberia.wheretoeat.ru/winners_2024/bulgakov/',
                  'thumbnail': ''},
 'Хозяин тайги': {'title': 'Хозяин тайги',
                  'extract': 'Ресторан «Хозяин тайги» связан с образом сибирской кухни и локальных традиций. Интерьер, подача блюд и '
                             'концепция заведения отражают природный и культурный образ Красноярского края, поэтому место хорошо подходит '
                             'для гастрономической карты города.',
                  'url': 'https://bellinigroup.ru/rest/khozyain-taygi/',
                  'thumbnail': ''},
 'Кофейня Академия кофе': {'title': 'Академия кофе',
                           'extract': 'Академия кофе — городская кофейня для встреч, прогулок и небольших пауз в центре Красноярска. Место '
                                      'связано с современной кофейной культурой, спокойным отдыхом, разговорами и ощущением живого '
                                      'городского ритма.',
                           'url': '',
                           'thumbnail': ''},
 'Гастробар Tunguska': {'title': 'Гастробар Tunguska',
                        'extract': 'Гастробар Tunguska — известный гастрономический проект Красноярска. Его концепция связана с '
                                   'современной интерпретацией сибирской кухни, локальными продуктами и атмосферой города, который '
                                   'стремится показать собственный вкус и характер.',
                        'url': 'https://tunguskarestaurant.ru/',
                        'thumbnail': ''},
 'Ресторан Bangkok': {'title': 'Ресторан Bangkok',
                      'extract': 'Ресторан Bangkok добавляет в гастрономическую карту Красноярска азиатскую кухню и другой ритм вкусов. '
                                 'Место подходит для встреч, ужинов и знакомства с более разнообразной ресторанной средой города.',
                      'url': '',
                      'thumbnail': ''},
"Памятник «Царь-рыба»": {"title": "Памятник «Царь-рыба»",
                        "url": "https://visitsiberia.info/czar-ryiba.html",
                        "extract": "Памятник «Царь-рыба» расположен на Слизневском утёсе возле Красноярска. Скульптура создана по мотивам произведения Виктора Астафьева и является одной из самых известных смотровых площадок региона."
                    },
 'Кафе Green Villa Pizza': {'title': 'Green Villa Pizza',
                            'extract': 'Green Villa Pizza — место для еды, встреч и семейного отдыха. Формат кафе подходит для дружеских '
                                       'посиделок, простого городского маршрута и спокойного гастрономического впечатления без '
                                       'официальности.',
                            'url': 'https://greenvillapizza.ru/',
                            'thumbnail': ''},
 'Кафе Traveler’s Coffee': {'title': 'Traveler’s Coffee',
                            'extract': 'Traveler’s Coffee — кофейня для перекуса, встреч, работы и спокойного отдыха. Это удобная '
                                       'городская точка, где можно выпить кофе, поговорить или сделать паузу во время прогулки по '
                                       'Красноярску.',
                            'url': '',
                            'thumbnail': ''}}

def get_wikipedia_page(page_title):
    try:
        url = "https://ru.wikipedia.org/w/api.php"

        # Сначала пробуем открыть страницу по точному названию
        response = requests.get(
            url,
            params={
                "action": "query",
                "titles": page_title,
                "prop": "extracts|pageimages|info",
                "exintro": 1,
                "explaintext": 1,
                "exsentences": 6,
                "pithumbsize": 900,
                "redirects": 1,
                "format": "json",
                "utf8": 1
            },
            headers={"User-Agent": "EmotionalMap/1.0"},
            timeout=6
        )

        data = response.json()
        pages = data.get("query", {}).get("pages", {})

        for page_id, page_data in pages.items():
            if page_id != "-1":
                title = page_data.get("title", "")
                extract = page_data.get("extract", "")
                if extract:
                    return {
                        "title": title,
                        "extract": extract,
                        "url": f"https://ru.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
                        "thumbnail": page_data.get("thumbnail", {}).get("source", "")
                    }

        # Если точной страницы нет, ищем через поиск Wikipedia
        search_response = requests.get(
            url,
            params={
                "action": "query",
                "list": "search",
                "srsearch": page_title,
                "srlimit": 1,
                "format": "json",
                "utf8": 1
            },
            headers={"User-Agent": "EmotionalMap/1.0"},
            timeout=6
        )

        search_data = search_response.json()
        results = search_data.get("query", {}).get("search", [])

        if not results:
            return None

        found_title = results[0].get("title")
        if not found_title:
            return None

        # Открываем найденную страницу
        response = requests.get(
            url,
            params={
                "action": "query",
                "titles": found_title,
                "prop": "extracts|pageimages|info",
                "exintro": 1,
                "explaintext": 1,
                "exsentences": 6,
                "pithumbsize": 900,
                "redirects": 1,
                "format": "json",
                "utf8": 1
            },
            headers={"User-Agent": "EmotionalMap/1.0"},
            timeout=6
        )

        data = response.json()
        pages = data.get("query", {}).get("pages", {})

        for page_id, page_data in pages.items():
            if page_id != "-1":
                title = page_data.get("title", "")
                extract = page_data.get("extract", "")
                if extract:
                    return {
                        "title": title,
                        "extract": extract,
                        "url": f"https://ru.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
                        "thumbnail": page_data.get("thumbnail", {}).get("source", "")
                    }

        return None

    except Exception as e:
        print(f"Ошибка получения страницы Wikipedia: {e}")
        return None


def is_bad_wiki_result(wiki_data):
    if not wiki_data:
        return True

    title = (wiki_data.get("title") or "").strip()
    extract = (wiki_data.get("extract") or "").strip()

    if not title or not extract:
        return True

    if title in BAD_WIKI_TITLES:
        return True

    # Отсекаем страницы-списки и общие понятия, которые не описывают конкретное место.
    bad_phrases = [
        "может означать",
        "имеющее несколько значений",
        "значения",
        "см.",
    ]

    short_extract = extract[:250].lower()
    if any(phrase in short_extract for phrase in bad_phrases):
        return True

    return False

def normalize_image_url(url):
    if not url:
        return ""

    if url.startswith("//"):
        return "https:" + url

    return url

def search_wikipedia(place_name, latitude=None, longitude=None):
    if place_name in FORCE_EXTERNAL_PLACES:
        return None

    variants = []

    override_title = WIKI_TITLE_OVERRIDES.get(place_name)

    if override_title:
        variants.append(override_title)

    variants.append(place_name)
    variants.append(f"{place_name} Красноярск")

    seen = set()
    clean_variants = []

    for item in variants:
        if item and item not in seen:
            seen.add(item)
            clean_variants.append(item)

    for title in clean_variants:
        print("ИЩУ В WIKI:", title)
        wiki_data = get_wikipedia_page(title)

        if not is_bad_wiki_result(wiki_data):
            return wiki_data

    return None

def normalize_place_name(name):
    return clean_value(name).replace("ё", "е").lower()


def find_external_article(place_name):
    article = EXTERNAL_ARTICLES.get(place_name)
    if article:
        return article

    normalized = normalize_place_name(place_name)

    for key, value in EXTERNAL_ARTICLES.items():
        if normalize_place_name(key) == normalized:
            return value

    return None


def normalize_image_url(url):
    if not url:
        return ""

    url = str(url).strip()

    if url.startswith("//"):
        url = "https:" + url

    return url


def extract_first_image_from_article(url):
    if not url:
        return ""

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 EmotionalMap/1.0"},
            timeout=7
        )

        if response.status_code >= 400:
            return ""

        html_text = response.text

        match = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            html_text,
            flags=re.I
        )

        if not match:
            match = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                html_text,
                flags=re.I
            )

        if match:
            img_url = normalize_image_url(match.group(1))
            return urljoin(url, img_url)

        images = re.findall(
            r'<img[^>]+src=["\']([^"\']+)["\']',
            html_text,
            flags=re.I
        )

        for img_url in images:
            low = img_url.lower()

            if any(bad in low for bad in ["logo", "icon", "sprite", "blank", "counter"]):
                continue

            if any(ext in low for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                img_url = normalize_image_url(img_url)
                return urljoin(url, img_url)

    except Exception as e:
        print("Ошибка загрузки картинки внешней статьи:", e)

    return ""


def get_external_article(place_name):
    article = find_external_article(place_name)

    if not article:
        return None

    return {
        "title": article.get("title", place_name),
        "extract": article.get("extract", ""),
        "url": article.get("url", ""),
        "thumbnail": normalize_image_url(article.get("thumbnail", ""))
    }

@app.route("/api/places")
def api_places():
    category_id = request.args.get("category_id", type=int)
    query = db_session.query(Place).filter(Place.is_verified == True)
    if category_id:
        query = query.filter(Place.category_id == category_id)

    result = []
    for place in query.all():
        result.append({
            "id": place.id,
            "name": place.name,
            "latitude": place.latitude,
            "longitude": place.longitude,
            "category_id": place.category_id,
            "category_name": place.category.name,
            "category_icon": place.category.icon,
            "category_color": place.category.color,
            "description": place.description or "",
            "address": place.address or "",
            "votes_count": place.votes_count or 0,
            "wifi_free": place.wifi_free,  # ← ДОБАВИТЬ
            "wheelchair_accessible": place.wheelchair_accessible  # ← ДОБАВИТЬ
        })
    return jsonify(result)


@app.route("/api/categories")
def api_categories():
    categories = db_session.query(Category).filter(Category.is_active == True).all()
    result = []
    for cat in categories:
        count = db_session.query(Place).filter(Place.category_id == cat.id, Place.is_verified == True).count()
        result.append({
            "id": cat.id,
            "name": cat.name,
            "icon": cat.icon,
            "color": cat.color,
            "places_count": count,
            "max_places": 10
        })
    return jsonify(result)


@app.route("/api/place/<int:place_id>")
def api_place(place_id):
    place = db_session.query(Place).get(place_id)
    if not place:
        return jsonify({"error": "Место не найдено"}), 404

    place.views_count = (place.views_count or 0) + 1
    db_session.commit()

    return jsonify({
        "id": place.id,
        "name": place.name,
        "description": place.description,
        "address": place.address,
        "category_name": place.category.name,
        "category_icon": place.category.icon,
        "category_color": place.category.color,
        "views_count": place.views_count,
        "votes_count": place.votes_count,
        "complaints_count": place.complaints_count
    })


@app.route("/api/place_of_day")
def api_place_of_day():
    today_index = int(datetime.now().strftime("%j"))
    places = db_session.query(Place).filter(Place.is_verified == True).order_by(Place.id.asc()).all()

    if not places:
        return jsonify([])

    start = today_index % len(places)
    selected = [places[(start + i) % len(places)] for i in range(min(5, len(places)))]
    result = []

    for place in selected:
        photo = place.photo_url or ""
        if not photo:
            wiki_data = search_wikipedia(place.name, place.latitude, place.longitude)
            if wiki_data and wiki_data.get("thumbnail"):
                photo = wiki_data["thumbnail"]
                place.photo_url = photo
                place.photo_source = "Wikipedia"
                db_session.commit()

        result.append({
            "id": place.id,
            "name": place.name,
            "category_icon": place.category.icon,
            "category_name": place.category.name,
            "category_color": place.category.color,
            "description": (place.description or "")[:140],
            "photo_url": photo  # ← ИСПРАВЛЕНО: было "wiki_photo"
        })

    return jsonify(result)


@app.route("/api/geocode", methods=["POST"])
def api_geocode():
    data = request.get_json() or {}
    lat, lon = geocode_address(data.get("address", ""))
    return jsonify({"lat": lat, "lon": lon})



@app.route("/api/place_wiki/<int:place_id>")
def api_place_wiki(place_id):
    place = db_session.query(Place).get(place_id)

    if not place:
        return jsonify({"error": "Место не найдено"}), 404

    print("API_PLACE_WIKI:", place.id, place.name)

    if place.name in FORCE_EXTERNAL_PLACES:
        external_article = get_external_article(place.name)

        if external_article and external_article.get("extract"):
            thumbnail = external_article.get("thumbnail", "")

            try:
                place.photo_url = thumbnail or ""
                place.photo_source = "External article" if thumbnail else ""
                db_session.commit()
            except Exception:
                db_session.rollback()

            return jsonify({
                "success": True,
                "title": external_article.get("title", place.name),
                "extract": external_article.get("extract", ""),
                "url": external_article.get("url", ""),
                "thumbnail": thumbnail,
                "source": "Article"
            })

    wiki_data = search_wikipedia(place.name, place.latitude, place.longitude)

    if wiki_data and wiki_data.get("extract"):
        thumbnail = normalize_image_url(wiki_data.get("thumbnail", ""))

        try:
            place.photo_url = thumbnail or ""
            place.photo_source = "Wikipedia" if thumbnail else ""
            db_session.commit()
        except Exception:
            db_session.rollback()

        extract = wiki_data.get("extract", "")
        if len(extract) > 900:
            extract = extract[:900] + "..."

        return jsonify({
            "success": True,
            "title": wiki_data.get("title", ""),
            "extract": extract,
            "url": wiki_data.get("url", ""),
            "thumbnail": thumbnail,
            "source": "Wikipedia"
        })

    external_article = get_external_article(place.name)

    if external_article and external_article.get("extract"):
        thumbnail = external_article.get("thumbnail", "")

        try:
            place.photo_url = thumbnail or ""
            place.photo_source = "External article" if thumbnail else ""
            db_session.commit()
        except Exception:
            db_session.rollback()

        return jsonify({
            "success": True,
            "title": external_article.get("title", place.name),
            "extract": external_article.get("extract", ""),
            "url": external_article.get("url", ""),
            "thumbnail": thumbnail,
            "source": "Article"
        })

    # Последний fallback: всё равно success=True, чтобы не было заглушки "не удалось".
    return jsonify({
        "success": True,
        "title": place.name,
        "extract": place.description or "Описание места пока не добавлено.",
        "url": "",
        "thumbnail": "",
        "source": "Local"
    })


@app.route("/api/vote/<int:place_id>", methods=["POST"])
def api_vote(place_id):
    place = db_session.query(Place).get(place_id)
    if not place:
        return jsonify({"error": "Место не найдено"}), 404

    data = request.get_json() or {}
    value = int(data.get("value", 1))
    user_ip = request.remote_addr

    existing_vote = db_session.query(Vote).filter(Vote.place_id == place_id, Vote.ip_address == user_ip).first()
    if existing_vote:
        return jsonify({"status": "already_voted", "message": "Вы уже голосовали за это место"}), 400

    db_session.add(Vote(place_id=place_id, ip_address=user_ip, value=value))
    place.votes_count = (place.votes_count or 0) + (1 if value == 1 else -1)
    db_session.commit()

    return jsonify({"status": "ok", "message": "Спасибо за оценку!", "votes_count": place.votes_count})


@app.route("/api/complaint/<int:place_id>", methods=["POST"])
def api_complaint(place_id):
    place = db_session.query(Place).get(place_id)
    if not place:
        return jsonify({"error": "Место не найдено"}), 404

    data = request.get_json() or {}
    reason = data.get("reason", "Эмоция не подходит")
    suggested_category_id = data.get("suggested_category_id")
    user_ip = request.remote_addr

    existing = db_session.query(Complaint).filter(Complaint.place_id == place_id, Complaint.ip_address == user_ip).first()
    if existing:
        return jsonify({"status": "already_complained", "message": "Вы уже жаловались на это место"}), 400

    if suggested_category_id:
        suggested_category = db_session.query(Category).get(int(suggested_category_id))
        if suggested_category:
            reason = f"{reason}. Предложенная эмоция: {suggested_category.name}"

    db_session.add(Complaint(place_id=place_id, ip_address=user_ip, reason=reason))
    place.complaints_count = (place.complaints_count or 0) + 1
    db_session.commit()

    return jsonify({"status": "ok", "message": "Жалоба отправлена администратору", "complaints_count": place.complaints_count})


@app.route("/")
def index():
    categories = db_session.query(Category).filter(Category.is_active == True).all()
    return render_template("index.html", categories=categories)


@app.route("/place/<int:place_id>")
def place_detail(place_id):
    place = db_session.query(Place).get(place_id)
    if not place:
        flash("Место не найдено", "error")
        return redirect(url_for("index"))
    return render_template("place_detail.html", place=place)


@app.route("/suggest", methods=["GET", "POST"])
def suggest_place():
    categories = db_session.query(Category).filter(Category.is_active == True).all()

    if request.method == "POST":
        try:
            lat = float(request.form.get("latitude", 56.0106))
            lon = float(request.form.get("longitude", 92.8526))
            name = clean_value(request.form.get("name"))
            category_id = int(request.form.get("category_id"))

            exists = db_session.query(Place).filter(func.lower(Place.name) == name.lower()).first()
            if exists:
                flash("⚠️ Такое место уже есть на карте. Дубли не добавляются.", "error")
                return redirect(url_for("suggest_place"))

            wiki_data = search_wikipedia(name, lat, lon)
            is_known_place = bool(wiki_data)

            place = Place(
                name=name,
                category_id=category_id,
                description=clean_value(request.form.get("description")),
                address=clean_value(request.form.get("address")),
                latitude=lat,
                longitude=lon,
                photo_url=wiki_data.get("thumbnail", "") if wiki_data else clean_value(request.form.get("photo_url")),
                photo_source="Wikipedia" if wiki_data else clean_value(request.form.get("photo_source")),
                photo_author=clean_value(request.form.get("photo_author")),
                track_url=clean_value(request.form.get("track_url")),
                track_author=clean_value(request.form.get("track_author")),
                track_author_death_year=request.form.get("track_author_death_year") or None,
                track_title=clean_value(request.form.get("track_title")),
                wifi_free=request.form.get("wifi_free") == "on",
                wheelchair_accessible=request.form.get("wheelchair_accessible") == "on",
                is_verified=is_known_place,
                votes_count=0,
                complaints_count=0,
                views_count=0
            )

            db_session.add(place)
            db_session.commit()

            return redirect(url_for("index"))
        except Exception as e:
            db_session.rollback()
            flash(f"Ошибка: {e}", "error")

    return render_template("suggest_place.html", categories=categories)


@app.route("/ideas")
def ideas():
    return render_template("ideas.html")


@app.route("/settings")
def settings():
    return render_template("settings.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/sql_table")
def sql_table():
    return render_template("sql_table.html")


@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():
    super_admin_exists = db_session.query(Admin).filter(Admin.is_super_admin == True, Admin.is_approved == True).first()

    if request.method == "POST":
        username = clean_value(request.form.get("username"))
        email = clean_value(request.form.get("email"))
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        full_name = clean_value(request.form.get("full_name"))

        if not username or not email or not password:
            flash("Заполните все обязательные поля", "error")
            return redirect(url_for("admin_register"))

        if password != confirm_password:
            flash("Пароли не совпадают", "error")
            return redirect(url_for("admin_register"))

        if len(password) < 6:
            flash("Пароль должен содержать минимум 6 символов", "error")
            return redirect(url_for("admin_register"))

        existing = db_session.query(Admin).filter((Admin.username == username) | (Admin.email == email)).first()
        if existing:
            flash("Пользователь с таким логином или email уже существует", "error")
            return redirect(url_for("admin_register"))

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        admin = Admin(
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            is_super_admin=not bool(super_admin_exists),
            is_approved=not bool(super_admin_exists)
        )
        db_session.add(admin)
        db_session.commit()

        if not super_admin_exists:
            flash("✅ Супер-администратор создан! Теперь вы можете войти.", "success")
        else:
            flash("✅ Регистрация отправлена на одобрение супер-администратору.", "success")

        return redirect(url_for("admin_login"))

    return render_template("admin_register.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        admin = db_session.query(Admin).filter((Admin.username == username) | (Admin.email == username)).first()
        if admin:
            if not admin.is_approved:
                flash("❌ Ваша учётная запись ещё не одобрена супер-администратором.", "error")
                return redirect(url_for("admin_login"))

            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if admin.password_hash == password_hash:
                session["admin_id"] = admin.id
                session["admin_username"] = admin.username
                session["is_super_admin"] = admin.is_super_admin
                admin.last_login = datetime.utcnow()
                db_session.commit()
                flash(f"Добро пожаловать, {admin.full_name or admin.username}!", "success")
                return redirect(url_for("admin_dashboard"))

        flash("Неверный логин/email или пароль", "error")

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Вы вышли из системы", "info")
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    total_places = db_session.query(Place).filter(Place.is_verified == True).count()
    total_pending = db_session.query(Place).filter(Place.is_verified == False).count()
    pending_places = db_session.query(Place).filter(Place.is_verified == False).order_by(Place.votes_count.desc()).all()
    verified_places = db_session.query(Place).filter(Place.is_verified == True).order_by(Place.votes_count.desc()).all()
    places_with_complaints = db_session.query(Place).filter(Place.complaints_count >= 1).order_by(
        Place.complaints_count.desc()).all()

    # Места с отрицательным рейтингом (votes_count < 0)
    disliked_places = db_session.query(Place).filter(Place.is_verified == True, Place.votes_count < 0).order_by(
        Place.votes_count.asc()).all()

    categories = db_session.query(Category).all()

    admins = db_session.query(Admin).order_by(Admin.id.asc()).all()

    categories_stats = []
    for cat in categories:
        count = db_session.query(Place).filter(Place.category_id == cat.id, Place.is_verified == True).count()
        categories_stats.append({"name": cat.name, "icon": cat.icon, "color": cat.color, "count": count, "max": 10})

    age_stats = {"15-20": 0, "21-30": 0, "31-45": 0, "46+": 0}
    db_structure = [
        {"table": "categories", "description": "Категории эмоций"},
        {"table": "places", "description": "Основные места карты"},
        {"table": "votes", "description": "Оценки пользователей"},
        {"table": "complaints", "description": "Жалобы на эмоции"},
        {"table": "admins", "description": "Администраторы"},
        {"table": "suggested_places", "description": "Предложенные места"},
    ]

    return render_template(
        "admin_dashboard.html",
        total_places=total_places,
        total_pending=total_pending,
        pending_places=pending_places,
        verified_places=verified_places,
        places_with_complaints=places_with_complaints,
        disliked_places=disliked_places,  # ← добавьте эту переменную
        admins=admins,  # ← ЭТО САМОЕ ГЛАВНОЕ - передаём список администраторов
        categories_stats=categories_stats,
        age_stats=age_stats,
        db_structure=db_structure
    )


@app.route("/admin/seed-krasnoyarsk-places")
@admin_required
def admin_seed_krasnoyarsk_places():
    added, skipped = seed_krasnoyarsk_places_once()
    flash(f"✅ Разовая загрузка выполнена. Добавлено: {added}. Пропущено дублей/ошибок: {skipped}.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/admins")
@admin_required
def admin_admins_list():
    if not session.get("is_super_admin"):
        flash("Доступ запрещён. Требуются права супер-администратора.", "error")
        return redirect(url_for("admin_dashboard"))

    pending_admins = db_session.query(Admin).filter(Admin.is_approved == False).all()
    active_admins = db_session.query(Admin).filter(Admin.is_approved == True).all()
    return render_template("admin_admins_list.html", pending_admins=pending_admins, active_admins=active_admins)


@app.route("/admin/admins/approve/<int:admin_id>")
@admin_required
def admin_approve_admin(admin_id):
    if not session.get("is_super_admin"):
        flash("Доступ запрещён", "error")
        return redirect(url_for("admin_dashboard"))

    admin = db_session.query(Admin).get(admin_id)
    if admin:
        admin.is_approved = True
        db_session.commit()
        flash(f"✅ Администратор '{admin.username}' одобрен!", "success")
    return redirect(url_for("admin_admins_list"))


@app.route("/admin/admins/delete/<int:admin_id>")
@admin_required
def admin_delete_admin(admin_id):
    if not session.get("is_super_admin"):
        flash("Доступ запрещён", "error")
        return redirect(url_for("admin_dashboard"))

    if admin_id == session.get("admin_id"):
        flash("❌ Нельзя удалить самого себя", "error")
        return redirect(url_for("admin_admins_list"))

    admin = db_session.query(Admin).get(admin_id)
    if admin:
        username = admin.username
        db_session.delete(admin)
        db_session.commit()
        flash(f"✅ Администратор '{username}' удалён", "success")
    return redirect(url_for("admin_admins_list"))


@app.route("/admin/admin/create", methods=["GET", "POST"])
@admin_required
def admin_create_admin():
    if not session.get("is_super_admin"):
        flash("Доступ запрещён. Требуются права супер-администратора.", "error")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = clean_value(request.form.get("username"))
        email = clean_value(request.form.get("email"))
        password = request.form.get("password")
        full_name = clean_value(request.form.get("full_name"))
        is_super_admin = request.form.get("is_super_admin") == "on"

        if not username or not email or not password:
            flash("Заполните все обязательные поля", "error")
            return redirect(url_for("admin_create_admin"))

        if len(password) < 6:
            flash("Пароль должен содержать минимум 6 символов", "error")
            return redirect(url_for("admin_create_admin"))

        existing = db_session.query(Admin).filter((Admin.username == username) | (Admin.email == email)).first()
        if existing:
            flash("Пользователь с таким логином или email уже существует", "error")
            return redirect(url_for("admin_create_admin"))

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        admin = Admin(username=username, email=email, password_hash=password_hash, full_name=full_name, is_super_admin=is_super_admin, is_approved=True)
        db_session.add(admin)
        db_session.commit()
        flash(f"✅ Администратор '{username}' создан!", "success")
        return redirect(url_for("admin_admins_list"))

    return render_template("admin_create_admin.html")


@app.route("/admin/place/add", methods=["GET", "POST"])
@admin_required
def admin_add_place():
    categories = db_session.query(Category).all()
    if request.method == "POST":
        try:
            address = clean_value(request.form.get("address"))
            lat_raw = request.form.get("latitude")
            lon_raw = request.form.get("longitude")
            if lat_raw and lon_raw:
                lat = float(lat_raw)
                lon = float(lon_raw)
            else:
                lat, lon = geocode_address(address)

            place = Place(
                name=clean_value(request.form.get("name")),
                category_id=int(request.form.get("category_id")),
                description=clean_value(request.form.get("description")),
                address=address,
                latitude=lat,
                longitude=lon,
                photo_url=clean_value(request.form.get("photo_url")),
                photo_source=clean_value(request.form.get("photo_source")),
                photo_author=clean_value(request.form.get("photo_author")),
                track_url=clean_value(request.form.get("track_url")),
                track_author=clean_value(request.form.get("track_author")),
                track_author_death_year=request.form.get("track_author_death_year") or None,
                track_title=clean_value(request.form.get("track_title")),
                wifi_free=request.form.get("wifi_free") == "on",
                wheelchair_accessible=request.form.get("wheelchair_accessible") == "on",
                is_verified=True,
                votes_count=0,
                complaints_count=0,
                views_count=0
            )
            db_session.add(place)
            db_session.commit()
            flash("✅ Место добавлено!", "success")
            return redirect(url_for("admin_dashboard"))
        except Exception as e:
            db_session.rollback()
            flash(f"Ошибка: {e}", "error")
    return render_template("admin_add_place.html", categories=categories)


@app.route("/admin/place/edit/<int:place_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_place(place_id):
    place = db_session.query(Place).get(place_id)
    if not place:
        flash("Место не найдено", "error")
        return redirect(url_for("admin_dashboard"))

    categories = db_session.query(Category).all()

    if request.method == "POST":
        try:
            place.name = clean_value(request.form.get("name"))
            place.category_id = int(request.form.get("category_id"))
            place.description = clean_value(request.form.get("description"))
            place.address = clean_value(request.form.get("address"))
            place.photo_url = clean_value(request.form.get("photo_url"))
            place.photo_source = clean_value(request.form.get("photo_source"))
            place.photo_author = clean_value(request.form.get("photo_author"))
            place.track_url = clean_value(request.form.get("track_url"))
            place.track_author = clean_value(request.form.get("track_author"))
            place.track_title = clean_value(request.form.get("track_title"))

            year = request.form.get("track_author_death_year")
            if year:
                place.track_author_death_year = int(year)

            place.wifi_free = request.form.get("wifi_free") == "on"
            place.wheelchair_accessible = request.form.get("wheelchair_accessible") == "on"

            db_session.commit()
            flash("✅ Место обновлено!", "success")
            return redirect(url_for("admin_dashboard"))
        except Exception as e:
            db_session.rollback()
            flash(f"Ошибка: {e}", "error")

    return render_template("admin_edit_place.html", place=place, categories=categories)


@app.route("/admin/place/delete/<int:place_id>")
@admin_required
def admin_delete_place(place_id):
    place = db_session.query(Place).get(place_id)
    if place:
        name = place.name
        db_session.delete(place)
        db_session.commit()
        flash(f"✅ Место '{name}' удалено", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/complaints/clear/<int:place_id>")
@admin_required
def admin_clear_complaints(place_id):
    if not session.get("is_super_admin"):
        flash("Доступ запрещён", "error")
        return redirect(url_for("admin_dashboard"))

    place = db_session.query(Place).get(place_id)
    if place:
        place.complaints_count = 0
        db_session.commit()
        flash(f"✅ Счётчик жалоб для '{place.name}' сброшен", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/export/kml")
@admin_required
def export_kml():
    try:
        import simplekml
        kml = simplekml.Kml(name="Эмоциональная карта Красноярска")
        places = db_session.query(Place).filter(Place.is_verified == True).all()

        for place in places:
            pnt = kml.newpoint(name=place.name)
            pnt.coords = [(place.longitude, place.latitude)]
            pnt.description = f"{place.description}\nКатегория: {place.category.name}"

        filename = f"emotional_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.kml"
        filepath = Path(filename)
        kml.save(str(filepath))
        return send_file(str(filepath), as_attachment=True, download_name=filename)
    except Exception as e:
        flash(f"Ошибка экспорта: {e}", "error")
        return redirect(url_for("admin_dashboard"))


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    init_categories()
    app.run(debug=True, use_reloader=False)
