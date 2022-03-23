from b2sdk.v2 import *
import random
import time
import watchdog.observers
import watchdog.events
import yaml
import loguru
import os

logger = loguru.logger
logger.add("macos-screenshot.log")
logger.info("Starting macos-screenshot")

with open("config.yml", "r") as stream:
    try:
        config = yaml.safe_load(stream)
        print(yaml.safe_load(stream))
    except yaml.YAMLError as exc:
        print(exc)

def b2_authorize(id, key):
    logger.info("Authorization requested")
    """Authorize an account with the Backblaze B2 api."""
    global b2_api
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    logger.info(f"Authorization using keys.")
    b2_api.authorize_account("production", id, key)
    logger.info("Authorization completed")


def b2_upload(file_name, file_path):
    """Upload a file to the Backblaze B2 bucket."""
    logger.info("Upload requested")
    b2_authorize(config["creds"]["B2_KEY_ID"], config["creds"]["B2_KEY"])
    bucket = b2_api.get_bucket_by_name(config["settings"]["BUCKET"])
    bucket.upload_local_file(
        local_file=file_path,
        file_name=file_name
    )
    logger.info("Upload completed")

def generate_filename(file_name):
    """Generate a filename for the uploaded file."""
    logger.info("Generating filename")
    if config["settings"]["FILENAME_SETTINGS"] == "numbers":
        return str(random.randint(1, 99999)) + ".png"
    logger.info("Filename generated")

def macos_notify(filename):
    url = config["settings"]["B2_URL"] + filename
    cmd = 'echo {} | tr -d "\n" | pbcopy'.format(url)
    os.system(cmd)
    title = "Screenshot uploaded"
    text = str(url)
    sound = "default"
    os.system("""osascript -e 'display notification "{}" with title "{}" sound name "{}"'""".format(text, title, sound))

class Handler(watchdog.events.PatternMatchingEventHandler):
    def __init__(self):
        # Set the patterns for PatternMatchingEventHandler
        watchdog.events.PatternMatchingEventHandler.__init__(self, patterns=['*.png'],
                                                             ignore_directories=True, case_sensitive=False)
    def on_created(self, event):
        logger.info(f"Watchdog received created event - {event.src_path}")
        time.sleep(2)
        file_name = generate_filename(event.src_path)
        stripped = config["settings"]["SCREENSHOTS"] + event.src_path.removeprefix(config["settings"]["SCREENSHOTS"] + ".")
        logger.info(f"Making updated path: - {stripped}")
        b2_upload(file_name, stripped)
        logger.info("Uploaded %s to B2" % file_name)
        macos_notify(file_name)
  
if __name__ == "__main__":
    src_path = config["settings"]["SCREENSHOTS"]
    event_handler = Handler()
    observer = watchdog.observers.Observer()
    observer.schedule(event_handler, path=src_path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()