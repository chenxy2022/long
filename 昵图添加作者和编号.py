import aiohttp
import asyncio
from lxml import etree
import re, os


class Match:
    def __init__(self, filepath):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'
        }
        self.files = self.get_files(filepath)
        self.nicpic_files = [x for x in self.files if os.path.basename(x).startswith('昵图')]
        self.nicpic_url = 'https://soso.nipic.com/?q={}'
        self.num = 0

    @staticmethod
    def get_files(filepath):
        return [os.path.join(root, f)
                for root, _, files in os.walk(filepath)
                for f in files]

    def getno(self, filename: str):
        regex = re.compile(r'(\d+)\.[^.]+$')
        r = regex.search(filename)
        if r:
            return r.group(1)

    async def run_nipic(self):
        tasks = [self.nicpic(file) for file in self.nicpic_files]
        await asyncio.gather(*tasks)

    async def fetch(self, session, url):
        async with session.get(url) as response:
            return await response.text()

    async def nicpic(self, file):
        url = self.nicpic_url.format(self.getno(file))
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                r = await self.fetch(session, url)
                el = etree.HTML(r)
                path = '//*[@id="img-list-outer"]/li/a/@href'
                detail_url = 'https:' + el.xpath(path)[0]
                r = await self.fetch(session, detail_url)
                el = etree.HTML(r)
                upload_user_path = '//*[@id="contextBox"]/div[3]/dl/dd/div[1]/div/a'
                upload_user = el.xpath(upload_user_path)[0]
                username = upload_user.xpath('./@title')[0]
                usercode = re.search(r'\d{3,}', upload_user.xpath('./@href')[0]).group()
                userinfo = (f"{username}_{usercode}")
                filename_new = os.path.join(os.path.dirname(file), f'{userinfo}_{os.path.basename(file)}')
                os.rename(file, filename_new)
                self.num += 1
        except Exception as e:
            print(e)


if __name__ == '__main__':
    file_path = r'D:\图片'
    match = Match(file_path)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(match.run_nipic())
    print(f'修改了文件数:{match.num}')

