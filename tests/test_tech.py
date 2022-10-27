import boto3
import time
import sys
sys.path.append('..')
from presage_technologies import Physiology

physio = Physiology("", base_api_url="https://api.test.physiology.presagetech.com")
# vid_id = physio.queue_processing_hr_rr("/Users/rick/Desktop/test_videos/vid_aya_15x30bpm.avi")
vid_id = physio.queue_processing_all("/Users/rick/Desktop/mobile_example.mp4", preprocess=True)
print("Have video id", vid_id)
time.sleep(60)
final_data = physio.retrieve_result(vid_id)
print(final_data)
