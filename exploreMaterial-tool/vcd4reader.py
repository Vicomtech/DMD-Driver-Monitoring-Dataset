import json
import numpy as np
import vcd.core as core
import vcd.types as types

from pathlib import Path


# TODO: get actions and objects per frame

# TODO: funtion to get frame intervals per action or object presence
#TODO: fusion with vcd4parser?
#TODO: delete unecessary code

# dict for changes in structures
# data manipulation is only for external structures
dmd_struct = {
    "groups": {
        "grupo1A": "gA",
        "grupo2A": "gB",
        "grupo2M": "gC",
        "grupo3B": "gD",
        "grupoE": "gE",
        "grupo4B": "gF",
        "grupoZ": "gZ",
    },
    "sessions": {
        "attm": "s1",
        "atts": "s2",
        "reach": "s3",
        "attc": "s4",
        "gaze": "s5",
        "gazec": "s6",
        "drow": "s7",
        "attm2": "s1",
        "atts2": "s2",
        "reach2": "s3",
        "attc2": "s4",
        "gaze2": "s5",
        "gazec2": "s6",
        "drow2": "s7",
    },
}

# Type of annotation
annotate_dict = {0: "unchanged", 1: "manual", 2: "interval"}


def is_string_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def keys_exists(element, *keys):
    """
    Check if *keys (nested) exists in `element` (dict).
    """
    if not isinstance(element, dict):
        raise AttributeError("keys_exists() expects dict as first argument.")
    if len(keys) == 0:
        raise AttributeError(
            "keys_exists() expects at least two arguments, one given.")

    _element = element
    for key in keys:
        try:
            _element = _element[key]
        except KeyError:
            return False
    return True


class VcdHandler:
    
    def __init__(self, vcd_file: Path, dict_file: Path):

        # vcd variables
        self.__vcd = None
        self.__vcd_file = str(vcd_file)
        self.__vcd_loaded = False

        # Internal Variables and Initialization
        self.__uid_driver = None
        self.ont_uid = 0

        self.__group = None
        self.__subject = None
        self.__session = None
        self.__date = None

        self.__bf_shift = None
        self.__hb_shift = None
        self.__hf_shift = None

        self.__face_frames = None
        self.__body_frames = None
        self.__hands_frames = None

        self.__face_uri = None
        self.__body_uri = None
        self.__hands_uri = None

        # If vcd_file exists then load data into vcd object
        if vcd_file.exists():

            # -- Load VCD from file --

            # Create a VCD instance and load file
            self.__vcd = core.VCD(file_name=self.__vcd_file, validation=True)
            # vcd json is in self.__vcd.data

            # Check required essential fields inside to be considered loaded
            vcd_metadata = self.__vcd.get_metadata()
            body_sh_exist = keys_exists(vcd_metadata,"streams","body_camera","stream_properties","sync","frame_shift")
            hands_sh_exist = keys_exists(vcd_metadata,"streams","hands_camera","stream_properties","sync","frame_shift")

            # If shifts fields exist then consider the vcd loaded was valid
            if body_sh_exist and hands_sh_exist:
                self.__vcd_loaded = True
            else:
                raise RuntimeError(
                    "VCD doesn't have all necesary information. Not valid."
                )

            # -- Get video info --

            # Get video basic metadata
            self.__group, self.__subject, self.__session, self.__date = self.get_basic_metadata()

            # Get stream shifts
            self.__bf_shift, self.__hf_shift, self.__hb_shift = self.get_shifts()

            #Get video uri's
            self.__face_uri, self.__body_uri, self.__hands_uri = self.get_videos_uris()

            # Get frame numbers
            self.__face_frames, self.__body_frames, self.__hands_frames, self.__full_mosaic_frames = self.get_frame_numbers()

            #Number of actions in vcd
            self.__num_actions = self.__vcd.get_num_actions()
            print("There are %s actions in this VCD" % (self.__num_actions))

            self.__vcd_loaded = False



        else:
            raise RuntimeError("VCD file not found.")

        # Get dictionary information
        self.__dict_file = Path()
        self.__dicts = None
        self.__dicts_uids = None
        self.__initDicts(dict_file)

    def get_frame_data(self, frameId: int):
        print("get_action", self.__vcd.get_action(0))
        #print("get_all", self.__vcd.get_all(core.ElementType(2)))
        #print("get_frame", self.__vcd.get_frame)
        #print("get obejcts with data", self.__vcd.get_objects_with_object_data_name("age"))
    
    def get_basic_metadata(self):
        if self.__vcd_file:
            if self.__vcd.data["vcd"]["name"]:
                # e.g: gA_1_s1_2019-03-08T09;31;15+01;00
                name = str(self.__vcd.data["vcd"]["name"]).split("_")
                group = name[0]
                subject = name[1]
                session = name[2]
                date = name[3].replace(";", ":")
                return group, subject, session, date
            else:
                raise RuntimeError("WARNING: VCD does not have a name")
        else:
            return self.__group, self.__subject, self.__session, self.__date

    #function to get intervals from specific action, providing its name or its uid
    def get_frames_intervals_of_action(self, uid):
        if isinstance(uid, str):
            uid = self.is_action_type_get_uid(uid)[1]
        if uid >=0:
            intervals = self.__vcd.get_frame_intervals_of_element(core.ElementType(2), uid)
            return intervals
        else:
            raise RuntimeError("WARNING: VCD does not have action with uid",uid)  

    #Function to know if an action name (label) given is an action type name. It is useful because type names are composed by level_name/label_name
    #Also returns uid of action (e.g "only_left" will return 8)
    def is_action_type_get_uid(self, action_string):
        for uid, action_type in enumerate(self.get_action_type_list()):
            if action_string == action_type.split("/")[1] or action_string == action_type:
                return True, uid
        return False, -1

    #Funcion to go through the VCD and get the "type" val of all actions available
    def get_action_type_list(self):
        action_type_list = []
        if self.__vcd_file:
            for uid in range(self.__num_actions):
                action_type_list.append(self.__vcd.data["vcd"]['actions'][uid].get('type'))
        return action_type_list


    def __initDicts(self, dict_json: Path):
        """
        Obtain the dictionaries from file
        """
        # Check dict_json file exists
        if not dict_json.exists():
            raise RuntimeError(
                "Dictionary file doesn't exist: " + str(Path(dict_json).name)
            )

        # # Get Dictionaries
        # Function to transform int keys to integer if possible
        def keys_to_int(x):
            r = {int(k) if is_string_int(k) else k: v for k, v in x}
            return r

        def dict_to_uid(x):
            r = {
                int(k) if is_string_int(k) else k: -1 if is_string_int(k) else v
                for k, v in x
            }
            return r

        with open(str(dict_json), "r") as dict_file:
            dicts = json.load(dict_file, object_pairs_hook=keys_to_int)
        with open(str(dict_json), "r") as dict_file:
            dicts_uids = json.load(dict_file, object_pairs_hook=dict_to_uid)

        self.__dict_file = dict_json
        self.__dicts = dicts
        self.__dicts_uids = dicts_uids

    # Return flag that indicate if vcd was loaded from file
    def fileLoaded(self):
        return self.__vcd_loaded

    # This function reads each stream video uri from the VCD
    def get_videos_uris(self):
        if self.__vcd_loaded:
            metadata = self.__vcd.get_metadata()
            if metadata == dict():
                raise RuntimeError("VCD doesn't have metadata information")
            streams_data = metadata["streams"]
            face = str(streams_data["face_camera"]["uri"])
            body = str(streams_data["body_camera"]["uri"])
            hands = str(streams_data["hands_camera"]["uri"])
        else:
            face = self.__face_uri
            body = self.__body_uri
            hands = self.__hands_uri
        return face, body, hands

    # This function reads the number of frames of the hands video from the VCD
    def get_frame_numbers(self):
        if self.__vcd_loaded:
            metadata = self.__vcd.get_metadata()
            if metadata == dict():
                raise RuntimeError("VCD doesn't have metadata information")
            streams_data = metadata["streams"]
            face = int(streams_data["face_camera"]
                       ["stream_properties"]["total_frames"])
            body = int(streams_data["body_camera"]
                       ["stream_properties"]["total_frames"])
            hands = int(streams_data["hands_camera"]
                        ["stream_properties"]["total_frames"])
            mosaic = int(self.__vcd.get_frame_intervals()[
                         0]["frame_end"]) + 1  # because is 0 count

        else:
            face = self.__face_frames
            body = self.__body_frames
            hands = self.__hands_frames
            mosaic = self.__full_mosaic_frames
        return face, body, hands, mosaic

    # This function allows to get the stream shifts directly from a valid and
    # loaded VCD file
    # Returns:
    # @body_face_shift
    # @hands_face_shift
    # @hands_body_shift
    def get_shifts(self):
        if self.__vcd_loaded:
            metadata = self.__vcd.get_metadata()
            if metadata == dict():
                raise RuntimeError("VCD doesn't have metadata information")

            streams_data = metadata["streams"]
            body_face_sh = streams_data["body_camera"]["stream_properties"]["sync"][
                "frame_shift"
            ]
            hands_face_sh = streams_data["hands_camera"]["stream_properties"]["sync"][
                "frame_shift"
            ]
            hands_body_sh = hands_face_sh - body_face_sh
        else:
            body_face_sh = self.__bf_shift
            hands_face_sh = self.__hf_shift
            hands_body_sh = self.__hb_shift
        return body_face_sh, hands_face_sh, hands_body_sh

    # This function extracts the annotation information from a valid and loaded
    # VCD file
    # Returns:
    # @annotations: A matrix consisting of the annotation labels for each of
    #               the levels in dict
    # @validations: A matrix consisting of the validation method while
    #               annotating
    def getAnnotationVectors(self):
        # Get some handy variables
        vcd = self.__vcd
        body_face_shift = self.__bf_shift
        hands_face_shift = self.__hf_shift

        if vcd is None or body_face_shift is None or hands_face_shift is None:
            raise RuntimeError("Couldn't get VCD data")

        # Create annotation and validation vectors
        frame_interval = vcd.get_frame_intervals()
        total_frames = frame_interval[-1]["frame_end"] + 1
        total_levels = len(self.__dicts["dict_names"])
        # initial values for annotations: --,looking,--,both,--,--,safe drive
        annotations = np.array([[99, 0, 99, 0, 99, 99, 0]
                                for _ in range(total_frames)])
        validations = np.array(
            [[0 for _ in range(total_levels)] for _ in range(total_frames)]
        )

        # Fill annotation data
        annotation_groups = self.__dicts["dict_names"].items()
        annotation_types = self.__dicts["dict_types"].items()

        # Fill Data of annotation and validation vectors
        # Loop over all the annotation levels searching for annotated frame
        # intervals
        for level_code, level_type in zip(annotation_groups, annotation_types):
            assert level_code[0] == level_type[0]
            dict_name = "A" + str(level_code[0]) + "_dict"
            level_labels = self.__dicts[dict_name].items()
            assert len(level_labels) > 0
            # Loop over each level labels
            for label_id, label_str in level_labels:
                if label_id == 99 or label_id == 100:
                    continue
                if level_type[1] == "action" or level_type[1] == "object":
                    ann_type = None
                    elem_type = None
                    if level_type[1] == "action":
                        ann_type = level_code[1] + "/" + label_str
                        elem_type = core.ElementType.action
                    elif level_type[1] == "object":
                        ann_type = label_str
                        elem_type = core.ElementType.object
                    l_uids = vcd.get_elements_of_type(
                        element_type=elem_type, semantic_type=ann_type
                    )
                    # Only allowed 0 or 1 action type in VCD
                    assert 0 <= len(l_uids) <= 1
                    # Loop over all elements of specific type
                    for uid in l_uids:
                        l_fi = vcd.get_frame_intervals_of_element(
                            element_type=elem_type, uid=uid
                        )
                        # Loop over frame intervals
                        for fi in l_fi:
                            start = fi["frame_start"]
                            end = fi["frame_end"] + 1
                            annotations[start:end, level_code[0]] = label_id
                            # Get annotation method (validations)
                            for f_num in range(start, end):
                                f = vcd.get_frame(frame_num=f_num)
                                lev = level_type[1]
                                if keys_exists(
                                    f, lev + "s", uid, lev + "_data", "text"
                                ):
                                    # Search data of annotation method
                                    data = f[lev + "s"][uid][lev +
                                                             "_data"]["text"]
                                    for d in data:
                                        if d["name"] == "annotated":
                                            val_id = [
                                                k
                                                for k, v in annotate_dict.items()
                                                if v == d["val"]
                                            ]
                                            cod = level_code[0]
                                            validations[f_num, cod] = val_id[0]

                elif level_type[1] == "stream_properties":
                    # Only way is to read frame by frame the stream_properties
                    # field
                    for f_num in range(total_frames):
                        f = vcd.get_frame(frame_num=f_num)
                        if keys_exists(
                            f,
                            "frame_properties",
                            "streams",
                            label_str,
                            "stream_properties",
                            "occlusion",
                        ):
                            a = f["frame_properties"]["streams"][label_str][
                                "stream_properties"
                            ]
                            ann_str = a["occlusion"]["annotated"]
                            annotations[f_num, level_code[0]] = label_id
                            val_id = [
                                k for k, v in annotate_dict.items() if v == ann_str
                            ]
                            assert len(val_id) == 1
                            validations[f_num, level_code[0]] = val_id[0]

        face_shift = 0
        body_shift = body_face_shift
        hands_shift = hands_face_shift
        # START
        # Fill with NAN codes those levels where the corresponding reference
        # video has no frames
        if body_face_shift > 0 and hands_face_shift > 0:
            # Face starts first , then body or hands
            annotations[0:body_face_shift, 5:7] = 100
            annotations[0:hands_face_shift, 3:5] = 100
        elif body_face_shift < hands_face_shift:
            # Body starts first
            face_shift = abs(body_face_shift)
            body_shift = 0
            hands_shift = face_shift + hands_face_shift
            annotations[0:face_shift, 1:3] = 100
            annotations[0:hands_shift, 3:5] = 100
        elif hands_face_shift < body_face_shift:
            # Hands starts first
            face_shift = abs(hands_face_shift)
            body_shift = face_shift + body_face_shift
            hands_shift = 0
            annotations[0:face_shift, 1:3] = 100
            annotations[0:body_shift, 5:7] = 100
        elif hands_face_shift == body_face_shift:
            # Hands and Body start at the same time
            face_shift = abs(hands_face_shift)
            body_shift = 0
            hands_shift = 0
            annotations[0:face_shift, 1:3] = 100
        # END

        # Fill end of vectors with NAN values - body related
        if (self.__body_frames + body_shift) < total_frames:
            body_end = self.__body_frames + body_shift
            annotations[body_end:total_frames, 5:7] = 100

        # If there is information about frame number of videos in vcd
        if self.isNumberOfFrames():
            metadata = self.__vcd.get_metadata()
            if metadata == dict():
                raise RuntimeError("VCD doesn't have metadata information")
            streams_data = metadata["streams"]
            # Fill end of vectors with NAN values - hands related
            hands_frames = streams_data["hands_camera"]["stream_properties"][
                "total_frames"
            ]
            if (hands_frames + hands_shift) < total_frames:
                annotations[hands_frames +
                            hands_shift: total_frames, 3:5] = 100
            # Fill end of vectors with NAN values - face related
            face_frames = streams_data["face_camera"]["stream_properties"][
                "total_frames"
            ]
            if (face_frames + face_shift) < total_frames:
                annotations[face_frames + face_shift: total_frames, 1:3] = 100

        return annotations, validations


    # --- TEMP FEATURE ---#
    # this functions checks if the vcd has the fields of statics annotations
    # and the numbers of frames registered are not 0. If true, static
    # annotations exist
    def isStaticAnnotation(self, staticDict, obj_id):
        exist = True
        vcd_object = self.__vcd.get_object(obj_id)
        for att in staticDict:
            att_exist = keys_exists(
                vcd_object, "object_data", str(att["type"]))
            if not att_exist:
                exist = False
                break
        frames = self.isNumberOfFrames()
        if not (frames and exist):
            exist = False
        return exist

    # --- TEMP FEATURE ---#
    # This function get different values from vcd to keep the consistency when
    # the user saves/creates a new vcd
    # @staticDict: dict of static annotations to get its values from vcd
    # @ctx_id: id of the context (in this case 0)
    def getStaticVector(self, staticDict, ctx_id):
        for x in range(5):
            att = staticDict[x]
            # Get each of the static annotations of the directory from the VCD
            object_vcd = dict(self.__vcd.get_object_data(0, att["name"]))
            att.update({"val": object_vcd["val"]})
        # context
        context = dict(self.__vcd.get_context(ctx_id))["context_data"]["text"]
        staticDict[5].update({"val": context[0]["val"]})
        staticDict[6].update({"val": context[1]["val"]})
        # record_time = context[2]["val"]
        # Annotator id
        meta_data = dict(self.__vcd.get_metadata())
        annotator = meta_data["annotator"]
        staticDict[7].update({"val": annotator})
        # returns:
        # @staticDict: the dict with the values taken from the vcd
        return staticDict

    # --- TEMP FEATURE ---#
    # This function get different values from vcd to keep the consistency when
    # the user saves/creates a new vcd
    # @ctx_id: id of the object (in this case 0)
    def getMetadataVector(self, ctx_id):
        # context
        context = dict(self.__vcd.get_context(ctx_id))["context_data"]["text"]
        record_time = context[2]["val"]
        # frames
        meta_data = dict(self.__vcd.get_metadata())
        face = meta_data["streams"]["face_camera"]["stream_properties"]["total_frames"]
        body = meta_data["streams"]["body_camera"]["stream_properties"]["total_frames"]
        hands = meta_data["streams"]["hands_camera"]["stream_properties"][
            "total_frames"
        ]
        face_mat = meta_data["streams"]["face_camera"]["stream_properties"][
            "intrinsics_pinhole"
        ]["camera_matrix_3x4"]
        body_mat = meta_data["streams"]["body_camera"]["stream_properties"][
            "intrinsics_pinhole"
        ]["camera_matrix_3x4"]
        hands_mat = meta_data["streams"]["hands_camera"]["stream_properties"][
            "intrinsics_pinhole"
        ]["camera_matrix_3x4"]
        # returns:
        # @face_meta: [rgb_video_frames,mat]
        # @body_meta: [date_time,rgb_video_frames,mat]
        # @face_meta: [rgb_video_frames,mat]
        return [face, face_mat], [record_time, body, body_mat], [hands, hands_mat]

    def isNumberOfFrames(self):
        exist = True
        meta_data = dict(self.__vcd.get_metadata())
        face = meta_data["streams"]["face_camera"]["stream_properties"]["total_frames"]
        body = meta_data["streams"]["body_camera"]["stream_properties"]["total_frames"]
        hands = meta_data["streams"]["hands_camera"]["stream_properties"][
            "total_frames"
        ]
        if face == 0 or hands == 0 or body == 0:
            exist = False
        return exist

    """def get_frames_with_action_data_name(self, uid, data_name):
        frames = []
        if uid in self.data['vcd']['actions'] and uid in self.__object_data_names:
            object_ = self.data['vcd']['actions'][uid]
            if data_name in self.__object_data_names[uid]:
                # Now look into Frames
                fis = object_['frame_intervals']
                for fi in fis:
                    fi_tuple = (fi['frame_start'], fi['frame_end'])
                    for frame_num in range(fi_tuple[0], fi_tuple[1]+1):
                        if self.has_frame_object_data_name(frame_num, data_name, uid):
                            frames.append(frame_num)
        return frames

    def get_frames_with_action(self, action_uid):
        frames = []
        if uid_action in self.data['vcd']['actions']: #and uid in self.__object_data_names:
            action_ = self.data['vcd']['actions'][uid]
            if data_name in self.__object_data_names[uid]:
                # Now look into Frames
                fis = action_['frame_intervals']
                for fi in fis:
                    fi_tuple = (fi['frame_start'], fi['frame_end'])
                    for frame_num in range(fi_tuple[0], fi_tuple[1]+1):
                        if self.has_frame_object_data_name(frame_num, data_name, uid):
                            frames.append(frame_num)
        return frames

    def has_frame_action_data_name(self, frame_num, data_name, uid_=-1):
        if frame_num in self.data['vcd']['frames']:
            for uid, obj in self.data['vcd']['frames'][frame_num]['actions'].items():
                if uid_ == -1 or uid == uid_:  # if uid == -1 means we want to loop over all objects
                    for valArray in obj['action_data'].values():
                        for val in valArray:
                            if val['name'] == data_name:
                                return True
        return False"""
