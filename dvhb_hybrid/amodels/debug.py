import logging

from sqlalchemy.dialects import postgresql


class ConnectionLogger:
    _logger = logging.getLogger('common.db')

    def __init__(self, sa_connection):
        self._sa_connection = sa_connection

    def __getattr__(self, attr):
        return getattr(self._sa_connection, attr)

    def _log(self, query):
        if not self._logger.hasHandlers():
            return
        if not isinstance(query, str):
            query = repr_stmt(query)
        self._logger.debug(query)

    async def execute(self, query, *multiparams, **params):
        self._log(query)
        return await self._sa_connection.execute(query, *multiparams, **params)

    async def scalar(self, query, *multiparams, **params):
        self._log(query)
        return await self._sa_connection.scalar(query, *multiparams, **params)


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
