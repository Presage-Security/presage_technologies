import requests
import time
import logging
from pathlib import Path
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [PresagePhysiology] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
class Physiology:
    def __init__(self, api_key=None, base_api_url="https://api.physiology.presagetech.com"):
        if not api_key:
            logging.critical("An API key is required in order to run this package.")
            return
        self.api_key = api_key
        self.base_api_url = base_api_url
    def preprocess_video(self, video):
        logging.warning("Not yet implemented")
        pass
    def retrieve_result(self, id, timeout=1800):
        """Short summary.

        Parameters
        ----------
        id : str
            Id of the uploaded video that was retireved during the video or json payload upload step.
        timeout : int
            Default: 1800. How long to try, in seconds, until to give up.

        Returns
        -------
        dict
            JSON payload returned from the API for the id you chose. If no value is returned before timeout a None value will be returned.

        """
        stop_at = time.time()+timeout

        while True:
            if timeout and time.time()>=stop_at:
                logging.warning("Timeout triggered for id", id,"please try again later.")
                return None
            response = requests.post(
                self.base_api_url+ "/retrieve-data",
                headers={"x-api-key": self.api_key},
                json={"id": id},
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 201:
                time.sleep(5)
            elif response.status_code == 401:
                logging.warning("Unauthorized error! Please make sure your API key is correct.")
                return
            else:
                time.sleep(60)
        return None

    def queue_processing_hr_rr(self, video_path, preprocess=False):
        """Using the Presage Physiology API, get the Heart Rate and Resporation Rate
        of a subject within a video.

        Returns
        -------
        str
            Id for the video uploaded that can be used to later retrieveresults with the retrieve_result function.
        """
        max_size = 5 * 1024 * 1024

        url = self.base_api_url + "/v1/upload-url"
        headers = {"x-api-key": self.api_key}

        target_file = Path(video_path)
        file_size = target_file.stat().st_size

        response = requests.post(url, headers=headers, json={"file_size": file_size})
        if response.status_code == 401:
            logging.warning("Unauthorized error! Please make sure your API key is correct.")
            return
        vid_id = response.json()["id"]
        urls = response.json()["urls"]
        upload_id = response.json()["upload_id"]
        if preprocess:
            pass
        else:
            #TODO: implement wait on server overload status
            # Upload file to S3 using presigned URL
            #with open(video_path, "rb") as f:
            #    files = {"file": (vid_id, f)}
            #    r = requests.post(link["url"], data=link["fields"], files=files)
            parts = []
            with target_file.open("rb") as fin:
                for num, url in enumerate(urls):
                    part = num + 1
                    file_data = fin.read(max_size)
                    res = requests.put(url, data=file_data)
                    if res.status_code != 200:
                        return
                    etag = res.headers["ETag"]
                    parts.append({"ETag": etag, "PartNumber": part})
            url = self.base_api_url + "/v1/complete"
            response = requests.post(url, headers=headers, json={"id": vid_id, "upload_id": upload_id, "parts": parts})
            logging.info("Video uploaded successfully and is now processing.")
        return vid_id
    def queue_processing_all(self, video_path, preprocess=False):
        """Using the Presage Physiology API, get all vitals
        of a subject within a video.

        Returns
        -------
        str
            Id for the video uploaded that can be used to later retrieveresults with the retrieve_result function.
        """
        max_size = 5 * 1024 * 1024

        url = self.base_api_url + "/v1/upload-url"
        headers = {"x-api-key": self.api_key}

        target_file = Path(video_path)
        file_size = target_file.stat().st_size

        response = requests.post(url, headers=headers, json={"file_size": file_size, "so2": {"to_process": True}})
        if response.status_code == 401:
            logging.warning("Unauthorized error! Please make sure your API key is correct.")
            return
        vid_id = response.json()["id"]
        urls = response.json()["urls"]
        upload_id = response.json()["upload_id"]
        if preprocess:
            pass
        else:
            #TODO: implement wait on server overload status
            # Upload file to S3 using presigned URL
            #with open(video_path, "rb") as f:
            #    files = {"file": (vid_id, f)}
            #    r = requests.post(link["url"], data=link["fields"], files=files)
            parts = []
            with target_file.open("rb") as fin:
                for num, url in enumerate(urls):
                    part = num + 1
                    file_data = fin.read(max_size)
                    res = requests.put(url, data=file_data)
                    if res.status_code != 200:
                        return
                    etag = res.headers["ETag"]
                    parts.append({"ETag": etag, "PartNumber": part})
            url = self.base_api_url + "/v1/complete"
            response = requests.post(url, headers=headers, json={"id": vid_id, "upload_id": upload_id, "parts": parts})
            logging.info("Video uploaded successfully and is now processing.")
        return vid_id
    def list_uploads(self):
        """Using the Presage Physiology API, get all available videos a user has processed.

        Returns
        -------
        list
            Returns a list of JSON from the API with Video ID and Upload Date
        """
        response = requests.get(self.base_api_url+ "/list-uploads", headers={"x-api-key": self.api_key})
        items = response.json()
        return items
