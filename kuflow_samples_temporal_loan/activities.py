import requests
import asyncio

from temporalio import activity
from dataclasses import dataclass

@dataclass
class ConvertRequest:
    amount: float
    base_currency: str
    target_currency: str

@dataclass
class ConvertResponse:
    amount: float

class CurrencyConversionActivities:
    pass

    @activity.defn
    async def convert(self, request: ConvertRequest) -> ConvertResponse:
        # Make a GET request to the API
        response = requests.get(f'https://cdn.jsdelivr.net/gh/fawazahmed0/currency-api@1/latest/currencies/{request.base_currency}/{request.target_currency}.json')

        # Parse the response JSON
        data = response.json()

        # Get the exchange rate
        exchange_rate = data[request.target_currency]

        # Convert
        result = exchange_rate * request.amount

        return ConvertResponse(amount=result)
