import asyncio
import logging
from functools import partial

from asyncpgsa.connection import compile_query
from sqlalchemy.dialects import postgresql


class ConnectionLogger:
    _logger = logging.getLogger('common.db')

    def __init__(self, sa_connection):
        self._sa_connection = sa_connection

    def __getattr__(self, attr):
        if attr in ('fetch', 'fetchval', 'fetchrow', 'execute'):
            return partial(self._wrapper, attr)
        return getattr(self._sa_connection, attr)

    async def _wrapper(self, cmd, query, *multiparams, **params):
        fetch = getattr(self._sa_connection, cmd)
        coro = fetch(query, *multiparams, **params)
        try:
            return await asyncio.wait_for(coro, timeout=10)
        except Exception as e:
            q, p = compile_query(query)
            self._logger.critical('SQL ERROR %s:\n%s\n%s', e, q, p)
            raise


class DebugCompiler(postgresql.dialect.statement_compiler):
    def render_literal_value(self, value, type_):
        return repr(value)

    def visit_bindparam(self, bindparam, *args, **kwargs):
        try:
            return super().visit_bindparam(bindparam, *args, **kwargs)
        except Exception:
            # Can't render None, try again
            return self.render_literal_bindparam(
                bindparam,
                within_columns_clause=True,
                *args,
                **kwargs
            )


class DebugDialect(postgresql.dialect):
    statement_compiler = DebugCompiler


def repr_stmt(stmt):
    return stmt.compile(dialect=DebugDialect(), compile_kwargs={'literal_binds': True}).string
