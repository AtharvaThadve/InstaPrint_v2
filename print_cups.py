import os
import time
import subprocess
from threading import Thread, Lock

from flask import Flask, request, jsonify
from flask_cors import CORS

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

app = Flask(__name__)
CORS(app)

DOCS_FOLDER = "/var/www/html/docs"
printer_name = "PDF"  # or "Virtual_Printer" etc.

print_settings = {
    "printType": "single",
    "colorPrint": "Black & White",
    "paymentMethod": "UPI"
}

print_settings_ready = False  # Only start printing after this becomes True
pending_files = []
lock = Lock()  # For thread-safe access to pending_files

def print_pdf(filepath, settings):
    options = []

    # Duplex
    if settings.get("printType") == "double":
        options.append("-o sides=two-sided-long-edge")
    else:
        options.append("-o sides=one-sided")

    # Color
    if settings.get("colorPrint") == "Color":
        options.append("-o ColorModel=Color")
    else:
        options.append("-o ColorModel=Gray")

    cmd = ["lp", "-d", printer_name] + options + [filepath]
    print(f"\n[INFO] Printing command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"[SUCCESS] Printed {os.path.basename(filepath)} with settings: {settings}")
        os.remove(filepath)
        print(f"[CLEANUP] Deleted: {filepath}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Printing failed for {filepath}:\n{e.stderr}")

def process_pending_files():
    global pending_files
    with lock:
        print(f"[PROCESS] Processing {len(pending_files)} pending files...")
        for file_path in pending_files:
            if os.path.exists(file_path):
                print_pdf(file_path, print_settings)
        pending_files = []  # Clear the queue after printing

class DocsFolderHandler(FileSystemEventHandler):
    def on_created(self, event):
        global print_settings_ready
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            print(f"[DETECTED] New PDF: {event.src_path}")
            time.sleep(1)  # Ensure file is fully saved
            with lock:
                if print_settings_ready:
                    print_pdf(event.src_path, print_settings)
                else:
                    print("[QUEUE] Print settings not ready, queued.")
                    pending_files.append(event.src_path)

def start_watchdog():
    event_handler = DocsFolderHandler()
    observer = Observer()
    observer.schedule(event_handler, DOCS_FOLDER, recursive=False)
    observer.start()
    print(f"[WATCHDOG] Monitoring folder: {DOCS_FOLDER}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

@app.route('/api/print-settings', methods=['POST'])
def update_print_settings():
    global print_settings_ready
    data = request.json
    print("[POST] Received settings from frontend:", data)
    for key in print_settings:
        if key in data:
            print_settings[key] = data[key]

    print_settings_ready = True
    print("[READY] Print settings received. Starting printing process...")
    process_pending_files()

    return jsonify({
        "status": "success",
        "message": "Print settings updated. Pending documents are printing now.",
        "settings": print_settings
    })

@app.route('/api/print-settings', methods=['GET'])
def get_print_settings():
    return jsonify(print_settings)

if __name__ == '__main__':
    # Start monitoring thread
    watcher_thread = Thread(target=start_watchdog, daemon=True)
    watcher_thread.start()

    app.run(debug=True, host='0.0.0.0')
