import time, asyncio

from playwright.async_api import async_playwright
import re


class Play_get_pic:
    def __init__(self, picurl, sem=6):
        self.picurl = picurl
        self.num = 0
        self.sem = sem

    async def pageon(self, browser, url, sem):
        async with sem:
            async def handle_response(response):
                if (response.ok  # successful response (status in the range 200-299)
                        and response.request.resource_type == "image"  # it is of type image
                ):
                    # print(response.url)
                    if 'https://dimg.dillards.com/is/image/DillardsZoom/mainProduct/' in response.url:
                        print(response.url)
                        await page.dblclick('//*[@id="main-product-image"]')
                    if self.picurl in response.url:
                        filename = re.findall(r'\w+.jpg', response.url)[0]
                        self.num += 1
                        filename = f'./download/{self.num}_{filename}'
                        with open(filename, 'wb') as f:
                            f.write(await response.body())
                            print(filename)

                            await page.close()

            page = await browser.new_page()
            page.on("response", handle_response)
            try:
                await page.goto(url)
                # page.close()
            except Exception as e:
                # print(e)
                pass

    async def run(self, urls):
        async with async_playwright() as playwright:
            chromium = playwright.chromium  # or "firefox" or "webkit".
            browser = await chromium.launch(headless=False)
            tasks = []
            sem = asyncio.Semaphore(self.sem)
            if isinstance(urls, str):
                urls = [urls]

            for ehurl in urls:
                tasks.append(asyncio.create_task(self.pageon(browser, ehurl, sem)))
            await asyncio.ensure_future(asyncio.wait(tasks))


async def main(urls, picurl):
    myclass = Play_get_pic(picurl)
    start_t = time.perf_counter()
    await myclass.run(urls)
    print(f'共下载{myclass.num}张图片，耗时：{time.perf_counter() - start_t:.0f}秒。')


if __name__ == '__main__':
    '''只要把需要下载图片的网页的网址组成列表，传入main就行'''
    picurl = 'https://dimg.dillards.com/is/image/DillardsZoom/zoom/'
    url = 'https://www.dillards.com/p/calessa-tie-split-round-neck-34-bracelet-sleeve-embroidered-tunic/514569768/sale'
    url1 = 'https://www.dillards.com/p/calessa-crew-neck-bracelet-long-sleeve-floral-print-patchwork-tiered-embroidered-babydoll-tunic/514359262'
    urls = [url, url1]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(urls, picurl))
