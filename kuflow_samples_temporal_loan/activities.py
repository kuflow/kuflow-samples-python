# coding=utf-8
#
# MIT License
#
# Copyright (c) 2022 KuFlow
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

import requests

from temporalio import activity
from dataclasses import dataclass

CONVERT_ENDPOINT = (
    "https://cdn.jsdelivr.net/gh/fawazahmed0/currency-api@1/latest/currencies"
)


@dataclass
class ConvertRequest:
    amount: float
    base_currency: str
    target_currency: str


@dataclass
class ConvertResponse:
    amount: float


class CurrencyConversionActivities:
    def __init__(self):
        self.activities = [self.convert]

    @activity.defn(name="Currency_convert")
    async def convert(self, request: ConvertRequest) -> ConvertResponse:
        # Make a GET request to the API
        response = requests.get(
            f"{CONVERT_ENDPOINT}/{request.base_currency}/{request.target_currency}.json"
        )

        # Parse the response JSON
        data = response.json()

        # Get the exchange rate
        exchange_rate = data[request.target_currency]

        # Convert
        result = exchange_rate * request.amount

        return ConvertResponse(amount=result)
