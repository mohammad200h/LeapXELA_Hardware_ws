echo "Valid Sensor IDs: 1-15"
SENSOR_ID=${1:-1}

./linux_1.8.0_208601/xela_viz -p 5001 -i 0.0.0.0  -f /etc/xela/xServ_leap.ini
