from aiohttp import web
from dvhb_hybrid.export.xlsx import XLSXResponse


async def handler1(request):
    with XLSXResponse(filename='1.xlsx') as r:
        await r.prepare(request)
        r.append({'x': 2, 'y': 3})
        r.append({'x': 'a', 'y': 'f'})
        return r


async def handler2(request):
    head = ['Column X', 'Column Y']
    fields = ['x', 'y']
    with XLSXResponse(head=head, fields=fields) as r:
        await r.prepare(request)
        r.append({'x': 2, 'y': 3})
        r.append({'x': 'a', 'y': 'f'})
        return r


async def test_xlsx(test_client, loop):
    app = web.Application(loop=loop)
    app.router.add_get('/xlsx1', handler1)
    app.router.add_get('/xlsx2', handler2)
    client = await test_client(app)

    r = await client.get('/xlsx1')
    assert r.status == 200
    data = await r.read()
    assert data

    r = await client.get('/xlsx2')
    assert r.status == 200
    data = await r.read()
    assert data
    # with open('/tmp/test.xlsx', 'wb') as f:
    #     f.write(data)
