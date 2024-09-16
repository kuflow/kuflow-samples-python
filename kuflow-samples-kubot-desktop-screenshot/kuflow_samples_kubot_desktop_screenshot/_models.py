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

import logging
import os
from dataclasses import dataclass
from enum import Enum

from kuflow_rest import KuBotTokenCredential, KuFlowRestClient


class KuFlowEnvironmentVariablesConstants(Enum):  # noqa: F821
    """
    See more in https://docs.kuflow.com/
    """

    # KuFlow API REST Endpoint
    KUFLOW_API_ENDPOINT = "KUFLOW_API_ENDPOINT"

    # Current user token
    KUFLOW_API_TOKEN = "KUFLOW_API_TOKEN"

    # User token expiration in milliseconds
    KUFLOW_API_TOKEN_EXPIRE_ON = "KUFLOW_API_TOKEN_EXPIRE_ON"

    # Organization identifier
    KUFLOW_TENANT_ID = "KUFLOW_TENANT_ID"

    # Process identifier that requested KuBot Execution
    KUFLOW_PROCESS_ID = "KUFLOW_PROCESS_ID"

    # Task identifier that requested KuBot Execution
    KUFLOW_TASK_ID = "KUFLOW_TASK_ID"

    # KuBot identifier
    KUFLOW_ROBOT_ID = "KUFLOW_ROBOT_ID"

    # Execute command requested
    KUFLOW_ROBOT_OPERATION = "KUFLOW_ROBOT_OPERATION"

    # Path to the KuBot installation destination
    KUFLOW_ROBOT_HOME_PATH = "KUFLOW_ROBOT_HOME_PATH"

    # Path to a specific robot run. Each run creates a path that the KuBot can use to write its outputs.
    # This paths are frequently eliminated by KuBot Manager
    KUFLOW_EXECUTION_OUTDIR = "KUFLOW_EXECUTION_OUTDIR"


class RobotConstants(Enum):
    PROCESS_METADATA__SEARCH_TEXT = "SEARCH_TEXT"

    # Useful in development when using on-premise KuFlow App deployment.
    # In a normal case (KuFlow App Deployment), leave it empty or False
    # Default: None
    ALLOW_INSECURE_CONNECTION = "ALLOW_INSECURE_CONNECTION"


@dataclass
class RobotConfiguration:
    """Class with configuration values"""

    kf_execution_outdir: str


class RobotContext:
    kuFLow_client: KuFlowRestClient

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self.configuration = self._load_configuration()
        self.kuFLow_client = self._load_kuFlow_client()

    def _load_configuration(self) -> RobotConfiguration:
        kf_execution_outdir = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_EXECUTION_OUTDIR.value, None)

        return RobotConfiguration(kf_execution_outdir=kf_execution_outdir)

    def _load_kuFlow_client(self) -> KuFlowRestClient:
        # User Api Token
        kf_api_token = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_API_TOKEN.value, None)

        # User Api Expire Token
        kf_api_token_expire_on = os.environ.get(
            KuFlowEnvironmentVariablesConstants.KUFLOW_API_TOKEN_EXPIRE_ON.value, None
        )
        kf_api_token_expire_on = int(kf_api_token_expire_on)

        # Api Endpoint
        kf_api_endpoint = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_API_ENDPOINT.value, None)
        if kf_api_endpoint == "" or kf_api_endpoint.lower() == "none":
            kf_api_endpoint = None

        # Allow insecure connection
        kf_allow_insecure_connection = os.environ.get(RobotConstants.ALLOW_INSECURE_CONNECTION.value, None)

        credential = KuBotTokenCredential(kf_api_token, kf_api_token_expire_on)

        return KuFlowRestClient(
            credential=credential,
            endpoint=kf_api_endpoint,
            allow_insecure_connection=kf_allow_insecure_connection,
        )
