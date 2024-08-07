import csv
import datetime
import statistics
from tqdm import tqdm
import os
import chardet

def read_file_with_encoding(file_path):
    # Try to detect the encoding first
    with open(file_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
    
    # Try reading the file with the detected encoding
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            data_lines = file.readlines()
    except UnicodeDecodeError:
        # If the detected encoding fails, try 'latin-1' as a fallback
        with open(file_path, 'r', encoding='latin-1') as file:
            data_lines = file.readlines()
    return data_lines

def convert(data_path):
    extension = os.path.splitext(data_path)[1]

    output_file_path = data_path

    if extension == '.txt':
        input_file_path = data_path

        # Path to the output CSV file
        output_file_path = 'InitialTable/ConvertedData.csv'

        data_lines = read_file_with_encoding(input_file_path)

        # Split each line by tab character to separate columns and remove quotes
        table_data = [line.strip().replace('"', '').split('\t') for line in data_lines]


        # Define columns to remove (by index)
        columns_to_remove = [3, 4]  # Example: remove 'Validity' and 'Time_ms' columns

        # Define mapping for renaming sensors to more readable names
        sensor_name_mapping = {
            "HM1_MBDATA_statDataHeatMeterSharky775.statusHMI.Outlet_temperature_T2": "HM1_Outlet_Temp",
            "HM1_MBDATA_statDataHeatMeterSharky775.statusHMI.Inlet_temperature_T1": "HM1_Inlet_Temp",
            "HM1_MBDATA_statDataHeatMeterSharky775.statusHMI.Actual_Flow": "HM1_Flow",
            "HM1_MBDATA_statDataHeatMeterSharky775.statusHMI.Actual_Power": "HM1_Power",
            "HM2_MBDATA_statDataHeatMeterMC403.statusHMI.Actual_Power": "HM2_Power",
            "HM2_MBDATA_statDataHeatMeterMC403.statusHMI.Actual_Flow": "HM2_Flow",
            "HM2_MBDATA_statDataHeatMeterMC403.statusHMI.Outlet_temperature_T2": "HM2_Outlet_Temp",
            "HM2_MBDATA_statDataHeatMeterMC403.statusHMI.Inlet_temperature_T1": "HM2_Inlet_Temp",
        }

        odd_values = [
            "$RT_OFF$",
            "$RT_COUNT$",
            "HM1_MBDATA_statDataHeatMeterSharky775.statusHMI.Volume",
            "HM2_MBDATA_statDataHeatMeterMC403.statusHMI.Volume"
        ]

        # Function to filter data to keep only the initial and change points
        def filter_sensor_data(data):
            filtered_data = []
            sensor_last_values = {}
            
            for row in data:
                sensor_name = row[0]
                time_string = row[1]
                var_value = row[2]
                
                if sensor_name not in sensor_last_values:
                    sensor_last_values[sensor_name] = var_value
                    filtered_data.append(row)
                elif sensor_last_values[sensor_name] != var_value:
                    sensor_last_values[sensor_name] = var_value
                    filtered_data.append(row)
            
            return filtered_data

        # Process the table data
        processed_data = []
        for row in table_data[1:]:
            if row[0] in odd_values:
                continue
            # Rename the first element in each line according to the mapping
            row[0] = sensor_name_mapping.get(row[0], row[0])
            # Remove specified columns
            row = [value for idx, value in enumerate(row) if idx not in columns_to_remove]
            processed_data.append(row)

        # Filter the processed data to keep only initial and change points
        processed_data = filter_sensor_data(processed_data)

        # Round the time to the nearest second and convert values to float
        for row in tqdm(processed_data, desc="Rounding time and converting values"):
            row[1] = str(datetime.datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S").replace(microsecond=0))
            row[2] = float(row[2])

        # Remove rows with odd values (outliers)
        sensor_values = {}
        for row in processed_data:
            sensor_name = row[0]
            if sensor_name not in sensor_values:
                sensor_values[sensor_name] = []
            sensor_values[sensor_name].append(row[2])

        median_values = {sensor: statistics.median(values) for sensor, values in sensor_values.items()}

        all_sensors = sorted(set(row[0] for row in processed_data for row[0] in row[:1]))
        sensors_stdev = {}
        for sensor in all_sensors:
            sensors_stdev[sensor] = statistics.stdev(sensor_values[sensor])


        filtered_processed_data = []
        for row in tqdm(processed_data, desc="Removing outliers"):
            sensor_name = row[0]
            median_value = median_values[sensor_name]
            if abs(row[2] - median_value) <= 5 * sensors_stdev[sensor_name]:
                filtered_processed_data.append(row)

        # Transform data to have datetime and sensor values as columns
        data_dict = {}
        last_known_values = {sensor: None for sensor in all_sensors}  # Initialize last known values dictionary
        
        for row in tqdm(filtered_processed_data, desc="Transforming data structure"):
            time_string = row[1]
            sensor_name = row[0]
            var_value = row[2]
            
            if time_string not in data_dict:
                data_dict[time_string] = {}
            data_dict[time_string][sensor_name] = var_value

        # Write the processed data to a CSV file with headers
        with open(output_file_path, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            # Write the header
            writer.writerow(['datetime'] + all_sensors + ['SUM_Flow', 'SUM_Power'])
            
            for time_string, sensors in sorted(data_dict.items()):
                row = [time_string]
                for sensor in all_sensors:
                    if sensor in sensors:
                        last_known_values[sensor] = sensors[sensor]
                    row.append(last_known_values[sensor])

                sum_flow = float(row[1]) + float(row[5])
                row.append(sum_flow)
                sum_power = float(row[4]) + float(row[8])
                row.append(sum_power)

                writer.writerow(row)
        
    data_dict = {}
    
    with open(output_file_path, 'r', newline='') as csv_file:
        reader = csv.reader(csv_file)
        
        # Read the header
        header = next(reader)
        all_sensors = header[1:]  # The first element is 'datetime'
        
        for row in reader:
            time_string = row[0]
            sensors = {sensor: float(value) if value else 0 for sensor, value in zip(all_sensors, row[1:])}
            data_dict[time_string] = sensors
            
    # Calculate and print median and average values for each sensor
    print("Sensor Statistics:")
    for sensor in all_sensors:
        values = [sensors.get(sensor, 0) for sensors in data_dict.values() if sensor in sensors]
        median_value = statistics.median(values) if values else 0
        average_value = sum(values) / len(values) if values else 0
        print(f"{sensor}: Median = {median_value}, Average = {average_value}")

