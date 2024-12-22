from fastapi import FastAPI, HTTPException
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional, List
import re
import requests
from urllib.parse import urljoin
import uvicorn
app = FastAPI(title="Eco Trails API")


@dataclass
class EcoTrail:
    """Класс для хранения информации об эко-тропе"""
    name: str
    length: float
    description: str
    map_url: Optional[str] = None


def clean_text(text: str) -> str:
    """Очищает текст от лишних пробелов и специальных символов"""
    text = text.replace('&nbsp;', ' ')
    text = text.replace('\xa0', ' ').strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def get_page_content(url: str) -> str:
    """Загружает содержимое страницы с указанного URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке страницы: {str(e)}")


def find_map_url(soup, trail_name: str) -> Optional[str]:
    """Ищет URL карты для конкретной тропы в HTML"""
    h2_elements = soup.find_all('h2')
    for h2 in h2_elements:
        if trail_name in h2.text:
            current = h2.find_next('p')
            while current and current.name == 'p':
                iframe = current.find('iframe')
                if iframe and iframe.get('src'):
                    return iframe['src']

                ymaps = current.find('ymaps')
                if ymaps:
                    scripts = soup.find_all('script')
                    for script in scripts:
                        if script.get('src') and 'constructor' in script['src']:
                            match = re.search(r'um=constructor[%3A|:]([^&]+)', script['src'])
                            if match:
                                return f"https://yandex.ru/map-widget/v1/?um=constructor:{match.group(1)}"

                current = current.find_next('p')
    return None


def parse_eco_trails(html_content: str) -> List[EcoTrail]:
    """Парсит HTML-страницу с эко-тропами"""
    soup = BeautifulSoup(html_content, 'html.parser')
    content_div = soup.find('div', {'data-formatted-text': True})

    if not content_div:
        raise HTTPException(status_code=500, detail="Не найден основной контейнер с данными")

    trails = []
    current_trail = None

    for element in content_div.children:
        if element.name == 'h2':
            if current_trail:
                current_trail.map_url = find_map_url(soup, current_trail.name)
                trails.append(current_trail)

            text = clean_text(element.text)
            match = re.match(r'([^-]+)-\s*(.+)', text)
            if match:
                name = match.group(1).strip()
                description = match.group(2).strip()
            else:
                title_parts = text.split(' - ')
                name = title_parts[0].strip()
                description = title_parts[1].strip() if len(title_parts) > 1 else ""

            current_trail = EcoTrail(
                name=name,
                length=0.0,
                description=description
            )

        elif element.name == 'p' and current_trail:
            text = clean_text(element.text)
            length_match = re.search(r'протяженностью\s*(\d+(?:[.,]\s*\d*)?)\s*км', text)
            if length_match:
                length_str = length_match.group(1).replace(' ', '').replace(',', '.')
                current_trail.length = float(length_str)

    if current_trail:
        if current_trail.name == "Северная энергия":
            current_trail.map_url = "https://yandex.ru/maps/80/yuzhno-sakhalinsk/?from=mapframe&l=sat&ll=142.793450%2C46.957413&mode=usermaps&source=mapframe&um=constructor%3A97f3eaa38d056b248e8b2119cb211a5410992ad4c5b2a9decccaa07f43b2defc&utm_source=mapframe&z=16"
        else:
            current_trail.map_url = find_map_url(soup, current_trail.name)
        trails.append(current_trail)

    return trails


@app.get("/", response_model=List[EcoTrail])
async def get_eco_trails():
    """Получить список всех эко-троп"""
    url = 'https://ski-gv.ru/navigate/eko-tropyi/'
    try:
        html_content = get_page_content(url)
        trails = parse_eco_trails(html_content)
        return trails
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trail/{trail_name}", response_model=EcoTrail)
async def get_trail_by_name(trail_name: str):
    """Получить информацию о конкретной эко-тропе по названию"""
    url = 'https://ski-gv.ru/navigate/eko-tropyi/'
    try:
        html_content = get_page_content(url)
        trails = parse_eco_trails(html_content)

        for trail in trails:
            if trail.name.lower() == trail_name.lower():
                return trail

        raise HTTPException(status_code=404, detail="Эко-тропа не найдена")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Точка входа в приложение
if __name__ == "__main__":

    try:
        uvicorn.run(app, host="0.0.0.0", port=8004)
    except Exception as e:
        print(f"Ошибка запуска парсера подъемников: {e}")