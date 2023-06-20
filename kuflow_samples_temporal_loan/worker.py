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

import asyncio
import logging
import yaml

from pathlib import Path
from deepmerge import always_merger

from typing import Optional

from temporalio.client import TLSConfig

from kuflow_rest import KuFlowRestClient
from kuflow_temporal_common.connection import (
    KuFlowTemporalConnection,
    KuFlowConfig,
    TemporalConfig,
    TemporalClientConfig,
    TemporalWorkerConfig,
)
from kuflow_temporal_activity_kuflow import KuFlowAsyncActivities, KuFlowSyncActivities


from kuflow_samples_temporal_loan.activities import CurrencyConversionActivities
from kuflow_samples_temporal_loan.workflow import SampleWorkflow


logging.basicConfig(level=logging.INFO)


async def run_worker():
    """Worker to run your workflow

    This example configures a Temporal.io worker with the necessary authentication
    mechanisms for KuFlow (mTLS and token authorization). It also acts as activity
    worker for the set of activities that interact with the KuFlow Api rest.
    """

    configuration = load_configurations()

    # Rest client for the KuFlow API
    # Necessary for the activities that connect to KuFlow, as well as for the
    # management of the Temporal.io worker's authorization token.
    kuflow_rest_client = KuFlowRestClient(
        endpoint=configuration.kuflow_api_endpoint,
        client_id=configuration.kuflow_api_client_id,
        client_secret=configuration.kuflow_api_client_secret,
    )

    # Initializing KuFlow Temporal.io activities
    kuflow_sync_activities = KuFlowSyncActivities(kuflow_rest_client)
    kuflow_async_activities = KuFlowAsyncActivities(kuflow_rest_client)

    # Initializing custom activities
    currency_conversion_activities = CurrencyConversionActivities()

    # Activities for the worker
    activities = (
        kuflow_sync_activities.activities
        + kuflow_async_activities.activities
        + currency_conversion_activities.activities
    )

    # KuFlow Temporal connection
    kuflow_temporal_connection = KuFlowTemporalConnection(
        kuflow=KuFlowConfig(rest_client=kuflow_rest_client),
        temporal=TemporalConfig(
            client=TemporalClientConfig(
                target_host=configuration.temporal_host,
                namespace=configuration.temporal_namespace,
                tls=TLSConfig(
                    server_root_ca_cert=configuration.temporal_server_root_ca_cert,
                    client_cert=configuration.temporal_client_cert,
                    client_private_key=configuration.temporal_client_key,
                ),
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
    kuflow_api_client_id: str
    kuflow_api_client_secret: str
    kuflow_api_endpoint: Optional[str]

    temporal_host: str
    temporal_namespace: str
    temporal_queue: str
    temporal_server_root_ca_cert: bytes
    temporal_client_cert: bytes
    temporal_client_key: bytes

    def __init__(
        self,
        *,
        kuflow_api_client_id: str,
        kuflow_api_client_secret: str,
        kuflow_api_endpoint: Optional[str] = None,
        temporal_host: Optional[str] = None,
        temporal_namespace: str,
        temporal_queue: str,
        temporal_server_root_ca_cert: bytes,
        temporal_client_cert: bytes,
        temporal_client_key: bytes,
    ):
        self.kuflow_api_client_id = kuflow_api_client_id
        self.kuflow_api_client_secret = kuflow_api_client_secret
        self.kuflow_api_endpoint = kuflow_api_endpoint

        self.temporal_host = temporal_host
        self.temporal_namespace = temporal_namespace
        self.temporal_queue = temporal_queue
        self.temporal_server_root_ca_cert = temporal_server_root_ca_cert
        self.temporal_client_cert = temporal_client_cert
        self.temporal_client_key = temporal_client_key


def load_configurations() -> SamplesConfiguration:
    configration_base = load_configuration("application.yaml")
    configration_local = load_configuration("application-local.yaml")
    configuration = always_merger.merge(configration_base, configration_local)

    return parse_configuration(configuration)


def parse_configuration(configuration) -> SamplesConfiguration:
    kuflow_api_endpoint = configuration["kuflow"]["api"].get("endpoint")
    kuflow_api_client_id = configuration["kuflow"]["api"]["client-id"]
    kuflow_api_client_secret = configuration["kuflow"]["api"]["client-secret"]
    temporal_host = configuration["temporal"].get("target")
    temporal_namespace = configuration["temporal"]["namespace"]
    temporal_queue = configuration["temporal"]["kuflow-queue"]
    temporal_server_root_ca_cert = configuration["temporal"]["mutual-tls"]["ca-data"]
    temporal_server_root_ca_cert = temporal_server_root_ca_cert.encode("utf-8")
    temporal_client_cert = configuration["temporal"]["mutual-tls"]["cert-data"]
    temporal_client_cert = temporal_client_cert.encode("utf-8")
    temporal_client_key = configuration["temporal"]["mutual-tls"]["key-data"]
    temporal_client_key = temporal_client_key.encode("utf-8")

    return SamplesConfiguration(
        kuflow_api_endpoint=kuflow_api_endpoint,
        kuflow_api_client_id=kuflow_api_client_id,
        kuflow_api_client_secret=kuflow_api_client_secret,
        temporal_host=temporal_host,
        temporal_namespace=temporal_namespace,
        temporal_queue=temporal_queue,
        temporal_server_root_ca_cert=temporal_server_root_ca_cert,
        temporal_client_cert=temporal_client_cert,
        temporal_client_key=temporal_client_key,
    )


def load_configuration(file: str) -> dict:
    configuration_path = Path(__file__).with_name(file)

    if configuration_path.exists() is False:
        return {}

    with open(Path(__file__).with_name(file), "r") as file:
        yaml_data = yaml.safe_load(file)

        return dict(yaml_data)


if __name__ == "__main__":
    asyncio.run(run_worker())
