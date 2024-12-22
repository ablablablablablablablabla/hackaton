from fastapi import FastAPI, HTTPException
from bs4 import BeautifulSoup
import requests
import re
from typing import List, Optional, Dict
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware


# Определение моделей данных с использованием Pydantic
class SkiPass(BaseModel):
    """
    Модель для хранения информации о конкретном ски-пассе

    Attributes:
        name: Название ски-пасса
        description: Описание ски-пасса (опционально)
        regular_price: Обычная цена (опционально)
        sakhalin_card_price: Цена по карте Сахалин (опционально)
    """
    name: str
    description: Optional[str]
    regular_price: Optional[int]
    sakhalin_card_price: Optional[int]


class Category(BaseModel):
    """
    Модель категории, содержащая список ски-пассов

    Attributes:
        name: Название категории
        passes: Список ски-пассов в данной категории
    """
    name: str
    passes: List[SkiPass]


class RootCategory(BaseModel):
    """
    Корневая категория, содержащая список всех подкатегорий

    Attributes:
        name: Название корневой категории (по умолчанию "Разовые подъемы")
        categories: Список всех подкатегорий
    """
    name: str = "Разовые подъемы"
    categories: List[Category]


class SkiPassResponse(BaseModel):
    """
    Модель ответа API

    Attributes:
        success: Флаг успешности операции
        data: Данные ответа в виде RootCategory
        error: Сообщение об ошибке (опционально)
    """
    success: bool
    data: RootCategory
    error: Optional[str] = None


# Инициализация приложения FastAPI с метаданными
app = FastAPI(
    title="Ski Pass Parser API",
    description="API для получения информации о ски-пассах с сайта ski-gv.ru",
    version="1.0.0"
)

# Настройка CORS для разрешения кросс-доменных запросов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с любых доменов
    allow_credentials=True,  # Разрешаем передачу учетных данных
    allow_methods=["*"],  # Разрешаем все HTTP методы
    allow_headers=["*"],  # Разрешаем все заголовки
)


def clean_price(text: str) -> Optional[int]:
    """
    Очистка и преобразование текстовой цены в целое число

    Args:
        text: Строка с ценой

    Returns:
        Optional[int]: Очищенная цена или None, если цена не указана
    """
    if text == '-':
        return None
    price = re.sub(r'[^\d]', '', text)  # Удаляем все символы кроме цифр
    return int(price) if price else None


def get_page_content(url: str) -> Optional[str]:
    """
    Загрузка HTML-содержимого страницы с использованием requests

    Args:
        url: URL страницы для загрузки

    Returns:
        Optional[str]: HTML-содержимое страницы

    Raises:
        HTTPException: В случае ошибки при загрузке страницы
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                      ' (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке страницы: {str(e)}")


def parse_ski_pass_table(html_content: str) -> Dict:
    """
    Парсинг HTML-таблицы с информацией о ски-пассах

    Args:
        html_content: HTML-содержимое страницы

    Returns:
        Dict: Структурированные данные о ски-пассах

    Raises:
        HTTPException: Если таблица не найдена на странице
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table')

    if not table:
        raise HTTPException(status_code=404, detail="Таблица не найдена на странице")

    categories_data = {}
    current_category = None
    is_first_category = True

    # Обход всех строк таблицы
    for row in table.find_all('tr'):
        # Пропускаем первую строку с градиентом
        if is_first_category and 'background' in str(row):
            is_first_category = False
            continue

        cells = row.find_all(['th', 'td'])

        # Обработка заголовка категории
        if len(cells) == 1 and cells[0].get('colspan') == '5':
            current_category = cells[0].get_text(strip=True)
            if current_category not in categories_data:
                categories_data[current_category] = []
            continue

        # Обработка строки с данными о ски-пассе
        if len(cells) >= 3 and current_category:
            name_cell = cells[0]

            # Извлечение названия
            name = name_cell.find('h3')
            if name:
                name = name.get_text(strip=True)
            else:
                name = name_cell.get_text(strip=True)

            # Извлечение описания
            description = name_cell.find('div')
            description = description.get_text(strip=True) if description else None

            # Извлечение цен
            regular_price = clean_price(cells[1].get_text(strip=True))
            sakhalin_card_price = clean_price(cells[2].get_text(strip=True))

            # Создание объекта ски-пасса
            ski_pass = SkiPass(
                name=name,
                description=description,
                regular_price=regular_price,
                sakhalin_card_price=sakhalin_card_price
            )

            categories_data[current_category].append(ski_pass)

    # Формирование итоговой иерархической структуры
    categories = [
        Category(name=category, passes=passes)
        for category, passes in categories_data.items()
    ]

    return RootCategory(categories=sorted(categories, key=lambda x: x.name))


# Определение маршрутов API

@app.get("/", response_model=SkiPassResponse)
async def root():
    """
    Получение всех ски-пассов в иерархической структуре

    Returns:
        SkiPassResponse: Полный список ски-пассов по категориям
    """
    try:
        url = "https://ski-gv.ru/skipass-info/"
        html_content = get_page_content(url)
        root_category = parse_ski_pass_table(html_content)
        return SkiPassResponse(success=True, data=root_category)
    except Exception as e:
        return SkiPassResponse(success=False,
                               data=RootCategory(categories=[]),
                               error=str(e))


@app.get("/categories", response_model=List[str])
async def get_categories():
    """
    Получение списка всех доступных категорий

    Returns:
        List[str]: Список названий категорий

    Raises:
        HTTPException: В случае ошибки при получении данных
    """
    try:
        url = "https://ski-gv.ru/skipass-info/"
        html_content = get_page_content(url)
        root_category = parse_ski_pass_table(html_content)
        return [category.name for category in root_category.categories]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/category/{category}", response_model=SkiPassResponse)
async def get_by_category(category: str):
    """
    Получение ски-пассов для конкретной категории

    Args:
        category: Название категории

    Returns:
        SkiPassResponse: Список ски-пассов в указанной категории
    """
    try:
        url = "https://ski-gv.ru/skipass-info/"
        html_content = get_page_content(url)
        root_category = parse_ski_pass_table(html_content)

        # Поиск запрошенной категории
        filtered_category = next(
            (cat for cat in root_category.categories if cat.name == category),
            None
        )

        if not filtered_category:
            return SkiPassResponse(
                success=False,
                data=RootCategory(categories=[]),
                error=f"Категория '{category}' не найдена"
            )

        return SkiPassResponse(
            success=True,
            data=RootCategory(categories=[filtered_category])
        )
    except Exception as e:
        return SkiPassResponse(
            success=False,
            data=RootCategory(categories=[]),
            error=str(e)
        )