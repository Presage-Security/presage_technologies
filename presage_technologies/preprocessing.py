from presage_technologies.mediapipefunctions import initiate_face_mesh_model, get_face_mesh_landmarks
import numpy as np
import ffmpeg
import json
import cv2
import mediapipe as mp
mp_pose = mp.solutions.pose


class NumpyArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NumpyArrayEncoder, self).default(obj)



def get_rr_tracking_pts(frame, face_location):
    """
    returns chest, and left right shoulder rois - binary mask same size as input
    """
    corners = []
    corner_labels = []

    try:
        with mp_pose.Pose(
            model_complexity=1,
            enable_segmentation=True,
                min_detection_confidence=0.5) as pose:

            sz = frame.shape[0:2]
            # Convert the BGR image to RGB before processing.
            results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            lshoulder = results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER]
            rshoulder = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER]
            lhip = results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_HIP]
            rhip = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_HIP]

            rshoulder = [int(rshoulder.x * sz[1]), int(rshoulder.y * sz[0])]
            lshoulder = [int(lshoulder.x * sz[1]), int(lshoulder.y * sz[0])]
            rhip = [int(rhip.x * sz[1]), int(rhip.y * sz[0])]
            lhip = [int(lhip.x * sz[1]), int(lhip.y * sz[0])]

            lxint = get_x_int(lhip, lshoulder)
            rxint = get_x_int(rhip, rshoulder)


            polygon = np.array([[lhip[0], lhip[1]],
                                [lshoulder[0], lshoulder[1]],
                                [lxint, 0],
                                [rxint, 0],
                                [rshoulder[0], rshoulder[1]],
                                [rhip[0], rhip[1]]], dtype='int32')

            polygon_chest = np.array([[lhip[0], lhip[1]],
                                [lshoulder[0], lshoulder[1]],
                                [rshoulder[0], rshoulder[1]],
                                [rhip[0], rhip[1]]], dtype='int32')

            polygon_face = []
            smaller_face = False
            if len(face_location)>4:
                polygon_face = np.array(face_location, dtype='int32')
            elif len(face_location)>0:
                polygon_face = np.array([
                                   [face_location[0], face_location[3]],
                                   [face_location[2], face_location[3]],
                                   [face_location[2], face_location[1]],
                                   [face_location[0], face_location[1]]], dtype='int32')
            else:
                # here we use mp to extract the face points
                smaller_face = True
                for i in range(11):
                    polygon_face.append(
                                [int(results.pose_landmarks.landmark[i].x * sz[1]),
                                 int(results.pose_landmarks.landmark[i].y * sz[0])])

                polygon_face = np.array(polygon_face, dtype='int32')

            upper_mask = np.zeros(frame.shape[0:2])
            if len(polygon) > 0:
                hull = cv2.convexHull(polygon)
                upper_mask = cv2.fillConvexPoly(upper_mask, hull, 1)
            upper_mask = upper_mask > 0.5

            chest_mask = np.zeros(frame.shape[0:2])
            if len(polygon_chest) > 0:
                hull = cv2.convexHull(polygon_chest)
                chest_mask = cv2.fillConvexPoly(chest_mask, hull, 1)
            chest_mask = chest_mask > 0.5


            face_mask = np.zeros(frame.shape[0:2])
            if len(polygon_face) > 0:
                hull = cv2.convexHull(polygon_face)
                face_mask = cv2.fillConvexPoly(face_mask, hull, 1)
            if False: #smaller_face:
                dilate_sz = int(np.sum(face_mask)**.5/4)
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_sz, dilate_sz))
                face_mask = cv2.dilate(face_mask, kernel, iterations=2)
            face_mask = face_mask > 0.5


            pose_mask = results.segmentation_mask > .5

            # for the area we use, assume 15^2 points, must be spaced this much apart
            min_distance = round(np.sum((upper_mask & pose_mask).astype('uint8'))**.5/15)
            feature_params = dict(maxCorners=225, qualityLevel=.0005, minDistance=min_distance)  # , blockSize=3)
            corners = cv2.goodFeaturesToTrack(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
                                              mask=(upper_mask & pose_mask & ~face_mask).astype('uint8'), **feature_params)


            # ret, thresh = cv2.threshold(chest_mask*255, 125, 255, cv2.THRESH_BINARY_INV) #, 0.5, 1, 0)
            contours_chest, hierarchy = cv2.findContours(chest_mask.astype('uint8'), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            contours_face, hierarchy = cv2.findContours(face_mask.astype('uint8'), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            corner_labels = np.zeros(corners.shape[0])
            for ipt in range(corners.shape[0]):
                closest_chest = cv2.pointPolygonTest(contours_chest[0],  (corners[ipt,0,0], corners[ipt,0,1]), True)
                closest_face = cv2.pointPolygonTest(contours_face[0], (corners[ipt, 0, 0], corners[ipt, 0, 1]), True)
                if closest_face > closest_chest:  # closer to face, within face point (1)
                    corner_labels[ipt] = 1

    except Exception as ex:
        pass
    return corners, corner_labels

def average_rois(frame, points):
    """
       inputs: frame (frame in BGR); points (face mesh points)
       outputs: average of BGR values in face mesh points

       computes the convex hull of the face and then takes average of RGB values
       """
    # forehead
    left_fh_t = [54, 68, 104, 69, 67, 103]
    left_fh_b = [68, 63, 105, 66, 69, 104]
    center_fh_lt = [67, 69, 108, 151, 10, 109]
    center_fh_lb = [69, 66, 107, 9, 151, 108]
    center_fh_rt = [10, 151, 337, 299, 297, 338]
    center_fh_rb = [151, 9, 336, 296, 299, 337]
    right_fh_t = [297, 299, 333, 298, 284, 332]
    right_fh_b = [299, 296, 334, 293, 298, 333]
    center_fh_b = [107, 55, 193, 168, 417, 285, 336, 9]
    # nose
    nose_top = [193, 122, 196, 197, 419, 351, 417, 168]
    nose_bot = [196, 3, 51, 45, 275, 281, 248, 419, 197]
    # left cheek
    lc_t = [31, 117, 50, 101, 100, 47, 114, 121, 230, 229]
    lc_b = [50, 187, 207, 206, 203, 129, 142, 101]
    # right cheek
    rc_t = [261, 346, 280, 330, 329, 277, 343, 350, 450, 449, 448]
    rc_b = [280, 411, 427, 426, 423, 358, 371, 330]
    all_rois = [left_fh_t, left_fh_b, center_fh_lt, center_fh_lb, center_fh_rt, center_fh_rb, right_fh_t, right_fh_b,
                center_fh_b, nose_top, nose_bot, lc_t, lc_b, rc_t, rc_b]

    grid_bgr = np.zeros((len(all_rois),3))
    points = np.array(np.squeeze(points), dtype='int32')
    h, w, _ = frame.shape
    dummy_mat = np.zeros((h, w)).astype(np.int32)

    for ccc, kk in enumerate(all_rois):
        outline = np.squeeze(cv2.convexHull(points[kk, :]))
        face_mask = cv2.fillPoly(dummy_mat.copy(), [outline], 1)
        grid_bgr[ccc, :] = np.array(cv2.mean(frame, face_mask.astype(np.uint8)))[:-1]

    outline = np.squeeze(cv2.convexHull(points))
    face_mask = cv2.fillPoly(dummy_mat.copy(), [outline], 1)
    whole_face = np.array(cv2.mean(frame, face_mask.astype(np.uint8)))[:-1]
    return whole_face, grid_bgr

def get_face_values(frame, face_points):
    """
    get_face_values gets intensity of image within ROIs
    """
    bgr = average_rois(frame, face_points)
    return bgr
def track_points_face(frame, face_mesh_model):
    """
    Updates the new mesh face vertices simply by calling mediapipe again with the new frame
    - using the old model as input, we get less jitter and it's significantly faster
    """
    try:
        mesh_pts, face_mesh_model = get_face_mesh_landmarks(frame, face_mesh_model)
        return mesh_pts, face_mesh_model

    except Exception as e:
        print(f'Error in track points face: {e}')
        return None, None

    if not mesh_pts:
        print("No Face")
        return None, None

def get_face_points(frame):
    """
    get_face_points gets usable points to track on the face
    - get feature landmarks on face (eg. from dlib or mediapipe)
    - get ROIs
    - get "good points to track" within particular ROI
    - get the boundary of the face (using face mesh or otherwise)
    - if None for track points (pts) and face mesh points (current_face_cords)

    returns pts (good points to track for tracking), current_face_cords (media pipe face mesh points)
    returns pts: None, current_face_cords: None if there is no face found to trigger a reset
    """
    face_mesh_model = initiate_face_mesh_model()
    try:
        pts, face_mesh_model = get_face_mesh_landmarks(frame, face_mesh_model)
    except Exception as e:
        print(f'Error in getting face points: {e}')
        pts = None
    return pts, face_mesh_model
def process_frame_rr(frame, frame_last, traces_last):
    """
    proces_frame_rr analyzes the image to extract points to be tracked on upper body regions
    - reset flag turned on when tracking needs to be reset
    """

    # todo: fix resets
    try:
        face_location = traces_last['hr_pts']
    except:
        face_location = []

    try:
        rr_pts_prev = traces_last["rr_pts"]
        rr_pt_labels = traces_last["rr_pt_labels"]
    except:
        rr_pts_prev = []
        rr_pt_labels = []

    valid_count = np.sum([~np.isnan(x[0][0]) for x in rr_pts_prev])
    if valid_count < 20:
        reset_flag = True
        rr_pts, rr_pt_labels = get_rr_tracking_pts(frame, face_location)
    else:
        reset_flag = False
        rr_pts = track_points_rr(frame, frame_last, rr_pts_prev)

    valid_count = np.sum([~np.isnan(x[0][0]) for x in rr_pts])

    return {"rr_pts": rr_pts, "rr_pt_labels": rr_pt_labels, 'rr_reset': reset_flag}


def process_frame_pleth(frame, face_mesh_model):
    """
    process_frame_pleth analyzes the image to extract the face location, points to track, and ultimately the RGB traces
    - all data here can be used for HR/RR/SpO2/HRV/pleth generation
    - frame_analyzed is a dictionary of all analysis content
    """
    bgr = []
    if face_mesh_model is None:
        hr_pts, face_mesh_model = get_face_points(frame)
    else:
        try:
            hr_pts, face_mesh_model = track_points_face(frame, face_mesh_model)
        except:
            # here we are in a "reset" state.  the last frame analyzed didn't have points, so we start over
            hr_pts, face_mesh_model = get_face_points(frame)

    if hr_pts is not None:
        bgr = get_face_values(frame, hr_pts)  # mean RGB over ROIs
    return {"bgr": bgr, "hr_pts": hr_pts}, face_mesh_model

def frame_skipper(fps_current, fps_desired):
    """
    computes the number of frames to skip given the original fps and the desired fps
    - eg. if og fps = 30, and desired is 10fps, then we must skip 3 frames (eg. every 3rd frame) to ensure that
    """
    if fps_desired == float('inf'):
        mod_amount = 1
    else:
        mod_amount = int(np.round(fps_current / fps_desired))
    return mod_amount


def frame_skipper_rr(fps, mod_hr):
    """
    this function tries to find the optimal number of frames to jump such that
    we are maximizing overlap between HR analysis and RR analysis
    - RR is optimal when analyzed on the order of 3-8 FPS
    """
    rr_fps_ideal = 5
    mod_rr = frame_skipper(fps, rr_fps_ideal)
    mod_rr = mod_hr * round(mod_rr / mod_hr)
    return mod_rr

def get_settings_variables(settings):
    """
    goes through the settings module and finds which attributes are variables
    - outputs it to a dictionary to be saved later
    """
    svar = {}
    for v in dir(settings):
        try:
            attribute = eval(f'settings.{v}')
            if not (callable(attribute) or isinstance(attribute, ModuleType) or v[0:2] == '__'):
                svar[v] = attribute
        except Exception as ex:
            print(f'Could not export setting variables, error: {ex}')
            pass

    return svar

def video_preprocess(path):
    """
    Video_preprocess reads in a video from source (path) and subsequently processes each frame into a set of variables stored in traces
    - internally used parameter variables are stored in settings
    - traces a python dict which is then serialized into a json object and returned
     - traces can be post processed to extract absolute vital measurements
    """
    traces = {}
    cap = cv2.VideoCapture(path)
    fps_orig = round(cap.get(cv2.CAP_PROP_FPS))
    vid_length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    mod_amount = frame_skipper(fps_orig, 10)
    mod_amount_rr = frame_skipper_rr(fps_orig, mod_amount)

    traces['settings']= {"FPS_ORIG_EFF":round(fps_orig / mod_amount),
    "FPS_NR_EFF":fps_orig / mod_amount, "FPS_OG":fps_orig,
    "MOD_AMOUNT_HR":mod_amount, "MOD_AMOUNT_RR":mod_amount_rr,
    "TOTAL_FRAMES":int(vid_length / mod_amount) + 1, "DN_SAMPLE":1, "HR_FPS":10,
    "RR_SPEC_PARAMS":{'band_time': 15, 'band_bpm': [4, 40], 'delta_t': 1, 'delta_bpm': .2,
    'normalize': True, 'snr_thresh': 2},"HR_SPEC_PARAMS":{'band_time':10}
    }


    orientation_done = False
    video_metadata = ffmpeg.probe(path)
    use_meta = None
    side_list_location = -1
    #only needed if the vertical video bug persists on mobile
    if cv2.__version__ == "4.6.0":
        for ind in video_metadata["streams"]:
            if ind["codec_type"] == "video":
                use_meta = ind
                break

        if use_meta:
            if len(use_meta.get("side_data_list", [])) > 0:
                for x in range(0, len(use_meta["side_data_list"])):
                    if use_meta["side_data_list"][x].get("displaymatrix", False):
                        side_list_location = x
                        break
    try:
        frame_last_rr = None
        frame_index_last = 0
        frame_index_last_rr = 0
        traces[frame_index_last] = None
        traces[frame_index_last_rr] = None
        face_mesh_model = None

        for frame_index in range(0, vid_length):
            ret, frame = cap.read()
            if not ret:
                continue
            if not orientation_done:
                vid_height, vid_width = frame.shape[:2]
                print("Video Height:", vid_height)
                print("Video Width:", vid_width)
                orientation_done = True

            if np.mod(frame_index, mod_amount) == 0:
                #this will likely not apply on mobile since all videos are vertical
                #but it is a good idea to make sure they are being processed right side up
                if cv2.__version__ == "4.6.0":
                    if frame.shape[0] > frame.shape[1]:
                        if side_list_location > -1:
                            if "\n00000000:            0       65536           0\n00000001:       -65536           0           0" in \
                                    use_meta["side_data_list"][side_list_location]["displaymatrix"]:
                                frame = cv2.rotate(frame, cv2.ROTATE_180)
                        else:
                            frame = cv2.rotate(frame, cv2.ROTATE_180)

                frame = cv2.resize(frame,
                                   (frame.shape[1] // traces['settings']["DN_SAMPLE"], frame.shape[0] // traces['settings']["DN_SAMPLE"]),
                                   cv2.INTER_AREA)

                try:
                    traces[frame_index], face_mesh_model = process_frame_pleth(frame, face_mesh_model)
                except Exception as e:
                    print(f"Processing error in HR analysis at frame: {frame_index}, error: {e}")
                    pass

                try:
                    # here we compute all metrics associated with RR analysis, tracked points of body
                    if np.mod(frame_index, mod_amount_rr) == 0:
                        if frame_index not in traces:
                            traces[frame_index] = {}

                        rr_traces = process_frame_rr(frame, frame_last_rr, traces[frame_index_last_rr])
                        traces[frame_index] = {**traces[frame_index], **rr_traces}
                        frame_index_last_rr = frame_index
                        frame_last_rr = frame

                except Exception as e:
                    print(f"Processing error in RR analysis at frame: {frame_index}, error: {e}")
                    pass

                if frame_index in traces:
                    time_now = {'time_now': frame_index / fps_orig}
                    traces[frame_index] = {**traces[frame_index], **time_now}

    except Exception as e:
        print(f"CV2 error at frame: {frame_index}, error: {e}")
        pass
    cap.release()
    # serialize all traces data and return as json
    return json.dumps(traces, cls=NumpyArrayEncoder)
