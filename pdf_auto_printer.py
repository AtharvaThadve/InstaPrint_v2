import time
import os
import cups
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCH_DIR = "/var/www/html/docs"

class PDFHandler(FileSystemEventHandler):
    def __init__(self):
        self.conn = cups.Connection()
        self.printer_name = self.conn.getDefault()
        if not self.printer_name:
            raise Exception("No default printer set. Use `lpoptions -d PRINTER_NAME` to set one.")

    def on_created(self, event):
        if event.is_directory or not event.src_path.lower().endswith(".pdf"):
            return
        
        file_path = event.src_path
        print(f"Detected new file: {file_path}")
        try:
            job_id = self.conn.printFile(self.printer_name, file_path, "Auto Print Job", {})
            print(f"Submitted job ID: {job_id}")

            # Wait until the job is accepted by the printer
            while True:
                jobs = self.conn.getJobs()
                if job_id not in jobs:
                    break
                time.sleep(1)

            os.remove(file_path)
            print(f"Printed and deleted: {file_path}")
        except Exception as e:
            print(f"Error printing file: {e}")

if __name__ == "__main__":
    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, path=WATCH_DIR, recursive=False)
    observer.start()
    print(f"Watching folder: {WATCH_DIR}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
