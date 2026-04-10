#!/usr/bin/env python3
"""
Лабораторная работа №2 по ОИП — Токенизация, лемматизация, стоп-слова.

Читает файлы из папки pages/ (выход лаб №1),
обрабатывает каждый документ и сохраняет результат в папку processed/.

Использование:
    python3 processing.py

Зависимости:
    pip install pymorphy3 nltk
"""

import os
import re
import logging
import pymorphy3
import nltk
from nltk.corpus import stopwords

# ── Настройки ────────────────────────────────────────────────────────────────
INPUT_DIR  = "pages"      # папка с файлами от лаб №1
OUTPUT_DIR = "processed"  # папка для обработанных файлов
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


def download_nltk_data():
    """Скачивает нужные данные NLTK если их нет."""
    try:
        stopwords.words("russian")
    except LookupError:
        log.info("Скачиваем стоп-слова NLTK...")
        nltk.download("stopwords", quiet=True)


def tokenize(text: str) -> list[str]:
    """Токенизация — выделяем только слова из кириллических букв."""
    tokens = re.findall(r"[а-яёА-ЯЁ]+", text)
    return [t.lower() for t in tokens]


def lemmatize(tokens: list[str], morph: pymorphy3.MorphAnalyzer) -> list[str]:
    """Лемматизация — приводим каждое слово к начальной форме."""
    return [morph.parse(token)[0].normal_form for token in tokens]


def remove_stopwords(tokens: list[str], stop_words: set) -> list[str]:
    """Удаляем стоп-слова."""
    return [t for t in tokens if t not in stop_words]


def process_file(filepath: str, morph: pymorphy3.MorphAnalyzer, stop_words: set) -> list[str]:
    """Полная обработка одного файла: токенизация → лемматизация → стоп-слова."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    tokens = tokenize(text)
    lemmas = lemmatize(tokens, morph)
    result = remove_stopwords(lemmas, stop_words)
    return result


def main():
    if not os.path.exists(INPUT_DIR):
        log.error(f"Папка '{INPUT_DIR}' не найдена. Сначала запусти crawler.py (лаб №1).")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    download_nltk_data()

    morph      = pymorphy3.MorphAnalyzer()
    stop_words = set(stopwords.words("russian"))

    # Дополнительные стоп-слова характерные для Хабра
    extra_stops = {
        "это", "также", "который", "которая", "которое", "которые",
        "свой", "весь", "быть", "мочь", "год", "один", "два",
        "например", "однако", "поэтому", "хотя", "если", "когда",
        "чтобы", "потому", "просто", "очень", "уже", "ещё", "даже",
    }
    stop_words.update(extra_stops)

    files = sorted(
        [f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")],
        key=lambda x: int(x.replace(".txt", ""))
    )

    if not files:
        log.error(f"В папке '{INPUT_DIR}' нет .txt файлов.")
        return

    log.info(f"Найдено файлов: {len(files)}")
    log.info(f"Стоп-слов: {len(stop_words)}")

    for filename in files:
        filepath = os.path.join(INPUT_DIR, filename)
        log.info(f"Обработка: {filename}")

        tokens = process_file(filepath, morph, stop_words)

        out_path = os.path.join(OUTPUT_DIR, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(tokens))

        log.info(f"  ✓ Токенов после обработки: {len(tokens)}")

    log.info(f"\n{'='*50}")
    log.info(f"Готово! Обработано файлов: {len(files)}")
    log.info(f"Результаты в папке: ./{OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
