from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from core.models import Base


class Currency(Base):
    # TODO: with my naming logic still need to write down the name if it ends with "ies" in multiple form
    __tablename__ = "currencies"

    # TODO: think about it: maybe we don't need it (?)
    # TODO: decide if we should keep more than one language (?)
    # name: Mapped[str] = mapped_column(String, nullable=False) # Example: US Dollar, Euro, Russian Ruble etc.
    # symbol: Mapped[str] = mapped_column(String(1), nullable=True) # Example: $, £, €

    abbreviation: Mapped[str] = mapped_column(String, nullable=False)  # Example: USD, EUR, RUB etc.

    def __repr__(self) -> str:
        return "<Currency(id=%s, abbreviation=%s)>" % (self.id, self.abbreviation)
