import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Set up logging to file with auto-flushing
log_file = 'file_changes.log'
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(message)s')

# Enable auto-flushing for logging
logger = logging.getLogger()
handler = logging.FileHandler(log_file)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Define event handler for file changes
class ChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory:
            print(f"Modified: {event.src_path}")  # Debug print
            logging.info('MODIFIED: %s', event.src_path)  # Write log entry and flush

    def on_created(self, event):
        if not event.is_directory:
            print(f"Created: {event.src_path}")  # Debug print
            logging.info('CREATED: %s', event.src_path)  # Write log entry and flush

    def on_deleted(self, event):
        if not event.is_directory:
            print(f"Deleted: {event.src_path}")  # Debug print
            logging.info('DELETED: %s', event.src_path)  # Write log entry and flush

if __name__ == "__main__":
    path = 'C:/Users/DELL/PycharmProjects/pythonProject/newproject'  # Path to your project
    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=True)  # Set recursive=True to monitor subdirectories
    observer.start()
    print(f"Started monitoring changes in: {path}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
import logging
import time
import difflib
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.FileHandler('file_changes.log'), logging.StreamHandler()]
)
logger = logging.getLogger()


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self.file_contents = {}

    def get_file_diff(self, file_path):
        """Get the difference between the previous and current version of the file."""
        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r') as file:
            current_content = file.readlines()

        previous_content = self.file_contents.get(file_path)

        if previous_content:
            diff = difflib.unified_diff(previous_content, current_content, fromfile=file_path, tofile=file_path)
            return '\n'.join(diff)
        return None

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        logger.info(f'Modified: {file_path}')

        # Get the diff of the file
        diff = self.get_file_diff(file_path)
        if diff:
            logger.info(f'Changes made in {file_path}:\n{diff}')

        # Update the file contents in memory
        with open(file_path, 'r') as file:
            self.file_contents[file_path] = file.readlines()

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        logger.info(f'Created: {file_path}')

        # Store the initial content of the file
        with open(file_path, 'r') as file:
            self.file_contents[file_path] = file.readlines()

    def on_deleted(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        logger.info(f'Deleted: {file_path}')

        # Remove the file content from memory
        if file_path in self.file_contents:
            del self.file_contents[file_path]


def start_monitoring(path='.'):
    event_handler = FileChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)  # Monitor the entire project recursively
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    logger.info('Starting file change monitoring...')
    start_monitoring()  # Starts monitoring from the current directory
import logging
import time
import difflib
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Set up logging to a file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('file_changes.log'),  # logs what file is changed
        logging.StreamHandler()  # prints to terminal
    ]
)
logger = logging.getLogger()


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self.file_contents = {}  # Cache to track previous contents

    def get_file_diff(self, file_path):
        """Returns a line-by-line difference from the previous version."""
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.readlines()
        except Exception as e:
            logger.warning(f"Error reading file for diff: {file_path} - {e}")
            return None

        previous_content = self.file_contents.get(file_path)

        if previous_content:
            diff = difflib.unified_diff(
                previous_content,
                current_content,
                fromfile=file_path,
                tofile=file_path,
                lineterm=''
            )
            return '\n'.join(diff)
        return None

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        logger.info(f'MODIFIED: {file_path}')

        # Get line-by-line differences
        diff = self.get_file_diff(file_path)
        if diff:
            logger.info(f'Changes in {file_path}:\n{diff}')

            # Save changes to diff_output.txt
            with open('diff_output.txt', 'a', encoding='utf-8') as f:
                f.write(f'\n[{time.ctime()}] Changes in {file_path}:\n')
                f.write(diff)
                f.write('\n' + '-' * 80 + '\n')

        # Update the cached content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.file_contents[file_path] = f.readlines()
        except Exception as e:
            logger.warning(f"Error reading file after modification: {file_path} - {e}")

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        logger.info(f'CREATED: {file_path}')

        # Store initial content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.file_contents[file_path] = f.readlines()
        except Exception as e:
            logger.warning(f"Error reading newly created file: {file_path} - {e}")

    def on_deleted(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        logger.info(f'DELETED: {file_path}')

        # Remove cached content
        self.file_contents.pop(file_path, None)


def start_monitoring(path='.'):
    logger.info(f"Starting file change monitoring in: {os.path.abspath(path)}")
    event_handler = FileChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping monitoring...")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    start_monitoring(path='.')  # "." means monitor current directory and all subfolders
