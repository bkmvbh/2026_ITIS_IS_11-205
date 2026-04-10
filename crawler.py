#!/usr/bin/env python3
"""
Лабораторная работа №1 по ОИП — Краулер для habr.com
Скачивает 100 статей на русском языке с Хабра.

Использование:
    python3 crawler.py
"""

import os, re, time, logging
from collections import deque
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

# ── Настройки ────────────────────────────────────────────────────────────────
TARGET_PAGES   = 100
MIN_WORDS      = 1000
REQUEST_DELAY  = 1.0
OUTPUT_DIR     = "pages"
INDEX_FILE     = "index.txt"
ANTIINDEX_FILE = "antiindex.txt"

# Стартовые страницы — хабы с большим количеством статей
START_URLS = [
    "https://habr.com/ru/articles/",
    "https://habr.com/ru/hubs/python/articles/",
    "https://habr.com/ru/hubs/artificial_intelligence/articles/",
    "https://habr.com/ru/hubs/machine_learning/articles/",
]
# ─────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


def is_habr_article(url: str) -> bool:
    """Только статьи вида habr.com/ru/articles/XXXXXX/"""
    p = urlparse(url)
    if "habr.com" not in p.netloc:
        return False
    # Статьи имеют вид /ru/articles/123456/ или /ru/company/.../blog/123456/
    if re.search(r"/(?:articles|blog)/\d+/?$", p.path):
        return True
    return False


def is_habr_listing(url: str) -> bool:
    """Страницы-листинги с которых берём ссылки на статьи"""
    p = urlparse(url)
    if "habr.com" not in p.netloc:
        return False
    return bool(re.search(r"/ru/(articles|hubs|flows)/", p.path))


def get_page(url: str, session: requests.Session):
    for attempt in range(3):
        try:
            r = session.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r
        except Exception as e:
            log.warning(f"  Попытка {attempt+1}/3: {e}")
            time.sleep(2)
    return None


def extract_article_text(html: str) -> str:
    """Извлекает текст статьи Хабра из основного блока контента."""
    soup = BeautifulSoup(html, "html.parser")

    # Основной блок статьи на Хабре
    article = (
        soup.find("div", class_=re.compile(r"article-formatted-body")) or
        soup.find("div", {"id": "post-content-body"}) or
        soup.find("div", class_=re.compile(r"tm-article-body")) or
        soup.find("article")
    )

    if article:
        # Убираем мусор внутри статьи
        for tag in article.find_all(["script", "style", "figure", "aside"]):
            tag.decompose()
        return article.get_text(separator="\n", strip=True)

    # Fallback — весь body
    body = soup.find("body")
    if body:
        for tag in body.find_all(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return body.get_text(separator="\n", strip=True)
    return ""


def count_words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def is_russian(text: str) -> bool:
    total = len(text)
    if total == 0:
        return False
    return len(re.findall(r"[а-яёА-ЯЁ]", text)) / total > 0.20


def extract_links(html: str, base_url: str):
    """Возвращает (article_links, listing_links, anti_links)"""
    soup = BeautifulSoup(html, "html.parser")
    article_links = []
    listing_links = []
    anti_links    = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            anti_links.append(href)
            continue

        full = urljoin(base_url, href)
        p = urlparse(full)
        clean = p._replace(fragment="", query="").geturl()

        if is_habr_article(clean):
            article_links.append(clean)
        elif is_habr_listing(clean):
            listing_links.append(clean)
        else:
            anti_links.append(clean)

    return article_links, listing_links, anti_links


def crawl():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    visited        = set()
    article_queue  = deque()
    listing_queue  = deque(START_URLS)
    saved          = 0
    index_entries  = []
    anti_set       = set()

    session = requests.Session()
    log.info(f"Старт краулинга Хабра. Цель: {TARGET_PAGES} статей с ≥{MIN_WORDS} словами")

    while saved < TARGET_PAGES:
        # Сначала берём статьи из очереди
        if article_queue:
            url = article_queue.popleft()
        elif listing_queue:
            # Если статей нет — заходим на листинг и собираем ссылки
            listing_url = listing_queue.popleft()
            if listing_url in visited:
                continue
            visited.add(listing_url)
            log.info(f"  [листинг] {listing_url}")
            resp = get_page(listing_url, session)
            if resp:
                art, lst, anti = extract_links(resp.text, listing_url)
                for lnk in art:
                    if lnk not in visited:
                        article_queue.append(lnk)
                for lnk in lst:
                    if lnk not in visited:
                        listing_queue.append(lnk)
                for lnk in anti:
                    anti_set.add(lnk)
                # Добавляем следующую страницу листинга (пагинация)
                next_page = listing_url.rstrip("/") + "/page2/"
                if next_page not in visited:
                    listing_queue.appendleft(next_page)
            time.sleep(REQUEST_DELAY)
            continue
        else:
            log.warning("Очередь пуста, статей не хватает!")
            break

        if url in visited:
            continue
        visited.add(url)

        log.info(f"[{saved}/{TARGET_PAGES}] {url}")
        resp = get_page(url, session)
        if not resp:
            continue
        if "text/html" not in resp.headers.get("Content-Type", ""):
            continue

        html = resp.text
        art, lst, anti = extract_links(html, url)
        for lnk in art:
            if lnk not in visited:
                article_queue.append(lnk)
        for lnk in lst:
            if lnk not in visited:
                listing_queue.append(lnk)
        for lnk in anti:
            anti_set.add(lnk)

        text = extract_article_text(html)
        wc   = count_words(text)

        if wc < MIN_WORDS:
            log.info(f"  Мало слов: {wc}, пропускаем")
            time.sleep(REQUEST_DELAY)
            continue
        if not is_russian(text):
            log.info(f"  Не русский текст, пропускаем")
            time.sleep(REQUEST_DELAY)
            continue

        saved += 1
        with open(f"{OUTPUT_DIR}/{saved}.txt", "w", encoding="utf-8") as f:
            f.write(text)
        index_entries.append((saved, url))
        log.info(f"  ✓ Сохранено {saved}.txt ({wc} слов)")
        time.sleep(REQUEST_DELAY)

    # Сохраняем index.txt
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        for num, url in index_entries:
            f.write(f"{num}\t{url}\n")

    # Сохраняем antiindex.txt
    with open(ANTIINDEX_FILE, "w", encoding="utf-8") as f:
        for lnk in sorted(anti_set):
            f.write(lnk + "\n")

    log.info(f"\n{'='*50}")
    log.info(f"Готово! Сохранено статей: {saved}")
    log.info(f"Папка: ./{OUTPUT_DIR}/")
    log.info(f"Индекс: ./{INDEX_FILE}")


if __name__ == "__main__":
    crawl()
