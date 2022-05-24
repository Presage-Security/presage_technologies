# presage_technologies

**The information contained in this Python client, API, or data responses as expected form normal usage of the data should not be used to diagnose or treat any disease or illness. This is for informational and research purposes only.**

A Python client for Presage Technologies' APIs. [Presage Technologies](https://presagetech.com)


## License

Provided under [MIT License] by Presage Technologies.

```
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```
## General

Currently, the only API used in this package is for [Physiology API](https://physiology.presagetech.com)
The functions and methods for this library should mirror the
endpoints specified by the Physiology API [documentation](https://docs.physiology.presagetech.com).

## Installation

Installation for the package can be done via `pip`:

```bash
$ pip install presage_technologies
```

## Physiology Usage

After installation, import the client class into your project and initialize with the API key:

```python
from presage_technologies import Physiology
physio = Physiology("api_key_here")
```

Use `.queue_processing_hr_rr()` to upload your video for processing and return an id for the upload to allow for async processing. You are able to upload multiple videos as you would like as long as it is within your plan limits.

```python
video_id = physio.queue_processing_hr_rr("/path/to/video/file")
```

We currently recommend waiting half the length of your video to start checking whether it is not but this is not a hard limit. When you are ready to start checking for the result you can use `.retrieve_result()` with your video_id to return the results.

```python
data = physio.return_resuls(video_id)
```

Data will return a dictionary with keys `hr` and `rr`. Both will have keys that represent the time within the video the value was recorded.
