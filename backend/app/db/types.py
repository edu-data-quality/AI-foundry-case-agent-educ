"""Tipos customizados portáveis entre SQLite e PostgreSQL."""

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class DateTimeUtc(TypeDecorator[datetime]):
    """Datetime sempre em UTC com timezone.

    O PostgreSQL guarda e devolve com timezone; o SQLite devolve naive. Este
    tipo normaliza os dois lados para `datetime` aware em UTC, para que
    aritmética de datas se comporte igual em dev/testes e em produção.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(
        self, value: datetime | None, dialect: object
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
