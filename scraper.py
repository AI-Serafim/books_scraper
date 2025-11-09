import time
import requests
import schedule
from bs4 import BeautifulSoup
import pprint
from urllib.parse import urljoin
import json

def get_book_data(book_url: str, session=None) -> dict:
    """
    Извлекает данные о книге с указанного URL страницы книги.
    Если передана сессия (session), то используем её, иначе requests.

    Функция отправляет HTTP-запрос на URL, парсит HTML-код страницы и извлекает
    следующую информацию о книге:
    - Название
    - Жанр 
    - Цена (с и без налога)
    - Налог
    - Наличие
    - Рейтинг
    - Описание
    - UPC (уникальный код)
    - Тип продукта
    - Количество отзывов
    - Ссылка на изображение

    Если какой-либо элемент не найден на странице, соответствующее поле
    в возвращаемом словаре будет равно None.

    Args:
        book_url (str): URL-адрес страницы книги на сайте.

    Returns:
        dict: Словарь с извлечёнными данными о книге. Ключи:
              - 'name': str or None
              - 'genre': str or None
              - 'price': str or None
              - 'availability': str or None
              - 'rating': str or None
              - 'description': str or None
              - 'upc': str or None
              - 'product_type': str or None
              - 'price_excl_tax': str or None
              - 'price_incl_tax': str or None
              - 'tax': str or None
              - 'number_of_reviews': str or None
              - 'image_link': str or None
              В случае ошибки HTTP или отсутствия страницы возвращает пустой словарь.
    """
    # НАЧАЛО ВАШЕГО РЕШЕНИЯ
    if session is not None:
        response = session.get(book_url)
    else:
        response = requests.get(book_url)
    response.encoding = 'utf-8'

    if response.status_code != 200:
        print(f"Ошибка загрузки страницы: {response.status_code}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    product_main = soup.find("div", attrs={"class": "col-sm-6 product_main"})

    # извлечение из product_main с проверками 
    if product_main:
        # наименование
        h1_tag = product_main.find("h1")
        book_name = h1_tag.get_text(strip=True) if h1_tag else None

        # цена
        price_tag = product_main.find("p", attrs={"class": "price_color"})
        price = price_tag.get_text(strip=True) if price_tag else None

        # наличие
        availability_tag = product_main.find("p", class_="instock availability")
        availability = availability_tag.get_text(strip=True) if availability_tag else None

        # рейтинг
        rating_tag = product_main.find("p", class_="star-rating")
        rating = None
        if rating_tag:
            classes = rating_tag.get("class")
            if classes and len(classes) >= 2:
                rating = classes[1]
    else:
        # если product_main не найден, устанавливаем все связанные переменные в None
        book_name = price = availability = rating = None
        print("Не найден product_main")

    # извлечение описания с проверкой 
    description_header = soup.find("div", attrs={"id": "product_description"})
    description = None
    if description_header:
        description_p = description_header.find_next_sibling("p")
        if description_p:
            description = description_p.get_text(strip=True)

    # извлечение из таблицы с проверками 
    table = soup.find("table", class_="table table-striped")
    if table:
        # функция для извлечения значения по заголовку
        def get_value_by_header(header_text):
            header_tag = table.find("th", string=header_text)
            if header_tag:
                parent_tr = header_tag.find_parent("tr")
                if parent_tr:
                    td_tag = parent_tr.find("td")
                    if td_tag:
                        return td_tag.get_text(strip=True)
            return None

        upc_value = get_value_by_header("UPC")
        product_type = get_value_by_header("Product Type")
        price_excl_tax = get_value_by_header("Price (excl. tax)")
        price_incl_tax = get_value_by_header("Price (incl. tax)")
        tax = get_value_by_header("Tax")
        # availability уже могла быть найдена в product_main, но берём из таблицы, если таблица есть
        availability = get_value_by_header("Availability")
        number_of_reviews = get_value_by_header("Number of reviews")
    else:
        # если таблица не найдена, устанавливаем все её переменные в None
        upc_value = product_type = price_excl_tax = price_incl_tax = tax = number_of_reviews = None

    # извлечение жанра
    breadcrumb_list = soup.find("ul", class_="breadcrumb")
    genre = None
    if breadcrumb_list:
        # Находим все ссылки внутри списка
        all_links = breadcrumb_list.find_all("a")
        if len(all_links) >= 2:
            genre = all_links[-1].get_text(strip=True) 
        elif len(all_links) == 1:
            # если только одна ссылка, то, возможно, жанр отсутствует или не определён
            genre = all_links[0].get_text(strip=True)
    
    # извлечение ссылки на обложку
    item_div = soup.find("div", class_="item active")
    image_link = None
    if item_div:
        img_tag = item_div.find("img")
        if img_tag and img_tag.has_attr("src"):
            image_link = img_tag["src"]
    if image_link:
        image_link = urljoin(book_url, image_link)

    # сбор данных в словарь 
    book_data = {
        "name": book_name,
        "genre": genre,
        "price": price,
        "availability": availability,
        "rating": rating,
        "description": description,
        "upc": upc_value,
        "product_type": product_type,
        "price_excl_tax": price_excl_tax,
        "price_incl_tax": price_incl_tax,
        "tax": tax,
        "number_of_reviews": number_of_reviews,
        "image_link": image_link
    }

    return book_data # возвращаем словарь
    # КОНЕЦ ВАШЕГО РЕШЕНИЯ

def scrape_books(save_to_file: bool = False) -> list:
    """
    Парсит все книги с сайта books.toscrape.com.

    Функция проходит по всем страницам каталога (page-1.html, page-2.html и т.д.),
    извлекает данные о каждой книге с помощью функции get_book_data и собирает
    их в один список. Может сохранить результат в файл books_data.txt.

    Args:
        save_to_file (bool, optional): Если True, результат будет сохранён
                                       в файл 'books_data.txt' в формате JSON.
                                       По умолчанию False.

    Returns:
        list: Список словарей, каждый из которых содержит данные
              о книге, полученные из get_book_data.
              Возвращает пустой список в случае ошибки.
    """
    # НАЧАЛО ВАШЕГО РЕШЕНИЯ
    with requests.Session() as session: # Создаём сессию
        all_books_data = []
        base_url = "http://books.toscrape.com/catalogue/page-{page_num}.html"
        page_num = 1

        while True:
            url = base_url.format(page_num=page_num)
            response = session.get(url) 
            if response.status_code != 200:
                print(f"Страница {url} не найдена или ошибка. Останавливаем сканирование.")
                break

            soup = BeautifulSoup(response.text, "html.parser")

            # найдём все элементы книг на странице
            book_articles = soup.find_all("article", class_="product_pod")

            if not book_articles:
                # если на странице нет книг, значит, это последняя страница или ошибка
                print(f"На странице {url} не найдено книг. Останавливаем сканирование.")
                break

            # для каждой книги на странице находим ссылку и вызываем get_book_data
            for book_article in book_articles:
                link_tag = book_article.find("h3").find("a")
                if link_tag and link_tag.has_attr("href"):
                    relative_book_url = link_tag["href"]
                    absolute_book_url = requests.compat.urljoin(url, relative_book_url)
                    # session в get_book_data
                    book_data = get_book_data(absolute_book_url, session)
                    if book_data:  
                        all_books_data.append(book_data)
                    # задержка, чтобы не перегружать сервер
                    time.sleep(0.1)

            page_num += 1

        if save_to_file:
            try:
                with open("artifacts/books_data.txt", "w", encoding="utf-8") as f:
                    # записываем список словарей в файл в формате JSON
                    json.dump(all_books_data, f, ensure_ascii=False, indent=4)
                print("Данные о книгах сохранены в 'books_data.txt'.")
            except IOError as e:
                print(f"Ошибка при сохранении файла: {e}")

        return all_books_data
    # КОНЕЦ ВАШЕГО РЕШЕНИЯ

# НАЧАЛО ВАШЕГО РЕШЕНИЯ
def run_scheduler(target_time: str = "19:00"):
    """
    Запускает планировщик для ежедневного выполнения scrape_books в заданное время.

    Args:
        target_time (str, optional): Время запуска в формате 'HH:MM'. По умолчанию '19:00'.
    """
    def job():
        """
        Обёртка для scrape_books, вызываемая schedule.
        """
        print(f"Запуск сбора данных в {time.strftime('%Y-%m-%d %H:%M:%S')}")
        scraped_data = scrape_books(save_to_file=True)
        print(f"Сбор завершён. Обработано {len(scraped_data)} книг. Данные сохранены в 'books_data.txt'.")

    # настраиваем расписание
    schedule.every().day.at(target_time).do(job)

    print(f"Планировщик запущен. Ожидание задачи на {target_time} ежедневно...")

    # бесконечный цикл
    while True:
        # проверяем, не нужно ли выполнить запланированную задачу
        schedule.run_pending()
        time.sleep(60)
# КОНЕЦ ВАШЕГО РЕШЕНИЯ

run_scheduler()