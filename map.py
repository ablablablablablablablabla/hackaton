import requests
from bs4 import BeautifulSoup
import json
from typing import Dict, List, Optional




class SkiTrackParser:
    def __init__(self, url: str):
        self.url = url
        self.base_url = "https://ski-gv.ru"

    def get_page_content(self) -> str:
        """Получает содержимое страницы"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(self.url, headers=headers)
        response.raise_for_status()
        return response.text

    def parse_layer_data(self, img_element) -> Dict:
        """Парсит данные слоя из img элемента"""
        data = {
            'src': f"{self.base_url}{img_element.get('src', '')}",
            'layer_number': img_element.get('data-scheme-layer'),
            'position': {
                'left': img_element.get('data-left'),
                'top': img_element.get('data-top'),
                'width': img_element.get('data-width'),
                'height': img_element.get('data-height')
            }
        }
        return data

    def parse_scheme(self) -> Dict[str, List[Dict]]:
        """Основной метод парсинга схемы"""
        html_content = self.get_page_content()
        soup = BeautifulSoup(html_content, 'html.parser')

        # Находим основной div со схемой
        scheme_div = soup.find('div', class_='scheme__layers map')
        if not scheme_div:
            raise ValueError("Схема не найдена на странице")

        # Получаем стили трансформации основного div
        transform_style = {
            'transform': scheme_div.get('style', '').split('transform: ')[1].split(';')[
                0] if 'transform: ' in scheme_div.get('style', '') else None,
            'width': scheme_div.get('style', '').split('width: ')[1].split(';')[0] if 'width: ' in scheme_div.get(
                'style', '') else None
        }

        # Парсим основное изображение холма
        hill_img = scheme_div.find('img', class_='scheme__hill')
        hill_data = {
            'src': f"{self.base_url}{hill_img.get('src', '')}",
            'dimensions': {
                'width': hill_img.get('data-width'),
                'height': hill_img.get('data-height'),
                'top': hill_img.get('data-top'),
                'left': hill_img.get('data-left')
            }
        }

        # Парсим все слои схемы
        layers = []
        for img in scheme_div.find_all('img', class_='scheme__layer'):
            layer_data = self.parse_layer_data(img)
            layers.append(layer_data)

        return {
            'hill': hill_data,
            'layers': layers
        }

    def save_to_json(self, filename: str):
        """Сохраняет результаты парсинга в JSON файл"""
        data = self.parse_scheme()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)




# Пример использования
if __name__ == "__main__":
    import asyncio

    # Для запуска без uvicorn можно использовать hypercorn
    import hypercorn.asyncio
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:8003"]

    asyncio.run(hypercorn.asyncio.serve(config))

