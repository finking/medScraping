import re

config = 'config.ini'

dict_med = {}
url_dict = {}


# Получение названий лекарств, аптек, ссылок
def begin_info():
    with open(config) as f:
        data = f.readlines()

    number = 0
    name_drug = ''
    for line in data:
        line = line.strip()
        if number == 0:
            name_drug = line
            # print(f'Лекарство: {name_drug}')
            number = number + 1
        else:
            if line == '':
                # print('Пустая строка')
                number = 0
                dict_med.update({name_drug: url_dict.copy()})
                url_dict.clear()
            else:
                ph, url = re.split("=", line)
                url_dict.update({ph: url})
                # print(f'Аптека: {ph.strip()}, URL: {url.strip()}')

    dict_med.update({name_drug: url_dict})
    # print(dict_med)
    return dict_med


if __name__ == '__main__':
    begin_info()