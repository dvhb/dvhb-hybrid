"""
http://stackoverflow.com/questions/5631078/sqlalchemy-print-the-actual-query
"""

from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.sqltypes import String, DateTime, NullType


class StringLiteral(String):
    def literal_processor(self, dialect):
        processor = super().literal_processor(dialect)

        def process(value):
            if not isinstance(value, str):
                value = str(value)
            result = processor(value)
            if isinstance(result, bytes):
                result = result.decode(dialect.encoding)
            return result
        return process


class LiteralDialect(postgresql.dialect):
    colspecs = {
        # prevent various encoding explosions
        String: StringLiteral,
        # teach SA about how to literalize a datetime
        DateTime: StringLiteral,
        # don't format py2 long integers to NULL
        NullType: StringLiteral,

        postgresql.UUID: StringLiteral,
    }


def literalquery(statement):
    return statement.compile(
        dialect=LiteralDialect(),
        compile_kwargs={'literal_binds': True},
    ).string
