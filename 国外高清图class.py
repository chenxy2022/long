import time

from playwright.sync_api import sync_playwright
import re


class Play_get_pic:
    def __init__(self, picurl):
        self.picurl = picurl
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.num = 1

    def handle_response(self, response):
        try:
            if (response.ok  # successful response (status in the range 200-299)
                    and response.request.resource_type == "image"  # it is of type image
            ):
                # print([x for x in dir(response.request) if x[0]!='_'])
                if 'https://dimg.dillards.com/is/image/DillardsZoom/mainProduct/' in response.url:
                    self.page.dblclick('//*[@id="main-product-image"]')
                if self.picurl in response.url:
                    filename = re.findall(r'\w+.jpg', response.url)[0]
                    filename = f'{self.num}_{filename}'
                    with open(filename, 'wb') as f:
                        f.write(response.body())
                        print(filename)
                        self.num += 1
                        self.page.close()
        except Exception as e:
            # print(e)
            pass

    def run(self, urls):
        for ehurl in urls:
            self.page.on("response", self.handle_response)
            try:
                self.page.goto(ehurl)
            except Exception as e:
                self.page = self.context.new_page()


if __name__ == '__main__':
    '''只要把需要下载图片的网页的网址组成列表，传入run就行'''
    picurl = 'https://dimg.dillards.com/is/image/DillardsZoom/zoom/'
    url = 'https://www.dillards.com/p/calessa-tie-split-round-neck-34-bracelet-sleeve-embroidered-tunic/514569768/sale'
    url1 = 'https://www.dillards.com/p/calessa-crew-neck-bracelet-long-sleeve-floral-print-patchwork-tiered-embroidered-babydoll-tunic/514359262'
    myclass = Play_get_pic(picurl)
    start_t = time.perf_counter()
    myclass.run([url, url1])
    print(f'共下载{myclass.num - 1}张图片，耗时：{time.perf_counter() - start_t:.0f}秒。')
