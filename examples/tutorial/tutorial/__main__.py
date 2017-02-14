from aiohttp import web

from .app import Application


def main():
    app = Application()
    web.run_app(app)


main()
