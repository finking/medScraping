import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from time import sleep, perf_counter
from config import begin_info
from Gsheets import Gsheet
from datetime import datetime

path = r"C:\Users\user\PycharmProjects\geckogeckodriver\geckodriver.exe"
userAgent = 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'

# Получение входных данных из файла config.ini
# TODO выполнить проверки в .ini: первая строка, последовательность, наличие "=", добавить комментарии с примерами как надо
dict_med = begin_info()
dict_price = {} # Словарь для отправки в Гугл.Таблицы.

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

    browser.find_element_by_xpath('//*[@id="__next"]/div[2]/div/div/div[2]/div[1]/div/div[2]/div[2]/div/span').click()
    browser.find_element_by_xpath(
        '/html/body/div/div[2]/div/div/div[2]/div[1]/div/div[2]/div[3]/div/div/div/div[1]/div[2]/div[35]/div/div[2]/button').click()

    title = browser.find_element_by_xpath('//*[@id="__next"]/div[2]/div/div/div[3]/div/div[2]/div/div[1]/span').text
    priceOld = ''

    try:
        price = float(browser.find_element_by_xpath(
            '//*[@id="__next"]/div[2]/div/div/div[3]/div/div[3]/div/div[3]/div/div[2]/div/div[1]/div[1]/div/div/span').text.split(
            ' ')[0])
    except:
        price = ''
    browser.close()

    return title, priceOld, price


# Получение данных из apteka.ru
def info_apteka_ru(html):
    bs = BeautifulSoup(html, 'lxml')
    title = bs.find('h1').text
    ProductPage = bs.find('div', class_='ProductOffer')
    try:
        priceOld = float(ProductPage.find('div', class_='ProductOffer__ndisc').text.split('₽')[0])
    except:
        priceOld = ''
    try:
        price = float(ProductPage.find('div', class_='ProductOffer__price').text.split('₽')[0])
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
            priceInPharm = 99999.0  # Чтобы следующая действительная цена была меньше этой.
        listPriceDialog.append(priceInPharm)
    price = min(listPriceDialog)
    if price == 99999.0:  # В случае, если ни в одной из выбранных аптек нет лекарства
        price = 0.0
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
    try:
        browser.find_element_by_xpath('//*[@id="block-fixed_price-close"]').click()
    except:
        sleep(1)
        browser.refresh()
        browser.find_element_by_xpath('//*[@id="block-fixed_price-close"]').click()

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
        # price = float(soup.find('span', class_='b-price--large').text.strip().split(' ')[-2])
        price = float(soup.find('span', class_='b-price--large').text.strip().split(' ')[0].split('\n')[-1])
    except Exception as e:
        price = ''
        print(e)
    return title, priceOld, price


def main():
    price = 0.0
    for names, urls in dict_med.items():
        time_start_drug = perf_counter() # Начало отчета времени для конкретного лекарства
        print(f'Получение данных по {names}.')
        for pharmacy, url in urls.items():
            print(f"Получение данных с {pharmacy}.")
            time_start_pharmacy = perf_counter()  # Начало отчета времени для конкретной аптеки
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
                try:
                    html = get_html(url)
                except:
                    print('Не удалось получить информацию.')
                    break
                title, priceOld, price = info_gorzdrav(html)
                appendMedList(pharmacy, title, price, priceOld, url)
            dict_price[pharmacy] = price
            print(f'Получение информации с сайта {pharmacy} заняло {round(perf_counter()-time_start_pharmacy, 4)} секунд')

        sleep(1)

        # Запись в csv-file
        time_start_csv = perf_counter()
        writeCSV(names)
        print(f'Время записи в csv-файл составляет: {round(perf_counter() - time_start_csv, 4)} секунд')

        # Запись в googlesheets
        time_start_googlesheets = perf_counter()
        writeGoogleSheets(names, dict_price)
        print(f'Время записи в google-таблицы составляет: {round(perf_counter() - time_start_googlesheets, 4)} секунд')

        # Очистка списков после записи цен на лекарства. Для использования с новым.
        medList.clear()
        listPriceDialog.clear()
        listPricePlaneta.clear()
        dict_price.clear()
        print(f'Время обработки данных для {names} составляет: {round(perf_counter()-time_start_drug, 4)} секунд')

# Запись в Гугл.Таблицы
def writeGoogleSheets(med, data):
    sheet = Gsheet(med)
    ws = sheet.worksheet
    try:
        ws.append_row([datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                       data['apteka.ru'],
                       data['zdorov.ru'],
                       data['dialog.ru'],
                       data['planetazdorovo.ru'],
                       data['ZdravCity.ru'],
                       data['gorzdrav.org']])
        print(f'Запись в Гугл.Таблицу по {med} завершена успешна')
    except Exception as e:
        print(f'Запись в Гугл.Таблицу по {med} не удалась')
        print(e)


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
    time_start_total = perf_counter()  # Начало отчета работы скрипта
    main()
    print(f'Общее время работы скрипта: {round(perf_counter() - time_start_total, 4)} секунд')
