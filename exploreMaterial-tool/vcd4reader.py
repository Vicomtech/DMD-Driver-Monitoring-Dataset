import warnings
from pathlib import Path
import json
import numpy as np
import vcd.core as core
import vcd.types as types
import time



# TODO: get actions and objects per frame

# TODO: funtion to get frame intervals per action or object presence
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


class VcdHandler():
    
    def __init__(self, vcd_file: Path):

        # vcd variables
        self._vcd = None
        self._vcd_file = str(vcd_file)
        self.__vcd_loaded = False

        # If vcd_file exists then load data into vcd object
        if vcd_file.exists():

            # -- Load VCD from file --

            # Create a VCD instance and load file
            self._vcd = core.VCD(file_name=self._vcd_file, validation=False)
            # vcd json is in self._vcd.data

            #Number of frames in video
            self.__full_mosaic_frames= int(self._vcd.get_frame_intervals().get_dict()[0]["frame_end"]) + 1 
            
            #Number of actions in vcd
            self.__num_actions = self._vcd.get_num_actions()
            print("There are %s actions in this VCD" % (self.__num_actions))

            self.__vcd_loaded = True

        else:
            raise RuntimeError("VCD file not found.")

        
    
    #function to get intervals from specific action, providing its name or its uid
    def get_frames_intervals_of_action(self, uid):
        if isinstance(uid, str):
            uid = self.is_action_type_get_uid(uid)[1]
        if uid >=0:
            intervals = self._vcd.data["vcd"]["actions"][str(uid)]["frame_intervals"]
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
        if self._vcd_file:
            for uid in range(self.__num_actions):
                action_type_list.append(self._vcd.data["vcd"]['actions'][str(uid)].get('type'))
        return action_type_list

    # Return flag that indicate if vcd was loaded from file
    def fileLoaded(self):
        return self.__vcd_loaded

    

    # This function reads each stream video uri from the VCD
    def get_videos_uri(self):
        
        streams_data = self._vcd.get_streams()
        general = str(streams_data["general_camera"]["uri"])
        
        return general
    
    def get_frames_number(self):
        return int(self._vcd.get_frame_intervals().get_dict()[0]["frame_end"]) + 1

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

class VcdDMDHandler(VcdHandler):
    def __init__(self, vcd_file: Path):
        super().__init__(vcd_file)

        # Internal Variables initialization
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

        # Check required essential fields inside to be considered loaded
        vcd_metadata = self._vcd.data["vcd"]
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
        self.__face_frames, self.__body_frames, self.__hands_frames = self.get_frame_numbers()

    def get_basic_metadata(self):
        if self._vcd_file:
            
            if dict(self._vcd.get_metadata())["name"]:
                # e.g: gA_1_s1_2019-03-08T09;31;15+01;00
                name = str(dict(self._vcd.get_metadata())["name"]).split("_")
                group = name[0]
                subject = name[1]
                session = name[2]
                if not self._vcd.get_context_data(0, "recordTime") ==None:
                    record_time =self._vcd.get_context_data(0, "recordTime")["val"]
                    record_time = record_time.replace(";", ":")
                    date = record_time.split("T")          
                    # Just get day and hour from the full timestamp        
                    date = date[0]+"-"+date[1].split("+")[0]
                else:
                    #current date
                    named_tuple = time.localtime() # get struct_time
                    date = time.strftime("%Y-%m-%d-%H;%M;%S", named_tuple)
                return group, subject, session, date
            else:
                raise RuntimeError("WARNING: VCD does not have a name")
        else:
            return self.__group, self.__subject, self.__session, self.__date


    # This function allows to get the stream shifts directly from a valid and
    # loaded VCD file
    # Returns:
    # @body_face_shift
    # @hands_face_shift
    # @hands_body_shift
    def get_shifts(self):
        if self.__vcd_loaded:
            stream = self._vcd.get_stream("body_camera")
            body_face_sh = stream['stream_properties']['sync']['frame_shift']

            stream = self._vcd.get_stream("hands_camera")
            hands_face_sh = stream['stream_properties']['sync']['frame_shift']

            hands_body_sh = hands_face_sh - body_face_sh
        else:
            body_face_sh = self.__bf_shift
            hands_face_sh = self.__hf_shift
            hands_body_sh = self.__hb_shift
        return body_face_sh, hands_face_sh, hands_body_sh

    # This function reads each stream video uri from the VCD
    def get_videos_uris(self):
        if self.__vcd_loaded:
            stream = self._vcd.get_stream("face_camera")
            face = str(stream["uri"])
            stream = self._vcd.get_stream("body_camera")           
            body = str(stream["uri"])
            stream = self._vcd.get_stream("hands_camera")
            hands = str(stream["uri"])
        else:
            face = self.__face_uri
            body = self.__body_uri
            hands = self.__hands_uri
        return face, body, hands

    # This function reads the number of frames of the hands video from the VCD
    def get_frame_numbers(self):
        if self.__vcd_loaded:
            stream = self._vcd.get_stream("face_camera")
            face = int(stream["stream_properties"]["total_frames"])
            stream = self._vcd.get_stream("body_camera")           
            body = int(stream["stream_properties"]["total_frames"])
            stream = self._vcd.get_stream("hands_camera")
            hands = int(stream["stream_properties"]["total_frames"])
        else:
            face = self.__face_frames
            body = self.__body_frames
            hands = self.__hands_frames
        return face, body, hands

    def get_intrinsics(self):
        stream = self._vcd.get_stream("face_camera")
        face = stream['stream_properties']['intrinsics_pinhole'][
                'camera_matrix_3x4']
        stream = self._vcd.get_stream("body_camera")           
        body = stream['stream_properties']['intrinsics_pinhole'][
                'camera_matrix_3x4']
        stream = self._vcd.get_stream("hands_camera")
        hands = stream['stream_properties']['intrinsics_pinhole'][
                'camera_matrix_3x4']
        return face, body, hands


    def isNumberOfFrames(self):
        exist = True
        face, body, hands = self.get_frame_numbers()
        if face == 0 or hands == 0 or body == 0:
            exist = False
        return exist


    # this functions checks if the vcd has the fields of statics annotations
    # and the numbers of frames registered are not 0. If true, static
    # annotations exist
    def isStaticAnnotation(self, staticDict, obj_id):
        exist = True
        vcd_object = self._vcd.get_object(obj_id)
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

    # This function get different values from vcd to keep the consistency when
    # the user saves/creates a new vcd
    # @staticDict: dict of static annotations to get its values from vcd
    # @ctx_id: id of the context (in this case 0)
    def getStaticVector(self, staticDict, ctx_id):
        for x in range(5):
            att = staticDict[x]
            # Get each of the static annotations of the directory from the VCD
            object_vcd = dict(self._vcd.get_object_data(0, att["name"]))
            att.update({"val": object_vcd["val"]})
        # context
        context = dict(self._vcd.get_context(ctx_id))["context_data"]["text"]
        staticDict[5].update({"val": context[0]["val"]})
        staticDict[6].update({"val": context[1]["val"]})
        # record_time = context[2]["val"]
        # Annotator id
        meta_data = dict(self._vcd.get_metadata())
        annotator = meta_data["annotator"]
        staticDict[7].update({"val": annotator})
        # returns:
        # @staticDict: the dict with the values taken from the vcd
        return staticDict

    # This function get different values from vcd to keep the consistency when
    # the user saves/creates a new vcd
    # @ctx_id: id of the object (in this case 0)
    def getMetadataVector(self, ctx_id):
        # context
        record_time = 0
        if not self._vcd.get_context_data(ctx_id, "recordTime") ==None:
            record_time =self._vcd.get_context_data(ctx_id, "recordTime")["val"]
        # frames
        face,body,hands = self.get_frame_numbers()
        #intrinsics
        face_mat, body_mat, hands_mat = self.get_intrinsics()
        # returns:
        # @face_meta: [rgb_video_frames,mat]
        # @body_meta: [date_time,rgb_video_frames,mat]
        # @face_meta: [rgb_video_frames,mat]
        return [face, face_mat], [record_time, body, body_mat], [hands, hands_mat]

