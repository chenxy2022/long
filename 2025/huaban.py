import logging
import os
from io import BytesIO

import aiohttp
import asyncio
import pandas as pd
import requests
from PIL import Image
from myfunction import addtag

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global variable for tracking downloads
numbers = 0


async def download_image(session: aiohttp.ClientSession, url: str, path: str, note: str) -> bool:
    global numbers
    try:
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                content = await response.read()
                img = Image.open(BytesIO(content))
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.save(path, 'JPEG', quality=95)
                addtag(path, {'note': note})
                numbers += 1
                return True
            else:
                logging.error(f"Failed to download {url}, status code: {response.status}")
                return False
    except aiohttp.ClientError as e:
        logging.error(f"Network error downloading {url}: {e}")
        return False
    except Image.UnidentifiedImageError as e:
        logging.error(f"Invalid image format for {url}: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error downloading {url}: {e}")
        return False


async def download_images(df: pd.DataFrame) -> int:
    global numbers
    async with aiohttp.ClientSession() as session:
        tasks = []
        for index, row in df.iterrows():
            image_url = row['file']
            file_path = os.path.join(down_path, f"{row['pin_id']}.jpg")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            note = row['pageurl']
            tasks.append(download_image(session, image_url, file_path, note))

        # Gather results and count successful downloads
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_downloads = sum(1 for result in results if result)
        return successful_downloads


def read_txt(file_name: str) -> list:
    if file_name and "." not in file_name:
        return [file_name]
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            keys = f.readlines()
    except FileNotFoundError:
        logging.error(f"File {file_name} not found")
        return []
    except UnicodeDecodeError:
        logging.error(f"File {file_name} encoding error")
        return []
    seen = set()
    unique_keys = [x.strip() for x in keys if not (x.strip() in seen or seen.add(x.strip()))]
    return unique_keys


async def main(q: str, start: int, end: int) -> None:
    global numbers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36',
    }
    url = 'https://huaban.com/v3/search/file'
    params = {
        "text": q,
        "sort": "all",
        "limit": 40,
        "page": 1,
        "position": "search_pin",
        "fields": "pins:PIN|total,facets,split_words,relations,rec_topic_material,topics"
    }
    for i in range(start, end + 1):
        params['page'] = i
        r = requests.get(url, headers=headers, params=params)
        myjson = r.json()
        df = pd.DataFrame(myjson['pins'])
        df_need = df[['pin_id', 'file']].copy()

        def trans_url(x):
            return 'https://{bucket}.huaban.com/{key}'.format(**x)

        df_need['file'] = df_need['file'].map(trans_url)

        df_need['pageurl'] = df_need['pin_id'].map(lambda x: f'https://huaban.com/pins/{x}')

        # Download images and get count of successful downloads
        successful_downloads = await download_images(df_need)
        logging.info(f'{q} 第{i}页下载完成，共下载 {successful_downloads} 张图片 (累计: {numbers})')


if __name__ == '__main__':
    down_path = r'd:\download\test'
    # q = '五星红旗'
    q = r'd:\download\1.txt'  # 搜索关键词 自动判断关键字还是文件
    start = 1
    end = 2

    for q in read_txt(q):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(q, start, end))
