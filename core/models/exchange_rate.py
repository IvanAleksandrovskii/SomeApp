import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Float, DateTime, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, joinedload

from core.models import Base, TransferProvider, Currency


class ProviderExchangeRate(Base):
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transfer_providers.id", ondelete="CASCADE"),
                                                   nullable=False)
    provider: Mapped[TransferProvider] = relationship("TransferProvider", back_populates="exchange_rates",
                                                      lazy='joined')
    from_currency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("currencies.id", ondelete="CASCADE"), nullable=False)
    from_currency: Mapped[Currency] = relationship("Currency", foreign_keys=[from_currency_id], lazy="joined")

    to_currency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("currencies.id", ondelete="CASCADE"), nullable=False)
    to_currency: Mapped[Currency] = relationship("Currency", foreign_keys=[to_currency_id], lazy="joined")

    rate: Mapped[float] = mapped_column(Float, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint('provider_id', 'from_currency_id', 'to_currency_id', name='uq_provider_from_to_currency'),
        Index('idx_provider_exchange_rate_provider', 'provider_id'),
        Index('idx_provider_exchange_rate_from_currency', 'from_currency_id'),
        Index('idx_provider_exchange_rate_to_currency', 'to_currency_id'),
    )

    @classmethod
    def get_list_query(cls):
        return cls.active().options(
            joinedload(cls.provider),
            joinedload(cls.from_currency),
            joinedload(cls.to_currency)
        )

    def __str__(self):
        return f"{self.provider.name}: {self.from_currency.abbreviation} -> {self.to_currency.abbreviation} = {self.rate}"

    def __repr__(self) -> str:
        return (f"<ProviderExchangeRate(id={self.id}, from={self.from_currency_id}, "
                f"to={self.to_currency_id}, rate={self.rate}, last_updated={self.last_updated})>")
