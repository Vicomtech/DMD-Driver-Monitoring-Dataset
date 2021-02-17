import warnings
from pathlib import Path

import numpy as np

import vcd.core as core
import vcd.types as types
# Import local class to get tato configuration and paths
from setUp import ConfigTato

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


def keys_exist(element: dict, *keys):
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


class VcdHandler(object):
    def __init__(self, setUpManager: ConfigTato):
        self._setUpManager = setUpManager

        # Get TaTo annotation mode
        self._annotation_mode = self._setUpManager._annotation_mode

        # Internal Variables
        self._vcd = None
        self._vcd_file = self._setUpManager._vcd_file_path
        self._vcd_loaded = False

        # Get dictionary information
        self._dict_file = self._setUpManager._config_json

        self._dicts, self._annotation_levels, \
            self._default_levels, self._annotation_types, \
            self._level_labels, self._camera_dependencies, \
            self._total_levels = self._setUpManager.get_annotation_config()

        # Dictionary that contains the
        self._statics_dict = self._setUpManager.get_statics_dict()

        self._annotation_levels = self._annotation_levels.items()
        self._default_levels = self._default_levels.items()
        self._annotation_types = self._annotation_types.items()

        # If vcd_file exists then load data from file
        if self._vcd_file.exists():
            print("VCD exists")
            # Create a VCD instance and load file
            self._vcd = core.VCD(file_name=self._vcd_file, validation=False)
            self._vcd_loaded = True
        else:
            # Create Empty VCD
            self._vcd = core.VCD()
            self._vcd_loaded = False

    
    # This function adds the annotations and validation vectors to the provided
    # VCD object.
    # IMPORTANT: Call to this function should be done after defining all the
    # available streams for annotation, as this function could write
    # stream_properties
    def add_annotations(self, vcd: core.VCD, annotations, validations, ontology_uid: int):

        # Loop over all annotation levels to add the elements present in
        # annotation vector
        for level_code, level_type in zip(self._annotation_levels,
                                          self._annotation_types):
            level_idx = int(level_code[0])
            level_name = level_code[1]
            level_type_idx = int(level_type[0])
            level_type_name = level_type[1]

            assert (level_idx == level_type_idx)
            assert (len(self._level_labels) > 0)

            level_labels = self._level_labels[level_idx]

            for label_idx, label_name in level_labels.items():
                # Do not save NaN and Empty annotations
                if label_idx == 100 or label_idx == 99:
                    continue

                annotations = np.array(annotations)
                validations = np.array(validations)
                # Compute frame number of all occurrences of label_idx
                f_list = np.where(annotations[:, level_idx] == label_idx)[0]
                v_list = validations[f_list, level_idx]

                #From frames with lable_idx, select frames with validation 0, 1 and 2
                v_list_0 = f_list[np.where(v_list==0)]
                v_list_1 = f_list[np.where(v_list==1)]
                v_list_2 = f_list[np.where(v_list==2)]
                
                #If there are not annotated frames, then all validations are 0 (unchanged)
                if len(f_list)==0:
                    v_list_0  = validations[f_list, level_idx]

                # Make intervals of frames
                f_interv = []
                f_interv = list(self.interval_extract(f_list))

                #Make intervals of validation
                v_0_intervals=list(self.interval_extract(v_list_0))
                v_1_intervals=list(self.interval_extract(v_list_1))
                v_2_intervals =list(self.interval_extract(v_list_2))
                

                # ## Add the elements
                # Add an action
                if level_type_name == 'action':
                    action_type = level_name + '/' + label_name
                    if len(f_interv)>0:
                        el_uid = vcd.add_action("", semantic_type=action_type,
                                                frame_value=f_interv,
                                                ont_uid=ontology_uid)
                    

                    # Add how the annotation was done
                    if len(v_0_intervals)>0:
                        #Intervals with validation 0
                        validation_data = types.text(name='annotated', val=annotate_dict[0])
                        vcd.add_action_data(uid=el_uid,
                                            action_data=validation_data,
                                            frame_value=v_0_intervals)
                    if len(v_1_intervals)>0:
                        #Intervals with validation 1
                        validation_data = types.text(name='annotated', val=annotate_dict[1])
                        vcd.add_action_data(uid=el_uid,
                                            action_data=validation_data,
                                            frame_value=v_1_intervals)
                    if len(v_2_intervals)>0:
                        #Intervals with validation 2
                        validation_data = types.text(name='annotated', val=annotate_dict[2])
                        vcd.add_action_data(uid=el_uid,
                                            action_data=validation_data,
                                            frame_value=v_2_intervals)
                                            
                # Add an object
                elif level_type_name == 'object':
                    object_type = label_name
                    if len(f_interv)>0:
                        el_uid = vcd.add_object("", semantic_type=object_type,
                                                frame_value=f_interv,
                                                ont_uid=ontology_uid)
                        # Add how the annotation was done
                        #Intervals with validation 0
                        validation_data = types.text(name='annotated',
                                                        val=annotate_dict[0])
                        vcd.add_object_data(uid=el_uid,
                                            object_data=validation_data,
                                            frame_value=v_0_intervals)
                        #Intervals with validation 1
                        validation_data = types.text(name='annotated',
                                                        val=annotate_dict[1])
                        vcd.add_object_data(uid=el_uid,
                                            object_data=validation_data,
                                            frame_value=v_1_intervals)
                        #Intervals with validation 2
                        validation_data = types.text(name='annotated',
                                                        val=annotate_dict[2])
                        vcd.add_object_data(uid=el_uid,
                                            object_data=validation_data,
                                            frame_value=v_2_intervals)
                # Add stream properties
                elif level_type_name == 'stream_properties':
                    # When a level is defined as stream_properties, the annotations
                    # will always be considered as boolean, since TaTo only allows
                    # the presence or absence of that property.
                    # E.g. occlusion can only be True or False
                    if len(f_interv)>0:
                        for i, frame_num in enumerate(f_list):
                            
                            stream = label_name
                            if stream == "--":
                                continue
                            property_dict = {
                                level_name: {
                                    'val': True,
                                    'annotated': annotate_dict[int(v_list[i])]
                                }
                            }
                            vcd.add_stream_properties(stream_name=stream,
                                                    stream_sync=types.StreamSync(
                                                        frame_vcd=int(frame_num)),
                                                    properties=property_dict)
                else:
                    raise RuntimeError(
                        'Invalid group type: ' + level_type_name)
        return vcd

    #This functions gets a list of numbers (frames) and make intervals. 
    # Useful for add_annotations() function
    def interval_extract(self, list):
        if len(list) <= 0:
            return []
        #list = sorted(set(list))
        range_start = previous_number = list[0]
        for number in list[1:]:
            if number == previous_number + 1:
                previous_number = number
            else:
                yield [int(range_start), int(previous_number)]
                range_start = previous_number = number
        yield [int(range_start), int(previous_number)]

    # Return flag that indicate if vcd was loaded from file
    def file_loaded(self):
        return self._vcd_loaded

    # This function only saves the stored VCD object in the external file
    def save_vcd(self, pretty=False):
        # Save into file
        self._vcd.save(self._vcd_file, pretty=pretty)

    def update_vcd(self, annotations, validations):
        """ From an empty VCD, the annotation and validation vectors are
            parsed to VCD format.

        """
        # Get total number of lines which is equivalent to total number of
        # frames input video
        assert (len(annotations) == len(validations))
        total_frames = len(annotations)

        # 1.- Create VCD only with annotations and validations
        new_vcd = core.VCD()

        # 2.- VCD Name
        vcd_name = Path(self._vcd_file).stem
        new_vcd.add_name(str(vcd_name))

        # 3.- Camera
        # Build Uri to video files
        general_uri = self._setUpManager._video_file_path
        general_video_descr = 'Unique general camera'
        new_vcd.add_stream('general_camera', str(general_uri), general_video_descr,
                       core.StreamType.camera)
        # 4.- Stream Properties
        # Real Intrinsics of camera
        new_vcd.add_stream_properties(stream_name='general_camera',
                                  properties={
                                      'total_frames': total_frames,
                                  })
        # 5.- Add annotations and validations
        vcd = self.add_annotations(new_vcd,annotations, validations,0)

        # Update current VCD with newly created VCD
        self._vcd = vcd

    # This function is handy to perform simultaneously the updating and saving
    # of the VCD object
    # @annotations: annotations array
    # @validations: validations array
    # @statics: dict with values
    # @metadata: array with values from metadata file
    # @pretty
    def update_save_vcd(self, annotations, validations, pretty=False):
        # Update VCD
        self.update_vcd(annotations, validations)

        # Save VCD
        self.save_vcd(pretty)
        self._vcd_loaded = True

    # This function extracts the annotation information from the vcd object
    # Returns:
    # @annotations: A matrix consisting of the annotation labels for each of
    #               the levels in dict
    # @validations: A matrix consisting of the validation method while
    #               annotating
    def get_annotation_vectors(self):
        # Get a copy of VCD object
        vcd = self._vcd

        if vcd is None:
            raise RuntimeError("Couldn't get VCD data")

        # Create annotation and validation vectors
        frame_interval = vcd.get_frame_intervals().fis_dict
        total_frames = frame_interval[-1]['frame_end'] + 1
        # Fill with initial default values
        annotations = np.array([[val for x, val in self._default_levels]
                                for _ in range(total_frames)])
        validations = np.array([[0 for _ in range(self._total_levels)]
                                for _ in range(total_frames)])

        # Fill Data of annotation and validation vectors
        # Loop over all the annotation levels searching for annotated frame
        # intervals
        for level_code, level_type in zip(self._annotation_levels,
                                          self._annotation_types):
            level_idx = level_code[0]
            level_name = level_code[1]
            level_type_idx = level_type[0]
            level_type_name = level_type[1]

            assert (level_idx == level_type_idx)
            assert (len(self._level_labels) > 0)

            # Loop over each level labels
            levels_list = self._level_labels[level_idx].items()
            for label_id, label_str in levels_list:
                if label_id == 99 or label_id == 100:
                    continue
                if level_type[1] == 'action' or level_type[1] == 'object':
                    ann_type = None
                    elem_type = None
                    if level_type[1] == 'action':
                        ann_type = level_name + '/' + label_str
                        elem_type = core.ElementType.action
                    elif level_type[1] == 'object':
                        ann_type = label_str
                        elem_type = core.ElementType.object
                    l_uids = vcd.get_elements_of_type(element_type=elem_type,
                                                      semantic_type=ann_type)
                    # Only allowed 0 or 1 action type in VCD
                    assert (0 <= len(l_uids) <= 1)
                    # Loop over all elements of specific type
                    if len(l_uids) == 0:
                        continue
                    uid = l_uids[0]
                    l_fi = vcd.get_element_frame_intervals(elem_type, uid=uid)
                    # Loop over frame intervals
                    for fi in l_fi.fis_dict:
                        start = fi['frame_start']
                        end = fi['frame_end'] + 1
                        annotations[start:end, level_idx] = label_id
                        # Get annotation method (validations)
                        for f_num in range(start, end):
                            d = vcd.get_element_data(elem_type, uid,
                                                     'annotated', f_num)
                            val_id = [k for k, v in annotate_dict.items()
                                      if v == d['val']]
                            validations[f_num, level_idx] = val_id[0]
                elif level_type[1] == 'stream_properties':
                    # Only way is to read frame by frame the stream_properties
                    for f_num in range(total_frames):
                        f = vcd.get_frame(frame_num=f_num)
                        if keys_exist(f, 'frame_properties', 'streams',
                                      label_str, 'stream_properties',
                                      level_name):
                            a = f['frame_properties']['streams'][label_str][
                                'stream_properties']
                            ann_str = a[level_name]['annotated']
                            val_id = [k for k, v in annotate_dict.items()
                                      if
                                      v == ann_str]
                            assert (len(val_id) == 1)
                            annotations[f_num, level_idx] = label_id
                            validations[f_num, level_idx] = val_id[0]

        return annotations, validations

# Class to handle specific fields in VCD when the DMD dataset is used


class DMDVcdHandler(VcdHandler):

    def __init__(self, setUpManager):
        super().__init__(setUpManager)

        # Ontology
        self.ont_uid = 0

        # VCD metadata
        self.group = self._setUpManager._group
        self.subject = self._setUpManager._subject
        self.session = self._setUpManager._session
        self.date = self._setUpManager._date
        if self._setUpManager._external_struct:
            self.date = self._setUpManager._timestamp

        # Stream metadata
        self._bf_shift = None
        self._hb_shift = None
        self._hf_shift = None

        self._b_frames = None
        self._f_frames = None
        self._h_frames = None

        self._f_intrinsics = np.zeros(12).tolist()
        self._b_intrinsics = np.zeros(12).tolist()
        self._h_intrinsics = np.zeros(12).tolist()

        # Driver statics
        self.uid_driver = None
        self.age = None
        self.gender = None
        self.glasses = None
        self.drive_freq = None
        self.experience = None

        # Recording context
        self.weather = None
        self.setup = None
        self.timestamp = None

        # Other metadata
        self.annotatorID = -1

        # If a VCD file was loaded,
        # Try to extract metadata and statics
        if self._vcd_loaded:
            # Get values of shifts from loaded VCD
            self._bf_shift, self._hf_shift, self._hb_shift = self.get_shifts()

            # Get values of stream frame number from loaded VCD
            self._f_frames, self._b_frames, self._h_frames = self.get_frames()

            # Get stream intrinsics from loaded VCD
            self._f_intrinsics, self._b_intrinsics, self._h_intrinsics = \
                self.get_intrinsics(self._vcd)

    def add_annotationsx(self, vcd: core.VCD, annotations, validations, ontology_uid: int):
        return super().add_annotations(vcd, annotations, validations, ontology_uid)

    def save_vcd_dmd(self, pretty=False):
        # Save into file
        self._vcd.save(self._vcd_file, pretty=pretty)

    def update_vcd(self, annotations, validations, statics=None, metadata=None):
        """ Convert annotations into VCD4 format
        """
        # But, if there are already static annotations in vcd, take and keep
        # them for the next vcd
        areStatics = bool(statics)
        isMetadata = bool(metadata)

        if isMetadata:
            # @metadata: [face_meta, body_meta,hands_meta]
            # @face_meta (5): [rgb_video_frames,mat]
            # @body_meta (6): [date_time,rgb_video_frames,mat]
            # @hands_meta (7): [rgb_video_frames,mat]
            self._f_frames = int(metadata[0][0])
            self._f_intrinsics = metadata[0][1]

            self.timeStamp = str(metadata[1][0])
            # Change ":" symbol to ";" for windows correct visualization
            self.timeStamp.replace(":", ";")

            self._b_frames = int(metadata[1][1])
            self._b_intrinsics = metadata[1][2]

            self._h_frames = int(metadata[2][0])
            self._h_intrinsics = metadata[2][1]

        if areStatics:
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

        if self._bf_shift is None or self._hb_shift is None or \
                self._hf_shift is None:
            raise RuntimeError(
                "Shift values have not been set. Run set_shifts() function "
                "before")
        body_face_shift = self._bf_shift
        # hands_body_shift = self.__hb_shift
        hands_face_shift = self._hf_shift

        # Get total number of lines which is equivalent to total number of
        # frames of mosaic
        assert (len(annotations) == len(validations))
        total_frames = len(annotations)

        # 1.- Create a VCD instance
        vcd = core.VCD()

        # 2.- Add Object for Subject
        self.uid_driver = vcd.add_object(self.subject, "driver", ont_uid=0,
                                         frame_value=(0, total_frames - 1))

        # 3.- VCD Name
        vcd.add_name(self.group + '_' + self.subject + '_' +
                     self.session + '_' + self.date + '_' +
                     self._annotation_mode)

        # 4.- Annotator
        if areStatics:
            vcd.add_annotator(annotatorID)

        # 5- Ontology
        vcd.add_ontology('http://dmd.vicomtech.org/ontology')

        # 6.- Cameras
        # Build Uri to video files
        if self._setUpManager._external_struct:
            video_root_path = Path() / self.group / self.subject / self.session
            face_uri = video_root_path / (self.group + '_' + self.subject + '_' +
                                        self.session + '_' + self.date +
                                        '_rgb_face.mp4')
            body_uri = video_root_path / (self.group + '_' + self.subject + '_' +
                                        self.session + '_' + self.date +
                                        '_rgb_body.mp4')
            hands_uri = video_root_path / (self.group + '_' + self.subject + '_' +
                                        self.session + '_' + self.date +
                                        '_rgb_hands.mp4')
        else:
            video_root_path = Path() / self.group / self.date / self.subject
            face_uri = video_root_path / (self.subject + '_' +self.session + '_' + 'face' + '_' + self.date +'.mp4')
            body_uri = video_root_path / (self.subject + '_' +self.session + '_' + 'body' + '_' + self.date +'.mp4')
            hands_uri = video_root_path / (self.subject + '_' +self.session + '_' + 'hands' + '_' + self.date +'.mp4')           

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
                                      'total_frames': self._f_frames,
                                  },
                                  stream_sync=types.StreamSync(frame_shift=0),
                                  intrinsics=types.IntrinsicsPinhole(
                                      width_px=1280, height_px=720,
                                      camera_matrix_3x4=self._f_intrinsics)
                                  )
        vcd.add_stream_properties(stream_name='body_camera',
                                  properties={
                                      'camera_module': 'Intel RealSense D435',
                                      'total_frames': self._b_frames,
                                  },
                                  stream_sync=types.StreamSync(
                                      frame_shift=body_face_shift),
                                  intrinsics=types.IntrinsicsPinhole(
                                      width_px=1280, height_px=720,
                                      camera_matrix_3x4=self._b_intrinsics)
                                  )
        vcd.add_stream_properties(stream_name='hands_camera',
                                  properties={
                                      'camera_module': 'Intel RealSense D415',
                                      'total_frames': self._h_frames,
                                  },
                                  stream_sync=types.StreamSync(
                                      frame_shift=hands_face_shift),
                                  intrinsics=types.IntrinsicsPinhole(
                                      width_px=1280, height_px=720,
                                      camera_matrix_3x4=self._h_intrinsics)
                                  )

        if areStatics or isMetadata:
            # 8.- Add Context of Recording session
            last_frame = total_frames - 1
            ctx_txt = 'recording_context'
            rec_context_uid = vcd.add_context(name='', semantic_type=ctx_txt,
                                              frame_value=(0, last_frame))
            
            if areStatics:
                vcd.add_context_data(rec_context_uid,
                                     types.text(name='weather', val=weather))
                vcd.add_context_data(rec_context_uid,
                                     types.text(name='setup', val=setup))

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
            if isMetadata:
                vcd.add_context_data(rec_context_uid,
                                     types.text(name='recordTime',
                                                val=self.timeStamp))

        # 10.- Save annotation and validation vectors in VCD format
        # Perform general update
        new_vcd = self.add_annotationsx(vcd, annotations, validations, self.ont_uid)

        # Update class variable __vcd with newly created object
        self._vcd = new_vcd
        return True

    # This function is handy to perform simultaneously the updating and saving
    # of the VCD object
    # @annotations: annotations array
    # @validations: validations array
    # @statics: dict with values
    # @metadata: array with values from metadata file
    # @pretty
    def update_save_vcd(self, annotations, validations, statics=None,
                        metadata=None, pretty=False):
        # Update VCD
        self.update_vcd(annotations, validations, statics, metadata)

        # Save VCD
        self.save_vcd_dmd(pretty)
        self._vcd_loaded = True

    # Return flag that indicate if vcd was loaded from file
    def file_loaded(self):
        return self._vcd_loaded

    # Function to check the existence of total_frames field in VCD given a
    # stream name
    def stream_frames_exist(self,_vcd, stream_name: str):
        frame_exists = False
        if _vcd.has_stream(stream_name):
            stream = _vcd.get_stream(stream_name)
            frame_exists = keys_exist(stream, 'stream_properties',
                                      'total_frames')
        else:
            warnings.warn('WARNING: stream ' + stream_name + ' is not present '
                          'in input VCD')
        return frame_exists

    # Function to check the existence of frame_shift field in VCD given a
    # stream name
    def shift_exist(self, _vcd,stream_name: str):
        shift_exists = False
        if _vcd.has_stream(stream_name):
            stream = _vcd.get_stream(stream_name)
            shift_exists = keys_exist(stream, 'stream_properties', 'sync',
                                      'frame_shift')
        else:
            warnings.warn('WARNING: stream ' + stream_name + ' is not present '
                          'in input VCD')
        return shift_exists

    # Function to check the existence of camera_matrix field in VCD given a
    # stream name
    def cam_matrix_exist(self,_vcd, stream_name: str):
        matrix_exist = False
        if _vcd.has_stream(stream_name):
            stream = _vcd.get_stream(stream_name)
            matrix_exist = keys_exist(stream, 'stream_properties',
                                      'intrinsics_pinhole',
                                      'camera_matrix_3x4')
        else:
            warnings.warn('WARNING: stream ' + stream_name + ' is not present '
                          'in input VCD')
        return matrix_exist

    # Function to check the existence of static fields of driver in VCD
    def driver_statics_exist(self):
        # Check in VCD the existence of the following statics variables
        driver_uid = self._vcd.get_object_uid_by_name(str(self.subject))
        elem_type = core.ElementType.object
        driver_list = self._vcd.get_elements_of_type(elem_type, "driver")

        # check if uid exists in list of objects of type 'driver'
        if driver_uid in driver_list:
            age_data = self._vcd.get_object_data(driver_uid, 'age')

            statics_exist = True
        else:
            statics_exist = False

        return statics_exist

        

    # This function reads the number of frames of a stream from the VCD object
    # Returns:
    #   stream_frames: number of frames of the requested stream
    def get_stream_frames_in_vcd(self, _vcd, stream_name: str):
        if self.stream_frames_exist(_vcd,stream_name):
            stream = _vcd.get_stream(stream_name)
            stream_frames = stream['stream_properties']['total_frames']
            return stream_frames
        else:
            raise RuntimeError("VCD: doesn't have frame number information for "
                               "stream: " + stream_name)

    # This function reads the shift of a stream from the VCD object
    # Returns:
    #   shift_in_vcd: shift of the given stream
    def get_shift_in_vcd(self, _vcd,stream_name: str):
        if self.shift_exist(_vcd,stream_name):
            stream = _vcd.get_stream(stream_name)
            shift_in_vcd = stream['stream_properties']['sync']['frame_shift']
            return shift_in_vcd
        else:
            raise RuntimeError("VCD: doesn't have shift information for "
                               "stream: " + stream_name)

    # This function reads the camera matrix of a stream from the VCD object
    # Returns:
    #   matrix_in_vcd: camera matrix of the given stream
    def get_cam_matrix_in_vcd(self, _vcd,stream_name: str):
        if self.cam_matrix_exist(_vcd,stream_name):
            stream = _vcd.get_stream(stream_name)
            matrix_in_vcd = stream['stream_properties']['intrinsics_pinhole'][
                'camera_matrix_3x4']
            return matrix_in_vcd
        else:
            raise RuntimeError("VCD: doesn't have shift information for "
                               "stream: " + stream_name)

    # This function returns all the three stream frame numbers
    # If a vcd is loaded, this function will get the numbers from the vcd object
    # If no vcd is loaded, this function will return the internal values.
    # Returns:
    #   face_frames: number of frames in face stream
    #   body_frames: number of frames in body stream
    #   hands_frames: number of frames in hands stream
    def get_frames(self):
        if self._vcd_loaded:
            face_frames = self.get_stream_frames_in_vcd(self._vcd,'face_camera')
            body_frames = self.get_stream_frames_in_vcd(self._vcd,'body_camera')
            hands_frames = self.get_stream_frames_in_vcd(self._vcd,'hands_camera')
        else:
            face_frames = self._f_frames
            body_frames = self._b_frames
            hands_frames = self._h_frames

        return face_frames, body_frames, hands_frames

    # With this function the shifts of all three streams could be retrieved.
    # If a vcd is loaded, this function will get the numbers from the vcd object
    # If no vcd is loaded, this function will return the internal values.
    # Returns:
    #   body_face_sh: shift of body stream respect to face stream
    #   hands_face_sh: shift of hands stream respect to face stream
    #   hands_body_sh: shift of hands stream respect to body stream
    def get_shifts(self):
        if self._vcd_loaded:
            body_face_sh = self.get_shift_in_vcd(self._vcd,"body_camera")
            hands_face_sh = self.get_shift_in_vcd(self._vcd,"hands_camera")
            hands_body_sh = hands_face_sh - body_face_sh
        else:
            body_face_sh = self._bf_shift
            hands_face_sh = self._hf_shift
            hands_body_sh = self._hb_shift
        return body_face_sh, hands_face_sh, hands_body_sh

    # With this function the camera matrix of all three streams could be
    # retrieved.
    # If a vcd is loaded, this function will get the numbers from the vcd object
    # If no vcd is loaded, this function will return the internal values.
    # Returns:
    #   face_cam_matrix: camera matrix of face camera
    #   body_cam_matrix: camera matrix of body camera
    #   hands_cam_matrix: camera matrix of hands camera
    def get_intrinsics(self, _vcd):
        if self._vcd_loaded:
            face_cam_matrix = self.get_cam_matrix_in_vcd(_vcd,"face_camera")
            body_cam_matrix = self.get_cam_matrix_in_vcd(_vcd,"body_camera")
            hands_cam_matrix = self.get_cam_matrix_in_vcd(_vcd,"hands_camera")
        else:
            face_cam_matrix = self._f_intrinsics
            body_cam_matrix = self._b_intrinsics
            hands_cam_matrix = self._h_intrinsics
        return face_cam_matrix, body_cam_matrix, hands_cam_matrix

    # This function is to set the number of frames of the body video to the VCD
    # @body_frames: number of frames
    def set_body_frames(self, body_frames):
        self._b_frames = int(body_frames)

    # This function is to set the number of frames of the face video to the VCD
    # @face_frames: number of frames
    def set_face_frames(self, face_frames):
        self._f_frames = int(face_frames)

    # This function is to set the number of frames of the hands video to the VCD
    # @hands_frames: number of frames
    def set_hands_frames(self, hands_frames):
        self._h_frames = int(hands_frames)

    # This function allows to set the stream shifts and store in the internal
    # variables to be used when saving the VCD file
    def set_shifts(self, body_face_shift=None, hands_face_shift=None,
                   hands_body_shift=None, ):
        if (body_face_shift is None and hands_face_shift is None) or \
                (body_face_shift is None and hands_body_shift is None) or \
                (hands_face_shift is None and hands_body_shift is None):
            raise RuntimeError('At least two shifts values must be passed')

        self._bf_shift = body_face_shift
        self._hf_shift = hands_face_shift
        self._hb_shift = hands_body_shift
        if body_face_shift is None:
            self._bf_shift = self._hf_shift - self._hb_shift
        if hands_face_shift is None:
            self._hf_shift = self._hb_shift + self._bf_shift
        if hands_body_shift is None:
            self._hb_shift = self._hf_shift - self._bf_shift

    # This function gets the annotation labels and includes shifts between
    # streams.
    # Returns:
    # @annotations: A matrix consisting of the annotation labels for each of
    #               the levels in dict
    # @validations: A matrix consisting of the validation method while
    #               annotating
    def get_annotation_vectors(self):
        # Perform general extraction of annotation and verification vectors
        annotations, validations = super().get_annotation_vectors()

        vcd = self._vcd
        frame_interval = vcd.get_frame_intervals().fis_dict
        total_frames = frame_interval[-1]['frame_end'] + 1

        # Get some handy variables
        body_face_shift = self._bf_shift
        hands_face_shift = self._hf_shift

        if body_face_shift is None or hands_face_shift is None:
            raise RuntimeError("Couldn't get VCD data")

        face_shift = 0
        body_shift = body_face_shift
        hands_shift = hands_face_shift
        # START
        face_dependant = self._camera_dependencies["face"]
        body_dependant = self._camera_dependencies["body"]
        hands_dependant = self._camera_dependencies["hands"]
        # Fill with NAN codes those levels where the corresponding reference
        # video has no frames
        if body_face_shift > 0 and hands_face_shift > 0:
            # Face starts first , then body or hands
            for level in body_dependant:
                annotations[0:body_face_shift, level] = 100
            for level in hands_dependant:
                annotations[0:hands_face_shift, level] = 100
        elif body_face_shift < hands_face_shift:
            # Body starts first
            face_shift = abs(body_face_shift)
            body_shift = 0
            hands_shift = face_shift + hands_face_shift
            for level in face_dependant:
                annotations[0:face_shift, level] = 100
            for level in hands_dependant:
                annotations[0:hands_shift, level] = 100
        elif hands_face_shift < body_face_shift:
            # Hands starts first
            face_shift = abs(hands_face_shift)
            body_shift = face_shift + body_face_shift
            hands_shift = 0
            for level in face_dependant:
                annotations[0:face_shift, level] = 100
            for level in body_dependant:
                annotations[0:body_shift, level] = 100
        elif hands_face_shift == body_face_shift:
            # Hands and Body start at the same time
            face_shift = abs(hands_face_shift)
            body_shift = 0
            hands_shift = 0
            for level in face_dependant:
                annotations[0:face_shift, level] = 100
        # END

        # Fill end of vectors with NAN values - body related
        if self._b_frames is not None and self._b_frames > 0:
            body_end = self._b_frames + body_shift
            if body_end < total_frames:
                for level in body_dependant:
                    annotations[body_end:total_frames, level] = 100
        else:
            warnings.warn('WARNING: Body frame number hasn\'t been set in VCD')
        # Fill end of vectors with NAN values - hands related
        if self._h_frames is not None and self._h_frames > 0:
            hands_end = self._h_frames + hands_shift
            if hands_end < total_frames:
                for level in hands_dependant:
                    annotations[hands_end:total_frames, level] = 100
        else:
            warnings.warn(
                'WARNING: Hands frame number hasn\'t been set in VCD')
        # Fill end of vectors with NAN values - face related
        if self._f_frames is not None and self._f_frames > 0:
            face_end = self._f_frames + face_shift
            if face_end < total_frames:
                for level in face_dependant:
                    annotations[face_end:total_frames, level] = 100
        else:
            warnings.warn('WARNING: Face frame number hasn\'t been set in VCD')

        return annotations, validations

    # This functions checks if the vcd has the fields of metadata and the values
    # are valid
    def verify_metadata(self, ctx_id):
        valid_metadata = True
        # @metadata: [face_meta, body_meta,
        #             hands_meta]
        # @face_meta: [rgb_video_frames,mat]
        # @body_meta: [date_time,rgb_video_frames,mat]
        # @face_meta: [rgb_video_frames,mat]
        # Number of frames
        face = self.get_stream_frames_in_vcd(self._vcd,'face_camera')
        body = self.get_stream_frames_in_vcd(self._vcd,'body_camera')
        hands = self.get_stream_frames_in_vcd(self._vcd,'hands_camera')

        if face == 0 or body == 0 or hands == 0:
            valid_metadata = False

        if self._vcd.get_context(ctx_id) == None:
            valid_metadata = False

        return valid_metadata

    # --- TEMP FEATURE ---#
    # this functions checks if the vcd has the fields of statics annotations
    # and the numbers of frames registered are not 0. If true, static
    # annotations exist
    def verify_statics(self, staticDict, obj_id):
        exist = True
        vcd_object = self._vcd.get_object(obj_id)
        for att in staticDict:
            att_exist = keys_exist(vcd_object, 'object_data',
                                   str(staticDict[att]["type"]))
            if not att_exist:
                exist = False
                break
        return exist

    # This function get different values from vcd to keep the consistency when
    # the user saves/creates a new vcd
    # @staticDict: dict of static annotations to get its values from vcd
    # @ctx_id: id of the context (in this case 0)
    def getStaticVector(self, staticDict, ctx_id):
        return self.get_static_in_vcd(self._vcd,staticDict,ctx_id)

    def get_static_in_vcd(self,_vcd,staticDict,ctx_id):
        for x in range(5):
            att = staticDict[x]
            # Get each of the static annotations of the directory from the VCD
            object_vcd = dict(_vcd.get_object_data(0, att["name"]))
            att.update({"val": object_vcd["val"]})
        # context
        context = dict(_vcd.get_context(ctx_id))["context_data"]["text"]
        staticDict[5].update({"val": context[0]["val"]})
        staticDict[6].update({"val": context[1]["val"]})
        # record_time = context[2]["val"]
        # Annotator id
        meta_data = dict(_vcd.get_metadata())
        annotator = meta_data["annotator"]
        staticDict[7].update({"val": annotator})
        # returns:
        # @staticDict: the dict with the values taken from the vcd
        return staticDict

    # This function get different values from vcd to keep the consistency when
    # the user saves/creates a new vcd
    # @ctx_id: id of the object (in this case 0)
    def getMetadataVector(self, ctx_id):
        return self.get_metadata_in_vcd(self._vcd,ctx_id)

    def get_metadata_in_vcd(self, _vcd, ctx_id):
        # context
        record_time = 0
        if not _vcd.get_context_data(ctx_id, "recordTime") ==None:
            record_time =_vcd.get_context_data(ctx_id, "recordTime")["val"]
        # frames
        face = self.get_stream_frames_in_vcd(_vcd,'face_camera')
        body = self.get_stream_frames_in_vcd(_vcd,'body_camera')
        hands = self.get_stream_frames_in_vcd(_vcd,'hands_camera')
        #intrinsics matrix
        face_mat, body_mat, hands_mat = self.get_intrinsics(_vcd)
        # returns:
        # @metadata: [face_meta, body_meta,
        #             hands_meta]
        # @face_meta: [rgb_video_frames,mat]
        # @body_meta: [date_time,rgb_video_frames,mat]
        # @face_meta: [rgb_video_frames,mat]
        return [face, face_mat], [record_time, body, body_mat], \
               [hands, hands_mat]

    # Function to extract shifts, metadata and maybe statics info to create a
    # new VCD
    def get_info_from_VCD(self, vcd_file_copy, staticDict, ctx_id):
        #load vcd
        copy_vcd = core.VCD(file_name=vcd_file_copy, validation=False)
        self._vcd_loaded = True
        #get shifts
        body_face_sh = self.get_shift_in_vcd(copy_vcd,"body_camera")
        hands_face_sh = self.get_shift_in_vcd(copy_vcd,"hands_camera")
        hands_body_sh = hands_face_sh - body_face_sh
        #get statics
        static = self.get_static_in_vcd(copy_vcd,staticDict,ctx_id)
        #get metadata
        metadata= self.get_metadata_in_vcd(copy_vcd,ctx_id)
        #Turn to false to save
        self._vcd_loaded = False
        return body_face_sh, hands_body_sh, static, metadata
