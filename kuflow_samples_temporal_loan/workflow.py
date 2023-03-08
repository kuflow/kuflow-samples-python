from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from kuflow_rest import models
    from kuflow_temporal_activity_kuflow import models as models_temporal
    from kuflow_temporal_activity_kuflow import KuFlowSyncActivities
    from kuflow_temporal_activity_kuflow import KuFlowAsyncActivities
    from kuflow_samples_temporal_loan.activities import ConvertRequest, ConvertResponse, CurrencyConversionActivities


@workflow.defn(name="SampleLoanWorkflow")
class SampleWorkflow:

    TASK_CODE_APPROVE_LOAN = "TASK_APPROVE_LOAN"
    TASK_CODE_LOAN_APPLICATION_FORM = "TASK_LOAN_APPLICATION"
    TASK_CODE_NOTIFICATION_OF_LOAN_GRANTED = "NOTIFICATION_GRANTED"
    TASK_CODE_NOTIFICATION_OF_LOAN_REJECTION = "NOTIFICATION_REJECTION"

    _default_retry_policy = RetryPolicy()
    _kuflow_activity_sync_start_to_close_timeout = timedelta(minutes=10)
    _kuflow_activity_sync_schedule_to_close_timeout = timedelta(days=365)
    _kuflow_activity_async_start_to_close_timeout = timedelta(days=1)
    _kuflow_activity_async_schedule_to_close_timeout = timedelta(days=365)

    async def create_task_approve__loan(self, task_loan_application: models.Task, amount_eur) -> models.Task:
        """Create task "Approve Loan" in KuFlow and wait for its completion"""

        # Currency is mandatory and not multiple
        first_name : models.TaskElementValueString = task_loan_application.element_values["FIRSTNAME"][0]
        last_name : models.TaskElementValueString = task_loan_application.element_values["LASTNAME"][0]

        id = workflow.uuid4()

        task_definition = models.TaskDefinitionSummary(code=self.TASK_CODE_APPROVE_LOAN)
        task = models.Task(id=id, process_id=task_loan_application.process_id, task_definition=task_definition)
        task.element_values = {}
        task.element_values["FIRSTNAME"] = [first_name]
        task.element_values["LASTNAME" ]= [last_name]
        task.element_values["AMOUNT"] = [models.TaskElementValueString(value=amount_eur)]

        await workflow.execute_activity(
            KuFlowAsyncActivities.create_task_and_wait_finished,
            models_temporal.CreateTaskRequest(task=task),
            start_to_close_timeout=self._kuflow_activity_async_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_async_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

        retrieveTaskResponse : models_temporal.RetrieveTaskResponse = await workflow.execute_activity(
            KuFlowSyncActivities.retrieve_task,
            models_temporal.RetrieveTaskRequest(taskId=id),
            start_to_close_timeout=self._kuflow_activity_sync_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_sync_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

        return retrieveTaskResponse.task

    async def create_task_loan__application__form(self, processId: str):
        """Create task "Loan Application Form" in KuFlow and wait for its completion"""

        id = workflow.uuid4()

        task_definition = models.TaskDefinitionSummary(code=self.TASK_CODE_LOAN_APPLICATION_FORM)
        task = models.Task(id=id, process_id=processId, task_definition=task_definition)

        await workflow.execute_activity(
            KuFlowAsyncActivities.create_task_and_wait_finished,
            models_temporal.CreateTaskRequest(task=task),
            start_to_close_timeout=self._kuflow_activity_async_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_async_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

        retrieveTaskResponse : models_temporal.RetrieveTaskResponse = await workflow.execute_activity(
            KuFlowSyncActivities.retrieve_task,
            models_temporal.RetrieveTaskRequest(taskId=id),
            start_to_close_timeout=self._kuflow_activity_sync_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_sync_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

        return retrieveTaskResponse.task

    async def create_task_notification_of_loan_granted(self, processId: str):
        """Create task "Notification of loan granted" in KuFlow and wait for its completion"""

        id = workflow.uuid4()

        task_definition = models.TaskDefinitionSummary(code=self.TASK_CODE_NOTIFICATION_OF_LOAN_GRANTED)
        task = models.Task(id=id, process_id=processId, task_definition=task_definition)

        await workflow.execute_activity(
            KuFlowAsyncActivities.create_task_and_wait_finished,
            models_temporal.CreateTaskRequest(task=task),
            start_to_close_timeout=self._kuflow_activity_async_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_async_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

    async def create_task_notification_of_loan_rejection(self, processId: str):
        """Create task "Notification of loan rejection" in KuFlow and wait for its completion"""

        id = workflow.uuid4()

        task_definition = models.TaskDefinitionSummary(code=self.TASK_CODE_NOTIFICATION_OF_LOAN_REJECTION)
        task = models.Task(id=id, process_id=processId, task_definition=task_definition)

        await workflow.execute_activity(
            KuFlowAsyncActivities.create_task_and_wait_finished,
            models_temporal.CreateTaskRequest(task=task),
            start_to_close_timeout=self._kuflow_activity_async_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_async_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

    async def complete_process(self, processId: str):
        """Complete Workflow"""

        await workflow.execute_activity(
            KuFlowSyncActivities.complete_process,
            models_temporal.CompleteProcessRequest(processId),
            start_to_close_timeout=self._kuflow_activity_sync_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_sync_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

    async def update_process_metadata(self, task_loan_application: models.Task) -> models.Task:
        # Currency is mandatory and not multiple
        first_name : models.TaskElementValueString = task_loan_application.element_values["FIRSTNAME"][0]
        last_name : models.TaskElementValueString = task_loan_application.element_values["LASTNAME"][0]

        process_metadata_first_name = models.ProcessElementValueString(value=first_name.value)
        process_metadata_last_name = models.ProcessElementValueString(value=last_name.value)

        await workflow.execute_activity(
            KuFlowSyncActivities.save_process_element,
            models_temporal.SaveProcessElementRequest(processId=task_loan_application.process_id, elementDefinitionCode="FIRSTNAME", elementValues=[process_metadata_first_name]),
            start_to_close_timeout=self._kuflow_activity_sync_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_sync_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

        await workflow.execute_activity(
            KuFlowSyncActivities.save_process_element,
            models_temporal.SaveProcessElementRequest(processId=task_loan_application.process_id, elementDefinitionCode="LASTNAME", elementValues=[process_metadata_last_name]),
            start_to_close_timeout=self._kuflow_activity_sync_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_sync_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

    async def convert_to_euros(self, currency, amount):
        if (currency == "EUR"):
            return amount

        create_task_response : ConvertResponse = await workflow.execute_activity(
            CurrencyConversionActivities.convert,
            ConvertRequest(amount=amount, base_currency=currency.lower(), target_currency="eur"),
            start_to_close_timeout=self._kuflow_activity_sync_start_to_close_timeout,
            schedule_to_close_timeout=self._kuflow_activity_sync_schedule_to_close_timeout,
            retry_policy=self._default_retry_policy,
        )

        return create_task_response.amount

    @workflow.run
    async def run(
        self, request: models_temporal.WorkflowRequest
    ) -> models_temporal.WorkflowResponse:
        workflow.logger.info(f"Process {request.processId} started")

        task_loan_application = await self.create_task_loan__application__form(request.processId)

        await self.update_process_metadata(task_loan_application)

        # Currency is mandatory and not multiple
        currency : models.TaskElementValueString = task_loan_application.element_values["CURRENCY"][0]
        # Amount is mandatory and not multiple
        amount : models.TaskElementValueString = task_loan_application.element_values["AMOUNT"][0]

        # Convert to euros
        amount_eur = await self.convert_to_euros(currency.value, amount.value)

        loan_authorized = True
        if amount_eur > 5000:
            task_approve__loan = await self.create_task_approve__loan(task_loan_application, amount_eur)
            # Approval is mandatory and not multiple
            approval = task_approve__loan.element_values["APPROVAL"][0]
            loan_authorized = approval == "YES"

        if loan_authorized:
            await self.create_task_notification_of_loan_granted(request.processId)
        else:
            await self.create_task_notification_of_loan_rejection(request.processId)

        await self.complete_process(request.processId)

        return models_temporal.WorkflowResponse(
            f"Completed process {request.processId}"
        )
