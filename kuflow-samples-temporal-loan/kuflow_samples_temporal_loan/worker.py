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

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import yaml
from deepmerge import always_merger
from kuflow_rest import KuFlowRestClient
from kuflow_temporal_activity_kuflow import KuFlowActivities
from kuflow_temporal_common.connection import (
    KuFlowConfig,
    KuFlowTemporalConnection,
    TemporalClientConfig,
    TemporalConfig,
    TemporalWorkerConfig,
)

from kuflow_samples_temporal_loan.activities import CurrencyConversionActivities
from kuflow_samples_temporal_loan.workflow import SampleWorkflow


logging.basicConfig(level=logging.INFO)


async def run_worker():
    """Worker to run your workflow

    This example configures a Temporal.io worker with the necessary authentication
    mechanisms for KuFlow (mTLS and token authorization). It also acts as activity
    worker for the set of activities that interact with the KuFlow Api rest.
    """

    configuration = load_configuration()

    # Rest client for the KuFlow API
    # Necessary for the activities that connect to KuFlow, as well as for the
    # management of the Temporal.io worker's authorization token.
    kuflow_rest_client = KuFlowRestClient(
        endpoint=configuration.kuflow_api_endpoint,
        client_id=configuration.kuflow_api_client_id,
        client_secret=configuration.kuflow_api_client_secret,
    )

    # Initializing KuFlow Temporal.io activities
    kuflow_activities = KuFlowActivities(kuflow_rest_client)

    # Initializing custom activities
    currency_conversion_activities = CurrencyConversionActivities()

    # Activities for the worker
    activities = kuflow_activities.activities + currency_conversion_activities.activities

    # KuFlow Temporal connection
    kuflow_temporal_connection = KuFlowTemporalConnection(
        kuflow=KuFlowConfig(rest_client=kuflow_rest_client),
        temporal=TemporalConfig(
            client=TemporalClientConfig(
                target_host=configuration.temporal_host,
            ),
            worker=TemporalWorkerConfig(
                task_queue=configuration.temporal_queue,
                workflows=[SampleWorkflow],
                activities=activities,
                debug_mode=True,
            ),
        ),
    )

    # Start temporal worker
    await kuflow_temporal_connection.run_worker()


class SamplesConfiguration:
    def __init__(
        self,
        *,
        kuflow_api_endpoint: Optional[str] = None,
        kuflow_api_client_id: str,
        kuflow_api_client_secret: str,
        temporal_host: Optional[str] = None,
        temporal_queue: str,
    ):
        self.kuflow_api_endpoint = kuflow_api_endpoint
        self.kuflow_api_client_id = kuflow_api_client_id
        self.kuflow_api_client_secret = kuflow_api_client_secret

        self.temporal_host = temporal_host
        self.temporal_queue = temporal_queue


def load_configuration() -> SamplesConfiguration:
    configuration_base = read_configuration("application.yaml")
    configuration_local = read_configuration("application-local.yaml")
    configuration = always_merger.merge(configuration_base, configuration_local)

    return parse_configuration(configuration)


def parse_configuration(configuration) -> SamplesConfiguration:
    kuflow_api_endpoint = find_configuration_property(configuration, "KUFLOW_API_ENDPOINT", "kuflow.api.endpoint")
    kuflow_api_client_id = retrieve_configuration_property(configuration, "KUFLOW_API_CLIENTID", "kuflow.api.client-id")
    kuflow_api_client_secret = retrieve_configuration_property(
        configuration, "KUFLOW_API_CLIENTSECRET", "kuflow.api.client-secret"
    )
    temporal_host = find_configuration_property(configuration, "TEMPORAL_TARGET", "temporal.target")
    temporal_queue = retrieve_configuration_property(configuration, "TEMPORAL_KUFLOWQUEUE", "temporal.kuflow-queue")

    return SamplesConfiguration(
        kuflow_api_endpoint=kuflow_api_endpoint,
        kuflow_api_client_id=kuflow_api_client_id,
        kuflow_api_client_secret=kuflow_api_client_secret,
        temporal_host=temporal_host,
        temporal_queue=temporal_queue,
    )


def retrieve_configuration_property(configuration: dict, property_environment_name: str, property_path: str) -> str:
    value = find_configuration_property(configuration, property_environment_name, property_path)
    if value is None:
        raise Exception(f"Property {property_path} not found")

    return find_configuration_property_from_conf(configuration, property_path)


def find_configuration_property(
    configuration: dict, property_environment_name: str, property_path: str
) -> Optional[str]:
    if os.environ.get(property_environment_name) is not None:
        return os.environ[property_environment_name]

    return find_configuration_property_from_conf(configuration, property_path)


def find_configuration_property_from_conf(configuration: dict, property_path: str) -> Optional[str]:
    property_parts = property_path.split(".", 1)
    property_name = property_parts[0] if len(property_parts) >= 1 else ""
    property_path_rest = property_parts[1] if len(property_parts) == 2 else ""
    value = configuration.get(property_name)
    if value is None:
        return None

    if isinstance(value, dict):
        return find_configuration_property_from_conf(value, property_path_rest)

    if isinstance(value, str) or isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
        return str(value)

    return None


def read_configuration(file: str) -> dict:
    configuration_path = Path(__file__).with_name(file)

    if configuration_path.exists() is False:
        return {}

    with open(Path(__file__).with_name(file)) as file:
        yaml_data = yaml.safe_load(file)

        return dict(yaml_data)


if __name__ == "__main__":
    asyncio.run(run_worker())
