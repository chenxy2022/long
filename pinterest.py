from playwright.sync_api import Playwright, sync_playwright, expect

searchfor = "孔雀鱼"  #要查询的关键字
base_url = 'https://www.pinterest.ca'
url = 'https://www.pinterest.ca/search/pins/?q={}'.format(searchfor)
pagechangetime = 4 #网页切换时间，如果设置太快，会导致一些图片无法加载完成（漏图片）,以秒為單位。


def run(playwright: Playwright) -> None:
    browser = playwright.firefox.launch(headless=False)
    context = browser.new_context()
    api_request_context = context.request
    # Open new page
    page = context.new_page()
    #set timeout 1 miniutes (default 30s)
    page.set_default_timeout(60000)

    def getpic(page, urls):
        global piccount
        def handle_response(response):
            try:

                if (response.ok  # successful response (status in the range 200-299)
                        and response.request.resource_type == "image"  # it is of type image

                    ):
                    # print(response.url)
                    # all response.body() saveto dic
                    tempdic[response.url]=response.body()

            except Exception as e:
                # print(e)
                pass

        page.on("response", handle_response)
        page.unroute("**/*")
        for url in urls[:]:
            tempdic=dict()
            page.goto(url)
            xpath='//*[@id="mweb-unauth-container"]/div/div/div[2]/div[2]/div/div/div/div/div[1]/div/div/div/div/div/div/div/img'
            try:
                picurl=page.query_selector(xpath).get_attribute('src')
                # print('图片网址:',picurl)
                path='./picdown/' #图片存放的目录
                filename=url.split('/')[-2] + '.' + picurl.split('.')[-1]
                filename=path + filename
                with open(filename, "wb") as f:

                    f.write(tempdic[picurl])
                    piccount +=1
                    print(filename,'累计已经下载{}张图片'.format(piccount))
            except:
                continue


    # page.route("**/*.{png,jpg,jpeg}", lambda route: route.abort())
    page.route("**/*", lambda route: route.abort() if route.request.resource_type == "image" else route.continue_())
    # page.unroute("**/*")
    page.goto(url)
    allurlsdic = dict()
    for i in range(3): #翻页的次数
        # page.wait_for_timeout(pagechangetime * 1000)
        page.wait_for_load_state('networkidle', )
        suburls = page.query_selector_all('//a[contains(@href,"/pin/")]')
        suburls = [base_url + x.get_attribute("href") for x in suburls]
        dic = dict.fromkeys(suburls)
        oldlen = len(allurlsdic)
        allurlsdic.update(dic)

        if len(allurlsdic) == oldlen: break
        print(len(allurlsdic))
        page.keyboard.press('End')
    print('图片链接地址一共{}个'.format(len(allurlsdic)))


    # if allurlsdic: #如果有网址爬到、
    #     print(list(allurlsdic))
        # getpic(page,list(allurlsdic))


    # ---------------------
    context.close()
    browser.close()



with sync_playwright() as playwright:
    piccount=0
    run(playwright)
    print('一共爬取{}张图片'.format(piccount))