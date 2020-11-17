import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from config import begin_info

path = r"C:\Users\user\PycharmProjects\geckogeckodriver\geckodriver.exe"
userAgent = 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'

# Получение входных данных из файла config.ini
# TODO выполнить проверки в .ini: первая строка, последовательность, наличие "=", добавить комментарии с примерами как надо
dict_med = begin_info()

medList = []  # Список лекарств
listPriceDialog = []  # Список цен в аптеках Диалог
listPricePlaneta = [] # Список цен в аптеках ПланетаЗдоровья
pathCSV = 'data/'  # Директория записи в csv


# Get-Запрос с помощью библиотеки requests
def get_html(url):
    r = requests.get(url, headers={'user-agent': userAgent })
    if r.ok:
        return r.text
    print(r.status_code)


# Получение данных из zdorov.ru, используя Selenium
def info_zdorov_ru(url):
    browser = webdriver.Firefox(executable_path=path)
    browser.get(url)
    sleep(1)
    WebDriverWait(browser, 1000000).until(
        EC.element_to_be_clickable((By.LINK_TEXT, 'Аптека самовывоза'))).click()
    # browser.find_element_by_link_text('Аптека самовывоза').click()
    browser.find_element_by_xpath('//*[@id="close-cookie"]').click()

    browser.find_element_by_xpath('//*[@id="173-header"]/a').click()
    browser.find_element_by_xpath('//*[@id="yt1"]').click()
    title = browser.find_element_by_id('topheader').text
    try:
        priceOld = float(browser.find_element_by_class_name('pricenormal').text)
    except:
        priceOld = ''
    try:
        price = float(browser.find_element_by_class_name('pricediscount').text.split('*')[0]) # 228.00*
    except:
        price = ''
    browser.close()

    return title, priceOld, price


# Получение данных из apteka.ru
def info_apteka_ru(html):
    bs = BeautifulSoup(html, 'lxml')
    ProductPage = bs.find('div', class_='ProductPage__aside-inner')
    title = ProductPage.find('p').text
    try:
        priceOld = float(ProductPage.find('div', class_='ProductPage__old-price').text)
    except:
        priceOld = ''
    try:
        price = float(ProductPage.find('div', class_='ProductPage__price').text)
    except:
        price = ''

    return title, priceOld, price


# Получение данных из dialog.ru
def info_dialog_ru(url):
    browser = webdriver.Firefox(executable_path=path)
    browser.get(url)
    # sleep(1)
    title = browser.find_element_by_xpath('/html/body/main/div[1]/div[1]/div[1]/h1').text
    try:
        priceOld = float(browser.find_element_by_xpath('/html/body/main/div[1]/div[1]/div[2]/div[2]/span[2]').text)
    except:
        priceOld = ''

    browser.find_element_by_link_text('Забронировать в аптеке').click()

    listStores = {'Новокосинская ул., д.11 стр.1': '53',
                    'Суздальская ул., д. 30/2': '32',
                    'Новокосинская ул.,  д. 35': '24',
                    'Носовихинское шоссе, д. 9': '87'}

    for key, value in listStores.items():
        try:
            priceInPharm = float(browser.find_element_by_xpath(f'//li[@data-storeid={value}]').find_element_by_class_name('price').text)

        except:
            print(f"В аптеке по адресу {key} нет запрашиваемого лекарства")
            priceInPharm = 0.0
        listPriceDialog.append(priceInPharm)
    price = min(listPriceDialog)
    browser.close()

    return title, priceOld, price


# Получение данных из planetazdorovo.ru
def info_planeta_ru(url):
    browser = webdriver.Firefox(executable_path=path)
    browser.get(url)
    try:
        browser.find_element_by_link_text('Да').click()
    except:
        browser.refresh()
    sleep(3) # За меньшее время не успевают загрузиться все скрипты
    try:
        title = browser.find_element_by_tag_name('h1').text
    except:
        title = ''
    try:
        priceOld = float(browser.find_element_by_class_name('product-detail__price_new').text.split(" ")[1])
    except:
        priceOld = ''

    # Способ через закрытия Фрейма. Отказался из-за эпизодических timeout'ов.
    # WebDriverWait(browser, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, 'carrot-popup-frame')))
    # el = browser.find_element_by_id("carrotquest-messenger-body-big-cont-close")
    # print(el.text)
    # el.click()
    # browser.switch_to.default_content()

    # Обновляем браузер, чтобы избавиться от всплывающего окна (iframe)
    browser.refresh()
    # sleep(1)

    # Подготовка списка аптек. Изначально доступно только 5 шт.
    try:
        for i in range(5):
            browser.find_element_by_link_text('Загрузить еще').click()
        sleep(1)
    except:
        browser.refresh() # при selenium.common.exceptions.ElementClickInterceptedException обновляем страницу

    # Параметры для цикла
    price = 0
    j = 0

    while True:
        # Будет загружено 5+5*5+5*20=130 аптек. Если среди них нет нужных, то либо в них товара нет, либо она высокая
        if j < 20:  # при j=20, 20*5=100 Дополнительных аптек
            try:
                listStores = {'Москва, Суздальская, 12, к. 1': '56091',
                                'Москва, Суздальская, 34': '55874',
                                'Реутов, Южная, 19': '56015'}

                for key, value in listStores.items():
                    try:
                        priceInPharm = float(browser.find_element_by_xpath(f'//div[@data-pharmacy_id={value}]').
                                             find_element_by_class_name('drugstore-list__total_price').
                                             text.split(" ")[0])
                        listPricePlaneta.append(priceInPharm)
                    except:
                        # Если аптеки нет в отображаемом списке, то будет исключение
                        pass

                price = min(listPricePlaneta)  # Если ошибка, то сработает "Загрузить еще"
                break
            except:
                # Если не удалось в списке обнаружить необходимые аптеки, то загружаем следующие
                browser.find_element_by_link_text('Загрузить еще').click()
                j = j + 1
        else:
            print(f"Нажато {j} раз. Но указанные аптеки не были найдены")
            break
    browser.quit()  # .close вызывало ошибку OSError: [WinError 6] при окончании работы скрипта
    # https://stackoverflow.com/questions/60512741/oserror-winerror-6-wrong-descriptor-error-using-selenium-through-python
    return title, priceOld, price


# Получение данных из ZdravCity.ru
def info_zdrav_city(html):
    soup = BeautifulSoup(html, 'lxml')
    title = soup.find('div', id='product-new-accordion').find('h1').text
    try:
        priceOld = float(soup.find('div', class_='b-product-new__price-old').find('span').text.strip())
    except:
        priceOld = ''
    try:
        price = float(soup.find('div', class_='b-product-new__price-new').find('span').text.strip())
    except:
        price = ''
    return title, priceOld, price


# Получение данных из gorzdrav.ru
def info_gorzdrav(html):
    soup = BeautifulSoup(html, 'lxml')
    title = soup.find('h1', class_='b-page-title').text
    try:
        priceOld = float(soup.find('span', class_='b-price--last').text.strip().split(' ')[0].replace(',', '.'))
    except:
        priceOld = ''
    try:
        price = float(soup.find('span', class_='b-price--large').text.strip().split(' ')[-2])
    except Exception as e:
        price = ''
        print(e)
    return title, priceOld, price


def main():

    for names, urls in dict_med.items():
        print(f'Получение данных по {names}.')
        for pharmacy, url in urls.items():
            print(f"Получение данных с {pharmacy}.")
            if pharmacy == 'apteka.ru':
                html = get_html(url)
                title, priceOld, price= info_apteka_ru(html)
                appendMedList(pharmacy, title, price, priceOld, url)
            elif pharmacy == 'zdorov.ru':
                title, priceOld, price = info_zdorov_ru(url)
                appendMedList(pharmacy, title, price, priceOld, url)
            elif pharmacy == 'dialog.ru':
                title, priceOld, price = info_dialog_ru(url)
                appendMedList(pharmacy, title, price, priceOld, url)
            elif pharmacy == 'planetazdorovo.ru':
                title, priceOld, price = info_planeta_ru(url)
                appendMedList(pharmacy, title, price, priceOld, url)
            elif pharmacy == 'ZdravCity.ru':
                html = get_html(url)
                title, priceOld, price = info_zdrav_city(html)
                appendMedList(pharmacy, title, price, priceOld, url)
            elif pharmacy == 'gorzdrav.org':
                html = get_html(url)
                title, priceOld, price = info_gorzdrav(html)
                appendMedList(pharmacy, title, price, priceOld, url)
        sleep(1)
        writeCSV(names)
        # Очистка списков после записи цен на лекарства. Для использования с новым.
        medList.clear()
        listPriceDialog.clear()
        listPricePlaneta.clear()


# Запись в csv
def writeCSV(names):
    print(f"Запись в файл: {pathCSV}{names}.csv")
    df = pd.DataFrame(medList)
    df.to_csv(f'{pathCSV}{names}.csv', sep=';', encoding='cp1251')


# Добавление данных по аптекам в Список лекарств
def appendMedList(pharmacy, title, price, priceOld, url):
    try:
        discount = - round((priceOld - price) / priceOld, 2)
    except:
        discount = 0
    info = {
        'pharmacy': pharmacy,
        'title': title,
        'url': url,
        'priceOld': str(priceOld).replace('.', ','),
        'price': str(price).replace('.', ','),
        'discount': str(discount).replace('.', ',')
    }
    medList.append(info)


if __name__ == '__main__':
    main()