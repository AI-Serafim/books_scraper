# tests/test_scraper.py
import pytest
import json
from unittest.mock import patch, MagicMock
from scraper import get_book_data, scrape_books

# пример HTML-кода страницы книги (минимизированный для теста)
MOCK_BOOK_HTML = """
<html>
<head><title>Test Book</title></head>
<body>
<div class="col-sm-6 product_main">
    <h1>Test Book Title</h1>
    <p class="price_color">£10.00</p>
    <p class="instock availability">In stock (5 available)</p>
    <p class="star-rating Five">
        <i class="icon-star"></i>
        <i class="icon-star"></i>
        <i class="icon-star"></i>
        <i class="icon-star"></i>
        <i class="icon-star"></i>
    </p>
</div>
<div id="product_description">
    <h2>Product Description</h2>
</div>
<p>This is a test description.</p>
<table class="table table-striped">
    <tr><th>UPC</th><td>1234567890ABC</td></tr>
    <tr><th>Product Type</th><td>Books</td></tr>
    <tr><th>Price (excl. tax)</th><td>£10.00</td></tr>
    <tr><th>Price (incl. tax)</th><td>£12.00</td></tr>
    <tr><th>Tax</th><td>£2.00</td></tr>
    <tr><th>Availability</th><td>In stock (5 available)</td></tr>
    <tr><th>Number of reviews</th><td>42</td></tr>
</table>
<ul class="breadcrumb">
    <li><a href="/">Home</a></li>
    <li><a href="/category/books/">Books</a></li>
    <li><a href="/category/books/fiction/">Fiction</a></li>
    <li class="active">Test Book Title</li>
</ul>
<div class="item active">
    <img src="/media/cache/test_image.jpg" alt="Test Book">
</div>
</body>
</html>
"""

# пример HTML-кода страницы каталога (минимизированный)
MOCK_CATALOG_PAGE_HTML = """
<html>
<body>
<ol class="row">
    <li class="col-xs-6 col-sm-4 col-md-3 col-lg-3">
        <article class="product_pod">
            <h3><a title="Test Book Title" href="test-book-title_123/index.html">Test Book Title</a></h3>
        </article>
    </li>
    <li class="col-xs-6 col-sm-4 col-md-3 col-lg-3">
        <article class="product_pod">
            <h3><a title="Another Test Book" href="another-test-book_456/index.html">Another Test Book</a></h3>
        </article>
    </li>
</ol>
</body>
</html>
"""

# пример HTML для 404 ошибки
MOCK_404_HTML = "<html><body><h1>Not Found</h1></body></html>"

# тесты для get_book_data 

class TestGetBookData:
    """
    Тесты для функции get_book_data.
    """
    @patch('scraper.requests.get') # Мокаем requests.get, так как мы передаём session=None
    def test_get_book_data_success(self, mock_get):
        """
        Тест: get_book_data возвращает словарь с ожидаемыми ключами и значениями при успешном парсинге.
        """
        # Настраиваем мок-объект
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = MOCK_BOOK_HTML
        mock_response.encoding = 'utf-8'
        mock_get.return_value = mock_response

        book_url = "http://books.toscrape.com/catalogue/test-book-title_123/index.html"
        result = get_book_data(book_url, session=None) # Передаём session=None

        # Проверки
        assert isinstance(result, dict)
        assert result["name"] == "Test Book Title"
        assert result["price"] == "£10.00"
        assert result["availability"] == "In stock (5 available)"
        assert result["rating"] == "Five"
        assert result["description"] == "This is a test description."
        assert result["upc"] == "1234567890ABC"
        assert result["product_type"] == "Books"
        assert result["price_excl_tax"] == "£10.00"
        assert result["price_incl_tax"] == "£12.00"
        assert result["tax"] == "£2.00"
        assert result["number_of_reviews"] == "42"
        assert result["genre"] == "Fiction"
        assert result["image_link"] == "http://books.toscrape.com/media/cache/test_image.jpg"

    @patch('scraper.requests.get')
    def test_get_book_data_handles_missing_elements(self, mock_get):
        """
        Тест: get_book_data возвращает None для отсутствующих полей.
        """
        # HTML без некоторых элементов
        minimal_html = """
        <html><body>
        <div class="col-sm-6 product_main">
            <h1>Minimal Book</h1>
        </div>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = minimal_html
        mock_response.encoding = 'utf-8'
        mock_get.return_value = mock_response

        book_url = "http://books.toscrape.com/catalogue/minimal-book_999/index.html"
        result = get_book_data(book_url, session=None)

        # Проверки
        assert result["name"] == "Minimal Book"
        assert result["price"] is None
        assert result["availability"] is None
        assert result["rating"] is None
        assert result["description"] is None
        assert result["upc"] is None
        assert result["genre"] is None
        assert result["image_link"] is None

    @patch('scraper.requests.get')
    def test_get_book_data_handles_404(self, mock_get):
        """
        Тест: get_book_data возвращает пустой словарь при ошибке HTTP (например, 404).
        """
        # Настраиваем мок-объект на 404
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = MOCK_404_HTML
        mock_response.encoding = 'utf-8'
        mock_get.return_value = mock_response

        book_url = "http://books.toscrape.com/catalogue/non-existent-book_999/index.html"
        result = get_book_data(book_url, session=None)

        # Проверка
        assert result == {}

# Тесты для scrape_books

class TestScrapeBooks:
    """
    Тесты для функции scrape_books.
    """
    @patch('scraper.requests.Session.get')
    def test_scrape_books_success(self, mock_session_get):
        """
        Тест: scrape_books возвращает список с ожидаемым количеством элементов.
        """
        # Имитируем ответы сессии
        # Страница 1
        mock_response_page_1 = MagicMock()
        mock_response_page_1.status_code = 200
        mock_response_page_1.text = MOCK_CATALOG_PAGE_HTML
        # Страница 2 (последняя)
        mock_response_page_2 = MagicMock()
        mock_response_page_2.status_code = 404 # Имитируем конец
        mock_response_page_2.text = MOCK_404_HTML

        # Настройка side_effect для возврата разных ответов
        mock_session_get.side_effect = [mock_response_page_1, mock_response_page_2]

        # Мокаем get_book_data, чтобы не парсить реальный HTML
        with patch('scraper.get_book_data') as mock_get_book_
            # Возвращаем фиктивные данные для двух книг
            mock_get_book_data.return_value = {"name": "Mocked Book"}

            result = scrape_books(save_to_file=False)

        # Проверка: вызваны ли методы для получения страниц
        assert mock_session_get.call_count == 2 # Должно вызваться 2 раза (1 и 2 страница)
        # Проверка: количество вызовов get_book_data (2 книги)
        assert mock_get_book_data.call_count == 2
        # Проверка: возвращённый список
        assert len(result) == 2
        assert result[0]["name"] == "Mocked Book"
        assert result[1]["name"] == "Mocked Book"

    @patch('scraper.requests.Session.get')
    def test_scrape_books_empty_result(self, mock_session_get):
        """
        Тест: scrape_books возвращает пустой список, если на странице нет книг.
        """
        # Имитируем ответ сессии без книг
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><ol class='row'></ol></body></html>" # Пустой список
        mock_session_get.return_value = mock_response

        result = scrape_books(save_to_file=False)

        # Проверка
        assert result == []
        # Проверка: вызвано только 1 раз, так как на второй итерации нет книг
        mock_session_get.assert_called_once()