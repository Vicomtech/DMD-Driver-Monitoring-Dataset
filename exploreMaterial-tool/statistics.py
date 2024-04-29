# -*- coding: utf-8 -*-
import os
from pathlib import Path  # To handle paths independent of OS

# Import local class to parse OpenLABEL content
from vcd4reader import VcdHandler

#Written by Paola Cañas with <3

#Script to get statistics of the data (# of frames per class and total # of frames)
class get_statistics():

    def __init__(self, vcdFile, destinationFile):

        self.vcdFile = vcdFile
        self.vcd_handler = VcdHandler(vcd_file=Path(self.vcdFile))

        self.actionPath = destinationFile.replace(".txt","-actions.txt")
        self.framesPath = destinationFile.replace(".txt","-frames.txt")

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
        
        self.countActions()
        self.countFrames()

    def countActions(self):
        string_txt = []

        if os.path.exists(self.actionPath):
            with open(self.actionPath, "r") as f:
                lines = f.readlines()
                for line in lines:
                    string_txt.append(line.split(":"))

            #Delete to avoid redundancy
            os.remove(self.actionPath)

        for annotation in self.actionList:
            sum = 0
            # Check if annotation is an object or an action
            if "object" in annotation:
                # get object intervals from OpenLABEL
                fullIntervals = self.vcd_handler.get_frames_intervals_of_object(annotation)
            else:
                # get action intervals from OpenLABEL
                fullIntervals = self.vcd_handler.get_frames_intervals_of_action(annotation)

            #sum all frames in intervals
            for interval in fullIntervals:
                sum = sum + int(interval["frame_end"]) - int(interval["frame_start"])

            found = False
            #replace the sum for the new one if annotation found in txt
            for num, line in enumerate(string_txt):
                if annotation in line[0]:
                    found = True
                    string_txt[num][1] = str(sum+int(string_txt[num][1]))+"\n"

            #if not found, add the sum
            if not found:
                string_txt.append([annotation,str(sum)+"\n"])

        #write
        file = open(self.actionPath, "a+")
        for line in string_txt:
            file.write(line[0]+":"+line[1])
        file.close()

    def countFrames(self):
            sum = 0
            if os.path.exists(self.framesPath):
                with open(self.framesPath, "r") as f:
                    lines = f.read()
                    sum = int(lines.split(":")[1])
                        
                #Delete to avoid redundancy
                os.remove(self.framesPath)

            sum = sum + self.vcd_handler.get_frames_number()

            #write
            file = open(self.framesPath, "a+")
            file.write("total_frames"+":"+str(sum))
            file.close()