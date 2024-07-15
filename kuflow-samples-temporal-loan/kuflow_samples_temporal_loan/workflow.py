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

from temporalio import workflow
from temporalio.common import RetryPolicy


with workflow.unsafe.imports_passed_through():
    from kuflow_rest import models
    from kuflow_rest.utils import TaskUtils
    from kuflow_temporal_activity_kuflow import (
        KUFLOW_ENGINE_SIGNAL_COMPLETED_TASK,
        KuFlowActivities,
    )
    from kuflow_temporal_activity_kuflow import models as models_temporal
    from kuflow_temporal_activity_kuflow.utils import SaveProcessElementRequestUtils

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

    @workflow.signal(name=KUFLOW_ENGINE_SIGNAL_COMPLETED_TASK)
    async def kuflow_engine_completed_task(self, task_id: str) -> None:
        self._kuflow_completed_task_ids.append(task_id)

    @workflow.run
    async def run(self, request: models_temporal.WorkflowRequest) -> models_temporal.WorkflowResponse:
        workflow.logger.info(f"Process {request.process_id} started")

        task_loan_application = await self._create_task_loan__application(request.process_id)

        await self._update_process_metadata(task_loan_application)

        currency = TaskUtils.get_element_value_as_str(task_loan_application, "CURRENCY")
        amount = TaskUtils.get_element_value_as_float(task_loan_application, "AMOUNT")

        # Convert to euros
        amount_eur = await self._convert_to_euros(currency, amount)

        loan_authorized = True
        if amount_eur > 5000:
            task_approve__loan = await self._create_task_approve__loan(task_loan_application, amount_eur)

            # Approval is mandatory and not multiple
            approval = TaskUtils.get_element_value_as_str(task_approve__loan, "APPROVAL")
            loan_authorized = approval == "YES"

        if loan_authorized:
            await self._create_task_notification_of_loan_granted(request.process_id)
        else:
            await self._create_task_notification_of_loan_rejection(request.process_id)

        return models_temporal.WorkflowResponse(f"Completed process {request.process_id}")

    async def _create_task_approve__loan(self, task_loan_application: models.Task, amount_eur) -> models.Task:
        """Create task "Approve Loan" in KuFlow and wait for its completion"""

        # Currency is mandatory and not multiple
        first_name = TaskUtils.get_element_value_as_str(task_loan_application, "FIRST_NAME")
        last_name = TaskUtils.get_element_value_as_str(task_loan_application, "LAST_NAME")

        task_id = str(workflow.uuid4())

        task_definition = models.TaskDefinitionSummary(code=SampleWorkflow._TASK_CODE_APPROVE_LOAN)
        task = models.Task(
            id=task_id,
            process_id=task_loan_application.process_id,
            task_definition=task_definition,
        )
        TaskUtils.add_element_value(task, "FIRST_NAME", first_name)
        TaskUtils.add_element_value(task, "LAST_NAME", last_name)
        TaskUtils.add_element_value(task, "AMOUNT", amount_eur)

        await self._create_task_and_wait_completion(task)

        retrieve_task_response: models_temporal.RetrieveTaskResponse = await workflow.execute_activity(
            KuFlowActivities.retrieve_task,
            models_temporal.RetrieveTaskRequest(task_id=task_id),
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )

        return retrieve_task_response.task

    async def _create_task_loan__application(self, process_id: str):
        """Create task "Loan Application" in KuFlow and wait for its completion"""

        task_id = str(workflow.uuid4())

        task_definition = models.TaskDefinitionSummary(code=SampleWorkflow._TASK_CODE_LOAN_APPLICATION_FORM)
        task = models.Task(id=task_id, process_id=process_id, task_definition=task_definition)

        await self._create_task_and_wait_completion(task)

        retrieve_task_response: models_temporal.RetrieveTaskResponse = await workflow.execute_activity(
            KuFlowActivities.retrieve_task,
            models_temporal.RetrieveTaskRequest(task_id=task_id),
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )

        return retrieve_task_response.task

    async def _create_task_notification_of_loan_granted(self, process_id: str):
        """Create task "Notification of loan granted" in KuFlow and wait for its completion"""

        task_id = str(workflow.uuid4())

        task_definition = models.TaskDefinitionSummary(code=SampleWorkflow._TASK_CODE_NOTIFICATION_OF_LOAN_GRANTED)
        task = models.Task(id=task_id, process_id=process_id, task_definition=task_definition)

        await self._create_task_and_wait_completion(task)

    async def _create_task_notification_of_loan_rejection(self, process_id: str):
        """Create task "Notification of loan rejection" in KuFlow and wait for its completion"""

        task_id = str(workflow.uuid4())

        task_definition = models.TaskDefinitionSummary(code=SampleWorkflow._TASK_CODE_NOTIFICATION_OF_LOAN_REJECTION)
        task = models.Task(id=task_id, process_id=process_id, task_definition=task_definition)

        await self._create_task_and_wait_completion(task)

    async def _update_process_metadata(self, task_loan_application: models.Task):
        await self._copy_task_element_to_process(task_loan_application, "FIRST_NAME")
        await self._copy_task_element_to_process(task_loan_application, "LAST_NAME")

    async def _copy_task_element_to_process(self, task_loan_application: models.Task, element_definition_code: str):
        value = TaskUtils.get_element_value_as_str(task_loan_application, element_definition_code)
        request = models_temporal.SaveProcessElementRequest(
            process_id=task_loan_application.process_id,
            element_definition_code=element_definition_code,
        )
        SaveProcessElementRequestUtils.add_element_value(request, value)

        await workflow.execute_activity(
            KuFlowActivities.save_process_element,
            request,
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )

    async def _convert_to_euros(self, currency: str, amount: float):
        if currency == "EUR":
            return amount

        create_task_response: ConvertResponse = await workflow.execute_activity(
            CurrencyConversionActivities.convert,
            ConvertRequest(amount=amount, base_currency=currency.lower(), target_currency="eur"),
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )

        return create_task_response.amount

    async def _create_task_and_wait_completion(self, task: models.Task) -> None:
        create_task_request = models_temporal.CreateTaskRequest(task=task)

        await workflow.execute_activity(
            KuFlowActivities.create_task,
            create_task_request,
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )
        await workflow.wait_condition(lambda: task.id in self._kuflow_completed_task_ids)
