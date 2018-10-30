from aiohttp import web
from dvhb_hybrid.export.xlsx import XLSXResponse


async def handler1(request):
    async with XLSXResponse(request, filename='1.xlsx') as r:
        r.append({'x': 2, 'y': 3})
        r.append({'x': 'a', 'y': 'f'})
    return r


async def handler2(request):
    head = ['Column X', 'Column Y']
    fields = ['x', 'y']
    async with XLSXResponse(request, head=head, fields=fields) as r:
        r.append({'x': 2, 'y': 3})
        r.append({'x': 'a', 'y': 'f'})
    return r


async def test_xlsx(aiohttp_client, loop):
    app = web.Application(loop=loop)
    app.router.add_get('/xlsx1', handler1)
    app.router.add_get('/xlsx2', handler2)
    client = await aiohttp_client(app)

    r = await client.get('/xlsx1')
    assert r.status == 200
    data = await r.read()
    assert data

    r = await client.get('/xlsx2')
    assert r.status == 200
    data = await r.read()
    assert data
