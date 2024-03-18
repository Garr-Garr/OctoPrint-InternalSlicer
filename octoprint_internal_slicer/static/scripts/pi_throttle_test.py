import subprocess
import time

while True:
    # Get the current time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    # Get the temperature and throttling status
    temperature_output = subprocess.check_output(["vcgencmd", "measure_temp"])
    throttling_output = subprocess.check_output(["vcgencmd", "get_throttled"])

    # Extract the temperature value from the output
    temperature = float(temperature_output.decode("utf-8").strip().split("=")[1][:-2])

    # Check if the CPU is throttled
    throttled = int(throttling_output.decode("utf-8").strip().split("=")[1], 16)
    if throttled & 0x4:
        throttling_status = "Yes"
    else:
        throttling_status = "No"

    # Print the temperature and throttling status with a timestamp
    print(f"{timestamp} Temperature: {temperature:.2f}°C, Throttling: {throttling_status}")

    # Wait for five seconds before polling again
    time.sleep(5)