# from flask import Flask, request, jsonify
# from flask_cors import CORS

# app = Flask(__name__)
# CORS(app)

# # Store latest print settings
# print_settings = {
#     "printType": "single",
#     "colorPrint": "Black & White",
#     "paymentMethod": "UPI",
#     "paymentAmount": 0
# }

# # Store latest payment verification and status data
# latest_payment = {
#     "amount": 0,
#     "status": "",
#     "razorpayPaymentId": None
# }

# @app.route('/api/print-settings', methods=['POST'])
# def update_print_settings():
#     data = request.json
#     print("Received settings from frontend:", data)
#     for key in print_settings:
#         if key in data:
#             print_settings[key] = data[key]
#     print("Updated print settings:", print_settings)
#     return jsonify({
#         "status": "success",
#         "message": "Print settings updated.",
#         "settings": print_settings
#     })

# @app.route('/api/print-settings', methods=['GET'])
# def get_print_settings():
#     return jsonify(print_settings)

# @app.route('/api/payment/verify', methods=['POST'])
# def verify_payment():
#     # Optional signature/order verification logic can go here
#     data = request.json
#     payment_id = data.get('razorpayPaymentId')
#     # We could verify signature here if needed
#     print(f"Razorpay payment verified: {payment_id}")
#     return jsonify({
#         "status": "success",
#         "message": "Payment verified."
#     })

# @app.route('/api/payment/status', methods=['POST'])
# def payment_status():
#     data = request.json
#     amt = data.get('amount')
#     status = data.get('status')
#     payment_id = data.get('razorpayPaymentId')

#     latest_payment['amount'] = amt
#     latest_payment['status'] = status
#     latest_payment['razorpayPaymentId'] = payment_id

#     # ✅ Print to terminal
#     print(f"Payment Status Received: {status} for ₹{amt}")
#     if status == 'success':
#         print("✅ Payment Successful - ID:", payment_id)
#     else:
#         print("❌ Payment Failed or Cancelled")

#     return jsonify({
#         "status": "success",
#         "message": f"Status '{status}' recorded for ₹{amt}",
#         "payment": latest_payment
#     })

# @app.route('/api/payment/status', methods=['GET'])
# def get_payment_status():
#     return jsonify(latest_payment)

# if __name__ == '__main__':
#     app.run(debug=True)


import os
import time
import cups
from flask import Flask, request, jsonify
from flask_cors import CORS
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

app = Flask(__name__)
CORS(app)

DOCS_DIR = "/var/www/html/docs"
PRINTER_NAME = "Virtual_Printer"  

print_settings = {
    "printType": "single",
    "colorPrint": "Black & White",
    "paymentMethod": "UPI",
    "paymentAmount": 0,
    "copies": 1,
    "paperSize": "A4",
    "serverFilename": None
}

latest_payment = {
    "amount": 0,
    "status": "",
    "razorpayPaymentId": None
}

def send_to_printer(filepath, settings):
    conn = cups.Connection()
    options = {}

    if settings["printType"] == "double":
        options["sides"] = "two-sided-long-edge"
    else:
        options["sides"] = "one-sided"

    if settings["colorPrint"] == "Black & White":
        options["ColorModel"] = "Gray"
    else:
        options["ColorModel"] = "Color"

    options["media"] = settings["paperSize"]
    options["copies"] = str(settings["copies"])

    print("🖨️ Sending to printer with options:", options)
    try:
        job_id = conn.printFile(PRINTER_NAME, filepath, "Document", options)
        print(f"✅ Sent to printer (Job ID: {job_id})")
        os.remove(filepath)
        return True
    except Exception as e:
        print("❌ Failed to print:", e)
        return False

@app.route('/api/print-settings', methods=['POST'])
def update_print_settings():
    data = request.json
    for key in print_settings:
        if key in data:
            print_settings[key] = data[key]
    print("Updated print settings:", print_settings)
    return jsonify({
        "status": "success",
        "message": "Print settings updated.",
        "settings": print_settings
    })

@app.route('/api/payment/status', methods=['POST'])
def payment_status():
    data = request.json
    amt = data.get('amount')
    status = data.get('status')
    payment_id = data.get('razorpayPaymentId')

    latest_payment.update({
        "amount": amt,
        "status": status,
        "razorpayPaymentId": payment_id
    })

    print(f"Payment Status Received: {status} for ₹{amt}")
    filename = print_settings.get("serverFilename")

    if status == 'success' and filename:
        filepath = os.path.join(DOCS_DIR, filename)
        if os.path.exists(filepath):
            success = send_to_printer(filepath, print_settings)
            if success:
                return jsonify({
                    "status": "success",
                    "message": "✅ Document sent for printing."
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": "❌ Failed to print."
                })
        else:
            return jsonify({
                "status": "error",
                "message": "❌ PDF file not found."
            })
    else:
        # delete file on failed payment
        if filename:
            filepath = os.path.join(DOCS_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        return jsonify({
            "status": "failure",
            "message": "❌ Payment failed. File deleted."
        })

@app.route('/api/payment/status', methods=['GET'])
def get_payment_status():
    return jsonify(latest_payment)

class FileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        print(f"📂 New file detected: {event.src_path}")
        # Optional: Could auto-trigger or notify when file arrives

def start_watchdog(path):
    observer = Observer()
    observer.schedule(FileHandler(), path=path, recursive=False)
    observer.start()
    print(f"👁️ Started watchdog on: {path}")
    return observer

if __name__ == '__main__':
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)

    observer = start_watchdog(DOCS_DIR)
    try:
        app.run(debug=True, use_reloader=False)
    finally:
        observer.stop()
        observer.join()
