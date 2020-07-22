import json
import numpy as np
import vcd.core as core
import vcd.types as types

from pathlib import Path

# dict for changes in structures
dmd_struct = {
    'groups': {
        'grupo1A': 'gA',
        'grupo2A': 'gB',
        'grupo2M': 'gC',
        'grupo3B': 'gD',
        'grupoE': 'gE',
        'grupo4B': 'gF',
        'grupoZ': 'gZ'
    },
    'sessions': {
        'attm': 's1',
        'atts': 's2',
        'reach': 's3',
        'attc': 's4',
        'gaze': 's5',
        'gazec': 's6',
        'drow': 's7',
        'attm2': 's1',
        'atts2': 's2',
        'reach2': 's3',
        'attc2': 's4',
        'gaze2': 's5',
        'gazec2': 's6',
        'drow2': 's7'
    }
}

# Type of annotation
annotate_dict = {
    0: 'unchanged',
    1: 'manual',
    2: 'interval'
}


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
        raise AttributeError('keys_exists() expects dict as first argument.')
    if len(keys) == 0:
        raise AttributeError(
            'keys_exists() expects at least two arguments, one given.')

    _element = element
    for key in keys:
        try:
            _element = _element[key]
        except KeyError:
            return False
    return True


class VcdHandler:

    def __init__(self, vcd_file: Path, dict_file: Path):
        self.uid_driver = None
        self.ont_uid = 0

        self.group = None
        self.subject = None
        self.session = None
        self.date = None

        # Internal Variables and Initialization
        self.__bf_shift = None
        self.__hb_shift = None
        self.__hf_shift = None

        self.__body_frames = None

        self.__vcd = None
        self.__vcd_file = str(vcd_file)
        self.__vcd_loaded = False
        # If vcd_file exists then load data into vcd object
        if vcd_file.exists():
            # Create a VCD instance and load file
            self.__vcd = core.VCD(file_name=self.__vcd_file, validation=True)

            # Check required essential fields inside to be considered loaded
            vcd_data = self.__vcd.get_metadata()
            body_sh_exist = keys_exists(vcd_data, 'streams', 'body_camera',
                                        'stream_properties',
                                        'sync', 'frame_shift')
            hands_sh_exist = keys_exists(vcd_data, 'streams', 'hands_camera',
                                         'stream_properties',
                                         'sync', 'frame_shift')
            # If shifts fields exist then consider the vcd loaded was valid
            if body_sh_exist and hands_sh_exist:
                self.__vcd_loaded = True
            else:
                self.__vcd_loaded = False

            # Get stream shifts
            self.__bf_shift, self.__hf_shift, self.__hb_shift = \
                self.getShifts()
            self.__body_frames = self.getBodyFrames()
        else:
            # Create Empty VCD
            self.__vcd = core.VCD()
            self.__vcd_loaded = False

        # Get dictionary information
        self.__dict_file = Path()
        self.__dicts = None
        self.__dicts_uids = None
        self.__initDicts(dict_file)

    def __initDicts(self, dict_json: Path):
        """
        Obtain the dictionaries from file
        """
        # Check dict_json file exists
        if not dict_json.exists():
            raise RuntimeError(
                "Dictionary file doesn't exist: " + str(Path(dict_json).name))

        # # Get Dictionaries
        # Function to transform int keys to integer if possible
        def keys_to_int(x):
            r = {int(k) if is_string_int(k) else k: v for k, v in x}
            return r

        def dict_to_uid(x):
            r = {int(k) if is_string_int(k) else k: -1 if is_string_int(
                k) else v for k, v in x}
            return r

        with open(str(dict_json), 'r') as dict_file:
            dicts = json.load(dict_file, object_pairs_hook=keys_to_int)
        with open(str(dict_json), 'r') as dict_file:
            dicts_uids = json.load(dict_file, object_pairs_hook=dict_to_uid)

        self.__dict_file = dict_json
        self.__dicts = dicts
        self.__dicts_uids = dicts_uids

    def __add_annotations(self, vcd: core.VCD, annotation_code: int,
                          validation_code: int,
                          group_name: str, group_type: str, dict_name: str,
                          dicts: dict,
                          dicts_uids: dict, frame_num: int):
        assert (self.uid_driver is not None)
        if annotation_code != 100 and annotation_code != 99:
            ann_type = group_name + '/' + dicts[dict_name][annotation_code]
            if dicts_uids[dict_name][annotation_code] == -1:
                # First time: Set flags and save instance uid
                el_uid = -1
                if group_type == 'action':
                    # First Time this action occur
                    el_uid = vcd.add_action("", semantic_type=ann_type,
                                            frame_value=frame_num,
                                            ont_uid=self.ont_uid, stream=None)
                    # Add how the annotation was done
                    ann_type = types.text(name='annotated',
                                          val=annotate_dict[validation_code])
                    vcd.add_action_data(uid=el_uid, action_data=ann_type,
                                        frame_value=frame_num)
                    # Add relation (removed temporally)
                    # r_uid = vcd.add_relation_object_action(name="",
                    # semantic_type="#isActorOf", object_uid=self.uid_driver,
                    # action_uid=el_uid, ont_uid=0)
                elif group_type == 'object':
                    # First Time this object appears
                    o_type = ann_type.split('/')
                    el_uid = vcd.add_object("", o_type[1],
                                            frame_value=frame_num,
                                            ont_uid=self.ont_uid, stream=None)
                    # Add how the annotation was done
                    ann_type = types.text(name='annotated',
                                          val=annotate_dict[validation_code])
                    vcd.add_object_data(uid=el_uid, object_data=ann_type,
                                        frame_value=frame_num)
                elif group_type == 'stream_properties':
                    # Add occlusion as a stream property
                    if 'occlusion' in group_name:
                        stream = dicts[dict_name][annotation_code]
                        occlusion_dict = {
                            'occlusion': {
                                'val': True,
                                'annotated': annotate_dict[validation_code]
                            }
                        }
                        vcd.add_stream_properties(stream_name=stream,
                                                  stream_sync=types.StreamSync(
                                                      frame_vcd=frame_num),
                                                  properties=occlusion_dict)
                        el_uid = -1
                else:
                    raise RuntimeError('Invalid group type: ' + group_type)
                # Update uid of annotation element
                dicts_uids[dict_name][annotation_code] = el_uid
            else:
                # Instance already saved
                if group_type == 'action':
                    # Already an action introduced in VCD
                    inst_uid = dicts_uids[dict_name][annotation_code]
                    vcd.add_action("", ann_type, uid=inst_uid,
                                   frame_value=frame_num,
                                   ont_uid=0, stream=None)
                    # Add how the annotation was done
                    ann_type = types.text(name='annotated',
                                          val=annotate_dict[validation_code])
                    vcd.add_action_data(uid=inst_uid, action_data=ann_type,
                                        frame_value=frame_num)
                elif group_type == 'object':
                    inst_uid = dicts_uids[dict_name][annotation_code]
                    o_type = ann_type.split('/')
                    vcd.add_object("", o_type[1], uid=inst_uid,
                                   frame_value=frame_num,
                                   ont_uid=0, stream=None)
                    # Add how the annotation was done
                    ann_type = types.text(name='annotated',
                                          val=annotate_dict[validation_code])
                    vcd.add_object_data(uid=inst_uid, object_data=ann_type,
                                        frame_value=frame_num)
                else:
                    raise RuntimeError('Invalid group type: ' + group_type)

    # Return flag that indicate if vcd was loaded from file
    def fileLoaded(self):
        return self.__vcd_loaded

    # This function takes as input the annotation and validation vectors and
    # generates a VCD object with the defined structure of DMD actions
    # annotations.
    def updateVCD(self, annotations, validations, statics, metadata,
                  external_structure):
        """ Convert annotations into VCD4 format
        """
        # Init dicts and dicts of elements UIDs
        self.__initDicts(self.__dict_file)

        # if external, basic metadata is taken from the file name
        if external_structure:
            # @metadata: [session, group, sub, date ,sub,timestamp]
            session = metadata[0]
            group = metadata[1]
            subject_id = metadata[2]
            date = metadata[4]

        # if internal, the file name order is different, so the metadata order
        else:
            # Session Data
            # @metadata: [sub, group, session, date ,face_meta, body_meta,
            #             hands_meta]
            subject_id = metadata[0]
            group = dmd_struct["groups"][str(metadata[1])]
            session = dmd_struct["sessions"][str(metadata[2])]
            date = metadata[3]  # '08-10'

        # Initialize var in zero to add something to the vcd
        total_frames_f = 0
        face_intrinsics = np.zeros(12).tolist()

        total_frames_b = self.__body_frames
        body_intrinsics = np.zeros(12).tolist()

        total_frames_h = 0
        hands_intrinsics = np.zeros(12).tolist()

        # But, if there are already static annotations in vcd, take and keep
        # them for the next vcd
        areStatics = bool(statics)
        annotatorID = 0
        age = None
        gender = None
        glasses = None
        drive_freq = None
        experience = None
        weather = None
        setup = None
        date_time = None

        if areStatics:
            # @metadata: [sub, group, session, date, --, face_meta, body_meta,
            #             hands_meta]
            # @face_meta (5): [rgb_video_frames,mat]
            # @body_meta (6): [date_time,rgb_video_frames,mat]
            # @hands_meta (7): [rgb_video_frames,mat]
            total_frames_f = int(metadata[5][0])
            face_intrinsics = metadata[5][1]

            date_time = str(metadata[6][0])
            # Change ":" symbol to ";" for windows correct visualization
            date = date_time.replace(":", ";")

            total_frames_b = int(metadata[6][1])
            body_intrinsics = metadata[6][2]

            total_frames_h = int(metadata[7][0])
            hands_intrinsics = metadata[7][1]

            # Driver Data
            age = int(statics[0]["val"])
            gender = statics[1]["val"]
            glasses = bool(statics[2]["val"])
            drive_freq = statics[3]["val"]
            experience = statics[4]["val"]

            # Context Data
            weather = statics[5]["val"]
            setup = statics[6]["val"]

            # Annotator
            annotatorID = str(statics[7]["val"])

        if self.__bf_shift is None or self.__hb_shift is None or \
                self.__hf_shift is None:
            raise RuntimeError(
                "Shift values have not been set. Run setShifts() function "
                "before")
        body_face_shift = self.__bf_shift
        # hands_body_shift = self.__hb_shift
        hands_face_shift = self.__hf_shift

        # Get total number of lines which is equivalent to total number of
        # frames of mosaic
        assert (len(annotations) == len(validations))
        total_frames = len(annotations)

        # 1.- Create a VCD instance
        vcd = core.VCD()

        # 2.- Add Object for Subject
        self.uid_driver = vcd.add_object(subject_id, "driver", ont_uid=0,
                                         frame_value=(0, total_frames - 1))

        # 3.- VCD Name
        vcd.add_name(group + '_' + subject_id + '_' + session + '_' + date)

        # 4.- Annotator
        if areStatics:
            vcd.add_annotator(annotatorID)

        # 5- Ontology
        vcd.add_ontology('http://dmd.vicomtech.org/ontology')

        # 6.- Cameras
        # Build Uri to video files
        video_root_path = Path() / group / subject_id / session
        face_uri = video_root_path / (group + '_' + subject_id + '_' + session
                                      + '_' + date + '_rgb_face.mp4')
        body_uri = video_root_path / (group + '_' + subject_id + '_' + session
                                      + '_' + date + '_rgb_body.mp4')
        hands_uri = video_root_path / (group + '_' + subject_id + '_' + session
                                       + '_' + date + '_rgb_hands.mp4')

        face_video_descr = 'Frontal face looking camera'
        body_video_descr = 'Side body looking camera'
        hands_video_descr = 'Hands and wheel looking camera'
        vcd.add_stream('face_camera', str(face_uri), face_video_descr,
                       core.StreamType.camera)
        vcd.add_stream('body_camera', str(body_uri), body_video_descr,
                       core.StreamType.camera)
        vcd.add_stream('hands_camera', str(hands_uri), hands_video_descr,
                       core.StreamType.camera)

        # 7.- Stream Properties
        #       Real Intrinsics of cameras
        vcd.add_stream_properties(stream_name='face_camera',
                                  properties={
                                      'cam_module': 'Intel RealSense D415',
                                      'total_frames': total_frames_f,
                                  },
                                  stream_sync=types.StreamSync(frame_shift=0),
                                  intrinsics=types.IntrinsicsPinhole(
                                      width_px=1280, height_px=720,
                                      camera_matrix_3x4=face_intrinsics)
                                  )
        vcd.add_stream_properties(stream_name='body_camera',
                                  properties={
                                      'camera_module': 'Intel RealSense D435',
                                      'total_frames': total_frames_b,
                                  },
                                  stream_sync=types.StreamSync(
                                      frame_shift=body_face_shift),
                                  intrinsics=types.IntrinsicsPinhole(
                                      width_px=1280, height_px=720,
                                      camera_matrix_3x4=body_intrinsics)
                                  )
        vcd.add_stream_properties(stream_name='hands_camera',
                                  properties={
                                      'camera_module': 'Intel RealSense D415',
                                      'total_frames': total_frames_h,
                                  },
                                  stream_sync=types.StreamSync(
                                      frame_shift=hands_face_shift),
                                  intrinsics=types.IntrinsicsPinhole(
                                      width_px=1280, height_px=720,
                                      camera_matrix_3x4=hands_intrinsics)
                                  )

        if areStatics:
            # 8.- Add Context of Recording session
            last_frame = total_frames - 1
            ctx_txt = 'recording_context'
            rec_context_uid = vcd.add_context(name='', semantic_type=ctx_txt,
                                              frame_value=(0, last_frame))
            vcd.add_context_data(rec_context_uid,
                                 types.text(name='weather', val=weather))
            vcd.add_context_data(rec_context_uid,
                                 types.text(name='setup', val=setup))
            vcd.add_context_data(rec_context_uid,
                                 types.text(name='recordTime', val=date_time))

            # 9.- Add Driver static properties
            vcd.add_object_data(self.uid_driver,
                                types.num(name='age', val=age))
            vcd.add_object_data(self.uid_driver,
                                types.text(name='gender', val=gender))
            vcd.add_object_data(self.uid_driver,
                                types.boolean(name='glasses', val=glasses))
            vcd.add_object_data(self.uid_driver,
                                types.text(name='experience', val=experience))
            vcd.add_object_data(self.uid_driver,
                                types.text(name='drive_freq', val=drive_freq))

        # 10.- Save annotation and validation vectors in VCD format
        annotation_groups = self.__dicts['dict_names'].items()
        annotation_types = self.__dicts['dict_types'].items()
        for frame_num, (ann_line, valid_line) in enumerate(
                zip(annotations, validations)):
            # Loop for each frame
            # Get the annotations and verification labels
            assert (len(ann_line) == len(valid_line))

            # 10.2.- Adding distraction-related actions and objects
            for item_code, item_type in zip(annotation_groups,
                                            annotation_types):
                assert (item_code[0] == item_type[0])
                annotation_code = int(ann_line[item_code[0]])
                validation_code = int(valid_line[item_code[0]])
                group_name = item_code[1]
                group_type = item_type[1]
                dict_name = 'A' + str(item_code[0]) + '_dict'
                self.__add_annotations(vcd, annotation_code, validation_code,
                                       group_name,
                                       group_type, dict_name, self.__dicts,
                                       self.__dicts_uids,
                                       frame_num)
        # Update class variable __vcd with newly created object
        self.__vcd = vcd
        return True

    # This function only saves the stored VCD object in the external file
    def saveVCD(self, pretty=False):
        # Save into file
        self.__vcd.save(self.__vcd_file, pretty=pretty)

    # This function is handy to perform simultanoeusly the updating and saving
    # of the VCD object
    # @annotations: annotations array
    # @validations: validations array
    # @statics: dict with values
    # @metadata: array with values from metadata file
    # @external_structure: flag, True if user is in external structure
    # @pretty
    def updateAndSaveVCD(self, annotations, validations, statics, metadata,
                         external_structure, pretty=False):
        # Update VCD
        self.updateVCD(annotations, validations, statics, metadata, 
                       external_structure)

        # Save VCD
        self.saveVCD(pretty)
        self.__vcd_loaded = True
    # This function allows to set the stream shifts and store in the internal
    # variables to be used when saving the VCD file
    def setShifts(self, body_face_shift=None, hands_face_shift=None,
                  hands_body_shift=None, ):
        if (body_face_shift is None and hands_face_shift is None) or \
                (body_face_shift is None and hands_body_shift is None) or \
                (hands_face_shift is None and hands_body_shift is None):
            raise RuntimeError('At least two variables must be passed')

        self.__bf_shift = body_face_shift
        self.__hf_shift = hands_face_shift
        self.__hb_shift = hands_body_shift
        if body_face_shift is None:
            self.__bf_shift = self.__hf_shift - self.__hb_shift
        if hands_face_shift is None:
            self.__hf_shift = self.__hb_shift + self.__bf_shift
        if hands_body_shift is None:
            self.__hb_shift = self.__hf_shift - self.__bf_shift

    # This function is to set the number of frames of the body video to the VCD
    # @bodyFrames: number of frames (sent from display_annotation where is
    #              len(ann))
    def setBodyFrames(self, bodyFrames):
        self.__body_frames = int(bodyFrames)

    # This function reads the number of frames of the hands video from the VCD
    def getBodyFrames(self):
        if self.__vcd_loaded:
            metadata = self.__vcd.get_metadata()
            if metadata == dict():
                raise RuntimeError("VCD doesn't have metadata information")
            streams_data = metadata['streams']
            body = streams_data['body_camera']['stream_properties'][
                'total_frames']

        else:
            body = self.__body_frames
        return body

    # This function allows to get the stream shifts directly from a valid and
    # loaded VCD file
    # Returns:
    # @body_face_shift
    # @hands_face_shift
    # @hands_body_shift
    def getShifts(self):
        if self.__vcd_loaded:
            metadata = self.__vcd.get_metadata()
            if metadata == dict():
                raise RuntimeError("VCD doesn't have metadata information")

            streams_data = metadata['streams']
            body_face_sh = \
                streams_data['body_camera']['stream_properties']['sync'][
                    'frame_shift']
            hands_face_sh = \
                streams_data['hands_camera']['stream_properties']['sync'][
                    'frame_shift']
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
        total_frames = frame_interval[-1]['frame_end'] + 1
        total_levels = len(self.__dicts['dict_names'])
        # initial values for annotations: --,looking,--,both,--,--,safe drive
        annotations = np.array(
            [[99, 0, 99, 0, 99, 99, 0] for _ in range(total_frames)])
        validations = np.array(
            [[0 for _ in range(total_levels)] for _ in range(total_frames)])

        # Fill annotation data
        annotation_groups = self.__dicts['dict_names'].items()
        annotation_types = self.__dicts['dict_types'].items()

        # Fill Data of annotation and validation vectors
        # Loop over all the annotation levels searching for annotated frame
        # intervals
        for level_code, level_type in zip(annotation_groups, annotation_types):
            assert (level_code[0] == level_type[0])
            dict_name = 'A' + str(level_code[0]) + '_dict'
            level_labels = self.__dicts[dict_name].items()
            assert (len(level_labels) > 0)
            # Loop over each level labels
            for label_id, label_str in level_labels:
                if label_id == 99 or label_id == 100:
                    continue
                if level_type[1] == 'action' or level_type[1] == 'object':
                    ann_type = None
                    elem_type = None
                    if level_type[1] == 'action':
                        ann_type = level_code[1] + '/' + label_str
                        elem_type = core.ElementType.action
                    elif level_type[1] == 'object':
                        ann_type = label_str
                        elem_type = core.ElementType.object
                    l_uids = vcd.get_elements_of_type(element_type=elem_type,
                                                      semantic_type=ann_type)
                    # Only allowed 0 or 1 action type in VCD
                    assert (0 <= len(l_uids) <= 1)
                    # Loop over all elements of specific type
                    for uid in l_uids:
                        l_fi = vcd.get_frame_intervals_of_element(
                            element_type=elem_type, uid=uid)
                        # Loop over frame intervals
                        for fi in l_fi:
                            start = fi['frame_start']
                            end = fi['frame_end'] + 1
                            annotations[start:end, level_code[0]] = label_id
                            # Get annotation method (validations)
                            for f_num in range(start, end):
                                f = vcd.get_frame(frame_num=f_num)
                                lev = level_type[1]
                                if keys_exists(f, lev + 's', uid,
                                               lev + '_data', 'text'):
                                    # Search data of annotation method
                                    data = f[lev + 's'][uid][lev + '_data'][
                                        'text']
                                    for d in data:
                                        if d['name'] == 'annotated':
                                            val_id = [k for k, v in
                                                      annotate_dict.items()
                                                      if v == d['val']]
                                            cod = level_code[0]
                                            validations[f_num, cod] = val_id[0]

                elif level_type[1] == 'stream_properties':
                    # Only way is to read frame by frame the stream_properties
                    # field
                    for f_num in range(total_frames):
                        f = vcd.get_frame(frame_num=f_num)
                        if keys_exists(f, 'frame_properties', 'streams',
                                       label_str,
                                       'stream_properties', 'occlusion'):
                            a = f['frame_properties']['streams'][label_str][
                                'stream_properties']
                            ann_str = a['occlusion']['annotated']
                            annotations[f_num, level_code[0]] = label_id
                            val_id = [k for k, v in annotate_dict.items() if
                                      v == ann_str]
                            assert (len(val_id) == 1)
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
            streams_data = metadata['streams']
            # Fill end of vectors with NAN values - hands related
            hands_frames = streams_data['hands_camera']['stream_properties'][
                'total_frames']
            if (hands_frames + hands_shift) < total_frames:
                annotations[hands_frames + hands_shift:total_frames, 3:5] = 100
            # Fill end of vectors with NAN values - face related
            face_frames = streams_data['face_camera']['stream_properties'][
                'total_frames']
            if (face_frames + face_shift) < total_frames:
                annotations[face_frames + face_shift:total_frames, 1:3] = 100

        return annotations, validations

    # --- TEMP FEATURE ---#
    # this functions checks if the vcd has the fields of statics annotations
    # and the numbers of frames registered are not 0. If true, static
    # annotations exist
    def isStaticAnnotation(self, staticDict, obj_id):
        exist = True
        vcd_object = self.__vcd.get_object(obj_id)
        for att in staticDict:
            att_exist = keys_exists(vcd_object, 'object_data',
                                    str(att["type"]))
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
        face = meta_data["streams"]["face_camera"]["stream_properties"][
            "total_frames"]
        body = meta_data["streams"]["body_camera"]["stream_properties"][
            "total_frames"]
        hands = meta_data["streams"]["hands_camera"]["stream_properties"][
            "total_frames"]
        face_mat = meta_data["streams"]["face_camera"]["stream_properties"][
            "intrinsics_pinhole"]["camera_matrix_3x4"]
        body_mat = meta_data["streams"]["body_camera"]["stream_properties"][
            "intrinsics_pinhole"]["camera_matrix_3x4"]
        hands_mat = meta_data["streams"]["hands_camera"]["stream_properties"][
            "intrinsics_pinhole"]["camera_matrix_3x4"]
        # returns:
        # @face_meta: [rgb_video_frames,mat]
        # @body_meta: [date_time,rgb_video_frames,mat]
        # @face_meta: [rgb_video_frames,mat]
        return [face, face_mat], [record_time, body, body_mat], \
               [hands, hands_mat]

    def isNumberOfFrames(self):
        exist = True
        meta_data = dict(self.__vcd.get_metadata())
        face = meta_data["streams"]["face_camera"]["stream_properties"][
            "total_frames"]
        body = meta_data["streams"]["body_camera"]["stream_properties"][
            "total_frames"]
        hands = meta_data["streams"]["hands_camera"]["stream_properties"][
            "total_frames"]
        if face == 0 or hands == 0 or body == 0:
            exist = False
        return exist
