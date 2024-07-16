import os

from PIL import ImageGrab


def take_a_desktop_screenshot_to_home():
    # Get the path to the user's home directory
    home_dir = os.path.expanduser("~")

    # Output file path
    image_path = os.path.join(home_dir, "desktop-screenshot.png")

    # Task screenshot
    screenshot = ImageGrab.grab()
    screenshot.save(image_path)

    print(f"Desktop screenshot has been written in {image_path}")


if __name__ == "__main__":
    take_a_desktop_screenshot_to_home()
