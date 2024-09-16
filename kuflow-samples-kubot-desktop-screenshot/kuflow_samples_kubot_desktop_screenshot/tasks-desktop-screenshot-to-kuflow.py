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
import mimetypes
import os

from kuflow_rest import models as models_rest
from PIL import ImageGrab

from kuflow_samples_kubot_desktop_screenshot._models import KuFlowEnvironmentVariablesConstants, RobotContext


###########################################
## Configuration
###########################################
# Set the logging level to INFO
logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

# Create execution context for the robot
global ROBOT_CONTEXT
ROBOT_CONTEXT = RobotContext()


###########################################
## Task
###########################################
def take_a_desktop_screenshot_to_kuflow():
    try:
        _LOGGER.info("Robot starts running")
        _append_log_message("<<<<< Robot execution begins >>>>>", models_rest.ProcessItemTaskLogLevel.INFO)

        image_path = os.path.join(ROBOT_CONTEXT.configuration.kf_execution_outdir, "screenshot.png")

        screenshot = ImageGrab.grab()
        screenshot.save(image_path)

        process_id = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_PROCESS_ID.value, None)
        process_item_id = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_TASK_ID.value, None)
        _upload_file(process_id, process_item_id, image_path)

        _append_log_message("<<<<< Robot execution ends >>>>>", models_rest.ProcessItemTaskLogLevel.INFO)
        _LOGGER.info("Robot job is done")
    except Exception as e:
        _LOGGER.error("Error executing robot", e)
        message = f"<<<<< Robot has ended unexpectedly. Details:: {e} >>>>>"
        _append_log_message(message, models_rest.ProcessItemTaskLogLevel.ERROR)
        raise e


def _upload_file(process_id: str, process_item_id: str, doc_path: str):
    file_name = os.path.basename(doc_path)
    file = open(doc_path, "rb")
    content_type = _guess_content_type(doc_path)
    document = models_rest.Document(
        file_mame=file_name,
        content_type=content_type,
        file_content=file,
    )

    document_reference = ROBOT_CONTEXT.kuFLow_client.process.upload_process_document(process_id, document)

    params = models_rest.ProcessItemTaskDataUpdateParams(
        data=models_rest.JsonValue(
            value={
                "file": document_reference.document_uri,
            }
        )
    )

    ROBOT_CONTEXT.kuFLow_client.process_item.update_process_item_task_data(
        id=process_item_id, process_item_task_data_update_params=params
    )


def _append_log_message(message: str, level: models_rest.ProcessItemTaskLogLevel) -> models_rest.ProcessItem:
    process_item_id = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_TASK_ID.value, None)

    params = models_rest.ProcessItemTaskAppendLogParams(message=message, level=level)
    process_item = ROBOT_CONTEXT.kuFLow_client.process_item.append_process_item_task_log(process_item_id, params)

    return process_item


def _guess_content_type(file_path):
    return mimetypes.guess_type(file_path)[0]


if __name__ == "__main__":
    take_a_desktop_screenshot_to_kuflow()
