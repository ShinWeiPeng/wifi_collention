import csv
from debug_log import log
import time
import threading

class SimulateCsv:
    def __init__(self, path, instruction):
        self.csv_path = path 
        self.instruction = instruction
        self.transmit_data_handle = threading.Thread(target=self.transmit_data, daemon=True)
        self.is_finish = False
    
    def transmit_data(self):
        with open(self.csv_path, 'r') as file:
            reader = csv.reader(file)
            header = next(reader)  # skip header
            count = 0
            
            for row in reader:
                try:
                    ax, ay, az = row[1:4]
                    ax = int(float(ax) * 8192)
                    ay = int(float(ay) * 8192)
                    az = int(float(az) * 8192)
                    # ax = int(ax)
                    # ay = int(ay)
                    # az = int(az)

                    self.instruction.write_accel_raw(ax, ay, az, count)
                    
                    count += 1
                    
                    if (count % 5 == 0):
                        time.sleep(0.001)
                        
                    if count >= 10000:
                        count = 0
                    
                except Exception as e:
                    log(f"{e}")
                    break
                
        while self.instruction.is_send_finish() == False:
            time.sleep(0.01)  
            
        log(f"Transmit finished! count = {count}")
        self.is_finish = True
    
    def start_transmit_data(self):
        self.transmit_data_handle.start()
        log("Transmit start!")