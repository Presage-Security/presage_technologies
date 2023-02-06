import boto3
import time
import sys
sys.path.append('..')
from presage_technologies import Physiology

physio = Physiology("EhPM5zB8vM7UM9C0A0uzV1jyfDjLaNN4YOstVTR7", base_api_url="https://api.test.physiology.presagetech.com")
vid_id = physio.queue_processing_hr_rr("/Users/rick/Desktop/mobile_example.mp4", preprocess=True)
# vid_id = physio.queue_processing_all("/Users/rick/Desktop/mobile_example.mp4", preprocess=True)
print("Have video id", vid_id)
time.sleep(60)
final_data = physio.retrieve_result(vid_id)
print(final_data)
