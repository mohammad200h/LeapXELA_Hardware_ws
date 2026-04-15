import csv
import sys
import os

if len(sys.argv) > 1:
    input_file = sys.argv[1]
else:
    input_file = 'leap_state_output.txt'

base, _ = os.path.splitext(input_file)
output_file = base + '.csv'

rows = []
current_block = []
in_data_block = False

with open(input_file, 'r') as infile:
    for line in infile:
        line = line.strip()
        if line == 'data:':
            in_data_block = True
            current_block = []
            continue
        if in_data_block:
            if line.startswith('- '):
                try:
                    value = float(line[2:])
                    current_block.append(value)
                except ValueError:
                    pass
                if len(current_block) == 16:
                    rows.append(current_block)
                    in_data_block = False
            else:
                in_data_block = False

with open(output_file, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([f'joint_{i+1}' for i in range(16)])  # header
    writer.writerows(rows)

print(f"Parsed {len(rows)} rows to {output_file}")