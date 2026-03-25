
DEVICE1=${1:-/dev/ttyUSB1}
DEVICE2=${2:-/dev/ttyUSB2}

#sudo apt install can-utils

echo "Using Assumed CAN devices: $DEVICE1 (can0), $DEVICE2 (can1). If incorrrect, please run with the correct devices as arguments."

echo "loading slcan module"
sudo modprobe slcan

echo "attaching CANs"
sudo slcand -o -s8 -t hw -S 3000000 "$DEVICE1" can0
sudo slcand -o -s8 -t hw -S 3000000 "$DEVICE2" can1

echo "bringing up interface"
sudo ip link set up can0
sudo ip link set up can1


sudo modprobe vcan
sudo modprobe can-gw


sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0


sudo cangw -A -s can0 -d vcan0 -e
sudo cangw -A -s can1 -d vcan0 -e
