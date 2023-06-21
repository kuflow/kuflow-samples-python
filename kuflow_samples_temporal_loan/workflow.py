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

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from kuflow_rest import models
    from kuflow_rest.utils import TaskUtils
    from kuflow_temporal_activity_kuflow import (
        KuFlowAsyncActivities,
        KuFlowSyncActivities,
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
    TASK_CODE_APPROVE_LOAN = "APPROVE_LOAN"
    TASK_CODE_LOAN_APPLICATION_FORM = "LOAN_APPLICATION"
    TASK_CODE_NOTIFICATION_OF_LOAN_GRANTED = "NOTIFICATION_GRANTED"
    TASK_CODE_NOTIFICATION_OF_LOAN_REJECTION = "NOTIFICATION_REJECTION"

    _default_retry_policy = RetryPolicy()
    _kuflow_activity_sync_start_to_close_timeout = timedelta(minutes=10)
    _kuflow_activity_sync_schedule_to_close_timeout = timedelta(days=365)
    _kuflow_activity_async_start_to_close_timeout = timedelta(days=1)
    _kuflow_activity_async_schedule_to_close_timeout = timedelta(days=365)

    async def create_task_approve__loan(
        self, task_loan_application: models.Task, amount_eur
    ) -> models.Task:
        """Create task "Approve Loan" in KuFlow and wait for its completion"""

        # Currency is mandatory and not multiple
        first_name = TaskUtils.get_element_value_as_str(
            task_loan_application, "FIRST_NAME"
        )
        last_name = TaskUtils.get_element_value_as_str(
            task_loan_application, "LAST_NAME"
        )

        task_id = str(workflow.uuid4())

        task_definition = models.TaskDefinitionSummary(code=self.TASK_CODE_APPROVE_LOAN)
        task = models.Task(
            id=task_id,
            process_id=task_loan_application.process_id,
            task_definition=task_definition,
        )
        TaskUtils.add_element_value(task, "FIRST_NAME", first_name)
        TaskUtils.add_element_value(task, "LAST_NAME", last_name)
        TaskUtils.add_element_value(task, "AMOUNT", amount_eur)

        await workflow.execute_activity(
            KuFlowAsyncActivities.create_task_and_wait_finished,
            models_temporal.CreateTaskRequest(task=task),
            start_to_close_timeout=self._kuflow_activity_async_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_async_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

        retrieve_task_response: models_temporal.RetrieveTaskResponse = await workflow.execute_activity(
            KuFlowSyncActivities.retrieve_task,
            models_temporal.RetrieveTaskRequest(task_id=task_id),
            start_to_close_timeout=self._kuflow_activity_sync_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_sync_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

        return retrieve_task_response.task

    async def create_task_loan__application(self, process_id: str):
        """Create task "Loan Application" in KuFlow and wait for its completion"""

        task_id = str(workflow.uuid4())

        task_definition = models.TaskDefinitionSummary(
            code=self.TASK_CODE_LOAN_APPLICATION_FORM
        )
        task = models.Task(
            id=task_id, process_id=process_id, task_definition=task_definition
        )

        await workflow.execute_activity(
            KuFlowAsyncActivities.create_task_and_wait_finished,
            models_temporal.CreateTaskRequest(task=task),
            start_to_close_timeout=self._kuflow_activity_async_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_async_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

        retrieve_task_response: models_temporal.RetrieveTaskResponse = await workflow.execute_activity(
            KuFlowSyncActivities.retrieve_task,
            models_temporal.RetrieveTaskRequest(task_id=task_id),
            start_to_close_timeout=self._kuflow_activity_sync_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_sync_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

        return retrieve_task_response.task

    async def create_task_notification_of_loan_granted(self, process_id: str):
        """Create task "Notification of loan granted" in KuFlow and wait for its completion"""

        task_id = str(workflow.uuid4())

        task_definition = models.TaskDefinitionSummary(
            code=self.TASK_CODE_NOTIFICATION_OF_LOAN_GRANTED
        )
        task = models.Task(
            id=task_id, process_id=process_id, task_definition=task_definition
        )

        await workflow.execute_activity(
            KuFlowSyncActivities.create_task,
            models_temporal.CreateTaskRequest(task=task),
            start_to_close_timeout=self._kuflow_activity_async_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_async_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

    async def create_task_notification_of_loan_rejection(self, process_id: str):
        """Create task "Notification of loan rejection" in KuFlow and wait for its completion"""

        task_id = str(workflow.uuid4())

        task_definition = models.TaskDefinitionSummary(
            code=self.TASK_CODE_NOTIFICATION_OF_LOAN_REJECTION
        )
        task = models.Task(
            id=task_id, process_id=process_id, task_definition=task_definition
        )

        await workflow.execute_activity(
            KuFlowSyncActivities.create_task,
            models_temporal.CreateTaskRequest(task=task),
            start_to_close_timeout=self._kuflow_activity_async_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_async_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

    async def complete_process(self, process_id: str):
        """Complete Workflow"""

        await workflow.execute_activity(
            KuFlowSyncActivities.complete_process,
            models_temporal.CompleteProcessRequest(process_id),
            start_to_close_timeout=self._kuflow_activity_sync_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_sync_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

    async def update_process_metadata(self, task_loan_application: models.Task):
        await self.copy_task_element_to_process(task_loan_application, "FIRST_NAME")
        await self.copy_task_element_to_process(task_loan_application, "LAST_NAME")

    async def copy_task_element_to_process(
        self, task_loan_application: models.Task, element_definition_code: str
    ):
        value = TaskUtils.get_element_value_as_str(
            task_loan_application, element_definition_code
        )
        request = models_temporal.SaveProcessElementRequest(
            process_id=task_loan_application.process_id,
            element_definition_code=element_definition_code,
        )
        SaveProcessElementRequestUtils.add_element_value(request, value)
        await workflow.execute_activity(
            KuFlowSyncActivities.save_process_element,
            request,
            start_to_close_timeout=self._kuflow_activity_sync_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_sync_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

    async def convert_to_euros(self, currency: str, amount: float):
        if currency == "EUR":
            return amount

        create_task_response: ConvertResponse = await workflow.execute_activity(
            CurrencyConversionActivities.convert,
            ConvertRequest(
                amount=amount, base_currency=currency.lower(), target_currency="eur"
            ),
            start_to_close_timeout=self._kuflow_activity_sync_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_sync_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

        return create_task_response.amount

    @workflow.run
    async def run(
        self, request: models_temporal.WorkflowRequest
    ) -> models_temporal.WorkflowResponse:
        workflow.logger.info(f"Process {request.process_id} started")

        task_loan_application = await self.create_task_loan__application(
            request.process_id
        )

        await self.update_process_metadata(task_loan_application)

        currency = TaskUtils.get_element_value_as_str(task_loan_application, "CURRENCY")
        amount = TaskUtils.get_element_value_as_float(task_loan_application, "AMOUNT")

        # Convert to euros
        amount_eur = await self.convert_to_euros(currency, amount)

        loan_authorized = True
        if amount_eur > 5000:
            task_approve__loan = await self.create_task_approve__loan(
                task_loan_application, amount_eur
            )

            # Approval is mandatory and not multiple
            approval = TaskUtils.get_element_value_as_str(
                task_approve__loan, "APPROVAL"
            )
            loan_authorized = approval == "YES"

        if loan_authorized:
            await self.create_task_notification_of_loan_granted(request.process_id)
        else:
            await self.create_task_notification_of_loan_rejection(request.process_id)

        await self.complete_process(request.process_id)

        return models_temporal.WorkflowResponse(
            f"Completed process {request.process_id}"
        )
