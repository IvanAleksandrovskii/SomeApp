from typing import List
from uuid import UUID

from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from core import logger
from core.models import db_helper, TransferProvider, TransferRule, ProviderExchangeRate, Country
from core.schemas import ProviderResponse, ExchangeRateResponse, CurrencyResponse, DetailedTransferRuleResponse

router = APIRouter()


@router.get("/all-providers", response_model=List[ProviderResponse])
async def get_providers(session: AsyncSession = Depends(db_helper.session_getter)):
    query = (
        TransferProvider.active()
        .options(
            selectinload(TransferProvider.transfer_rules.and_(TransferRule.is_active == True))
            .selectinload(TransferRule.send_country),
            selectinload(TransferProvider.transfer_rules.and_(TransferRule.is_active == True))
            .selectinload(TransferRule.receive_country),
            selectinload(TransferProvider.transfer_rules.and_(TransferRule.is_active == True))
            .selectinload(TransferRule.transfer_currency)
        )
    )
    try:
        result = await session.execute(query)
        providers = result.unique().scalars().all()
    except SQLAlchemyError as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Internal server error")

    return [ProviderResponse(id=provider.id, name=provider.name, url=provider.url) for provider in providers]


@router.get("/provider/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: UUID,
    session: AsyncSession = Depends(db_helper.session_getter)
):
    query = (
        TransferProvider.active()
        .where(
            TransferProvider.id == provider_id,
        )
    )
    try:
        result = await session.execute(query)
        provider = result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal server error")

    if not provider:
        logger.warning(f"Provider not found or inactive for id: {provider_id}")
        raise HTTPException(status_code=404, detail="Provider not found or inactive")

    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        url=provider.url
    )


@router.get("/all-transfer-rules", response_model=List[DetailedTransferRuleResponse])
async def get_all_transfer_rules(session: AsyncSession = Depends(db_helper.session_getter)):
    query = (
        TransferRule.active()
        .options(
            joinedload(TransferRule.send_country).joinedload(Country.local_currency),
            joinedload(TransferRule.receive_country).joinedload(Country.local_currency),
            joinedload(TransferRule.provider),
            joinedload(TransferRule.transfer_currency),
            joinedload(TransferRule.required_documents)
        )
    )
    try:
        result = await session.execute(query)
        transfer_rules = result.unique().scalars().all()
    except SQLAlchemyError as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal server error")

    return [DetailedTransferRuleResponse.model_validate(rule) for rule in transfer_rules]


@router.get("/transfer-rule/{transfer_rule_id}", response_model=DetailedTransferRuleResponse)
async def get_transfer_rule(transfer_rule_id: UUID, session: AsyncSession = Depends(db_helper.session_getter)):
    query = (
        TransferRule.active()
        .where(TransferRule.id == transfer_rule_id)
        .options(
            joinedload(TransferRule.send_country).joinedload(Country.local_currency),
            joinedload(TransferRule.receive_country).joinedload(Country.local_currency),
            joinedload(TransferRule.provider),
            joinedload(TransferRule.transfer_currency),
            joinedload(TransferRule.required_documents)
        )
    )
    try:
        result = await session.execute(query)
        transfer_rule = result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal server error")

    if not transfer_rule:
        raise HTTPException(status_code=404, detail="Transfer rule not found")

    return DetailedTransferRuleResponse.model_validate(transfer_rule)


@router.get("/all-exchange-rates")
async def debug_get_all_exchange_rates(session: AsyncSession = Depends(db_helper.session_getter)):
    try:
        query = ProviderExchangeRate.active().options(
            joinedload(ProviderExchangeRate.provider),
            joinedload(ProviderExchangeRate.from_currency),
            joinedload(ProviderExchangeRate.to_currency)
        )
        try:
            result = await session.execute(query)
            exchange_rates = result.unique().scalars().all()
        except SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(status_code=500, detail="Internal server error")
        response_data = []
        for rate in exchange_rates:
            try:
                rate_dict = {
                    "id": str(rate.id),
                    "provider": {
                        "id": str(rate.provider.id),
                        "name": rate.provider.name,
                        "url": rate.provider.url
                    },
                    "from_currency": {
                        "id": str(rate.from_currency.id),
                        "name": rate.from_currency.name,
                        "symbol": rate.from_currency.symbol,
                        "abbreviation": rate.from_currency.abbreviation
                    },
                    "to_currency": {
                        "id": str(rate.to_currency.id),
                        "name": rate.to_currency.name,
                        "symbol": rate.to_currency.symbol,
                        "abbreviation": rate.to_currency.abbreviation
                    },
                    "rate": float(rate.rate),
                    "last_updated": rate.last_updated.isoformat() if rate.last_updated else None
                }
                response_data.append(rate_dict)
            except Exception as e:
                logger.error(f"Error processing exchange rate {rate.id}: {str(e)}")
                response_data.append({"error": f"Failed to process rate {rate.id}: {str(e)}"})

        logger.info(f"Successfully retrieved {len(response_data)} exchange rates")
        return {"status": "success", "data": response_data}

    except Exception as e:
        logger.error(f"Error in debug_get_all_exchange_rates: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.get("/exchange-rate/{exchange_rate_id}", response_model=ExchangeRateResponse)
async def get_exchange_rate(
    exchange_rate_id: UUID,
    session: AsyncSession = Depends(db_helper.session_getter)
):
    query = (
        select(ProviderExchangeRate)
        .options(
            joinedload(ProviderExchangeRate.provider),
            joinedload(ProviderExchangeRate.from_currency),
            joinedload(ProviderExchangeRate.to_currency)
        )
        .where(
            ProviderExchangeRate.id == exchange_rate_id,
            ProviderExchangeRate.is_active == True,
            ProviderExchangeRate.provider.has(TransferProvider.is_active == True)
        )
    )
    try:
        result = await session.execute(query)
        exchange_rate = result.unique().scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal server error")

    if not exchange_rate:
        logger.warning(f"Exchange rate not found or inactive for id: {exchange_rate_id}")
        raise HTTPException(status_code=404, detail="Exchange rate not found or inactive")

    return ExchangeRateResponse(
        id=exchange_rate.id,
        provider=ProviderResponse(
            id=exchange_rate.provider.id,
            name=exchange_rate.provider.name,
            url=exchange_rate.provider.url
        ),
        from_currency=CurrencyResponse.model_validate(exchange_rate.from_currency),
        to_currency=CurrencyResponse.model_validate(exchange_rate.to_currency),
        rate=exchange_rate.rate,
        last_updated=exchange_rate.last_updated
    )
