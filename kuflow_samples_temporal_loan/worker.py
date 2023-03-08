import asyncio
import logging
import dataclasses
import yaml

from temporalio.client import Client, TLSConfig
from temporalio.worker import Worker
from temporalio.converter import DataConverter

from kuflow_temporal_activity_kuflow.converter import KuFlowPayloadConverter
from kuflow_temporal_common.authentication import KuFlowAuthorizationTokenProvider
from kuflow_rest import KuFlowRestClient
from kuflow_temporal_activity_kuflow import KuFlowAsyncActivities
from kuflow_temporal_activity_kuflow import KuFlowSyncActivities
from kuflow_samples_temporal_loan.activities import CurrencyConversionActivities

from kuflow_samples_temporal_loan.workflow import SampleWorkflow


logging.basicConfig(level=logging.INFO)

# Load configuration
with open("kuflow_samples_temporal_loan/application.yaml", "r") as file:
    yaml_data = yaml.safe_load(file)

    client_id = yaml_data["kuflow"]["api"]["client-id"]
    client_secret = yaml_data["kuflow"]["api"]["client-secret"]

    server_root_ca_cert = yaml_data["temporal"]["mutual-tls"]["ca-data"]
    server_root_ca_cert = server_root_ca_cert.encode("utf-8")
    client_cert = yaml_data["temporal"]["mutual-tls"]["cert-data"]
    client_cert = client_cert.encode("utf-8")
    client_key = yaml_data["temporal"]["mutual-tls"]["key-data"]
    client_key = client_key.encode("utf-8")

    temporal_host = yaml_data["temporal"]["target"]
    temporal_namespace = yaml_data["temporal"]["namespace"]
    temporal_queue = yaml_data["temporal"]["kuflow-queue"]


async def run_worker():
    """Worker to run your workflow

    This example configures a Temporal.io worker with the necessary authentication
    mechanisms for KuFlow (mTLS and token authorization). It also acts as activity
    worker for the set of activities that interact with the KuFlow Api rest.
    """

    # Rest client for the KuFlow API
    # Necessary for the activities that connect to KuFlow, as well as for the
    # management of the Temporal.io worker's authorization token.
    kuflow_client = KuFlowRestClient(
        client_id=client_id,
        client_secret=client_secret
    )

    # Initializing an KuFlow token provider
    kuflow_authorization_token_provider = KuFlowAuthorizationTokenProvider(
        kuflow_client=kuflow_client
    )

    # Temporal Client initialization
    client = await Client.connect(
        temporal_host,
        namespace=temporal_namespace,
        tls=TLSConfig(
            server_root_ca_cert=server_root_ca_cert,
            client_cert=client_cert,
            client_private_key=client_key,
        ),
        rpc_metadata=kuflow_authorization_token_provider.initialize_rpc_auth_metadata(),
        data_converter=dataclasses.replace(
            DataConverter.default,
            payload_converter_class=KuFlowPayloadConverter,
        ),
    )

    # Important. Do not forget.
    # Start in background, the auto-renewal of the Temporal.io connection token.
    kuflow_authorization_token_provider.start_auto_refresh(client)

    # Initializing KuFlow Temporal.io activities
    kuflow_sync_activities = KuFlowSyncActivities(kuflow_client)
    kuflow_async_activities = KuFlowAsyncActivities(kuflow_client)

    # Initializing custom activities
    currency_conversion_activities = CurrencyConversionActivities()

    # Activities for the worker
    activities = kuflow_sync_activities.activities  + kuflow_async_activities.activities + [currency_conversion_activities.convert]

    # Temporal Worker initialization
    worker = Worker(
        client,
        debug_mode=True,
        task_queue=temporal_queue,
        workflows=[SampleWorkflow],
        activities=activities
    )

    # Run a worker for the workflow
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
