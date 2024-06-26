# -*- coding: utf-8 -*-
import json
import re
from pathlib import Path  # To handle paths independent of OS
import datetime


def is_string_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


# Function to transform int keys to integer if possible
def keys_to_int(x):
    r = {int(k) if is_string_int(k) else k: v for k, v in x}
    return r


class ConfigTato:

    def __init__(self):
        """ Most of the paths specified are necessary for internal compatibility
            also for the construction of pre-annotations.
            If its running in external structure, the .json and .avi video paths
            should be enough
            Run the tool through the ./annotate.sh script to avoid confussions
            with paths
        """

        # ----GLOBAL VARIABLES----
        default_annotation_modes = ["distraction", "drowsiness", "gaze"]
        # @_external_struct: flag to know if is running in internal or external
        # extructure
        self._external_struct = True

        # ----LOAD CONFIG FROM JSON----

        # Config dictionary path
        self._config_json = "config.json"
        # From json to python dictionaries
        with open(self._config_json) as config_file:
            config_dict = json.load(config_file, object_pairs_hook=keys_to_int)
        tatoConfig = config_dict["tatoConfig"]
        self._interfaceTexts = config_dict["interfaceText"]
        self._consoleTexts = config_dict["consoleText"]
        self._colorConfig = config_dict["colors"]
        self._dimensions = config_dict["dimensions"]
        # Config variables
        self._pre_annotate = bool(tatoConfig["pre_annotate"])
        self._annotation_mode = tatoConfig["annotation_mode"]
        self._annotation_dataset = tatoConfig["dataset"]
        self._calculate_time = bool(tatoConfig["calculate_time"])
        self._default_annotation_mode = self._annotation_mode in default_annotation_modes
        self._dataset_dmd = self._annotation_dataset == "dmd"


        #----GET CONSOLE INPUTS----
        print("Welcome :)")
        #Capture video PATH
        self._video_file_path = Path(input(self._consoleTexts["video_path_dmd"][str(self._dataset_dmd)]))

        #Check if video exists
        if not self._video_file_path.exists():
            raise RuntimeError("Video file doesn't exist: " +
                            str(self._video_file_path.resolve()))
        else:
            print("Video from " + self._annotation_dataset +
                " loaded: " + self._video_file_path.name)
            
        #Check if config of annotation exists
        self._annConfig_file_path = Path("./config_"+self._annotation_mode+".json")
        if not self._annConfig_file_path.exists():
            raise RuntimeError("Annotation config file doesn't exist: " +
                            str(self._annConfig_file_path.resolve()) + " Please, define a config file for "+self._annotation_mode+" or change 'annotation_mode' option in "+self._config_json)
        else:
            print("TaTo is in "+self._annotation_mode+" annotation mode with " +
                self._annConfig_file_path.name+" annotation config file.")

        #----DEFINE FILES PATHS----
        root_path = self._video_file_path.parent
        #If annotating dmd
        if self._dataset_dmd:
            # Build a regular expression for the mosaic name to be satisfied by the input mosaic file name
            regex_internal = '(?P<subject>[1-9]|[1-2][0-9]|[3][0-7])_(?P<session>[a-z]{1,}|[a-z]{1,}[2])_'\
                '(?P<stream>mosaic|body|face|hands)_(?P<date>(?P<month>0[1-9]|1[012])-(?P<day>0[1-9]|[12][0-9]|3[01]))'
            regex_external = '(?P<group>g[A-z]{1,})_(?P<subject>[1-9]|[1-2][0-9]|[3][0-7])_'\
                '(?P<session>s[1-9]{1,})_(?P<timestamp>(?P<date>(?P<year>\d{4})-(?P<month>0[1-9]|1[012])-'\
                    '(?P<day>0[1-9]|[12][0-9]|3[01]))T(?P<time>(?P<hour>\d{1,2});(?P<minute>\d{1,2});'\
                        '(?P<second>\d{1,2}))\+\d{1,2};\d{1,2})_(?P<channel>rgb|depth|ir)_(?P<stream>mosaic|body|face|hands)'
            regex_internal = re.compile(regex_internal)
            regex_external = re.compile(regex_external)
            match_internal = regex_internal.search(str(self._video_file_path))
            match_external = regex_external.search(str(self._video_file_path))

            if match_internal:
                print("Video in internal structure")
                self._external_struct = False
                match = match_internal
            elif match_external:
                print("Video in external structure")
                self._external_struct = True
                match = match_external
            else:
                raise RuntimeError(
                    "Incompatible mosaic name format: " + str(self._video_file_path) + ". Please check file structure or change 'dataset' option in "+self._config_json)
            
            #Get video info from path
            base_name = match.group()
            #Get GROUP
            self._group = self._video_file_path.parts[-4]
            #Get SUBJECT
            self._subject = match.group("subject")
            #Get SESSION
            self._session = match.group("session")
            #Get DATE
            self._date = match.group("date")
            #Get STREAM
            self._stream = match.group("stream")

            #check if video is according to mode
            distractionRelated = ['attm', 's1', 'atts', 's2', 'reach', 's3', 'attc', 's4',
                                'attm2', 'atts2', 'reach2', 'attc2']
            drowsinessRelated = ['drow2', 's5', 'drow']
            gazeRelated = ['gaze', 's6', 'gazec', 's7', 'gaze2', 'gazec2']
            if self._annotation_mode == "distraction" and self._session not in distractionRelated or self._annotation_mode == "drowsiness" and self._session not in drowsinessRelated or self._annotation_mode == "gaze" and self._session not in gazeRelated:
                print("---!!WARNING!!: the annotation mode does not match the type of video session.---")

            #Get OpenLABEL, AutoSaveAnn and TIME paths
            if self._external_struct:
                self._vcd_file_name = (base_name.replace(match.group(
                    "stream"), 'ann') + '_' + self._annotation_mode + ".json")
                #To save progress in anotations in txt
                self._autoSave_file_name = (base_name.replace(
                    match.group("stream"), 'autoSaveAnn-A') + ".txt")
                # To read and write the time expended in annotation
                self._annTime_file_name = (base_name + '_annTime.txt')

                #Get TIMESTAMP
                self._timestamp = match.group("timestamp")
                #Get STREAM
                self._channel = match.group("channel")

            else:
                self._vcd_file_name = (base_name.replace(match.group(
                    "stream") + '_', '') + '_ann_' + self._annotation_mode + ".json")
                #To save progress in anotations in txt
                self._autoSave_file_name = (base_name.replace(
                    match.group("stream") + '_', '') + '_autoSaveAnn-A'+".txt")
                # To read and write the time expended in annotation
                self._annTime_file_name = (base_name + '_annTime.txt')
            
            #Define paths for PREANNOTATE annotation mode
            if self._pre_annotate:
                base_name_body = base_name.replace('mosaic', 'body')
                # To read the pre-annotations of the mosaic
                self._preAnn_file_path = root_path / (base_name_body + "_ann.txt")
                # To read the intel annotations of the mosaic
                self._intelAnn_file_path = root_path / \
                    (base_name_body + "_ann_intel.txt")
                # To keep compatibility with this ann format
                self._oldAnn_file_path = root_path / \
                    (base_name_body + "_manualAnn.txt")
                # To read the shifts of body, face and hands videos
                self._shifts_file_path = (
                    self._video_file_path.parents[3] / "logs-sync" / ("shifts-" + self._group + ".txt")).resolve()
                # To read the metadata of video session (driver info, frame numbers..etc)
                self._metadata_file_path = (
                    self._video_file_path.parents[3] / "metadata" / ("all_"+ self._group+"_bag_metadata.txt")).resolve()
                #Check if shifts and metadata files exist
                if not self._shifts_file_path.exists():
                    raise RuntimeError("Shift file doesn't exist: " +
                                    str(self._shifts_file_path.resolve()))
                if not self._metadata_file_path.exists():
                    raise RuntimeError("Metadata file doesn't exist: " +
                                    str(self._metadata_file_path.resolve()))
        else:
            if self._pre_annotate:
                print("---!!WARNING!!: pre_annotate option is on (1). This is not compatible with other datasets. This option will be change to (0) ---")
                self._pre_annotate = False

            self._group = "0"
            #Get SUBJECT
            self._subject = "0"
            #Get SESSION
            self._session = "default"
            #Get DATE
            self._date = str(datetime.datetime.now().date())
            #Get STREAM
            self._stream = "general"
            #Working with other dataset
            base_name = self._video_file_path.stem
            #Get OpenLABEL, AutoSaveAnn and TIME paths
            self._vcd_file_name = (base_name + '_ann_' +
                                self._annotation_mode + ".json")
            #To save progress in anotations in txt
            self._autoSave_file_name = (base_name + '_autoSaveAnn-A.txt')
            # To read and write the time expended in annotation
            self._annTime_file_name = (base_name + '_annTime.txt')

        self._vcd_file_path = root_path / self._vcd_file_name
        self._autoSave_file_path = root_path / self._autoSave_file_name
        self._annTime_file_path = root_path / self._annTime_file_name
        
    def get_annotation_config(self):
        with open(self._annConfig_file_path) as config_file:
            config_dict = json.load(config_file, object_pairs_hook=keys_to_int)

        #Complete Dictionaries
        self._config_dict = config_dict
        #Levels names
        self._level_names = config_dict["level_names"]
        #Levels defaults
        self._level_defaults = config_dict["level_defaults"]
        #Levels types
        self._level_types = config_dict["level_types"]
        #Labels
        self._level_labels = []
        for ide,name in self._level_names.items():
            self._level_labels.append(config_dict[ide])
        #Camera dependencies
        self._camera_dependencies = config_dict["camera_dependencies"]
        #Number of levels
        self._num_levels = len(self._level_labels)

        return self._config_dict, self._level_names, self._level_defaults, \
               self._level_types, self._level_labels, self._camera_dependencies,\
               self._num_levels

    def get_video_path_info(self):
        if self._external_struct:
            return self._group, self._subject, self._session, self._date, self._stream, self._timestamp, self._channel
        else:
            return self._group, self._subject, self._session, self._date, self._stream

    def get_statics_dict(self):
        with open("./config_statics.json") as config_file:
            config_dict = json.load(config_file, object_pairs_hook=keys_to_int)
        return config_dict["static_dict"]

