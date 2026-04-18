# Dataset Description

This dataset contains maintenance records and sensor readings from 20,000 industrial pumps, used to predict and analyze pump health. It includes various sensor data and operational parameters of pumps such as temperature, vibration, pressure, flow rate, and RPM. Additionally, it contains information on the operational hours of the pump and a maintenance flag indicating whether the pump required maintenance or not.

This dataset can be used for predictive maintenance models and machine learning algorithms to predict failures or required maintenance based on sensor data.

Dataset Structure:

Pump_ID: Unique identifier for each pump (Integer).
Temperature: Temperature reading of the pump (Float).
Vibration: Vibration intensity measurement of the pump (Float).
Pressure: Pressure level recorded in the pump (Float).
Flow_Rate: Flow rate of the fluid passing through the pump (Float).
RPM: Rotational speed of the pump in revolutions per minute (Float).
Operational_Hours: Number of hours the pump has been operational (Float).
Maintenance_Flag: Binary indicator (0 or 1) showing whether the pump required maintenance (1) or not (0) (Integer).

Dataset Characteristics:

Rows: 20,000
Columns: 8
Data types:
Numerical (float64): Temperature, Vibration, Pressure, Flow_Rate, RPM, Operational_Hours
Integer: Pump_ID, Maintenance_Flag
File Format: CSV

Usage: This dataset can be used for tasks such as:

Predictive maintenance modeling
Failure prediction
Time series analysis
Classification (for predicting the maintenance flag)
