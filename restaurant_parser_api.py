from fastapi import FastAPI, HTTPException
from bs4 import BeautifulSoup
import requests
from typing import List, Optional, Dict
from pydantic import BaseModel
import json

app = FastAPI(title="Restaurant Parser API")


class BreadcrumbItem(BaseModel):
    text: str
    link: str


class RestaurantData(BaseModel):
    name: Optional[str] = None
    schedule: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    description: List[str] = []
    images: List[str] = []
    breadcrumbs: List[BreadcrumbItem] = []


def parse_single_restaurant(url: str) -> RestaurantData:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Ошибка при запросе к {url}: {str(e)}")
        return RestaurantData()

    soup = BeautifulSoup(response.text, 'html.parser')

    restaurant_data = {
        'name': None,
        'schedule': None,
        'address': None,
        'phone': None,
        'description': [],
        'images': [],
        'breadcrumbs': []
    }

    # Название ресторана
    title = soup.find('h1', class_=lambda x: x and ('title' in x.lower() or 'heading' in x.lower())) or \
            soup.find('div', class_=lambda x: x and ('title' in x.lower() or 'heading' in x.lower())) or \
            soup.select_one('.page__title, .title, h1')
    if title:
        restaurant_data['name'] = title.text.strip()

    # Адрес
    address = soup.find('div', class_=lambda x: x and ('address' in x.lower() or 'location' in x.lower())) or \
              soup.find('div', {'itemprop': ['address', 'location']}) or \
              soup.find('div', string=lambda x: x and ('станция' in x.lower() or 'адрес' in x.lower()))
    if address:
        restaurant_data['address'] = address.text.strip()

    # Телефон
    phone = soup.find('div', class_=lambda x: x and ('phone' in x.lower() or 'tel' in x.lower())) or \
            soup.find('div', {'itemprop': ['telephone', 'phone']}) or \
            soup.find('a', {'href': lambda x: x and 'tel:' in x}) or \
            soup.find(['div', 'span', 'a'], string=lambda x: x and '+7' in x)
    if phone:
        restaurant_data['phone'] = phone.text.strip()

    # Расписание
    schedule = soup.find('div', class_=lambda x: x and (
            'schedule' in x.lower() or 'time' in x.lower() or 'hour' in x.lower())) or \
               soup.find('div', {'itemprop': ['openingHours', 'workingHours']}) or \
               soup.find('div',
                         string=lambda x: x and any(word in x for word in ['Пн-', 'Вт-', 'Пн–', 'время работы'])) or \
               soup.select_one('[class*="schedule"], [class*="time"], [class*="hour"]')
    if schedule:
        restaurant_data['schedule'] = ' '.join(schedule.text.strip().split())

    # Описание
    descriptions = []
    formatted_text = soup.find('div', attrs={'data-formatted-text': ''})
    if formatted_text:
        paragraphs = formatted_text.find_all('p')
        for p in paragraphs:
            text = p.text.strip()
            if text and text not in descriptions:
                descriptions.append(text)

    description_blocks = (
            soup.find_all(['div', 'p'], {'itemprop': 'description'}) +
            soup.find_all(['div', 'p'], class_=lambda x: x and x.lower() == 'description') +
            soup.find_all('div', class_='page__content')
    )

    for block in description_blocks:
        paragraphs = block.find_all('p') if block.name != 'p' else [block]
        for p in paragraphs:
            text = p.text.strip()
            if (text and text not in descriptions and
                    not any(skip in text.lower() for skip in ['©', '®', '™', 'cookies'])):
                descriptions.append(text)

    restaurant_data['description'] = descriptions

    # Изображения
    images = []
    base_url = 'https://ski-gv.ru'

    # Основное изображение
    main_image = soup.find('img', class_='page__main-image')
    if main_image and main_image.get('src'):
        src = main_image.get('src')
        if not src.startswith(('http://', 'https://')):
            src = f"{base_url}/{src.lstrip('/')}"
        images.append(src)

    # Поиск всех изображений
    all_images = (
            soup.find_all('img', class_='center') +
            soup.find_all('img', class_=lambda x: x and ('photo' in x.lower() or 'image' in x.lower())) +
            soup.find_all('div', class_=lambda x: x and ('gallery' in x.lower() or 'image' in x.lower()))
    )

    for img in all_images:
        if img.name == 'div':
            img_link = img.find('a') or img.find('img')
            if img_link:
                src = img_link.get('href') or img_link.get('src')
                if src and src not in images:
                    if not src.startswith(('http://', 'https://')):
                        src = f"{base_url}/{src.lstrip('/')}"
                    images.append(src)
        else:
            src = img.get('src')
            if src and src not in images:
                if not src.startswith(('http://', 'https://')):
                    src = f"{base_url}/{src.lstrip('/')}"
                images.append(src)

    restaurant_data['images'] = images

    # Хлебные крошки
    breadcrumbs = soup.find_all('a', class_=lambda x: x and (
            'breadcrumb' in x.lower() or 'bread' in x.lower() or 'nav' in x.lower()))

    restaurant_data['breadcrumbs'] = [
        {'text': crumb.text.strip(), 'link': crumb['href']}
        for crumb in breadcrumbs
        if crumb.get('href')
    ]

    return RestaurantData(**restaurant_data)


@app.get("/restaurant/")
async def get_all_restaurants():
    """
    Получение данных всех ресторанов
    """
    restaurant_ids = ['4', '5', '7']
    results = {}

    for rid in restaurant_ids:
        try:
            url = f'https://ski-gv.ru/restaurants/company/{rid}/'
            results[rid] = parse_single_restaurant(url)
        except Exception as e:
            print(f"Ошибка при парсинге ресторана {rid}: {str(e)}")
            continue

    return results


@app.get("/restaurant/{restaurant_id}")
async def get_restaurant_data(restaurant_id: str):
    """
    Получение данных конкретного ресторана
    """
    url = f'https://ski-gv.ru/restaurants/company/{restaurant_id}/'
    try:
        return parse_single_restaurant(url)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Ошибка при запросе к странице: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run(app, host="0.0.0.0", port=8001)
    except Exception as e:
        print(f"Ошибка запуска парсера трасс: {e}")