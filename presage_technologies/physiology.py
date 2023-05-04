import json
import logging
import os
import sys
import time
import gzip
from pathlib import Path

import requests
from presage_physiology_preprocessing import process

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [PresagePhysiology] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Physiology:
    def __init__(
        self, api_key=None, base_api_url="https://api.physiology.presagetech.com"
    ):
        if not api_key:
            logging.critical("An API key is required in order to run this package.")
            return
        self.api_key = api_key
        self.base_api_url = base_api_url

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
        stop_at = time.time() + timeout

        while True:
            if timeout and time.time() >= stop_at:
                logging.warning(
                    "Timeout triggered for id", id, "please try again later."
                )
                return None
            response = requests.post(
                self.base_api_url + "/retrieve-data",
                headers={"x-api-key": self.api_key},
                json={"id": id},
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 201:
                time.sleep(1)
            elif response.status_code == 401:
                logging.warning(
                    "Unauthorized error! Please make sure your API key is correct."
                )
                return
            else:
                time.sleep(1)
        return None

    def process_loop(self, video_path, preprocess, compress, type, trace=None):
        parts = []
        vid_id = None
        upload_id = None
        urls = []
        max_size = 5 * 1024 * 1024
        url = self.base_api_url + "/v1/upload-url"
        headers = {"x-api-key": self.api_key}
        max_size = 5 * 1024 * 1024

        if preprocess or trace is not None:
            if trace is None:
                preprocessed_data = process(video_path)
            else:
                preprocessed_data=trace
            preprocessed_data = json.dumps(preprocessed_data).encode("utf-8")
            if compress:
                preprocessed_data = gzip.compress(preprocessed_data)
            response = requests.post(
                url,
                headers=headers,
                json={
                    "file_size": sys.getsizeof(preprocessed_data),
                    type: {"to_process": True},
                },
            )
            if response.status_code == 401:
                logging.warning(
                    "Unauthorized error! Please make sure your API key is correct."
                )
                return
            vid_id = response.json()["id"]
            urls = response.json()["urls"]
            upload_id = response.json()["upload_id"]

            tracker = 0
            max_len = len(preprocessed_data)
            for num, url in enumerate(urls):
                part = num + 1
                if (max_len - tracker) < max_size:
                    file_data = preprocessed_data[tracker:max_len]
                else:
                    file_data = preprocessed_data[tracker:max_size]
                res = requests.put(url, data=file_data)
                tracker += max_size
                if res.status_code != 200:
                    return
                etag = res.headers["ETag"]
                parts.append({"ETag": etag, "PartNumber": part})
        else:
            target_file = Path(video_path)
            file_size = target_file.stat().st_size

            response = requests.post(
                url,
                headers=headers,
                json={"file_size": file_size, type: {"to_process": True}},
            )
            if response.status_code == 401:
                logging.warning(
                    "Unauthorized error! Please make sure your API key is correct."
                )
                return
            vid_id = response.json()["id"]
            urls = response.json()["urls"]
            upload_id = response.json()["upload_id"]
            with target_file.open("rb") as fin:
                for num, url in enumerate(urls):
                    part = num + 1
                    file_data = fin.read(max_size)
                    res = requests.put(url, data=file_data)
                    if res.status_code != 200:
                        return
                    etag = res.headers["ETag"]
                    parts.append({"ETag": etag, "PartNumber": part})
        return parts, upload_id, vid_id

    def queue_processing_hr_rr(self, video_path=None, trace=None, preprocess=True, compress=True):
        """Using the Presage Physiology API, get the Heart Rate and Resporation Rate
        of a subject within a video.

        Returns
        -------
        str
            Id for the video uploaded that can be used to later retrieveresults with the retrieve_result function.
        """

        headers = {"x-api-key": self.api_key}
        if video_path is None and trace is None:
            raise Exception("You must pass either a video path or trace json")
        parts, upload_id, vid_id = self.process_loop(video_path, preprocess, compress, type="hr_br", trace=trace)

        url = self.base_api_url + "/v1/complete"
        requests.post(
            url,
            headers=headers,
            json={"id": vid_id, "upload_id": upload_id, "parts": parts},
        )
        logging.info("Video uploaded successfully and is now processing.")
        return vid_id

    def queue_processing_all(self, video_path=None, trace=None, preprocess=True, compress=True):
        """Using the Presage Physiology API, get all vitals
        of a subject within a video.

        Returns
        -------
        str
            Id for the video uploaded that can be used to later retrieveresults with the retrieve_result function.
        """

        headers = {"x-api-key": self.api_key}
        if video_path is None and trace is None:
            raise Exception("You must pass either a video path or trace json")
        parts, upload_id, vid_id = self.process_loop(video_path, preprocess, compress, type="all", trace=trace)

        url = self.base_api_url + "/v1/complete"
        requests.post(
            url,
            headers=headers,
            json={"id": vid_id, "upload_id": upload_id, "parts": parts},
        )
        logging.info("Video uploaded successfully and is now processing.")
        return vid_id

    def list_uploads(self):
        """Using the Presage Physiology API, get all available videos a user has processed.

        Returns
        -------
        list
            Returns a list of JSON from the API with Video ID and Upload Date
        """
        response = requests.get(
            self.base_api_url + "/list-uploads", headers={"x-api-key": self.api_key}
        )
        items = response.json()
        return items
