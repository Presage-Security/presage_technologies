import boto3
import time
import sys
import json
sys.path.append('..')
from presage_technologies import Physiology

physio = Physiology("", base_api_url="https://api.test.physiology.presagetech.com")
with open("/Users/rick/Desktop/mobile_example.json", "r") as f:
    trace = json.load(f)
# vid_id = physio.queue_processing_hr_rr(trace=trace)
vid_id = physio.queue_processing_all(trace=trace)
print("Have video id", vid_id)
time.sleep(60)
final_data = physio.retrieve_result(vid_id)
print(final_data)
