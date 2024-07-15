import json
import logging
import mimetypes
import os

from PIL import ImageGrab

from kuflow_rest import models as kf_models
from kuflow_samples_kubot_desktop_screenshot.models import KuFlowEnvironmentVariablesConstants, RobotContext


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
        _append_log_message("<<<<< Robot execution begins >>>>>", kf_models.LogLevel.INFO)

        image_path = os.path.join(ROBOT_CONTEXT.configuration.kf_execution_outdir, "screenshot.png")

        screenshot = ImageGrab.grab()
        screenshot.save(image_path)

        task_id = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_TASK_ID.value, None)
        _upload_file(task_id, image_path)

        _append_log_message("<<<<< Robot execution ends >>>>>", kf_models.LogLevel.INFO)
        _LOGGER.info("Robot job is done")
    except Exception as e:
        _LOGGER.error("Error executing robot", e)
        message = f"<<<<< Robot has ended unexpectedly. Details:: {e} >>>>>"
        _append_log_message(message, kf_models.LogLevel.ERROR)
        raise e


def _upload_file(task_id: str, doc_path: str) -> kf_models.TaskSaveJsonFormsValueDocumentResponseCommand:
    command = kf_models.TaskSaveJsonFormsValueDocumentRequestCommand(schema_path="#/properties/file")

    file_name = os.path.basename(doc_path)
    file = open(doc_path, "rb")
    content_type = _guess_content_type(doc_path)
    file = kf_models.Document(
        file_mame=file_name,
        content_type=content_type,
        file_content=file,
    )

    value = ROBOT_CONTEXT.kuFLow_client.task.actions_task_save_json_forms_value_document(task_id, file, command).value

    json_model = {"file": value}
    json_text = json.loads(json.dumps(json_model))

    command_save_json = kf_models.TaskSaveJsonFormsValueDataCommand(data=json_text)

    return ROBOT_CONTEXT.kuFLow_client.task.actions_task_save_json_forms_value_data(
        id=task_id, command=command_save_json
    )


def _append_log_message(message: str, level: kf_models.LogLevel) -> kf_models.Task:
    task_id = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_TASK_ID.value, None)

    log = kf_models.Log(message=message, level=level)
    task = ROBOT_CONTEXT.kuFLow_client.task.actions_task_append_log(task_id, log)

    return task


def _guess_content_type(file_path):
    return mimetypes.guess_type(file_path)[0]

if __name__ == "__main__":
    take_a_desktop_screenshot_to_kuflow()
