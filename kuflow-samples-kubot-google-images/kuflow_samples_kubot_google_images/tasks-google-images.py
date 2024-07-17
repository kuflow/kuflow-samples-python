import json
import logging
import mimetypes
import os

from kuflow_rest import models as kf_models
from kuflow_rest.utils import ProcessUtils
from playwright.sync_api import expect
from robocorp import browser
from robocorp.tasks import setup, task, teardown

from kuflow_samples_kubot_google_images.models import (
    KuFlowEnvironmentVariablesConstants,
    RobotConstants,
    RobotContext,
)


###########################################
## Configuration
###########################################
# Set the logging level to INFO
logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15000  # Default maximum time for all the methods accepting timeout option.


@setup(scope="session")
def before_all(tasks):
    global ROBOT_CONTEXT
    ROBOT_CONTEXT = RobotContext()

    # Important:
    #   If the robot runs on KuBot Manager, we recommend set "isolated=True" in order to install browsers in
    #   KuBot Manager store (shared for all robots). If you set "isolated=False", the installation is global
    #   to the User.
    #   Additionally, to avoid installing the browsers the first time it is run, it is recommended to add a
    #   Post-Action in the robot manifest (kubot.yaml) that installs the browsers, like:
    #   - name: Install browsers
    #     shell: python -m robocorp.browser install chromium --isolated
    # Hints:
    #   To increase windows size, add param like: viewport_size=(1920, 1080)
    browser.configure(browser_engine="chromium", headless=False, slowmo=100, isolated=True)

    browser.context().set_default_timeout(DEFAULT_TIMEOUT)
    expect.set_options(timeout=60000)


@teardown(scope="task")
def handle_run_finished(task):
    try:
        if task.failed:
            message = f"<<<<< The robot has terminated with an error. Details: {task.message} >>>>>"
            append_log_message(message, kf_models.LogLevel.ERROR)
        else:
            message = "<<<<< The robot has finished successfully >>>>>"
            append_log_message(message, kf_models.LogLevel.INFO)
    except Exception as e:
        _LOGGER.exception("An error occurred running operation: %s. Details: %s", task.name, e)


###########################################
## Tasks
###########################################
@task
def run_robot():
    try:
        _LOGGER.info("Robot starts running")
        append_log_message("<<<<< Robot execution begins >>>>>", kf_models.LogLevel.INFO)

        process = get_process()
        text_search = get_text_search(process)
        go_google(text_search)

        _LOGGER.info("Robot job is done")
    except Exception as e:
        _LOGGER.error("Error executing robot", e)
        raise e
    finally:
        browser.context().close()


def go_google(text_search: str) -> str:
    page = browser.page()

    page.goto("https://images.google.com/", wait_until="load")

    page.locator("#L2AGLb > div").click()
    page.locator("textarea").nth(0).fill(text_search)
    page.locator("button.Tg7LZd").click()

    append_log_message("Awaiting user selection.", kf_models.LogLevel.INFO)

    locator = page.locator('div[jsname="figiqf"]')
    locator_count = locator.count()
    locator = page.locator(".p7sI2.PUxBg").nth(locator_count-2)
    expect(locator).to_be_visible()
    path = "output/capture.png"
    locator.screenshot(path=path, type="png")

    append_log_message("Capture done.", kf_models.LogLevel.INFO)

    task_id = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_TASK_ID.value, None)
    upload_file(task_id, path)


def get_process() -> kf_models.Process:
    process_id = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_PROCESS_ID.value, None)

    return ROBOT_CONTEXT.kuFLow_client.process.retrieve_process(process_id)


def upload_file(task_id: str, doc_path: str) -> kf_models.TaskSaveJsonFormsValueDocumentResponseCommand:
    command = kf_models.TaskSaveJsonFormsValueDocumentRequestCommand(schema_path="#/properties/file")

    file_name = os.path.basename(doc_path)
    file = open(doc_path, "rb")
    content_type = guess_content_type(doc_path)
    file = kf_models.Document(
        file_mame=file_name,
        content_type=content_type,
        file_content=file,
    )

    value = ROBOT_CONTEXT.kuFLow_client.task.actions_task_save_json_forms_value_document(task_id, file, command).value

    json_model = { 'file': value}
    json_text = json.loads(json.dumps(json_model))

    command_save_json = kf_models.TaskSaveJsonFormsValueDataCommand(data=json_text)

    return ROBOT_CONTEXT.kuFLow_client.task.actions_task_save_json_forms_value_data(id=task_id, command=command_save_json)


def get_text_search(process: kf_models.Process) -> str:
    return ProcessUtils.get_element_value_as_str(process, RobotConstants.PROCESS_METADATA__SEARCH_TEXT.value)


def append_log_message(message: str, level: kf_models.LogLevel) -> kf_models.Task:
    task_id = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_TASK_ID.value, None)
    log = kf_models.Log(message=message, level=level)

    return ROBOT_CONTEXT.kuFLow_client.task.actions_task_append_log(task_id, log)

def guess_content_type(file_path):
    return mimetypes.guess_type(file_path)[0]
