# -*- coding: utf-8 -*-
import sys
import os
import cv2
from pathlib import Path  # To handle paths independent of OS
import numpy as np
import math
import time

# Import local class to parse VCD content
from vcd4reader import VcdHandler
from vcd4reader import VcdDMDHandler

import ffmpeg
# Written by Paola Cañas with <3

# Python and Opencv script to prepare/export material of DMD for training.
# Reads annotations in VCD and the 3 stream videos.
# To change export settings, go to __init__ and change control variables.

# Run it through python script DExTool.py
# -----
class exportClass():

    def __init__(self, vcdFile, rootDmd, destinationPath, datasetDMD=True):
        # ------ GLOBAL VARIABLES ------
        # - Args -
        self.vcdFile = vcdFile
        self.rootDmd = rootDmd+"/"
        self.destinationPath = destinationPath
        self.datasetDMD = datasetDMD

        if self.datasetDMD:

            # Create VCD Reader object
            self.vcd_handler = VcdDMDHandler(vcd_file=Path(self.vcdFile))
            # @self.info: [group, subject, session, date]
            self.info = self.vcd_handler.get_basic_metadata()
            # Just get day and hour from the full timestamp
            self.dateDayHour = self.info[3]
            # @shifts: [body_face_sh, hands_face_sh, hands_body_sh]
            self.shift_bf, self.shift_hf, self.shift_hb = self.vcd_handler.get_shifts()
        else:
            # Create VCD Reader object
            self.vcd_handler = VcdHandler(vcd_file=Path(self.vcdFile))
            self.info = ["g1","0","s1"]
            named_tuple = time.localtime() # get struct_time
            self.dateDayHour = time.strftime("%Y-%m-%d-%H;%M;%S", named_tuple)
            self.shift_bf, self.shift_hf, self.shift_hb = 0, 0, 0


        # @self.actionList: ["driver_actions/safe_drive", "gaze_on_road/looking_road",.. , ..]
        self.actionList = self.vcd_handler.get_action_type_list()
        #Get object list
        self.objectList = self.vcd_handler.get_object_type_list()
        #from 1 to not get "driver" object
        for object in self.objectList: 
            # Append objects to actionList
            if "driver" in object:
                #Dont add driver object
                continue
            self.actionList.append("objects_in_scene/"+object)
            
        self.frameNum = 0


        # -- CONTROL VARIABLES --

        """
        args:

        @material: list of data format you wish to export.
        Possible values: "image","video"

        @streams: list of camera names to export material from.
        Possible values: "face", "body", "hands", "general"

        @channels: list of channels of information you wish to export .
        Possible values: "rgb", "ir", "depth"
        
        @annotations: list of classes you wish to export (e.g. ["safe_drive","drinking"])
        Possible values: all labels names
        it can be the type name like in VCD ("driver_actions/safe_drive") or just the label name ("safe_drive"). Except for objects.
        Objects (cellphone, hair comb and bottle) have to be with the "object_in_scene/__" label before. 
        Also can be the action uid in number (e.g. [0,1,2]) but be aware that uid might not the same in all VCD's
        The var @self.actionList will get all the classes available in VCD

        @write: Flag to create/write material in destination folder (True) or just get the intervals (False)
        Possible values: True, False
        
        Optional args:
        
        @intervalChunk: size of divisions you wish to do to the frame intervals (in case you want videos of x frames each)
        Possible values: Number greater than 1
        
        @ignoreSmall: True to ignore intervals that cannot be cutted because they are smaller than @intervalChunk
        Possible values: True or False

        @asc: True to start cutting from start of interval (ascendant) or False from the end of interval (descendant)
        Possible values: True or False
        """
        # config
        material = ["image"]
        streams = ["body","face", "hands"] #must be "general" if not DMD dataset
        channels = ["rgb", "ir"] #Include "depth" to export Depth information too. It must be only "rgb" if not DMD dataset
        annotations = self.actionList
        write = True
        intervalChunk = 0

        #validations
        if not self.datasetDMD and (streams[0] != "general" or len(streams)> 1):
            raise RuntimeError(
                "WARNING: stream option for other datasets must be only 'general'")
        if not self.datasetDMD and len(channels)> 1:
            raise RuntimeError(
                "WARNING: channles option for other datasets must be only 'rgb'")
        #exec
        self.exportMaterial(material, streams, channels, annotations, write, intervalChunk, True)

    # @material: list of data format to export (e.g. ["image","video"])
    # @streams: list of camera names to export (e.g. ["body", "hands"])
    # @annotations: list of annotations to export (e.g. ["driver_actions/reach_side", "talking/talking","hands_using_wheel/only_left"])
    # @write: flag to export/create material or not
    # @intervalChunk: (optional) chunk size if the user wants to divide material by chunks
    # @ignoreSmall: (optional) True to ignore intervals that cannot be cutted because they are smaller than @ intervalChunk
    # @asc: (optional) flag to start cutting from start of interval (ascendant) or from the end of interval (descendant)
    def exportMaterial(self,material, streams, channels, annotations, write, intervalChunk=0, ignoreSmall=False, asc=True):
        for annotation in annotations:
            for channel in channels:
                for stream in streams:
                    for mat in material:
                        validAnnotation = False
                        # Check if annotation exists in vcd
                        if isinstance(annotation, str):
                            # if annotation is string, check with self.vcd_handler if it is in VCD
                            if self.vcd_handler.is_action_type_get_uid(annotation)[0] or self.vcd_handler.is_object_type_get_uid(annotation)[0]:
                                validAnnotation = True
                        elif isinstance(annotation, int):
                            # if annotation is int, is an id and has to be less then self.actionList length
                            if annotation < len(self.actionList):
                                validAnnotation = True
                        else:
                            raise RuntimeError(
                                "WARNING: Annotation argument must be string or int")
                        if validAnnotation:
                            print("\n\n-- Getting data of %s channel --" % (channel))
                            intervals = self.getIntervals(
                                mat, channel, stream, annotation, write, intervalChunk, ignoreSmall, asc)
                        else:
                            print("WARNING: annotation %s is not in this VCD." % str(annotation))

    # Function to get intervals of @annotation from VCD and if @write, exports the @material of @stream indicated to @self.destinationPath
    def getIntervals(self, material, channel, stream, annotation, write, intervalChunk=0, ignoreSmall=False, asc=True):
        #get name of action if uid is fiven
        if isinstance(annotation, int):
            annotation = self.actionList[annotation]

        print("\n\n-- Creating %s of action: %s --" % (material, str(annotation)))

        # Check and load valid video
        streamVideoPath = str(self.getStreamVideo(channel, stream))
        capVideo = cv2.VideoCapture(streamVideoPath)
        # Check if annotation is an object or an action
        if "object" in annotation:
            # get object intervals from vcd
            fullIntervals = self.vcd_handler.get_frames_intervals_of_object(annotation)
        else:
            # get action intervals from vcd
            fullIntervals = self.vcd_handler.get_frames_intervals_of_action(annotation)
        # make lists from dictionaries
        fullIntervalsAsList = self.dictToList(fullIntervals)
        # if intervals must be cutted, cut
        if intervalChunk > 1:
            fullIntervalsAsList = self.cutIntervals(fullIntervalsAsList, intervalChunk, ignoreSmall, asc)

        if write:
            print("Writing...")
            """If annotation string is the action type from VCD, it will create a folder 
            for each label inside their level folder because of the "/" in the name.
            If annotation is a number, then a folder will be created for each label with its uid as name """

            if self.datasetDMD:
                # create folder per annotation and per session
                dirName = Path(self.destinationPath +"/dmd_"+channel+ "/"+self.info[2] + "/" + str(annotation))
            else:
                dirName = Path(self.destinationPath+ "/" +str(annotation))
            if not dirName.exists():
                os.makedirs(str(dirName), exist_ok=True)
                print("Directory", dirName.name, "created")
            
            #@depthVideoArray: numpy array with all frames of video containing depth information
            depthVideoArray = []
            if channel == "depth" and (material == "image" or material == "images" ):
                depthVideoArray = self.getDepthVideoArray(streamVideoPath)

            for count, interval in enumerate(fullIntervalsAsList):

                # Check if frames are avalabile in stream. Find corresponding frames in stream, rigth now is mosaic frame
                valid, startFrame, endFrame = self.checkFrameInStream(
                    stream, interval[0], interval[1])

                if valid:
                    print('Exporting interval %d \r' % count, end="")
                    # Name with stream, date, subject and interval id to not overwrite
                    fileName = str(dirName) + "/" + stream + "_" + \
                        self.dateDayHour + "_"+self.info[1] + "_"+str(count)
                    if material == "image" or material == "images" or material == "img" or material == "imgs":
                        if channel == "depth":
                            self.depthFrameIntervalToImages(startFrame, endFrame, depthVideoArray, fileName)
                        else:
                            self.frameIntervalToImages(startFrame, endFrame, capVideo, fileName)
                    else:
                        if channel == "depth":
                            self.depthFrameIntervalToVideo(startFrame, endFrame, streamVideoPath, fileName)
                        else:
                            self.frameIntervalToVideo(startFrame, endFrame, capVideo, fileName)
                else:
                    print(
                        "WARNING: Skipped interval %i, because some of its frames do not exist in stream %s" %(count,stream))
        return fullIntervalsAsList

    # Function to get invervals as dictionaries and return them as a python list
    def dictToList(self,intervalsDict):
        assert (len(intervalsDict) > 0)
        intervalsList = []
        for interDict in intervalsDict:
            intervalsList.append(
                [interDict["frame_start"], interDict["frame_end"]])
        return intervalsList

    # Function to take list of intervals and cut them into sub intervals of desired size
    # @intervals: list of intervals to cut
    # @intervalChunk: chunks size
    # @ignoreSmall: True to ignore intervals that cannot be cutted because they are smaller than @intervalChunk
    # @asc: flag to start cutting from start of interval (ascendant) or from the end of interval (descendant)
    def cutIntervals(self, intervals, intervalChunk, ignoreSmall=False, asc=True):
        assert (len(intervals) > 0)
        assert (intervalChunk > 1)

        intervalsCutted = []
        framesSum = 0
        framesLostSum = 0

        for interval in intervals:
            framesLost = 0
            init = interval[0]
            end = interval[1]
            if end == self.frameNum-1:
                end = end-1
            dist = end - init
            framesSum = framesSum + dist
            count = init if asc else end

            # calculate how many chunks will result per interval
            numOfChunks = math.floor(dist / intervalChunk)
            # If the division of interval is not possible and cannot be ignored
            if numOfChunks <= 0 and not ignoreSmall:
                raise RuntimeError("WARNING: the interval chunk length chosen is too small, some intervals are too small to be cutted by",
                                   intervalChunk, "frames. To ignore small intervals, set True to ignoreSmall argument.")
            else:
                # if the division of interval is possible
                if numOfChunks > 0:
                    for x in range(numOfChunks):
                        # if Ascendant, take the initial limit of interval and start dividing chunks from there adding chunk size
                        if asc:
                            intervalsCutted.append([count, count + intervalChunk])
                            count = count + intervalChunk
                        # if descendant, take the final limit of interval and start dividing chunks from there substracting chunk size
                        else:
                            intervalsCutted.append([count, count - intervalChunk])
                            count = count - intervalChunk
                    framesLost = abs(
                        count - end) if asc else abs(count - init)
                else:
                    print("WARNING: Skipped interval",
                          interval, "for being too small :(")
            framesLostSum = framesLostSum + framesLost
        print("Total frame loss:", framesLostSum, "of total:", framesSum)
        print("Resulting number of intervals:", len(intervalsCutted),
              "from initial number:", len(intervals))

        return intervalsCutted

    # Function to create a sub video called @name.avi from @frameStart to @frameEnd of stream video @capVideo
    # saves video in @self.destinationPath
    # @capVideo: is video loaded in opencv, not path
    # @name of file with no extension
    def frameIntervalToVideo(self, frameStart, frameEnd, capVideo, name):
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        width = int(capVideo.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capVideo.get(cv2.CAP_PROP_FRAME_HEIGHT))
        intervalVideo = cv2.VideoWriter(name + ".avi", fourcc, 29.76, (width, height))
        success = True
        capVideo.set(cv2.CAP_PROP_POS_FRAMES, frameStart)
        while success and capVideo.get(cv2.CAP_PROP_POS_FRAMES) <= frameEnd:
            success, image = capVideo.read()
            intervalVideo.write(image)
        intervalVideo.release()

    # Function to create a sub video called @name.avi from @frameStart to @frameEnd of stream video @streamVideoPath from DEPTH channel.
    # Uses ffmpeg-python to properly cut the video
    # Cut must be made with time, not with frame number. That is why it is frameNumber/frameRate
    # saves video in @self.destinationPath
    # @streamVideoPath: is the depth video path, not video
    # @name of file with no extension
    def depthFrameIntervalToVideo(self, frameStart, frameEnd, streamVideoPath, name):

        vid = (
            ffmpeg.input(streamVideoPath)
            .trim(start=int(frameStart/29.76), end=int(frameEnd/29.76))
            .setpts('PTS-STARTPTS')
            .output(name+".avi", vcodec='ffv1', pix_fmt='gray16le', crf=0)
            .run()
        )

    # Function to get images from @frameStart to @frameEnd of stream video @capVideo
    # saves in @self.destinationPath
    # @capVideo: is video loaded in opencv, not path
    # @name of images with no extension
    def frameIntervalToImages(self,frameStart, frameEnd, capVideo, name):
        count = frameStart
        success = True
        capVideo.set(cv2.CAP_PROP_POS_FRAMES, frameStart)
        while success and capVideo.get(cv2.CAP_PROP_POS_FRAMES) <= frameEnd:
            success, image = capVideo.read()
            if not success:
                break
            cv2.imwrite(name+"_"+str(count)+".jpg", image)
            count += 1

    # Function to get images from @frameStart to @frameEnd of stream DEPTH info array @depthVideoArray

    # saves in @self.destinationPath
    # @name of images with no extension
    def depthFrameIntervalToImages(self, frameStart, frameEnd, depthVideoArray, name):
        for i in range(frameStart,frameEnd+1):
            if i != self.frameNum:
                cv2.imwrite(name+"_"+str(i)+".png",depthVideoArray[i])
            else:
                #write a black image
                cv2.imwrite(name+"_"+str(i)+".png",np.zeros((720,1280),dtype=np.uint16))

    # Function to get depth information of all frames from depth video in a unit16 array. Array should be [self.frameNum,720,1280]
    # Uses ffmpeg-python to properly extract info from video in gray16le pixelformat
    def getDepthVideoArray(self, streamVideoPath):
        out, _ = (
            ffmpeg
            .input(streamVideoPath)
            .output('pipe:', format='rawvideo', pix_fmt='gray16le')
            .run(capture_stdout=True)
        )
        array_imgs = (
            np
            .frombuffer(out, np.uint16)
            .reshape([-1, 720, 1280])
        )
        return array_imgs

    # Function to get uri of the @videoStream video from VCD and check if video frame count matches with VCD.
    # Returns @videoPath: path of @videoStream in VCD
    def getStreamVideo(self,videoChannel,videoStream):
        # load Uri and frame count
        # uri e.g.: gA/1/s1/gA_1_s1_2019-03-08T09;31;15+01;00_rgb_face.mp4
        if self.datasetDMD:
            if videoStream == "face":
                videoPath = self.vcd_handler.get_videos_uris()[0]
                self.frameNum = self.vcd_handler.get_frame_numbers()[0]
            elif videoStream == "body":
                videoPath = self.vcd_handler.get_videos_uris()[1]
                self.frameNum = self.vcd_handler.get_frame_numbers()[1]
            elif videoStream == "hands":
                videoPath = self.vcd_handler.get_videos_uris()[2]
                self.frameNum = self.vcd_handler.get_frame_numbers()[2]
            else:
                raise RuntimeWarning(
                    videoStream, ": Not a valid video stream. Must be: 'face', 'body' or 'hands'.")
            # change to desire channel video path
            videoPath = videoPath.replace("rgb", videoChannel)
            if videoChannel == "depth":
                videoPath = videoPath.replace("mp4", "avi")

        else:
            if videoStream =="general":
                videoPath = self.vcd_handler.get_videos_uri()
                self.frameNum = self.vcd_handler.get_frames_number()
            else:
                raise RuntimeWarning(videoStream,": Not a valid video stream. Must be 'general'")

        if self.datasetDMD:
            videoPath = Path(self.rootDmd + videoPath)
        else:
            videoPath = Path(videoPath)
        # Check video frame count and VCD's frame count
        if videoPath.exists():
            cap = cv2.VideoCapture(str(videoPath))
            length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if length != self.frameNum:
                #Some depth videos are missing 1 frame
                if videoChannel == "depth":
                    self.frameNum = self.frameNum - 1
                else:
                    raise RuntimeWarning(
                        "VCD's and real video frame count don't match.")
            else:
                print(videoChannel, videoStream, "stream loaded:", videoPath.name)
        else:
            raise RuntimeError(
                videoPath, "video not found. Video Uri in VCD is wrong or video does not exist")

        return videoPath

    #Function to check if the mosaic-count frame is available in stream requested. Then calculate corresponding frame position in stream-count
    def checkFrameInStream(self, stream, frameStart, frameEnd):

        if not self.datasetDMD:
            return True, frameStart, frameEnd

        faceLen, bodyLen, handsLen = self.vcd_handler.get_frame_numbers()

        # Check the starting order
        if self.shift_bf >= 0 and self.shift_hf >= 0:
            # Face starts first
            if stream == "face":
                if frameEnd < faceLen:
                    return True, frameStart, frameEnd
            elif stream == "body":
                if frameStart - self.shift_bf >= 0 and frameEnd - self.shift_bf <= bodyLen:
                    return True, frameStart - self.shift_bf, frameEnd - self.shift_bf
            elif stream == "hands":
                if frameStart - self.shift_hf >= 0 and frameEnd - self.shift_hf <= handsLen:
                    return True, frameStart - self.shift_hf, frameEnd - self.shift_hf

        elif self.shift_bf <= 0 and self.shift_hb >= 0:
            # Body starts first
            #shifts = [-self.shift_bf, self.shift_hb]

            if stream == "body":
                if frameEnd < bodyLen:
                    return True, frameStart, frameEnd
            elif stream == "face":
                if frameStart + self.shift_bf >= 0 and frameEnd + self.shift_bf <= faceLen:
                    return True, frameStart + self.shift_bf, frameEnd + self.shift_bf
            elif stream == "hands":
                if frameStart - self.shift_hb >= 0 and frameEnd - self.shift_hb <= handsLen:
                    return True, frameStart - self.shift_hb, frameEnd - self.shift_hb

        elif self.shift_hb <= 0 and self.shift_hf <= 0:
            # Hands starts first
            #shifts = [-self.shift_hf, -self.shift_hb]
            if stream == "hands":
                if frameEnd < handsLen:
                    return True, frameStart, frameEnd
            elif stream == "body":
                if frameStart + self.shift_hb >= 0 and frameEnd + self.shift_hb <= bodyLen:
                    return True, frameStart + self.shift_hb, frameEnd + self.shift_hb
            elif stream == "face":
                if frameStart + self.shift_hf >= 0 and frameEnd + self.shift_hf <= faceLen:
                    return True, frameStart + self.shift_hf, frameEnd + self.shift_hf
        else:
            raise RuntimeError("Error: Unknown order")

        return False, 0, 0


    def is_string_int(self,s):
        try:
            int(s)
            return True
        except ValueError:
            return False


    # Function to transform int keys to integer if possible
    def keys_to_int(self,x):
        return {int(k) if self.is_string_int(k) else k: v for k, v in x}




