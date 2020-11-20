# Установка заголовков таблицы
from Gsheets import Gsheet
from config import begin_info

name_sheet = 'Aflubin' # Имя листа, в котором будут установлены заголовки

gs = Gsheet(name_sheet)

dict_med = begin_info()
for name, urls in dict_med.items():
    if name == name_sheet:
        gs.set_headers(urls)
        gs.set_format()

