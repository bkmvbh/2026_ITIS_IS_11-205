#!/usr/bin/env python3
"""
Лабораторная работа №3 по ОИП — Инвертированный индекс и булев поиск.

Читает файлы из папки processed/ (выход лаб №2),
строит инвертированный индекс и сохраняет его в index_inverted.txt.
Затем выполняет булев поиск по индексу.

Использование:
    python3 inverted_index.py
"""

import os
import re
import logging
from collections import defaultdict

# ── Настройки ────────────────────────────────────────────────────────────────
INPUT_DIR    = "processed"           # папка с файлами от лаб №2
INDEX_FILE   = "index_inverted.txt"  # файл для сохранения инвертированного индекса
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


def build_index(input_dir: str) -> tuple[dict, int]:
    """
    Строит инвертированный индекс из папки с обработанными документами.
    Возвращает: (index, total_docs)
    index = { 'слово': {doc_id1, doc_id2, ...} }
    """
    index = defaultdict(set)
    total_docs = 0

    files = sorted(
        [f for f in os.listdir(input_dir) if f.endswith(".txt")],
        key=lambda x: int(x.replace(".txt", ""))
    )

    if not files:
        log.error(f"В папке '{input_dir}' нет файлов.")
        return {}, 0

    log.info(f"Строим индекс из {len(files)} документов...")

    for filename in files:
        doc_id = int(filename.replace(".txt", ""))
        total_docs = max(total_docs, doc_id)
        filepath = os.path.join(input_dir, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            tokens = [line.strip() for line in f if line.strip()]

        for token in tokens:
            index[token].add(doc_id)

    log.info(f"Индекс построен. Уникальных термов: {len(index)}")
    return dict(index), total_docs


def save_index(index: dict, filepath: str):
    """Сохраняет инвертированный индекс в файл, отсортированный по алфавиту."""
    with open(filepath, "w", encoding="utf-8") as f:
        for term in sorted(index.keys()):
            doc_ids = sorted(index[term])
            doc_ids_str = ", ".join(map(str, doc_ids))
            f.write(f"{term}: {doc_ids_str}\n")
    log.info(f"Индекс сохранён в '{filepath}'")


def boolean_search(query: str, index: dict, total_docs: int) -> set:
    """
    Булев поиск по инвертированному индексу.
    Поддерживает операторы: & (И), | (ИЛИ), ! (НЕ)
    А также русские слова: И, ИЛИ, НЕ
    """
    all_docs = set(range(1, total_docs + 1))

    # Нормализуем запрос — заменяем русские операторы на символы
    query = query.strip()
    query = re.sub(r'\bИЛИ\b', '|', query)
    query = re.sub(r'\bИ\b',   '&', query)
    query = re.sub(r'\bНЕ\b',  '!', query)

    # Токенизируем запрос — разбиваем на операнды и операторы
    tokens = re.findall(r'[!&|()]|[а-яёА-ЯЁa-zA-Z]+', query)

    def get_docs(term: str) -> set:
        """Возвращает множество документов содержащих терм."""
        return index.get(term.lower(), set()).copy()

    # Парсим выражение — простой рекурсивный спуск
    pos = [0]  # используем список чтобы менять внутри функций

    def parse_or():
        left = parse_and()
        while pos[0] < len(tokens) and tokens[pos[0]] == '|':
            pos[0] += 1
            right = parse_and()
            left = left | right
        return left

    def parse_and():
        left = parse_not()
        while pos[0] < len(tokens) and tokens[pos[0]] == '&':
            pos[0] += 1
            right = parse_not()
            left = left & right
        return left

    def parse_not():
        if pos[0] < len(tokens) and tokens[pos[0]] == '!':
            pos[0] += 1
            operand = parse_primary()
            return all_docs - operand
        return parse_primary()

    def parse_primary():
        if pos[0] >= len(tokens):
            return set()
        token = tokens[pos[0]]
        if token == '(':
            pos[0] += 1
            result = parse_or()
            if pos[0] < len(tokens) and tokens[pos[0]] == ')':
                pos[0] += 1
            return result
        else:
            pos[0] += 1
            return get_docs(token)

    return parse_or()


def run_examples(index: dict, total_docs: int):
    """Запускает 5 примеров булева поиска из задания."""

    # Выбираем 3 слова которые есть в индексе
    # Берём слова встречающиеся в разном количестве документов
    sorted_terms = sorted(index.items(), key=lambda x: len(x[1]), reverse=True)

    # word1 — встречается во многих документах
    # word2 — встречается в меньшем количестве
    # word3 — встречается в нескольких документах
    candidates = [(term, docs) for term, docs in sorted_terms if len(docs) >= 2]

    if len(candidates) < 3:
        log.warning("Недостаточно термов для примеров!")
        return

    word1 = candidates[0][0]
    word2 = candidates[len(candidates) // 3][0]
    word3 = candidates[len(candidates) // 2][0]

    print("\n" + "=" * 60)
    print(f"ПРИМЕРЫ БУЛЕВА ПОИСКА")
    print(f"  word1 = '{word1}' (в {len(index[word1])} документах)")
    print(f"  word2 = '{word2}' (в {len(index[word2])} документах)")
    print(f"  word3 = '{word3}' (в {len(index[word3])} документах)")
    print("=" * 60)

    examples = [
        f"{word1} & {word2} & {word3}",
        f"{word1} & {word2} & !{word3}",
        f"{word1} & {word2} | {word3}",
        f"{word1} & !{word2} | !{word3}",
        f"{word1} | {word2} | {word3}",
    ]

    for query in examples:
        result = boolean_search(query, index, total_docs)
        result_sorted = sorted(result)
        print(f"\nЗапрос: {query}")
        print(f"Найдено документов: {len(result_sorted)}")
        if result_sorted:
            # Показываем первые 10 если их много
            shown = result_sorted[:10]
            print(f"Документы: {shown}{'...' if len(result_sorted) > 10 else ''}")
        else:
            print("Документы: (нет результатов)")


def interactive_search(index: dict, total_docs: int):
    """Интерактивный режим поиска."""
    print("\n" + "=" * 60)
    print("ИНТЕРАКТИВНЫЙ ПОИСК")
    print("Операторы: & (И), | (ИЛИ), ! (НЕ)")
    print("Пример: искусственный & интеллект & !робот")
    print("Введите 'выход' для завершения")
    print("=" * 60)

    while True:
        query = input("\nЗапрос: ").strip()
        if query.lower() in ("выход", "exit", "quit", "q"):
            break
        if not query:
            continue
        try:
            result = boolean_search(query, index, total_docs)
            result_sorted = sorted(result)
            print(f"Найдено документов: {len(result_sorted)}")
            if result_sorted:
                shown = result_sorted[:20]
                print(f"Документы: {shown}{'...' if len(result_sorted) > 20 else ''}")
            else:
                print("Документы: (нет результатов)")
        except Exception as e:
            print(f"Ошибка в запросе: {e}")


def main():
    if not os.path.exists(INPUT_DIR):
        log.error(f"Папка '{INPUT_DIR}' не найдена. Сначала запусти processing.py (лаб №2).")
        return

    # Строим индекс
    index, total_docs = build_index(INPUT_DIR)
    if not index:
        return

    # Сохраняем в файл
    save_index(index, INDEX_FILE)

    # Запускаем 5 примеров из задания
    run_examples(index, total_docs)

    # Интерактивный поиск
    interactive_search(index, total_docs)


if __name__ == "__main__":
    main()
