echo "Valid Sensor ID: 1"
SENSOR_ID=${1:-0}

./linux_1.8.0_208601/xela_viz -p 5000 -i 0.0.0.0  -f /etc/xela/xServ_can0.ini
