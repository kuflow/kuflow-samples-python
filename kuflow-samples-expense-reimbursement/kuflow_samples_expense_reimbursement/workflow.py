#
# MIT License
#
# Copyright © 2024-present KuFlow S.L.
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


@workflow.defn(name="TEST")
class SampleWorkflow:
    MYAPP_ID = "FILL_ME"  # ADAPTATION FROM TEMPLATE

    TASK_CODE_SUBMIT_EXPENSE_CLAIM = "FILL_INFO"
    TASK_CODE_APPROVE_CLAIM = "APPROVAL"
    TASK_CODE_PROCESS_REIMBURSEMENT = "PROCESS"

    _KUFLOW_ACTIVITY_RETRY_POLICY = RetryPolicy()
    _KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT = timedelta(minutes=10)
    _KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT = timedelta(days=365)

    def __init__(self) -> None:
        self._kuflow_completed_task_ids: List[str] = []

    @workflow.signal(name=models_workflow.KUFLOW_ENGINE_SIGNAL_PROCESS_ITEM)
    async def kuflow_engine_signal_process_item(self, signal: models_workflow.SignalProcessItem) -> None:
        if signal.type == models_workflow.SignalProcessItemType.TASK:
            self._kuflow_completed_task_ids.append(signal.id)

    @workflow.run
    async def run(self, request: models_workflow.WorkflowRequest) -> models_workflow.WorkflowResponse:
        workflow.logger.info(f"Process {request.process_id} started")

        # ADAPTATION FROM TEMPLATE
        process_item_workflow = None
        needToRegister = False
        while True:
            process_item_workflow = await self.create_process_item_submit__expense__claim(
                request.process_id, process_item_workflow
            )

            amount = str(process_item_workflow.task.data.value["AMOUNT"])

            if float(amount) <= 1000:
                needToRegister = True
                break
            else:
                approval_task_workflow = await self.create_process_item_approve__claim(request.process_id)
                decision = approval_task_workflow.task.data.value["DECISION"]
                if decision == "ACCEPTED":
                    needToRegister = True
                    break
                if decision == "REJECTED":
                    needToRegister = False
                    break
                # Unnecesary, but we keep it for more legibility
                # if decision == "REVIEW":
                # continue

        if needToRegister:
            await self.create_process_item_process__reimbursement(request.process_id)
        # END OF ADAPTATION

        return models_workflow.WorkflowResponse(f"Completed process {request.process_id}")

    async def create_process_item_submit__expense__claim(self, process_id: str, previous_task):
        """Create process item "Submit Expense Claim" in KuFlow and wait for its completion"""

        process_item_id = str(uuid7())

        # ADAPTATION FROM TEMPLATE
        # We get the process initiator id
        process_retrieve_request = models_activity.ProcessRetrieveRequest(process_id=process_id)
        process_retrieve_response: models_activity.ProcessRetrieveResponse = await workflow.execute_activity(
            KuFlowActivities.retrieve_process,
            process_retrieve_request,
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )
        owner_id = process_retrieve_response.process.initiator_id

        # We get data from previous task execution
        task = None
        if previous_task is not None:
            task = models_rest.ProcessItemTaskCreateParams(data=previous_task.task.data)
        # END OF ADAPTATION

        request = models_activity.ProcessItemCreateRequest(
            id=process_item_id,
            process_id=process_id,
            type=models_rest.ProcessItemType.TASK,
            process_item_definition_code=SampleWorkflow.TASK_CODE_SUBMIT_EXPENSE_CLAIM,
            owner_id=owner_id,  # ADAPTION FROM TEMPLATE
            task=task,  # ADAPTION FROM TEMPLATE
        )

        # Create process item
        await workflow.execute_activity(
            KuFlowActivities.create_process_item,
            request,
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )

        # Wait for its external completion (outside this workflow, usually in the KuFlow APP or via Rest Api)
        # This line is useful if you are orchestrating asynchronous tasks, e.g. those performed by humans.
        # In the case of synchronous tasks, i.e. tasks that are completed by this Workflow itself,
        # you should remove this line and do not forget to add code to complete the task programmatically.
        await workflow.wait_condition(lambda: process_item_id in self._kuflow_completed_task_ids)

        # ADAPTATION FROM TEMPLATE
        # We need the process item
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
        # END OF ADAPTATION

    async def create_process_item_approve__claim(self, process_id: str):
        """Create process item "Approve Claim" in KuFlow and wait for its completion"""

        process_item_id = str(uuid7())

        request = models_activity.ProcessItemCreateRequest(
            id=process_item_id,
            process_id=process_id,
            type=models_rest.ProcessItemType.TASK,
            process_item_definition_code=SampleWorkflow.TASK_CODE_APPROVE_CLAIM,
        )

        # Create process item
        await workflow.execute_activity(
            KuFlowActivities.create_process_item,
            request,
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )

        # Wait for its external completion (outside this workflow, usually in the KuFlow APP or via Rest Api)
        # This line is useful if you are orchestrating asynchronous tasks, e.g. those performed by humans.
        # In the case of synchronous tasks, i.e. tasks that are completed by this Workflow itself,
        # you should remove this line and do not forget to add code to complete the task programmatically.
        await workflow.wait_condition(lambda: process_item_id in self._kuflow_completed_task_ids)

        # ADAPTATION FROM TEMPLATE
        # We need the process item
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
        # END OF ADAPTATION

    async def create_process_item_process__reimbursement(self, process_id: str):
        """Create process item "Process Reimbursement" in KuFlow and wait for its completion"""

        process_item_id = str(uuid7())

        request = models_activity.ProcessItemCreateRequest(
            id=process_item_id,
            process_id=process_id,
            type=models_rest.ProcessItemType.TASK,
            process_item_definition_code=SampleWorkflow.TASK_CODE_PROCESS_REIMBURSEMENT,
            owner_id=SampleWorkflow.MYAPP_ID,  # ADAPTATION FROM TEMPLATE: We specify the owner
        )

        # Create process item
        await workflow.execute_activity(
            KuFlowActivities.create_process_item,
            request,
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )

        # ADAPTATION FROM TEMPLATE
        # This is a task that is completed by this Workflow itself, so no need of this line
        # await workflow.wait_condition(lambda: process_item_id in self._kuflow_completed_task_ids)
        # instead we do whatever we need

        # We update the task information
        request: models_activity.ProcessItemTaskDataUpdateRequest = models_activity.ProcessItemTaskDataUpdateRequest(
            process_item_id=process_item_id,
            data=models_rest.JsonValue(value={"COMMENTS": "Registered automatically. Transaction ID 1338"}),
        )
        request: models_activity.ProcessItemTaskDataUpdateResponse = await workflow.execute_activity(
            KuFlowActivities.update_process_item_task_data,
            request,
            start_to_close_timeout=timedelta(days=1),
            schedule_to_close_timeout=timedelta(days=365),
            retry_policy=RetryPolicy(maximum_interval=timedelta(seconds=30)),
        )

        # We complete the task
        request = models_activity.ProcessItemTaskCompleteRequest(process_item_id=process_item_id)
        await workflow.execute_activity(
            KuFlowActivities.complete_process_item_task,
            request,
            start_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_START_TO_CLOSE_TIMEOUT,
            schedule_to_close_timeout=SampleWorkflow._KUFLOW_ACTIVITY_SCHEDULE_TO_CLOSE_TIMEOUT,
            retry_policy=SampleWorkflow._KUFLOW_ACTIVITY_RETRY_POLICY,
        )
        # END OF ADAPTATION


#
# End of the workflow
#
