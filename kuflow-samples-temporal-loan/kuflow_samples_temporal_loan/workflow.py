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

from datetime import timedelta
from typing import List

from kuflow_temporal_workflow_kuflow import uuid7
from temporalio import workflow
from temporalio.common import RetryPolicy


with workflow.unsafe.imports_passed_through():
    from kuflow_rest import models as models_rest
    from kuflow_temporal_activity_kuflow import KuFlowActivities
    from kuflow_temporal_activity_kuflow import models as models_activity
    from kuflow_temporal_workflow_kuflow import models as models_workflow

    from kuflow_samples_temporal_loan.activities import (
        ConvertRequest,
        ConvertResponse,
        CurrencyConversionActivities,
    )


@workflow.defn(name="SampleEngineWorkerLoanWorkflow")
class SampleWorkflow:
    _TASK_CODE_APPROVE_LOAN = "APPROVE_LOAN"
    _TASK_CODE_LOAN_APPLICATION_FORM = "LOAN_APPLICATION"
    _TASK_CODE_NOTIFICATION_OF_LOAN_GRANTED = "NOTIFICATION_GRANTED"
    _TASK_CODE_NOTIFICATION_OF_LOAN_REJECTION = "NOTIFICATION_REJECTION"

    _KUFLOW_ACTIVITY_RETRY_POLICY = RetryPolicy()
    _KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT = timedelta(minutes=10)
    _KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT = timedelta(days=365)

    def __init__(self) -> None:
        self._kuflow_completed_task_ids: List[str] = []

    @workflow.signal(name=models_workflow.KUFLOW_ENGINE_SIGNAL_PROCESS_ITEM)
    async def kuflow_engine_completed_task(self, signal: models_workflow.SignalProcessItem) -> None:
        if signal.type == models_workflow.SignalProcessItemType.TASK:
            self._kuflow_completed_task_ids.append(signal.id)

    @workflow.run
    async def run(self, request: models_workflow.WorkflowRequest) -> models_workflow.WorkflowResponse:
        workflow.logger.info(f"Process {request.process_id} started")

        process_item_loan_application = await self._create_process_item_loan_application(request.process_id)

        await self._update_process_metadata(process_item_loan_application)

        currency = str(process_item_loan_application.task.data.value.get("CURRENCY"))
        amount = str(process_item_loan_application.task.data.value.get("AMOUNT"))

        # Convert to euros
        amount_eur = await self._convert_to_euros(currency, amount)

        loan_authorized = True
        if float(amount_eur) > 5000:
            process_item_approve_loan = await self._create_process_item_approve_loan(
                process_item_loan_application, amount_eur
            )

            # Approval is mandatory and not multiple
            approval = str(process_item_approve_loan.task.data.value.get("APPROVAL"))
            loan_authorized = approval == "YES"

        if loan_authorized:
            await self._create_process_item_notification_of_loan_granted(request.process_id)
        else:
            await self._create_process_item_notification_of_loan_rejection(request.process_id)

        return models_workflow.WorkflowResponse(f"Completed process {request.process_id}")

    async def _create_process_item_approve_loan(
        self, process_item_loan_application: models_rest.ProcessItem, amount_eur: str
    ) -> models_rest.ProcessItem:
        """Create process item "Approve Loan" in KuFlow and wait for its completion"""

        # Currency is mandatory and not multiple
        first_name = str(process_item_loan_application.task.data.value.get("FIRST_NAME"))
        last_name = str(process_item_loan_application.task.data.value.get("LAST_NAME"))

        process_item_id = str(uuid7())

        create_request = models_activity.ProcessItemCreateRequest(
            id=process_item_id,
            process_id=process_item_loan_application.process_id,
            type=models_rest.ProcessItemType.TASK,
            task=models_rest.ProcessItemTaskCreateParams(
                task_definition_code=SampleWorkflow._TASK_CODE_APPROVE_LOAN,
                data=models_rest.JsonValue(
                    value={"FIRST_NAME": first_name, "LAST_NAME": last_name, "AMOUNT": amount_eur}
                ),
            ),
        )

        await self._create_process_item_and_wait_completion(create_request)

        retrieve_request = models_activity.ProcessItemRetrieveRequest(
            process_item_id=process_item_id,
        )
        retrieve_response: models_activity.ProcessItemRetrieveResponse = await workflow.execute_activity(
            KuFlowActivities.retrieve_process_item,
            retrieve_request,
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )

        return retrieve_response.process_item

    async def _create_process_item_loan_application(self, process_id: str):
        """Create process item "Loan Application" in KuFlow and wait for its completion"""

        process_item_id = str(uuid7())

        create_request = models_activity.ProcessItemCreateRequest(
            id=process_item_id,
            process_id=process_id,
            type=models_rest.ProcessItemType.TASK,
            task=models_rest.ProcessItemTaskCreateParams(
                task_definition_code=SampleWorkflow._TASK_CODE_LOAN_APPLICATION_FORM
            ),
        )

        await self._create_process_item_and_wait_completion(create_request)

        retrieve_response: models_activity.ProcessItemRetrieveResponse = await workflow.execute_activity(
            KuFlowActivities.retrieve_process_item,
            models_activity.ProcessItemRetrieveRequest(process_item_id=process_item_id),
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )

        return retrieve_response.process_item

    async def _create_process_item_notification_of_loan_granted(self, process_id: str):
        """Create process item "Notification of loan granted" in KuFlow and wait for its completion"""

        process_item_id = str(uuid7())

        create_request = models_activity.ProcessItemCreateRequest(
            id=process_item_id,
            process_id=process_id,
            type=models_rest.ProcessItemType.TASK,
            task=models_rest.ProcessItemTaskCreateParams(
                task_definition_code=SampleWorkflow._TASK_CODE_NOTIFICATION_OF_LOAN_GRANTED,
            ),
        )

        await self._create_process_item_and_wait_completion(create_request)

    async def _create_process_item_notification_of_loan_rejection(self, process_id: str):
        """Create process item "Notification of loan rejection" in KuFlow and wait for its completion"""

        process_item_id = str(uuid7())

        create_request = models_activity.ProcessItemCreateRequest(
            id=process_item_id,
            process_id=process_id,
            type=models_rest.ProcessItemType.TASK,
            task=models_rest.ProcessItemTaskCreateParams(
                task_definition_code=SampleWorkflow._TASK_CODE_NOTIFICATION_OF_LOAN_REJECTION,
            ),
        )

        await self._create_process_item_and_wait_completion(create_request)

    async def _update_process_metadata(self, process_item_loan_application: models_rest.ProcessItem):
        first_name = str(process_item_loan_application.task.data.value.get("FIRST_NAME"))
        last_name = str(process_item_loan_application.task.data.value.get("LAST_NAME"))

        request = models_activity.ProcessMetadataPatchRequest(
            process_id=process_item_loan_application.process_id,
            json_patch=[
                models_rest.JsonPatchOperation(
                    op=models_rest.JsonPatchOperationType.ADD, path="/FIRST_NAME", value=first_name
                ),
                models_rest.JsonPatchOperation(
                    op=models_rest.JsonPatchOperationType.ADD, path="/LAST_NAME", value=last_name
                ),
            ],
        )

        await workflow.execute_activity(
            KuFlowActivities.patch_process_metadata,
            request,
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )

    async def _convert_to_euros(self, currency: str, amount: str):
        if currency == "EUR":
            return amount

        create_task_response: ConvertResponse = await workflow.execute_activity(
            CurrencyConversionActivities.convert,
            ConvertRequest(amount=float(amount), base_currency=currency.lower(), target_currency="eur"),
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )

        return str(create_task_response.amount)

    async def _create_process_item_and_wait_completion(self, request: models_activity.ProcessItemCreateRequest) -> None:
        await workflow.execute_activity(
            KuFlowActivities.create_process_item,
            request,
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )
        await workflow.wait_condition(lambda: request.id in self._kuflow_completed_task_ids)
