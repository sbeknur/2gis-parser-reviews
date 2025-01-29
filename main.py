import time
import json
import csv
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright

def get_comments(url, page):
    """
    Открывает указанную страницу, скроллит отзывы и возвращает список all_comments.
    Передаём в аргументах уже созданную page, чтобы не открывать/закрывать браузер каждый раз.
    """
    all_comments = []

    # Функция-обработчик, которая добавляет комментарии в список
    def handle_response(response):
        if "comments" in response.url:
            try:
                data = response.json()
                # Проверим, что там действительно есть ключ "comments"
                if "comments" in data:
                    all_comments.extend(data["comments"])
            except Exception as e:
                print("Ошибка при парсинге JSON:", e)

    # Подключаем обработчик под ответ
    page.on("response", handle_response)

    # Переходим по ссылке
    page.goto(url)
    page.wait_for_load_state("networkidle")

    # Селектор для отдельного отзыва (проверьте в DevTools, что он актуален)
    review_selector = "div._1k5soqfl"

    while True:
        old_count = len(page.query_selector_all(review_selector))
        if old_count == 0:
            # если совсем нет отзывов
            break

        # Скроллим к последнему отзыву
        page.locator(review_selector).nth(old_count - 1).scroll_into_view_if_needed()
        time.sleep(2)  # подождём подгрузку данных

        # Снова считаем
        new_count = len(page.query_selector_all(review_selector))
        if new_count == old_count:
            # Если число не изменилось, значит подгрузка остановилась
            break

    # Отключаем обработчик, чтобы не повлиять на другие страницы
    page.remove_listener("response", handle_response)

    return all_comments

def save_as_json(data, filename):
    """Сохранение данных в JSON файл."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_as_csv(data, filename):
    """
    Сохранение данных в CSV.
    Поскольку структура комментариев может быть разная, 
    здесь просто берём ключи первого элемента как заголовки столбцов.
    Если список пуст, не сможем определить столбцы — нужна дополнительная логика.
    """
    if not data:
        print("Нет данных для сохранения в CSV.")
        return
    # Берём все ключи первого комментария
    fieldnames = data[0].keys()

    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            # На случай, если у некоторых комментариев отличаются наборы полей
            # (чтобы не было исключений), используем dict.get
            writer.writerow({fn: row.get(fn) for fn in fieldnames})

def save_as_xml(data, filename):
    """Сохранение данных в XML."""
    root = ET.Element("comments")
    for c in data:
        comment_el = ET.SubElement(root, "comment")
        for k, v in c.items():
            # Преобразуем всё в строки
            child = ET.SubElement(comment_el, k)
            child.text = str(v)
    tree = ET.ElementTree(root)
    tree.write(filename, encoding='utf-8', xml_declaration=True)

def main():
    # Пример массива ссылок (можете заменить на любой набор URL)
    urls = [
        "https://2gis.kz/astana/search/%D0%9A%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%B8%D0%B9%20%D1%8F%D0%B7%D1%8B%D0%BA%20(%D0%BA%D1%83%D1%80%D1%81%D1%8B%20%D0%BA%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%BE%D0%B3%D0%BE%20%D1%8F%D0%B7%D1%8B%D0%BA%D0%B0)/attributeId/70000201006749283/firm/70000001018369329/71.417986%2C51.124297/tab/reviews?m=71.443111%2C51.12972%2F10.66"
        "https://2gis.kz/astana/search/%D0%9A%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%B8%D0%B9%20%D1%8F%D0%B7%D1%8B%D0%BA%20(%D0%BA%D1%83%D1%80%D1%81%D1%8B%20%D0%BA%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%BE%D0%B3%D0%BE%20%D1%8F%D0%B7%D1%8B%D0%BA%D0%B0)/attributeId/70000201006749283/firm/70000001059717979/71.42735%2C51.113237/tab/reviews?m=71.443111%2C51.12972%2F10.66",
        "https://2gis.kz/astana/search/%D0%9A%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%B8%D0%B9%20%D1%8F%D0%B7%D1%8B%D0%BA%20(%D0%BA%D1%83%D1%80%D1%81%D1%8B%20%D0%BA%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%BE%D0%B3%D0%BE%20%D1%8F%D0%B7%D1%8B%D0%BA%D0%B0)/attributeId/70000201006749283/firm/70000001082581441/71.390434%2C51.131573/tab/reviews?m=71.443111%2C51.12972%2F10.66",
        "https://2gis.kz/astana/search/%D0%9A%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%B8%D0%B9%20%D1%8F%D0%B7%D1%8B%D0%BA%20(%D0%BA%D1%83%D1%80%D1%81%D1%8B%20%D0%BA%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%BE%D0%B3%D0%BE%20%D1%8F%D0%B7%D1%8B%D0%BA%D0%B0)/attributeId/70000201006749283/firm/70000001082581441/71.390434%2C51.131573/tab/reviews?m=71.443111%2C51.12972%2F10.66",
        "https://2gis.kz/astana/search/%D0%9A%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%B8%D0%B9%20%D1%8F%D0%B7%D1%8B%D0%BA%20(%D0%BA%D1%83%D1%80%D1%81%D1%8B%20%D0%BA%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%BE%D0%B3%D0%BE%20%D1%8F%D0%B7%D1%8B%D0%BA%D0%B0)/attributeId/70000201006749283/firm/70000001081314767/71.403318%2C51.10992/tab/reviews?m=71.443111%2C51.12972%2F10.66",
        "https://2gis.kz/astana/search/%D0%9A%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%B8%D0%B9%20%D1%8F%D0%B7%D1%8B%D0%BA%20(%D0%BA%D1%83%D1%80%D1%81%D1%8B%20%D0%BA%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%BE%D0%B3%D0%BE%20%D1%8F%D0%B7%D1%8B%D0%BA%D0%B0)/attributeId/70000201006749283/firm/70000001082747308/71.395133%2C51.123073/tab/reviews?m=71.443111%2C51.12972%2F10.66",
        "https://2gis.kz/astana/search/%D0%9A%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%B8%D0%B9%20%D1%8F%D0%B7%D1%8B%D0%BA%20(%D0%BA%D1%83%D1%80%D1%81%D1%8B%20%D0%BA%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%BE%D0%B3%D0%BE%20%D1%8F%D0%B7%D1%8B%D0%BA%D0%B0)/attributeId/70000201006749283/firm/70000001061805613/71.43117%2C51.166362/tab/reviews?m=71.443111%2C51.12972%2F10.66",
        "https://2gis.kz/astana/search/%D0%9A%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%B8%D0%B9%20%D1%8F%D0%B7%D1%8B%D0%BA%20(%D0%BA%D1%83%D1%80%D1%81%D1%8B%20%D0%BA%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%BE%D0%B3%D0%BE%20%D1%8F%D0%B7%D1%8B%D0%BA%D0%B0)/attributeId/70000201006749283/firm/70000001051582827/71.41166%2C51.142879/tab/reviews?m=71.443111%2C51.12972%2F10.66",
        "https://2gis.kz/astana/search/%D0%9A%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%B8%D0%B9%20%D1%8F%D0%B7%D1%8B%D0%BA%20(%D0%BA%D1%83%D1%80%D1%81%D1%8B%20%D0%BA%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%BE%D0%B3%D0%BE%20%D1%8F%D0%B7%D1%8B%D0%BA%D0%B0)/attributeId/70000201006749283/firm/70000001044593719/71.425644%2C51.169037/tab/reviews?m=71.443111%2C51.12972%2F10.66",
        "https://2gis.kz/astana/search/%D0%9A%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%B8%D0%B9%20%D1%8F%D0%B7%D1%8B%D0%BA%20(%D0%BA%D1%83%D1%80%D1%81%D1%8B%20%D0%BA%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D0%BA%D0%BE%D0%B3%D0%BE%20%D1%8F%D0%B7%D1%8B%D0%BA%D0%B0)/attributeId/70000201006749283/firm/70000001040868982/71.430998%2C51.123726/tab/reviews?m=71.443111%2C51.12972%2F10.66"
    ]

    # Общий список для всех комментариев
    total_comments = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for link in urls:
            print(f"Обрабатываем: {link}")
            comments = get_comments(link, page)
            # Добавим в общий список (можем так же хранить в виде словаря по ссылке)
            total_comments.extend(comments)

        # Сохраняем во все форматы
        print(f"Всего комментариев собрано: {len(total_comments)}")

        save_as_json(total_comments, "comments.json")
        save_as_csv(total_comments, "comments.csv")
        save_as_xml(total_comments, "comments.xml")

        browser.close()

if __name__ == "__main__":  
    main()
