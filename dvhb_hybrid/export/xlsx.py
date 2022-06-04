import asyncio
import io
from zipfile import ZIP_DEFLATED, ZipFile

import openpyxl
from aiohttp import web
from openpyxl.writer.excel import ExcelWriter


class XLSXResponse(web.StreamResponse):
    def __init__(self, request, *args, fields=None, head=None, filename=None, **kwargs):
        if filename:
            headers = kwargs.setdefault('headers', {})
            v = 'attachment; filename="{}"'.format(filename)
            headers['Content-Disposition'] = v
        super().__init__(*args, **kwargs)
        self.content_type = 'application/xlsx'
        self.request = request
        self.fields = fields
        self.head = head

    def prepare_workbook(self):
        wb = openpyxl.Workbook()
        self.file = io.BytesIO()
        self.archive = ZipFile(self.file, 'w', ZIP_DEFLATED)
        self.ws = wb.active
        self.writer = ExcelWriter(wb, self.archive)
        if self.head:
            self.ws.append(self.head)

    def append(self, data):
        if not self.fields:
            self.fields = list(data)
            if self.head is None:
                self.ws.append(self.fields)
        self.ws.append([data[i] for i in self.fields])

    def write_workbook(self):
        self.writer.write_data()
        self.archive.close()

    async def __aenter__(self):
        await self.prepare(self.request)
        self.prepare_workbook()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.write_workbook)
        await super().write(self.file.getbuffer())
