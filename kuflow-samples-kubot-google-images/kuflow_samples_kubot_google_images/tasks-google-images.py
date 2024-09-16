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
from playwright.sync_api import expect
from robocorp import browser
from robocorp.tasks import setup, task, teardown

from kuflow_samples_kubot_google_images._models import (
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
            append_log_message(message, models_rest.ProcessItemTaskLogLevel.ERROR)
        else:
            message = "<<<<< The robot has finished successfully >>>>>"
            append_log_message(message, models_rest.ProcessItemTaskLogLevel.INFO)
    except Exception as e:
        _LOGGER.exception("An error occurred running operation: %s. Details: %s", task.name, e)


###########################################
## Tasks
###########################################
@task
def run_robot():
    try:
        _LOGGER.info("Robot starts running")
        append_log_message("<<<<< Robot execution begins >>>>>", models_rest.ProcessItemTaskLogLevel.INFO)

        process = get_process()
        text_search = get_text_search(process)
        go_google(text_search)

        _LOGGER.info("Robot job is done")
    except Exception as e:
        _LOGGER.error("Error executing robot", e)
        raise e
    finally:
        browser.context().close()


def go_google(text_search: str):
    page = browser.page()

    page.goto("https://images.google.com/", wait_until="load")

    page.locator("#L2AGLb > div").click()
    page.locator("textarea").nth(0).fill(text_search)
    page.locator("button.Tg7LZd").click()

    append_log_message("Awaiting user selection.", models_rest.ProcessItemTaskLogLevel.INFO)

    locator = page.locator('div[jsname="figiqf"]')
    locator_count = locator.count()
    locator = page.locator(".p7sI2.PUxBg").nth(locator_count - 2)
    expect(locator).to_be_visible()
    path = "output/capture.png"
    locator.screenshot(path=path, type="png")

    append_log_message("Capture done.", models_rest.ProcessItemTaskLogLevel.INFO)

    process_id = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_PROCESS_ID.value, None)
    process_item_id = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_TASK_ID.value, None)
    upload_file(process_id, process_item_id, path)


def get_process() -> models_rest.Process:
    process_id = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_PROCESS_ID.value, None)

    return ROBOT_CONTEXT.kuFLow_client.process.retrieve_process(process_id)


def upload_file(process_id: str, process_item_id: str, doc_path: str):
    file_name = os.path.basename(doc_path)
    file_content = open(doc_path, "rb")
    content_type = guess_content_type(doc_path)
    document = models_rest.Document(
        file_mame=file_name,
        file_content=file_content,
        content_type=content_type,
    )

    document_reference = ROBOT_CONTEXT.kuFLow_client.process.upload_process_document(process_id, document)

    params = models_rest.ProcessItemTaskDataUpdateParams(
        data=models_rest.JsonValue(
            value={
                "file": document_reference.document_uri,
            },
        )
    )

    return ROBOT_CONTEXT.kuFLow_client.process_item.update_process_item_task_data(
        id=process_item_id, process_item_task_data_update_params=params
    )


def get_text_search(process: models_rest.Process) -> str:
    return str(process.metadata.value.get(RobotConstants.PROCESS_METADATA__SEARCH_TEXT.value))


def append_log_message(message: str, level: models_rest.ProcessItemTaskLogLevel) -> models_rest.ProcessItem:
    process_item_id = os.environ.get(KuFlowEnvironmentVariablesConstants.KUFLOW_TASK_ID.value, None)

    params = models_rest.ProcessItemTaskAppendLogParams(
        message=message,
        level=level,
    )

    return ROBOT_CONTEXT.kuFLow_client.process_item.append_process_item_task_log(process_item_id, params)


def guess_content_type(file_path):
    return mimetypes.guess_type(file_path)[0]
