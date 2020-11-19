import gspread

name_json = 'medscraping.json'
name_book = 'Price_for_medicine'


class Gsheet:

    def __init__(self, name):
        self.gs = gspread.service_account(filename=name_json)
        self.book = self.gs.open(name_book)
        self.worksheet = self.book.worksheet(name)

    def set_format(self):
        self.worksheet.format('3:3', {'textFormat': {'bold': True},
                                        'horizontalAlignment': 'CENTER',
                                        'verticalAlignment': 'MIDDLE',
                                        'wrapStrategy': 'WRAP'})
        self.worksheet.format('B4:G', {'numberFormat': {'type': 'NUMBER', 'pattern': '# ### ₽'}})
        self.worksheet.format('A4:A', {'numberFormat': {'type': 'DATE_TIME', 'pattern': 'dd-mm-yyyy hh:mm'}})


worksheet = Gsheet('Aquamaris')

