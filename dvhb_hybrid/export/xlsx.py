from zipfile import ZipFile, ZIP_DEFLATED

import openpyxl
from aiohttp import web
from openpyxl.writer.excel import ExcelWriter


class XLSXResponse(web.StreamResponse):
    def __init__(self, *args, fields=None, head=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.content_type = 'application/xlsx'
        self.fields = fields
        self.head = head

    def write(self, data):
        super().write(data)
        return len(data)

    def flush(self):
        return super().drain()

    def __enter__(self):
        wb = openpyxl.Workbook()
        self.archive = ZipFile(self, 'w', ZIP_DEFLATED, allowZip64=True)
        ws = wb.active
        self.ws = ws
        self.writer = ExcelWriter(wb, self.archive)
        if self.head:
            self.ws.append(self.head)
        return self

    def append(self, data):
        if not self.fields:
            self.fields = list(data)
            if self.head is None:
                self.ws.append(self.fields)
        self.ws.append([data[i] for i in self.fields])

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.writer.write_data()
        self.archive.close()
