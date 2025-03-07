import serial
import sys
import os
import time

# Configure your serial connection
SERIAL_PORT = "/dev/ttyS3"  # Replace with your port, e.g., "/dev/ttyS0" for Linux
BAUD_RATE = 2400
TIMEOUT = 1  # Adjust timeout as needed
REQ = ""

def read_from_serial(ser):
    """Read the response from the serial port and display it."""
    global REQ
    last_response = ""  # To store the last response for 'i'
    buffer = bytearray()  # Buffer to accumulate incoming bytes

    if REQ == 'y':  # Process response when REQ is 'y'
        while True:
            if ser.in_waiting > 0:
                response_bytes = ser.read(ser.in_waiting)
                filtered_bytes = bytes(byte for byte in response_bytes if byte != 0x0D)
                buffer.extend(filtered_bytes)

                # Check for carriage return (0x0D) to finalize response
                if b'\r' in response_bytes:
                    break  # Exit loop once carriage return is received

        # Process the accumulated response for REQ == 'y'
        if len(buffer) >= 7:
            eh0 = buffer[0]
            input_voltage = buffer[1] * 1.54
            output_voltage = buffer[2] * 1.54
            eh1 = buffer[3]
            eh2 = buffer[4]
            eh3 = buffer[5] * 0.2083
            eh4 = buffer[6]

            # Print detailed information
            print(f"\r[{eh0} Vin: {input_voltage:.2f}V Vout: {output_voltage:.2f}V Batt%: {eh1} {eh2} {eh3:.2f} FreqIn: {eh4}]", end="", flush=True)

            # Print each byte's decimal value
            decimal_values = ' '.join(str(byte) for byte in buffer[:7])
            print(f" (Buffer Decimals: {decimal_values})", end="", flush=True)

    elif REQ == 'i':  # Longer response expected for 'i'
        start_time = time.time()
        last_byte_time = time.time()  # Track the last time a byte was received
        buffer = bytearray()  # Buffer to accumulate response bytes

        while time.time() - start_time < 1:  # Run for up to 1s
            if ser.in_waiting > 0:
                response_bytes = ser.read(ser.in_waiting)
                filtered_bytes = bytes(byte for byte in response_bytes if byte != 0x0D)
                buffer.extend(filtered_bytes)
                last_byte_time = time.time()  # Update last byte received time

            # If no new byte has been received for 0.05s, break out of the loop
            if time.time() - last_byte_time > 0.05:
                break

        # Process the accumulated response for REQ == 'i'
        response_str = buffer.decode(errors='ignore').strip()

        # If the response is different from the last one, print it
        if response_str != last_response:
            print(f"\r{response_str}", end="", flush=True)
            last_response = response_str  # Update the last response

    else:  # REQ not in ('y', 'i'), expect a single-byte response
        while ser.in_waiting == 0:
            time.sleep(0.1)
        if ser.in_waiting > 0:
            response_bytes = ser.read(ser.in_waiting)
            filtered_bytes = bytes(byte for byte in response_bytes if byte != 0x0D)
            if filtered_bytes:
                response_str = filtered_bytes.decode(errors="ignore").strip()
                print(f"\r{response_str}", end="", flush=True)

                # Print hex and decimal representations
                hex_response = ' '.join(f"{byte:02X}" for byte in filtered_bytes)
                decimal_response = ' '.join(f"{byte}" for byte in filtered_bytes)
                print(f" (Hex: {hex_response}, Dec: {decimal_response})", end="", flush=True)

def get_single_character():
    """Get a single character input from the user."""
    if os.name == "nt":  # Windows
        import msvcrt
        return msvcrt.getch().decode("utf-8")
    else:  # Linux/Unix
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            char = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return char

def main():
    global REQ
    try:
        # Open the serial port
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.\n")

        print("Press a single key to send commands. Press '\\' to exit.")
        while True:
            char = get_single_character()  # Wait for a single character input
            if char.lower() == "\\":  # Exit when '\\' is pressed
                print("\nExiting...")
                break
            else:
                REQ = char.lower()

            # Convert to uppercase and send the character
            upper_char = char.upper()
            ser.write(upper_char.encode())  # Send command
            #ser.write(b'\r')  # Send carriage return if required by your device
            print(f"\nSent: {upper_char}")

            # Read and print the response from the serial port
            read_from_serial(ser)

    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting...")
    except serial.SerialException as e:
        print(f"Serial error: {e}")
    finally:
        if "ser" in locals() and ser.is_open:
            ser.close()
        print("Serial port closed.")

if __name__ == "__main__":
    main()
