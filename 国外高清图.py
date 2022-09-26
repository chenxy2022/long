import time

from playwright.sync_api import Playwright, sync_playwright, expect
import re
from queue import Queue


def run(playwright: Playwright) -> None:
    def handle_response(response):
        try:
            if (response.ok  # successful response (status in the range 200-299)
                    and response.request.resource_type == "image"  # it is of type image
            ):
                # print(response.url)

                if 'https://dimg.dillards.com/is/image/DillardsZoom/mainProduct/' in response.url:
                    page.dblclick('//*[@id="main-product-image"]')
                if 'https://dimg.dillards.com/is/image/DillardsZoom/zoom/' in response.url:
                    filename = re.findall(r'\w+.jpg', response.url)[0]
                    filename = f'{que.get()}_{filename}'
                    with open(filename, 'wb') as f:
                        f.write(response.body())
                        print(filename)
                        page.close()
        except Exception as e:
            # print(e)
            pass

    que = Queue()
    browser = playwright.chromium.launch(headless=False)  # chromium
    context = browser.new_context()
    # Open new page
    page = context.new_page()
    page.on("response", handle_response)
    urls = [url] * 3
    count = 0
    start_t = time.time()
    for ehurl in urls:
        count += 1
        que.put(count)
        try:
            page.goto(ehurl)
        except Exception as e:
            page = context.new_page()
            page.on("response", handle_response)
            continue
    print(time.time() - start_t)
    context.close()
    browser.close()


url = 'https://www.dillards.com/p/calessa-tie-split-round-neck-34-bracelet-sleeve-embroidered-tunic/514569768/sale'

with sync_playwright() as playwright:

    run(playwright)

