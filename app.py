from flask import Flask, render_template, jsonify
import serial
import threading
import time
import queue

# Configuration
#SERIAL_PORT = "/dev/ttyS3"  # Replace with your serial port
SERIAL_PORT = "/dev/ttyUSB0"  # Replace with your serial port
COMACTIVE = False
UPS_INFO = ''
UPS_STATE = ''
UPS_VIN = 0.00
UPS_VOUT = 0.00
UPS_VBATT = 0.00
UPS_LOAD = 0
UPS_FREQ = 0
UPS_CHGPWR = 0
UPS_J = 0
RESPONSE = b''

# Flask app
app = Flask(__name__)

# Serial communication setup
ser = serial.Serial(SERIAL_PORT, 2400, timeout=1)

# Command queue for serial communication
command_queue = queue.Queue()

# Function to process commands from the queue
def command_worker():
    """Worker thread to process commands in the queue."""
    while True:
        command = command_queue.get()  # Wait for a command
        if command is None:
            break  # Exit the thread if None is sent as a command
        ser_send(command)  # Process the command
        command_queue.task_done()  # Mark the task as done

# Function to send commands using the queue
def ser_send_with_queue(command):
    """Enqueue a command to be processed."""
    command_queue.put(command)

# Function to send commands over serial
def ser_send(command):
    global COMACTIVE
    if not COMACTIVE:
        COMACTIVE = True
        ser.write(command.encode())
        buffer = bytearray()
        try:
            start_time = time.time()
            if command == 'Y':
                global UPS_STATE, UPS_VIN, UPS_VOUT, UPS_VBATT, UPS_LOAD, UPS_FREQ
                while time.time() - start_time < 1:  # Run for up to 1s
                    if ser.in_waiting > 0:
                        response_bytes = ser.read(ser.in_waiting)
                        filtered_bytes = bytes(byte for byte in response_bytes if byte != 0x0D)
                        buffer.extend(filtered_bytes)

                        if b'\r' in response_bytes and len(buffer) >= 7:
                            UPS_STATE = buffer[0]
                            
                            UPS_VIN = buffer[1] * 1.50
                            UPS_VOUT = buffer[2] * 1.50
                            UPS_VBATT = buffer[3]
                            UPS_LOAD = buffer[4]
                            UPS_VBATT = buffer[5] * 0.213
                            UPS_FREQ = buffer[6]
                            break
            elif command == 'I':
                global UPS_INFO
                last_byte_time = time.time()
                while time.time() - start_time < 1:
                    if ser.in_waiting > 0:
                        response_bytes = ser.read(ser.in_waiting)
                        filtered_bytes = bytes(byte for byte in response_bytes if byte != 0x0D)
                        buffer.extend(filtered_bytes)
                        last_byte_time = time.time()
                    if time.time() - last_byte_time > 0.05:
                        break
                UPS_INFO = buffer.decode(errors='ignore').strip()
            else:
                global RESPONSE
                while time.time() - start_time < 1:
                    if ser.in_waiting > 0:
                        response_bytes = ser.read(ser.in_waiting)
                        filtered_bytes = bytes(byte for byte in response_bytes if byte != 0x0D)
                        if filtered_bytes:
                            RESPONSE = filtered_bytes
                            if command == 'V':
                                global UPS_CHGPWR
                                response_str = RESPONSE.decode(errors="ignore").strip()
                                hex_response = ' '.join(f"{byte:02X}" for byte in RESPONSE)
                                decimal_response = ' '.join(f"{byte}" for byte in RESPONSE)
                                decimal_response_float = float(decimal_response)
                                if decimal_response_float == 1:
                                    UPS_CHGPWR = 0
                                elif decimal_response_float == 2:
                                    UPS_CHGPWR = 10
                                else:
                                    UPS_CHGPWR = 10 ** ((decimal_response_float + 86.49) / 35.77)
                            elif command == 'J':
                                global UPS_J
                                response_str = RESPONSE.decode(errors="ignore").strip()
                                hex_response = ' '.join(f"{byte:02X}" for byte in RESPONSE)
                                decimal_response = ' '.join(f"{byte}" for byte in RESPONSE)
                                decimal_response_float = float(decimal_response)
                                UPS_J = decimal_response
                            break
        except serial.SerialException as e:
            print(f"Serial error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            buffer.clear()
            COMACTIVE = False

# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cmnd/<command>')
def cmnd(command):
    global RESPONSE

    # Enqueue the command
    ser_send_with_queue(command)

    # Wait for the command to be processed
    start_time = time.time()
    timeout = 2  # Maximum time to wait for the command to process
    while True:
        # Break if the queue is empty and RESPONSE is updated
        if command_queue.qsize() == 0 and RESPONSE != b'':
            break
        if time.time() - start_time > timeout:
            return jsonify({"error": "Command processing timed out"}), 504
        time.sleep(0.1)  # Avoid busy-waiting

        if command == 'T' or command == 'N' or command == 'U':
            data = "Request Sent"
            break

        # Process the response
        response_str = RESPONSE.decode(errors="ignore").strip()
        hex_response = ' '.join(f"{byte:02X}" for byte in RESPONSE)
        decimal_response = ' '.join(f"{byte}" for byte in RESPONSE)

        # Check the first byte and set notes accordingly
        notes = ""
        if RESPONSE:
            first_byte_hex = RESPONSE[0:1].hex().upper()  # Get hex of the first byte
            if first_byte_hex == '21':
                notes = "SUCCESS/OK!"
            elif first_byte_hex == '33':
                notes = "ERR/FAILED!"
            else:
                notes = 'N/A'
               
            if command == 'D' or command == 'R' or command == 'S' or command == 'O':
                data = f"{notes}"
            elif command == 'C' or command == 'H' or command == 'B' or command == 'X':
                # 1 = BATTERY, 2 = "H toggle", 4 = BATT VOLTS, 
                #data = f"{notes}"
                data = f"{response_str} (Hex: {hex_response}, Dec: {decimal_response}, Notes: {notes})"
            elif command == 'A':
                data = f"{notes}"
            elif command == 'V':
                global UPS_CHGPWR
                # You can now use watts in your code as needed
                data = f"{decimal_response} (Calculated Power: {UPS_CHGPWR:.0f} Watts)"
            elif command == 'E' or command == 'W' or command == 'G':
                data = f"{decimal_response} Amps"
            else:
                data = f"{response_str} (Hex: {hex_response}, Dec: {decimal_response}, Notes: {notes})"

    # Clear the global RESPONSE for the next request
    RESPONSE = b''

    return jsonify(data)


@app.route('/status')
def status():
    global UPS_INFO, UPS_STATE, UPS_VIN, UPS_VOUT, UPS_VBATT, UPS_LOAD, UPS_FREQ, UPS_CHGPWR
    return jsonify({
        "ups_info": UPS_INFO,
        "ups_state": UPS_STATE,
        "ups_vin": f"{int(UPS_VIN)}",
        "ups_vout": f"{int(UPS_VOUT)}",
        "ups_vbatt": f"{round(UPS_VBATT, 2)}",
        "ups_load": f"{UPS_LOAD}",
        "ups_freq": f"{UPS_FREQ}",
        "ups_chgpwr": f"{int(UPS_CHGPWR)}",
        "ups_j": f"{UPS_J}"
    })

# Periodic status update
def send_status_periodically():
    """Periodically send the 'Y' command to update UPS status."""
    firstrun = True
    while True:
        if firstrun:
            firstrun = False
            time.sleep(2)
        ser_send_with_queue('Y')
        ser_send_with_queue('C')
        ser_send_with_queue('V')
        ser_send_with_queue('J')
        time.sleep(2)

# Main entry point
if __name__ == "__main__":
    # Send the 'I' command once on startup to get the inverter info
    ser_send_with_queue('I')

    # Start the worker thread for the command queue
    command_worker_thread = threading.Thread(target=command_worker, daemon=True)
    command_worker_thread.start()

    # Start the periodic status update thread
    status_thread = threading.Thread(target=send_status_periodically, daemon=True)
    status_thread.start()

    # Run the Flask app
    try:
        app.run(debug=False, host="0.0.0.0", port=5000)
    finally:
        # Gracefully shut down the worker thread
        command_queue.put(None)  # Signal the worker to exit
        command_worker_thread.join()
