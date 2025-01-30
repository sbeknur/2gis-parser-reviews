import time
import json
import csv
import xml.etree.ElementTree as ET
from datetime import datetime
from playwright.sync_api import sync_playwright

def scroll_to_last_review(page, review_selector):
    """
    Прокручивает страницу до тех пор, пока количество элементов,
    соответствующих review_selector, не перестанет меняться.
    Возвращает список найденных элементов.
    """
    while True:
        old_count = len(page.query_selector_all(review_selector))
        if old_count == 0:
            break

        # Скроллим к последнему отзыву
        page.locator(review_selector).nth(old_count - 1).scroll_into_view_if_needed()
        time.sleep(2)  # Небольшая пауза, чтобы данные успели подгрузиться

        new_count = len(page.query_selector_all(review_selector))
        if new_count == old_count:
            # Если число не изменилось, значит подгрузка остановилась
            break

    return page.query_selector_all(review_selector)

def parse_site(page, url):
    """
    Переходит по адресу url, скроллит к последнему отзыву.
    Затем собирает:
    - company_name (селектор: h1._cwjbox>span)
    - rating (селектор: div._y10azs)
    - total_reviews (селектор: span._1xhlznaa)
    - список отзывов (review_selector = div._1k5soqfl)
      где каждый отзыв состоит из:
        user_name: span._16s5yj36
        date: div._139ll30 (из строки удаляем ", отредактирован" 
                            и обрабатываем дату формата "14 июля 2021")
        rating: div._1fkin5c (количество span в этом теге)
        text: a._1oir7fah
    Возвращает словарь нужной структуры.
    """

    # Карта русских названий месяцев для парсинга
    months_map = {
        "января": "01",
        "февраля": "02",
        "марта": "03",
        "апреля": "04",
        "мая": "05",
        "июня": "06",
        "июля": "07",
        "августа": "08",
        "сентября": "09",
        "октября": "10",
        "ноября": "11",
        "декабря": "12",
    }

    page.goto(url)
    page.wait_for_load_state("networkidle")

    # Парсим шапку компании
    company_name_elem = page.query_selector("h1._cwjbox>span")
    company_name = company_name_elem.inner_text() if company_name_elem else ""

    rating_elem = page.query_selector("div._y10azs")
    rating = rating_elem.inner_text() if rating_elem else ""

    total_reviews_elem = page.query_selector("span._1xhlznaa")
    total_reviews = total_reviews_elem.inner_text() if total_reviews_elem else ""

    # Теперь работаем с отзывами
    review_selector = "div._1k5soqfl"
    review_elements = scroll_to_last_review(page, review_selector)

    reviews_data = []
    for review_elem in review_elements:
        # Имя пользователя
        user_name_elem = review_elem.query_selector("span._16s5yj36")
        user_name = user_name_elem.inner_text() if user_name_elem else ""

        # Дата
        date_elem = review_elem.query_selector("div._139ll30")
        raw_date_text = date_elem.inner_text() if date_elem else ""
        # Удаляем ", отредактирован"
        raw_date_text = raw_date_text.replace(", отредактирован", "").strip()

        # Парсим "14 июля 2021"
        parts = raw_date_text.split()
        if len(parts) == 3:
            day_str, month_str, year_str = parts
            # Преобразуем месяц
            month_num = months_map.get(month_str.lower(), "01")
            # Собираем в формат DD.MM.YYYY для datetime
            date_for_parsing = f"{day_str}.{month_num}.{year_str}"
            try:
                parsed_date = datetime.strptime(date_for_parsing, "%d.%m.%Y")
                # Сохраняем в удобном формате (ISO, например)
                date_text = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                # Если дата не подошла — оставляем исходный текст
                date_text = raw_date_text
        else:
            date_text = raw_date_text

        # Рейтинг (количество <span> внутри div._1fkin5c)
        rating_div = review_elem.query_selector("div._1fkin5c")
        if rating_div:
            star_spans = rating_div.query_selector_all("span")
            review_rating = len(star_spans)
        else:
            review_rating = 0

        # Текст отзыва
        text_elem = review_elem.query_selector("a._1oir7fah")
        text = text_elem.inner_text() if text_elem else ""

        reviews_data.append({
            "user_name": user_name,
            "date": date_text,
            "rating": review_rating,
            "text": text
        })

    # Формируем результат для одного сайта
    result = {
        "company_name": company_name,
        "rating": rating,
        "total_reviews": total_reviews,
        "reviews": reviews_data
    }
    return result

def save_as_json(all_data, filename):
    """
    Сохраняет список компаний (all_data) в JSON.
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)
    print(f"[INFO] Сохранено в {filename}")

def save_as_csv(all_data, filename):
    """
    Сохраняет данные в CSV.
    Здесь каждая строка — это один отзыв.
    Поля компании (company_name, rating, total_reviews) дублируются для каждого отзыва.
    """
    # Заголовки CSV
    fieldnames = [
        "company_name", 
        "company_rating", 
        "company_total_reviews", 
        "user_name", 
        "review_date", 
        "review_rating", 
        "review_text"
    ]
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for company in all_data:
            company_name = company.get("company_name", "")
            company_rating = company.get("rating", "")
            company_total_reviews = company.get("total_reviews", "")
            for review in company.get("reviews", []):
                row = {
                    "company_name": company_name,
                    "company_rating": company_rating,
                    "company_total_reviews": company_total_reviews,
                    "user_name": review.get("user_name", ""),
                    "review_date": review.get("date", ""),
                    "review_rating": review.get("rating", ""),
                    "review_text": review.get("text", "")
                }
                writer.writerow(row)
    print(f"[INFO] Сохранено в {filename}")

def save_as_xml(all_data, filename):
    """
    Сохраняет данные в XML.
    Структура:
    <companies>
      <company>
        <company_name>...</company_name>
        <rating>...</rating>
        <total_reviews>...</total_reviews>
        <reviews>
          <review>
            <user_name>...</user_name>
            <date>...</date>
            <rating>...</rating>
            <text>...</text>
          </review>
          ...
        </reviews>
      </company>
      ...
    </companies>
    """
    root = ET.Element("companies")

    for company in all_data:
        company_el = ET.SubElement(root, "company")

        # Тэги с данными компании
        cn_el = ET.SubElement(company_el, "company_name")
        cn_el.text = str(company.get("company_name", ""))

        r_el = ET.SubElement(company_el, "rating")
        r_el.text = str(company.get("rating", ""))

        tr_el = ET.SubElement(company_el, "total_reviews")
        tr_el.text = str(company.get("total_reviews", ""))

        # Блок отзывов
        reviews_el = ET.SubElement(company_el, "reviews")
        for review in company.get("reviews", []):
            review_el = ET.SubElement(reviews_el, "review")

            uname_el = ET.SubElement(review_el, "user_name")
            uname_el.text = str(review.get("user_name", ""))

            date_el = ET.SubElement(review_el, "date")
            date_el.text = str(review.get("date", ""))

            rating_el = ET.SubElement(review_el, "rating")
            rating_el.text = str(review.get("rating", ""))

            text_el = ET.SubElement(review_el, "text")
            text_el.text = str(review.get("text", ""))

    tree = ET.ElementTree(root)
    tree.write(filename, encoding="utf-8", xml_declaration=True)
    print(f"[INFO] Сохранено в {filename}")

def main():
    # Список URL для парсинга
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

    all_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for link in urls:
            print(f"Обрабатываем: {link}")
            site_data = parse_site(page, link)
            all_data.append(site_data)

        browser.close()

    # Сохраняем итоговые данные во все форматы
    save_as_json(all_data, "comments.json")
    save_as_csv(all_data, "comments.csv")
    save_as_xml(all_data, "comments.xml")

    print("Готово. Данные собраны и сохранены в comments.json, comments.csv, comments.xml.")

if __name__ == "__main__":
    main()
