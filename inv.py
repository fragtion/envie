import serial
import threading
import sys
import os

# Configure your serial connection
SERIAL_PORT = "/dev/ttyS3"  # Replace with your port, e.g., "/dev/ttyS0" for Linux
BAUD_RATE = 2400
TIMEOUT = 1  # Adjust timeout as needed

def read_from_serial(ser):
    """Continuously read from the serial port and display data."""
    while True:
        if ser.in_waiting > 0:  # Check if there are bytes in the input buffer
            response_bytes = ser.read(ser.in_waiting)  # Read raw bytes from the serial port

            # Remove carriage return (0D) bytes
            filtered_bytes = bytes(byte for byte in response_bytes if byte != 0x0D)

            if filtered_bytes:
                # Decode into string
                response_str = filtered_bytes.decode(errors="replace")
#                response_str = ""

                # Print the filtered response string immediately
                print(f"{response_str}", end="", flush=True)

                # Print the hex and decimal representations of the filtered bytes
                hex_response = ' '.join(f"{byte:02X}" for byte in filtered_bytes)
                decimal_response = ' '.join(f"{byte}" for byte in filtered_bytes)
                print(f" (Hex: {hex_response}, Dec: {decimal_response})", end="", flush=True)


def rrread_from_serial(ser):
    """Continuously read from the serial port and display data."""
    buffer = bytearray()  # Buffer to accumulate incoming bytes
    while True:
        if ser.in_waiting > 0:  # Check if there are bytes in the input buffer
            byte = ser.read(1)  # Read one byte at a time
            if byte == b'\r':  # Check for delimiter (end of response)
                if buffer:  # If the buffer contains data
                    # Decode the response
                    response_str = buffer.decode(errors="replace")
                    print(f"{response_str}", end="", flush=True)

                    # Print the hex representation
                    hex_response = ' '.join(f"{b:02X}" for b in buffer)
                    print(f" ({hex_response})", end="", flush=True)

                    # Calculate and display voltages
                    if len(buffer) >= 3:  # Ensure there are enough bytes
                        eh0 = buffer[0]  # Scale based on observation
                        input_voltage = buffer[1] * 1.54 # Scale based on observation
                        output_voltage = buffer[2] * 1.54 # Scale based on observation
                        eh1 = buffer[3] # Scale based on observation
                        eh2 = buffer[4] # Scale based on observation
                        eh3 = buffer[5] * 0.2083  # Scale based on observation
                        eh4 = buffer[6] # Scale based on observation
                        print(f" [{eh0} Vin: {input_voltage}V\nVout: {output_voltage}V\n Batt%:{eh1} {eh2} {eh3} FreqIn: {eh4}]", end="", flush=True)

                    print()  # Newline for clarity
                    buffer.clear()  # Clear the buffer for the next response
            else:
                buffer.extend(byte)  # Add byte to buffer


def rread_from_serial(ser):
    """Continuously read from the serial port and display data."""
    while True:
        if ser.in_waiting > 0:  # Check if there are bytes in the input buffer
            response_bytes = ser.read(ser.in_waiting)  # Read raw bytes from the serial port
            
            # Remove carriage return (0D) bytes
            filtered_bytes = bytes(byte for byte in response_bytes if byte != 0x0D)

            if filtered_bytes:
                # Decode into string
                response_str = filtered_bytes.decode(errors="replace")

                # Print the filtered response string immediately
                print(f"{response_str}", end="", flush=True)

                # Print the hex representation of the filtered bytes (optional)
                hex_response = ' '.join(f"{byte:02X}" for byte in filtered_bytes)
                print(f"({hex_response}) ", end="", flush=True)

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
    try:
        # Open the serial port
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.\n")

        # Start a thread to read responses
        reader_thread = threading.Thread(target=read_from_serial, args=(ser,), daemon=True)
        reader_thread.start()

        print("Press a single key to send commands. Press '\\' to exit.")
        while True:
            char = get_single_character()  # Wait for a single character input
            if char.lower() == "\\":  # Exit when 'x' is pressed
                print("\nExiting...")
                break

            # Convert to uppercase and send the character
            upper_char = char.upper()
            ser.write(upper_char.encode())  # Send command
            ser.write(b'\r')  # Send carriage return if required by your device
            print(f"\nSent: {upper_char}")

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
