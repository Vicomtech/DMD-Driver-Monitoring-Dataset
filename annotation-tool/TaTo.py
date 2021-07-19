# -*- coding: utf-8 -*-
import datetime
import sys
import csv
import cv2
import numpy as np
from pathlib import Path  # To handle paths independent of OS

# Import local class to parse VCD content
from vcd4parser import VcdHandler
from vcd4parser import DMDVcdHandler

# Import local class to get tato configuration and paths
from setUp import ConfigTato


# ----TaTo----
# Written by Paola Cañas and Juan Diego Ortega with <3


# Python and Opencv script to make corrections to the pre annotations or/and annotate the DMD.
# Displays one mosaic video and offers a frame-per-frame annotation of differen levels of annotation
# Starts with pre-annotations from model inference (not available for external structures)
# Reads and writes annotations in VCD, saving temporary backups in txt.
# The annotation data for the tool is represented in lists/arrays where each row is a frame and a column is an annotation level.

#This tool is prepared to work inside DMD Developers internal structure and external structure. 

#-----

# Set up annotations in all levels depending on driver_actions level annotation.
# For the annotation of DMD, some dependencies and relations have been established  between labels from different levels.
# This function contains those relations and constraints between labels. 
# In case of other applications of the tool, these must be changed. 
# @bodyAnnId: id of the annotation from level 6
# @frameInfoId: id to identify what frames are available
def getDistractionAnnotationLine(bodyAnnId, frameInfoId):
    """ levels: 0: camera_occlusion
        1: gaze_on_road
        2: talking
        3: hands_using_wheel
        4: hand_on_gear
        5: objects_in_scene
        6: driver_actions"""
    a1Ann, a2Ann, a3Ann, a4Ann, a5Ann, a6Ann = 0, 99, 0, 99, 99, 0
    if bodyAnnId == 0:  # Safe drive
        # 99,looking,99,both,99,99,safe drive
        a1Ann, a3Ann, a6Ann = 0, 0, 0
    elif bodyAnnId == 1:  # texting_right
        # 99,not_looking,99,only_left,99,cellphone,texting_right
        a1Ann, a3Ann, a5Ann, a6Ann = 1, 2, 0, 1
    elif bodyAnnId == 2:  # phonecall_right
        # 99,looking,talking,only_left,99,cellphone,phonecall_right
        a1Ann, a2Ann, a3Ann, a5Ann, a6Ann = 0, 0, 2, 0, 2
    elif bodyAnnId == 3:  # texting_left
        # 99,not_looking,99,only_rigth,99,cellphone,texting_left
        a1Ann, a3Ann, a5Ann, a6Ann = 1, 1, 0, 3
    elif bodyAnnId == 4:  # phonecall_left
        # 99,looking,talking,only_right,99,cellphone,phonecall_left
        a1Ann, a2Ann, a3Ann, a5Ann, a6Ann = 0, 0, 1, 0, 4
    elif bodyAnnId == 5:  # radio
        # 99,not_looking,99,only_left,99,99,radio
        a1Ann, a3Ann, a6Ann = 1, 2, 5
    elif bodyAnnId == 6:  # drinking
        # 99,looking,99,only_left,99,99,drinking
        a1Ann, a3Ann, a5Ann, a6Ann = 0, 2, 2, 6
    elif bodyAnnId == 7:  # reach_side
        # 99,looking,99,only_left,99,99,reach_side
        a1Ann, a3Ann, a6Ann = 0, 2, 7
    elif bodyAnnId == 8:  # hair_and_makeup
        # 99,looking,99,only_left,99,haircomb,hair_and_makeup
        a1Ann, a3Ann, a5Ann, a6Ann = 0, 2, 1, 8
    elif bodyAnnId == 9:  # talking_to_passenger
        # 99,not_looking,talking,both,99,99,talking_to_passenger
        a1Ann, a2Ann, a3Ann, a6Ann = 1, 0, 0, 9
    elif bodyAnnId == 10:  # reach_backseat
        # 99,not_looking,99,only_left,99,99,reach_backseat
        a1Ann, a3Ann, a6Ann = 1, 2, 10
    elif bodyAnnId == 11:  # change_gear
        # 99,looking,99,only_left,0,99,change_gear
        a1Ann, a3Ann, a4Ann, a6Ann = 0, 2, 0, 11
    elif bodyAnnId == 12:  # standstill_or_waiting
        # 99,looking,99,none,0,99,standstill_or_waiting
        a1Ann, a3Ann, a6Ann = 0, 3, 12
    elif bodyAnnId == 13:  # unclassified
        # 99,looking,99,both,99,99,unclassified
        a6Ann = 13
    elif bodyAnnId == 100:
        frameInfoId = 3

    if frameInfoId == 0:
        # [A0,  A1,  A2,  A3, A4, A5,   A6]
        # ["--",0   ,"--",NA, NA, "--",  0]
        # add 7 zeros to write validation state per level
        return [99, a1Ann, a2Ann, 100, 100, a5Ann, a6Ann]
    elif frameInfoId == 1:
        # [A0,  A1,  A2,  A3, A4,  A5,  A6]
        # ["--",0   ,"--",0,  "--","--", 0]
        # add 7 zeros to write validation state per level
        return [99, a1Ann, a2Ann, a3Ann, a4Ann, a5Ann, a6Ann]
    else:
        return [99, 0, 99, 100, 100, 100, 100]


def getDrowAnnotationLine(ann):
    """ levels: 0: eye state (right)
        1: eye state(left) """
    bodyAnnId = ann[0]
    a1Ann = 0
    if bodyAnnId == 0:  # open
        a1Ann = 0
    elif bodyAnnId == 1:  # close
        a1Ann =1
    elif bodyAnnId == 2:  # opening
        a1Ann= 2
    elif bodyAnnId == 3:  # closing
        a1Ann=3
    elif bodyAnnId == 4:  # undefined
        a1Ann=4
    lineAnn = [bodyAnnId, a1Ann]
    
    for i in range(2, len(ann)):
        lineAnn.append(ann[i])
    return lineAnn
    

# Load shifts, annotations, and validation info of mosaic video from dmd
# shifts are in "shifts_group.txt" and annotations and validation info are in ".._ann.txt"
def loadPropertiesDMD():
    shift_bf = 0
    shift_hb = 0
    annotation = []
    validation = []
    static = {}
    metadata = {}
    global staticExists
    global metadataExists
    
    # ---- SHIFTS ----
    # Find shifts
    if vcd_handler.file_loaded():
        # Load shifts from VCD
        shift_bf, _, shift_hb = vcd_handler.get_shifts()
        print("\nLoading shifts from VCD..")
    # To read the shifts of body, face and hands videos
    elif not existAutoSaveAnn and setUpManager._pre_annotate:
        print("\nLoading shifts from txt..")
        shifts = open(str(setUpManager._shifts_file_path))
        # Find the shifts for the current video
        for shift_line in shifts:
            spl_str = shift_line.split(":")
            if str(setUpManager._video_file_path.name) in spl_str[0]:
                shift_bf = int(spl_str[1])
                shift_hb = int(spl_str[2])
        shifts.close()
        # Set this shifts files in the vcd handler
        vcd_handler.set_shifts(body_face_shift = shift_bf,
                              hands_body_shift = shift_hb,
                              hands_face_shift = shift_bf + shift_hb)
    elif existAutoSaveAnn:
    #Load shifts from metadata autoSave file (..autoSaveAnn-B.txt)
    #done later when metadata is recovered from autosave file 
        pass


    # ---- STATIC ANN AND METADATA ----
    if vcd_handler.file_loaded():
        # Check if there are statics and metadata in VCD:
        if staticExists:
            # !!In this case is a Dictionary
            print("\nThese are the static annotations ->")
            # (dic, object_id)
            static = vcd_handler.getStaticVector(statics_dic , 0)
            for val in static:
                print(static[val]["name"], ":", static[val]["val"])
        if metadataExists:
            metadata = vcd_handler.getMetadataVector(0)
            print("\nThis is the metadata ->")
            print("record_time:", metadata[1][0])
            print("face_frames:", metadata[0][0])
            print("body_frames:", metadata[1][1])
            print("hands_frames:", metadata[2][0])
    
    # ---- ANNOTATIONS ----
    # If there is a valid VCD file loaded then use this information to get
    # @annotation and @validation matrices.
    if vcd_handler.file_loaded():
        # If there is also a autoSaveAnn.txt, there must be a confusion of
        # annotations
        if existAutoSaveAnn:
            raise RuntimeError("/nThere are two annotation files: vcd and txt."
                               " Please, keep only the most recent one."
                               " \n You can delete '..ann.json' file or"
                               " '..autoSaveAnnA.txt and ..autoSaveAnnB.txt'"
                               " files"
            )
        else:
            print("\nLoading VCD...")
            # get @annotation and @validation vectors
            annotation, validation = vcd_handler.get_annotation_vectors()

    # else load old annotations(...autoSaveAnnA-B.txt) and save them in array
    elif existAutoSaveAnn:
        print("\nLoading provisional txt annotation files...")
            
        if metadataProvFile.exists():

            f = open(str(metadataProvFile))
            lines = f.readlines()

            # --get SHIFTS--
            line = lines[2].split("-")
            shift_bf = int(line[0]) 
            shift_hb = int(line[1])
            vcd_handler.set_shifts(body_face_shift=shift_bf, hands_body_shift=shift_hb, hands_face_shift=shift_bf + shift_hb)
                
            # --get STATIC ANN AND METADATA--
            # static
            line = lines[0].split("-")
            static = dict(statics_dic)
            num = 0

            if not line[0]=="\n":
                for key,att in static.items():
                    #for glasses boolean field
                    if line[num]=="False" or line[num]=="false":
                        att.update({"val": False})
                    else:
                        att.update({"val": line[num]})
                    num += 1
            else:
                static = []

            #metadata
            line = lines[1].split("|")
            face_mat = line[1].strip('][').split(', ')
            face_mat = [float(i) for i in face_mat]

            body_mat = line[4].strip('][').split(', ')
            body_mat = [float(i) for i in body_mat]

            hands_mat = line[6].strip('][\n').split(', ')
            hands_mat = [float(i) for i in hands_mat]

            # @face_meta: [rgb_video_frames,mat]
            # @body_meta: [date_time,rgb_video_frames,mat]
            # @face_meta: [rgb_video_frames,mat]
            face_meta = [line[0], face_mat]
            body_meta = [line[2], line[3], body_mat]
            hands_meta = [line[5], hands_mat]

            # set number of frames in vcd
            vcd_handler.set_body_frames(line[3])
            vcd_handler.set_face_frames(line[0])
            vcd_handler.set_hands_frames(line[5])

            #@metadata: [face_meta, body_meta,
            #             hands_meta]
            metadata = [face_meta, body_meta,
                            hands_meta]
        
        elif not metadataProvFile.exists():
            raise RuntimeError("No Metadata file found. Could not load shifts")

        
        # --get ANNOTATIONS AND VALIDATIONS--
        # [frame,A0,A1,A2,A3,A4,A5,A6]
        #    0   -0 -0 -0 -0 -0 -0 -0

        ann = open(str(setUpManager._autoSave_file_path))
        for ann_line in ann:
            if not "|" in ann_line:
                ann_line = ann_line.rstrip(" \n") + "|"+"0-"*(num_levels-1)+"0"
            annPart, validPart = ann_line.split("|")

            part = annPart.split("-")
            annotation.append([int(part[i]) for i in range(1, len(part))])

            part = validPart.split("-")
            validation.append([int(part[i].rstrip("\n")) for i in range(0, len(part))])
        ann.close()
        
    # else If there is not VCD nor autosaveAnn:
    elif setUpManager._pre_annotate:
        # load preannotations(..ann.txt) and (...ann_intel.txt) and create new
        # matrix for @annotation and other for @validation
        if existPreAnn:
            print("\nCreating new annotations from pre_annotation files, "
                  "reading shifts and metadata...")
            # open files and create arrays
            # @file_ann: pre-annotations of body video
            file_ann = open(str(setUpManager._preAnn_file_path))
            ann = []
            for line1 in file_ann:
                ann.append(line1)
            file_ann.close()

            # First check on @intelAnn
            # @intelAnn: intel annotations for body video
            # @existIntelAnn: boolean if intelAnnotationsFile exist
            intelAnn = []
            if existIntelAnn:
                fileIntelAnn = open(str(setUpManager._intelAnn_file_path))
                for lineIn in fileIntelAnn:
                    intelAnn.append(lineIn)
                fileIntelAnn.close()

            intelFrameAnn = 99
            frameAnn = 0
            # len(ann): num of annotations in file = num of frames in body vid
            # len(ann) + shift_bf = end of body video frames
            for i in range(frameNumber + 1):
                if i < len(ann) + shift_bf:
                    if existIntelAnn:
                        intelFrameAnn = int(intelAnn[i - shift_bf].split("-")[1])
                    frameAnn = int(ann[i - shift_bf].split("-")[1])
                # fill "99:"--" if there is not pre-annotation"
                # "100:NAN" for A2,A1 until hands camera starts at @shift_hb
                if i < shift_hb + shift_bf or i > len(ann) + shift_bf:
                    # "100:NAn" for A6,A5 until body camera starts at @shift_bf
                    if i < shift_bf or i > len(ann) + shift_bf:
                        # [A0,  A1,  A2,  A3, A4, A5, A6]
                        # ["--","--","--",NA, NA, NA, NA]
                        line = getDistractionAnnotationLine(100, 3)
                    else:
                        # [A0,  A1,  A2,  A3, A4, A5,   A6]
                        # ["--",0   ,"--",NA, NA, "--",  0]
                        # Fist check intel annotation, if not available, check
                        # pre-annotation
                        if intelFrameAnn != 99:
                            line = getDistractionAnnotationLine(intelFrameAnn, 0)
                        else:
                            line = getDistractionAnnotationLine(frameAnn, 0)
                # from here there is information from the three cameras
                else:
                    # [A0,  A1,  A2,  A3, A4,  A5,  A6]
                    # ["--",0   ,"--",0,  "--","--", 0]
                    # Fist check intel annotation, if not available, check
                    # pre-annotation
                    if intelFrameAnn != 99:
                        line = getDistractionAnnotationLine(intelFrameAnn, 1)
                    else:
                        line = getDistractionAnnotationLine(frameAnn, 1)

                annotation.append(line)
                # Append 7 zeros to initial validation state for all levels
                validation.append([0 for i in range(0, num_levels)])

        # create annotation from 0 (if there is not annotation file of any kind
        # but there are shifts and metadata)
        # -----------------------------------------------------
        else:   
            print("\nCreating new VCD file with default annotations, reading "
                  "shifts and metadata...")
            for i in range(frameNumber + 1):
                line = []
                val_line = []
                for default in dic_defaults:
                    line.append(int(dic_defaults[default]))
                    val_line.append(0)
                annotation.append(line)
                # Append  zeros to initial validation state for all levels
                validation.append(val_line)

        # @metadata: [face_meta, body_meta, hands_meta]
        # @face_meta: [rgb_video_frames,mat]
        # @body_meta: [date_time,rgb_video_frames,mat]
        # @face_meta: [rgb_video_frames,mat]
        metadata = getMetadataFromFile()
        face_frames_count = metadata[0][0]
        body_frames_count = metadata[1][1]
        hands_frames_count = metadata[2][0]

        vcd_handler.set_body_frames(body_frames_count)
        vcd_handler.set_face_frames(face_frames_count)
        vcd_handler.set_hands_frames(hands_frames_count)

    #create annotation from 0, trying to get shifts and metadata from other VCD. if failed, then set 0 to everything
    else:
        distractionVCD = str(setUpManager._vcd_file_path).replace(str(setUpManager._annotation_mode),"distraction")
        drowsinessVCD = str(setUpManager._vcd_file_path).replace(str(setUpManager._annotation_mode),"drowsiness")
        gazeVCD = str(setUpManager._vcd_file_path).replace(str(setUpManager._annotation_mode), "gaze")
        copyVCD = False
        copy_file = ""
        if Path(distractionVCD).exists():
            #Copy from distraction VCD
            copyVCD = True
            copy_file= distractionVCD
            print(
                "\nCreating new VCD file with default annotations, reading shifts and metadata from distraction VCD...")
        elif Path(drowsinessVCD).exists():
            #Copy from drowsiness VCD
            copyVCD = True
            copy_file = drowsinessVCD
            print(
                "\nCreating new VCD file with default annotations, reading shifts and metadata from drowsiness VCD...")
        elif Path(gazeVCD).exists():
            #Copy from gaze VCD
            copyVCD  = True
            copy_file = gazeVCD
            print(
                "\nCreating new VCD file with default annotations, reading shifts and metadata from gaze VCD...")
        else:
            copyVCD = False
            print("A default annotation VCD was not found!")
        
        for i in range(frameNumber + 1):
            line = []
            val_line = []
            for default in dic_defaults:
                line.append(int(dic_defaults[default]))
                val_line.append(0)
            annotation.append(line)
            # Append  zeros to initial validation state for all levels
            validation.append(val_line)

        if copyVCD:
            try:
                #Get info from default VCD
                shift_bf, shift_hb, static, metadata = vcd_handler.get_info_from_VCD(copy_file,statics_dic,0)
                vcd_handler.set_shifts(body_face_shift=shift_bf, hands_body_shift=shift_hb, hands_face_shift=shift_bf + shift_hb)
            except:
                #Create new VCD without shifts, statics and metadata
                print("\n ---WARNING---: An error occured while trying to get info from VCD...\nCreating new VCD file with default annotations, without shifts and metadata...")
                #Initialize with default annotations
                for i in range(frameNumber + 1):
                    line = []
                    val_line = []
                    for default in dic_defaults:
                        line.append(int(dic_defaults[default]))
                        val_line.append(0)
                    annotation.append(line)
                    # Append  zeros to initial validation state for all levels
                    validation.append(val_line)
                vcd_handler.set_shifts(body_face_shift=shift_bf, hands_body_shift=shift_hb, hands_face_shift=shift_bf + shift_hb)

        else:
            #Not default VCD was found
            #Create new VCD without shifts, statics and metadata
            print("\n---WARNING---: A defalut annotation VCD was not found... \nCreating new VCD file with default annotations, without shifts and metadata...")
            #Initialize with default annotations
            for i in range(frameNumber + 1):
                line = []
                val_line = []
                for default in dic_defaults:
                    line.append(int(dic_defaults[default]))
                    val_line.append(0)
                annotation.append(line)
                # Append  zeros to initial validation state for all levels
                validation.append(val_line)
            vcd_handler.set_shifts(body_face_shift=shift_bf, hands_body_shift=shift_hb, hands_face_shift=shift_bf + shift_hb)
            
    
    return shift_bf, shift_hb, annotation, validation, static, metadata

# Load annotations and validation info of video from another dataset
def loadPropertiesGeneral():
    annotation = []
    validation = []
    
    # ---- ANNOTATIONS ----
    # If there is a valid VCD file loaded then use this information to get @annotation and
    # @validation matrices.
    if vcd_handler.file_loaded():
        # If there is also a autoSaveAnn.txt, there must be a confusion of annotations
        if existAutoSaveAnn:
            raise RuntimeError(
                "/n There are two annotation files: vcd and txt. Please, keep only"
                "the most recent one. \n You can delete '..ann_xx.json' file or '..autoSaveAnnA.txt and ..autoSaveAnnB.txt' files"
            )
        else:
            print("\nLoading VCD...")
            # get @annotation and @validation vectors
            annotation, validation = vcd_handler.get_annotation_vectors()

    # else load old annotations(...autoSaveAnnA-B.txt) and save them in array
    elif existAutoSaveAnn:
        print("\nLoading provisional txt annotation files...")

        # --get ANNOTATIONS AND VALIDATIONS--
        # [frame,A0,A1,A2,A3,A4,A5,A6]
        #    0   -0 -0 -0 -0 -0 -0 -0

        ann = open(str(setUpManager._autoSave_file_path))
        for ann_line in ann:
            if not "|" in ann_line:
                ann_line = ann_line.rstrip(" \n") + "|"+"0-"*(num_levels-1)+"0"
            annPart, validPart = ann_line.split("|")

            part = annPart.split("-")
            annotation.append([int(part[i]) for i in range(1, len(part))])

            part = validPart.split("-")
            validation.append([int(part[i].rstrip("\n")) for i in range(0, len(part))])
        ann.close()

       
    #create annotation from 0
    else:
        print("\nCreating new VCD file with default annotations")
        for i in range(frameNumber + 1):
            line = []
            val_line = []
            for default in dic_defaults:
                line.append(int(dic_defaults[default]))
                val_line.append(0)
            annotation.append(line)
            # Append  zeros to initial validation state for all levels
            validation.append(val_line)


    return annotation, validation

# Called when [SPACE] or [ENTER] or [ESC] is pressed
# @annotations: array of current manual corrections/annotations
# @validations: array of current validation state of frames
# @toVCD: if True, save annotations in vcd format and delete txt, else write in txt
def save(annotations, validations, toVCD):
    # Save time expended during the annotation process

    
    global statics
    global staticExists
    global metadata
    global metadataExists

    """ Save elapsed time of annotation:
    -Go to config.json file
    -Change calculate_time variable
    -0: to not calculate, 1: to calculate
    """
    
    if setUpManager._calculate_time:
        saveHour()

    if toVCD:
        # Show "saving" window
        cv2.namedWindow("Annotation - Saving", flags=cv2.WINDOW_NORMAL)
        alertWindowHeight = 160
        alertSWindowWidth = 400
        alertSave = np.uint8(np.full((alertWindowHeight, alertSWindowWidth, 3),
                                    backgroundColorMain))
        alertSave[0:15, 0:alertSWindowWidth] = colorDict[12]
        alertSave[145:160, 0:alertSWindowWidth] = colorDict[12]
        cv2.putText(alertSave, "Saving...", (130, 85), font, 2, colorDict[7],
                    2, cv2.LINE_AA)
        while True:
            cv2.imshow("Annotation - Saving", alertSave)
            cv2.moveWindow("Annotation - Saving", 400, 400)
            key = cv2.waitKey(3)

            # Update VCD
            #Get static annotations and metadata from VCD
            if staticExists:
                statics = vcd_handler.getStaticVector(statics_dic, 0)    
            if metadataExists:
                metadata = vcd_handler.getMetadataVector(0)
                            
            #create vcd - dmd
            if setUpManager._dataset_dmd:
                vcd_handler.update_save_vcd(annotations, validations, statics,
                                            metadata, False)
                staticExists = vcd_handler.verify_statics(statics_dic, 0)
                metadataExists = vcd_handler.verify_metadata(0)
            else:
                vcd_handler.update_save_vcd(annotations, validations, False)

            # Delete (autoSaveAnnA.txt)
            file_to_rem = Path(setUpManager._autoSave_file_path)
            if file_to_rem.exists():
                file_to_rem.unlink()
            # Delete (autoSaveAnnB.txt)
            file_to_rem = Path(metadataProvFile)
            if file_to_rem.exists():
                file_to_rem.unlink()
            break
        cv2.destroyWindow("Annotation - Saving")
        

    else:
        # Save in TXT files
        # Annotations and validations
        # Open file
        f = open(str(setUpManager._autoSave_file_path), "w")
        # Save annotations and validation states in the same file. Separated by
        # "|" character
        for i, clas in enumerate(annotations):
            val = validations[i]
            line = str(i) 
            for j in range(len(clas)):
                line = line + "-" + str(clas[j])
            line = line + "|" + str(val[0])   
            for j in range(1,len(clas)):
                line = line + "-" + str(val[j])
            f.write(line + "\n" )
        f.close()
        if vcd_handler.file_loaded() and setUpManager._dataset_dmd:
            # save metadata and staticAnn to txt 
            # Open file
            f = open(str(metadataProvFile), "w")
            if staticExists:
                # Save metadata and static annotations same file in three lines
                static = vcd_handler.getStaticVector(statics_dic, 0)
                line = ""
                # static annotations separated by "-" character
                for val in static:
                    line = line + str(static[val]["val"]) + "-"
                line = line + "\n"
                f.write(line)
            else:
                f.write("\n")
            # metadata separated by "|" character
            meta = vcd_handler.getMetadataVector(0)
            line = (str(meta[0][0]) + "|" + str(meta[0][1]) + "|" + str(meta[1][0])
                    + "|" + str(meta[1][1]) + "|" + str(meta[1][2]) + "|" + str(meta[2][0])
                    + "|" + str(meta[2][1]) + "\n")
            f.write(line)
            # shifts separated by "-" character
            line = str(shift_bf)+"-"+str(shift_hb)
            f.write(line)


# Saves the accumulated elapsed time using the tool for the actual video
def saveHour():
    global GLOBAL_opening_time
    delta = datetime.timedelta(hours=0, minutes=0, seconds=0)
    # If there is an old time, load it
    if Path(setUpManager._annTime_file_path).exists():
        timeF = open(str(setUpManager._annTime_file_path))
        for time_line in timeF:
            spl = time_line.split(":")
            if "day" in spl[0]:
                spl[0] = "0"
            delta = datetime.timedelta(
                hours=int(spl[0]), minutes=int(spl[1]), seconds=int(spl[2]))
        timeF.close()
    # calculate elapsed time since the last saving or since the opening of the tool
    closing_time = datetime.datetime.now().time()
    closing_time = datetime.timedelta(
        hours=closing_time.hour,
        minutes=closing_time.minute,
        seconds=closing_time.second)
    elapsed_time = closing_time - GLOBAL_opening_time + delta
    # open file and rewrite time used in annotating
    f = open(str(setUpManager._annTime_file_path), "w")
    f.write(str(elapsed_time))
    f.close()
    # update opening_time to the last saved time (now)
    GLOBAL_opening_time = datetime.datetime.now()
    GLOBAL_opening_time = datetime.timedelta(
        hours=GLOBAL_opening_time.hour,
        minutes=GLOBAL_opening_time.minute,
        seconds=GLOBAL_opening_time.second
        )


# Create new window to display the actual video along with its annotations
# @count: the frame number to begin the video playing
# @mosaicVideo: actual video
# @annotations: annotations array to show along with the video
# @validations: validations array to show along with the video
# @mode: current level of annotation
def showLiveAnnotationsGeneral(countm, mosaicVideo, annotations, validations, mode):
    mosaicVideo.set(cv2.CAP_PROP_POS_FRAMES, countm)
    annArray = np.array(annotations)
    valArray = np.array(validations)
    ret_count = countm
    while True:
        key = cv2.waitKey(3)
        if key == 27:  # Press [esc] to quit
            break
        elif key == 32:  # Press [SPACE] to pause playback
            key = cv2.waitKey()
            if key == 13:  # Press [ENTER] to return to previous frame
                ret_count = countm - 1
                break
            elif key == 27:  # Press [esc] to quit
                break
        elif key == 13:  # Press [ENTER] to return to previous frame
            ret_count = countm - 1
            break
        retMosaic, frameMosaic = mosaicVideo.read()
        if not retMosaic:
            break
        mosaicA = frameMosaic
        
        h_line = 48 #space between titles
        height_calculation = len(dic_names)*int(h_line+10)
        mosaicA[0:height_calculation, width-int(w2/2):width] = np.uint8(np.full((height_calculation, int(w2/2), 3), backgroundColorMain))

        padding = width-int(w2/2) +30
        line = 30
        # Write annotations
        for j in range(len(dic_names)):
            cv2.putText(
                mosaicA,
                ("Label: " + dic_names[j]),
                (padding, (line + j * h_line)),
                font,
                1,
                textColorMain,
                1,
                cv2.LINE_AA,
            )
            cv2.putText(
                mosaicA,
                dic_levels[j][annotations[countm][j]], (padding,
                                                26 + line + j * h_line),
                font,
                1.5,
                textColorMain,
                1,
                cv2.LINE_AA,
            )
        padding = 100   
        line = height-150
        mosaicA[line-30:height, 0:300] = np.uint8(np.full((180, 300, 3), backgroundColorMain))
        # Write mosaic number
        cv2.putText(
            mosaicA,
            str(countm),
            (padding, line+20),
            font,
            3,
            (colorDict[7][0], colorDict[7][1], colorDict[7][2]),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            mosaicA,
            "Mosaic frame",
            (padding -10, line+40),
            font,
            1,
            textColorMain,
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            mosaicA,
            ". Press [space] to pause video",
            (padding -90, line+70),
            font,
            1,
            (colorDict[11][0], colorDict[11][1], colorDict[11][2]),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            mosaicA,
            ". Press [enter] to exit and go",
            (padding -90, line+90),
            font,
            1,
            (colorDict[11][0], colorDict[11][1], colorDict[11][2]),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(mosaicA, "to actual frame", (padding -50, line+110), font, 1,
                    (colorDict[11][0], colorDict[11][1], colorDict[11][2]), 1, cv2.LINE_AA)
        cv2.putText(mosaicA, ". Press [esc] to exit this window",
                    (padding -90, line+130), font, 1, (colorDict[11]
                                                    [0], colorDict[11][1], colorDict[11][2]), 1,
                    cv2.LINE_AA)

        # downscale image
        scale_percent = 90  # percent of original size
        new_width = int(width * scale_percent / 100)
        new_height = int(height * scale_percent / 100)
        dim = (new_width, new_height)
        mosaicA = cv2.resize(cv2.UMat(mosaicA), dim, interpolation=cv2.INTER_AREA)

        #move foward in timeline
        showTimeLine(annArray[:, mode], countm, valArray[:, mode])

        # set fixed window positions
        cv2.imshow("Annotation - viewer", mosaicA)
        cv2.moveWindow("Annotation - viewer", 30, 110)
        countm += 1

    cv2.destroyWindow("Annotation - viewer")
    return ret_count


#Create new window to play the actual video along with its annotations
# @count: the frame number to begin the video playing
# @mosaicVideo: actual video
# @annotations: annotations array to show along with the video
# @validations: validations array to show along with the video
# @mode: current level of annotation
def showLiveAnnotationsDMD(countm, mosaicVideo, annotations, validations, mode):
    mosaicVideo.set(cv2.CAP_PROP_POS_FRAMES, countm)
    annArray = np.array(annotations)
    valArray = np.array(validations)
    ret_count = countm
    while True:
        key = cv2.waitKey(3)
        if key == 27:  # Press [esc] to quit
            break
        elif key == 32:  # Press [SPACE] to pause playback
            key = cv2.waitKey()
            if key == 13:  # Press [ENTER] to return to previous frame
                ret_count = countm - 1
                break
            elif key == 27:  # Press [esc] to quit
                break
        elif key == 13:  # Press [ENTER] to return to previous frame
            ret_count = countm - 1
            break
        retMosaic, frameMosaic = mosaicVideo.read()
        if not retMosaic:
            break
        mosaicA = frameMosaic
        mosaicA[0:h2, w2:width] = np.uint8(np.full((h2, w2, 3), backgroundColorMain))
        line = 30
        h_line = 48
        padding = 50
        # Write annotations
        for j in range(len(dic_names)):
            cv2.putText(
                mosaicA,
                ("Label: " + dic_names[j]),
                (w2 + padding, (line + j * h_line)),
                font,
                1,
                textColorMain,
                1,
                cv2.LINE_AA,
            )
            cv2.putText(
                mosaicA,
                dic_levels[j][annotations[countm][j]],
                (w2 + padding, (26 + line + j * h_line)),
                font,
                1.5,
                textColorMain,
                1,
                cv2.LINE_AA,
            )
        # Write mosaic number
        cv2.putText(
            mosaicA,
            str(countm),
            (padding + 1000, 140),
            font,
            3,
            colorDict[7],
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            mosaicA,
            "Mosaic frame",
            (padding + 990, 160),
            font,
            1,
            textColorMain,
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            mosaicA,
            ". Press [space] to pause video",
            (padding + 910, 250),
            font,
            1,
            colorDict[11],
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            mosaicA,
            ". Press [enter] to exit and go",
            (padding + 910, 270),
            font,
            1,
            colorDict[11],
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            mosaicA,
            "to actual frame",
            (padding + 950, 290),
            font,
            1,
            colorDict[11],
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            mosaicA,
            ". Press [esc] to exit this window",
            (padding + 910, 310),
            font,
            1,
            colorDict[11],
            1,
            cv2.LINE_AA,
        )

        # downscale image
        scale_percent = 90  # percent of original size
        new_width = int(width * scale_percent / 100)
        new_height = int(height * scale_percent / 100)
        dim = (new_width, new_height)
        mosaicA = cv2.resize(cv2.UMat(mosaicA), dim, interpolation=cv2.INTER_AREA)

        #move foward in timeline
        showTimeLine(annArray[:, mode], countm, valArray[:, mode])

        # set fixed window positions
        cv2.imshow("Annotation - viewer", mosaicA)
        cv2.moveWindow("Annotation - viewer", 30, 110)
        countm += 1

    cv2.destroyWindow("Annotation - viewer")
    return ret_count

# Show window of Labels of the actual level of annotation @mode
# Called when the level of annotation is changed (press [TAB]) to refresh
# @mode: actual level of annotation
def showLabelsWindow(mode):
    labelS = np.uint8(np.full((total_height, width_Labels, 3), backgroundColorLabels))

    # Shifts equality
    padding = 20
    padVer = 30
    if setUpManager._dataset_dmd:
        frameInfo_resize = cv2.resize(cv2.UMat(frameInfo), (81, 27),
                                    interpolation=cv2.INTER_AREA)
        # 54x162
        labelS[padVer - 10: 47, padding: 81 + padding] = frameInfo_resize.get()
        cv2.putText(
            labelS,
            "=",
            (int(width_Labels / 2) - 15, padVer + 10),
            font,2,textColorLabels,2,
            cv2.LINE_AA,
        )
        cv2.putText(
            labelS,
            "Body: " + str(shift_bf),
            (int(width_Labels / 2) + padding, padVer),
            font, 1,textColorLabels,1,
            cv2.LINE_AA,
        )
        cv2.putText(
            labelS,
            "Hands: " + str(shift_hb) + "=" + str(shift_bf + shift_hb),
            (int(width_Labels / 2) + padding, padVer + 14),
            font,1,textColorLabels,1,
            cv2.LINE_AA,
        )

    # Get mosaic video with preceding 4 folders
    cv2.putText(
        labelS,
        str(setUpManager._vcd_file_name),
        (padding, padVer + 40),
        font,0.8,textColorLabels,1,
        cv2.LINE_AA,
    )
    cv2.putText(
        labelS,
        "Total frames: " + str(frameNumber),
        (padding + 90, padVer + 65),
        font,1,textColorLabels,1,
        cv2.LINE_AA,
    )

    # Annotation Id's info
    pad_class = 210
    cv2.putText(
        labelS,
        "Labels: ",
        (padding, pad_class - 75),
        font,1.8,textColorLabels,
        2,cv2.LINE_AA,
    )
    cv2.putText(
        labelS,
        "To overwrite the label",
        (padding, pad_class - 50),
        font,1,
        textColorLabels,1,
        cv2.LINE_AA,
    )
    cv2.putText(
        labelS,
        "press the corresponding key:",
        (padding, pad_class - 30),
        font,1,
        textColorLabels,1,
        cv2.LINE_AA,
    )

    # Display each label of the actual label
    for j, i in enumerate(dic_levels[mode]):
        num = j
        # show key symbols instead of class numbers above 10
        if i == 10:
            j = "/"
        if i == 11:
            j = "*"
        if i == 12:
            j = "-"
        if i == 13:
            j = "+"
        if i == 99:
            j = " . "
        # Dont show label NAN
        if i != 100:
            labelS[
            pad_class + (20 * int(num)) - 10: pad_class + (20 * int(num)),
            padding: padding + 10,
            ] = (colorDict[i][0], colorDict[i][1], colorDict[i][2])
            cv2.putText(
                labelS,
                "[" + str(j) + "]: " + str(dic_levels[mode][i]),
                (padding + 30, pad_class + (20 * int(num))),
                font,1,
                textColorLabels,1,
                cv2.LINE_AA,
            )
    cv2.putText(
        labelS,
        "NAN: not frame information",
        (padding, pad_class + 315),
        font,1, textColorLabels,1,cv2.LINE_AA,)
    cv2.putText(
        labelS,
        "--: no label",
        (padding, pad_class + 337),
        font,1, textColorLabels,1,cv2.LINE_AA,)
    # Validation colors info
    pad_class = 620
    cv2.putText(
        labelS,
        "Validation: ",
        (padding, pad_class - 30),
        font,1.7,textColorLabels,2,cv2.LINE_AA)
    labelS[pad_class - 10: pad_class, padding: padding +
           10] = (colorDict["val_0"][0], colorDict["val_0"][1], colorDict["val_0"][2])
    cv2.putText(
        labelS,
        ": frame not changed",
        (padding + 20, pad_class),
        font,1,
        textColorLabels,1,
        cv2.LINE_AA,
    )
    labelS[pad_class - 10 + 20: pad_class + 20, padding: padding +
           10] = (colorDict["val_1"][0], colorDict["val_1"][1], colorDict["val_1"][2])
    cv2.putText(
        labelS,
        ": manual change",
        (padding + 20, pad_class + 20),
        font,1,textColorLabels,1,cv2.LINE_AA)
    labelS[pad_class - 10 + 40: pad_class + 40, padding: padding +
           10] = (colorDict["val_2"][0], colorDict["val_2"][1], colorDict["val_2"][2])
    cv2.putText(
        labelS,
        ": block change",
        (padding + 20, pad_class + 40),
        font,1,textColorLabels,1,cv2.LINE_AA)
    cv2.putText(
        labelS,
        "Happy labelling :)",
        (padding, total_height - 25),
        font,0.8,textColorLabels,1,cv2.LINE_AA,)

    # Finally show window and fix position
    cv2.imshow("Annotation - Labels", labelS)


# Get the image of the mosaic, cut the corresponding video rectangles
# keeps the face rectangle as the original and shrinks the body and hands rectangle
# @frameImage: actual frame of the mosaic video
def getVideoRecs(frameImage):
    faceRec = frameImage[h2:height, 0:w2]  # Keep original size
    bodyRec = frameImage[h2:height, w2:width]
    handsRec = frameImage[0:h2, 0:w2]
    # shrink body and hands rectangle by @shrinkingPercentage
    bodyRec = cv2.resize(cv2.UMat(bodyRec), shrinkdim, interpolation=cv2.INTER_AREA)
    handsRec = cv2.resize(cv2.UMat(handsRec), shrinkdim, interpolation=cv2.INTER_AREA)
    # From UMat to array
    bodyRec = bodyRec.get()
    handsRec = handsRec.get()
    return faceRec, bodyRec, handsRec


# Shows window with annotation and validation arrays visualization in colors
# @annArray: array of the annotations from one level (@mode) dim:[frameNumber,1]
# @count: actual mosaic video frame position
# @validArray: array of the validations state from one level (@mode) dim:[frameNumber,1]
#  dim:[frameNumber,1]
def showTimeLine(annArray, count, validArray):
    global visualWidth
    pixelPerFrame = 2
    # @visualWidth and @visWidth2 have to be even
    if visualWidth % 2 != 0:
        visualWidth -= 1
    visWidth2 = int(visualWidth / 2)
    if visWidth2 % 2 != 0:
        visualWidth -= 2
        visWidth2 = int(visualWidth / 2)

    barColor = (70, 70, 70)
    if key_frame >= 0:
        barColor = keyFrameColor
    # Create window

    visualS = np.uint8(np.full((visualHeight, visualWidth, 3),backgroundColorMain))

    # --- MAIN (WHOLE) ANNOTATION BAR ---
    # title
    cv2.putText(
        visualS,
        "Total annotation timeline",
        (visWidth2 - 90, 20),
        font,0.9,textColorMain,1,cv2.LINE_AA,)
    # Draw annotation bar with colors
    for linePos in range(visualWidth):
        # @index: extrapolate the pixel number to an index in the @annArray
        index = int(linePos * (frameNumber + 1) / visualWidth)
        # draw a 20pixel vertical line with the correspondent label color
        visualS[30:50, linePos] = (colorDict[annArray[index]][0], colorDict[annArray[index]][1],colorDict[annArray[index]][2])
        visualS[50:57, linePos] = (colorDict["val_" + str(validArray[index])][0], colorDict["val_" + str(validArray[index])][1], colorDict["val_" + str(validArray[index])][2])
    # division
    visualS[50, 0:visualWidth] = (120, 120, 120)

    # POINTER
    # @count position calculated in colors bar
    framePos = int(visualWidth * count / (frameNumber + 1))
    # Draw a 30x1pixel vertical line and a 6x5pixel rectangle to indicate actual position in bar
    visualS[25:50, framePos] = barColor
    visualS[50:55, framePos - 3: framePos + 3] = barColor
    # @key_frame position calculated in colors bar
    keyFramePos = int(visualWidth * key_frame / (frameNumber + 1))
    # Draw a 40pixel vertical line to indicate key frame position in bar
    if key_frame >= 0:
        visualS[25:50, keyFramePos] = (0, 255, 0)

    # --- SECOND (ZOOM) ANNOTATION BAR ---
    # title
    cv2.putText(
        visualS,
        "Timeline Zoom in",
        (visWidth2 - 55, 75),
        font,0.8, textColorMain,1,cv2.LINE_AA)
    # factor 2 for showing each annotation in two pixels
    # max 0 when the start of the annotation array corresponds to a negative pixel in the screen
    annCounter = max(0, count - int(visWidth2 / pixelPerFrame))

    # draw annotations always keeping the actual frame position (@framePos or @count) in the center
    # of the window
    for pixel in range(0, visualWidth, pixelPerFrame):
        #what pixel should be each of the boundaries of the annArray (start and end)
        low_bound = visWidth2 - pixelPerFrame * count
        upp_bound = visWidth2 + pixelPerFrame * (frameNumber - count)
        # if there is an annotation for that pixel in the screen (control bounds of array)
        if low_bound <= pixel <= upp_bound:
            visualS[90:120, pixel: pixel + pixelPerFrame] = (colorDict[annArray[annCounter]][0], colorDict[annArray[annCounter]][1],colorDict[annArray[annCounter]][2])
            visualS[120:127, pixel: pixel + pixelPerFrame] = (colorDict["val_" + str(validArray[annCounter])][0],colorDict["val_" + str(validArray[annCounter])][1],colorDict["val_" + str(validArray[annCounter])][2])
            visualS[120, pixel: pixel + pixelPerFrame] = (120, 120, 120)
            annCounter += 1

    # POINTER
    # Draw a 40x2pixel square to indicate the center that represents the actual frame position
    visualS[85:127, visWidth2] = barColor
    visualS[85:127, visWidth2 + pixelPerFrame] = barColor
    visualS[90, visWidth2: visWidth2 + pixelPerFrame] = barColor
    visualS[120, visWidth2: visWidth2 + pixelPerFrame] = barColor

    # KEY-FAME
    # Draw a 40pixel vertical line to indicate the position of selected key frame if exists
    # Compute Key Frame offset with respect to actual frame
    if key_frame != -1:
        k_offset = (count - key_frame) * pixelPerFrame
        if abs(k_offset) <= visWidth2:
            low_lim = visWidth2 - k_offset
            high_lim = visWidth2 - k_offset + pixelPerFrame + 1
            visualS[85:127, low_lim:high_lim] = keyFrameColor
        # To show keyframe block in both directions
        if key_frame < count:
            # Key frame block in first timeline
            visualS[26:30, keyFramePos:framePos] = keyFrameColor
            # key frame block in second timeline
            start = max(0, visWidth2 - k_offset)
            end = visWidth2 + pixelPerFrame
            visualS[86:90, start: end] = keyFrameColor
        else:
            # Key frame block in first timeline
            visualS[26:30, framePos:keyFramePos] = keyFrameColor
            # key frame block in second timeline
            visualS[86:90, visWidth2: visWidth2 - k_offset] = keyFrameColor

    cv2.imshow("Annotation - visualization", visualS)


# shows window with instructions of each key
def showInstructionsWindow():
    while True:
        keyboardS = np.uint8(
            np.full(
                (instructionsHeight, instructionsWidth, 3), backgroundColorInstructions))
        # primer cuadrante
        keyboardS[40:300, 40:340] = (255, 255, 255)
        # segundo cuadrante
        keyboardS[40:300, 360:600] = (255, 255, 255)
        # tercer cuadrante
        keyboardS[320:480, 40:340] = (255, 255, 255)
        # cuarto cuadrante
        keyboardS[320:420, 360:600] = (255, 255, 255)

        # titulo
        cv2.putText(
            keyboardS,
            "-Instructions-",
            (int(instructionsWidth / 2) - 100, 25),
            font,
            1.6,
            (30, 30, 200),
            2,
            cv2.LINE_AA,
        )

        # -- primer cuadrante --             y, x
        # teclas
        keyboardS[80:120, 80:120] = textColorInstructions  # Q
        keyboardS[80:120, 140:180] = textColorInstructions  # W
        keyboardS[80:120, 200:240] = textColorInstructions  # E
        keyboardS[80:120, 260:300] = textColorInstructions  # R

        keyboardS[160:200, 140:180] = textColorInstructions  # A
        keyboardS[160:200, 200:240] = textColorInstructions  # S

        keyboardS[240:280, 80:240] = textColorInstructions  # SPACE
        keyboardS[240:280, 260:300] = textColorInstructions  # ?

        # text                                 x , y
        cv2.putText(
            keyboardS,"<-300",(80, 70),font,0.8,
            textColorInstructions,1,cv2.LINE_AA)  # Q
        cv2.putText(
            keyboardS, "Q", (90, 110), font, 2, textColorLabels, 2, cv2.LINE_AA
        )  # Q

        cv2.putText(
            keyboardS,
            "<-50", (140, 70), font, 0.8, textColorInstructions, 1, cv2.LINE_AA)  # W   
        cv2.putText(
            keyboardS, "W", (150, 110), font, 2, textColorLabels, 2, cv2.LINE_AA)  # W

        cv2.putText(
            keyboardS,
            "+50>",(200, 70), font,0.8,
            textColorInstructions,1, cv2.LINE_AA,)  # E        
        cv2.putText(
            keyboardS, "E", (210, 110), font, 2, textColorLabels, 2, cv2.LINE_AA)  # E

        cv2.putText(
            keyboardS,
            "+300>", (260, 70), font,0.8,
            textColorInstructions, 1, cv2.LINE_AA)  # R 
        cv2.putText(
            keyboardS, "R", (270, 110), font, 2, textColorLabels, 2, cv2.LINE_AA)  # R

        cv2.putText(
            keyboardS,
            "[<",
            (150, 150),
            font, 0.8, textColorInstructions, 1, cv2.LINE_AA)  # A     
        cv2.putText(
            keyboardS, "A", (150, 190), font, 2, textColorLabels, 2, cv2.LINE_AA)  # A

        cv2.putText(keyboardS, ">]", (210, 150), font, 0.8,
                    textColorInstructions, 1, cv2.LINE_AA)  # S
        cv2.putText(keyboardS, "S", (210, 190), font, 2, textColorLabels, 2,
                    cv2.LINE_AA)  # S

        cv2.putText(keyboardS, "<", (160, 230), font, 0.8,
                    textColorInstructions, 1, cv2.LINE_AA)  # space
        cv2.putText(keyboardS, "SPACE", (110, 270), font, 2, textColorLabels,
                    2, cv2.LINE_AA)  # space

        cv2.putText(keyboardS, ">", (270, 230), font, 0.8,
                    textColorInstructions, 1, cv2.LINE_AA)  # ?
        cv2.putText(keyboardS, "?", (270, 270), font, 2, textColorLabels, 2,
                    cv2.LINE_AA)  # ?

        # -- segundo cuadrante --             y, x

        # teclas
        keyboardS[60:100, 400:440] = textColorInstructions  # Esc

        keyboardS[120:160, 400:460] = textColorInstructions  # Enter
        keyboardS[160:180, 420:460] = textColorInstructions  # Enter

        keyboardS[120:160, 480:560] = textColorInstructions  # Backspace

        keyboardS[220:260, 400:460] = textColorInstructions  # Tab

        keyboardS[220:260, 500:540] = textColorInstructions  # P

        # text x +10 , -10+y
        cv2.putText(keyboardS, "Exit window", (450, 80), font, 0.8,
                    textColorInstructions, 1, cv2.LINE_AA)  # Esc
        cv2.putText(keyboardS, "Esc", (405, 85), font, 1, textColorLabels, 1,
                    cv2.LINE_AA)  # Esc

        cv2.putText(keyboardS, "Save", (415, 200), font, 0.8,
                    textColorInstructions, 1, cv2.LINE_AA)  # Enter
        cv2.putText(keyboardS, "Enter", (405, 145), font, 1, textColorLabels,
                    1, cv2.LINE_AA)  # Enter

        cv2.putText(keyboardS, "Open viewer", (480, 200), font, 0.8,
                    textColorInstructions, 1, cv2.LINE_AA)  # Backspace
        cv2.putText(keyboardS, "Backspace", (485, 145), font, 0.8,
                    textColorLabels, 1, cv2.LINE_AA)  # Backspace

        cv2.putText(keyboardS, "Switch levels", (385, 280), font, 0.8,
                    textColorInstructions, 1, cv2.LINE_AA)  # Tab
        cv2.putText(keyboardS, "Tab", (410, 245), font, 1, textColorLabels, 1,
                    cv2.LINE_AA)  # Tab

        cv2.putText(keyboardS, "Open Instructions", (475, 280), font, 0.7,
                    textColorInstructions, 1, cv2.LINE_AA)  # Tab
        cv2.putText(keyboardS, "P", (510, 250), font, 2, textColorLabels, 2,
                    cv2.LINE_AA)  # Tab

        # -- tercer cuadrante --             y, x

        # teclas
        keyboardS[340:380, 100:140] = textColorInstructions  # Z

        keyboardS[340:380, 220:260] = textColorInstructions  # M

        keyboardS[410:450, 160:200] = textColorInstructions  # X

        # text                                 x +10 , -10+y
        cv2.putText(keyboardS, "Set Keyframe", (72, 400), font, 0.8,
                    textColorInstructions, 1, cv2.LINE_AA)  # Esc
        cv2.putText(keyboardS, "Z", (110, 370), font, 2, textColorLabels, 2,
                    cv2.LINE_AA)  # Esc

        cv2.putText(keyboardS, "Go back to Keyframe", (175, 400), font, 0.8,
                    textColorInstructions, 1, cv2.LINE_AA)  # Enter
        cv2.putText(keyboardS, "M", (228, 370), font, 2, textColorLabels, 2,
                    cv2.LINE_AA)  # Enter

        cv2.putText(keyboardS, "Apply annotations to other levels", (75, 465),
                    font, 0.8, textColorInstructions, 1, cv2.LINE_AA)  # Enter
        cv2.putText(keyboardS, "X", (168, 440), font, 2, textColorLabels, 2,
                    cv2.LINE_AA)  # Enter

        # -- cuarto cuadrante --             y, x

        # teclas
        keyboardS[340:380, 400:440] = textColorInstructions  # 1

        keyboardS[360:365, 455:460] = textColorInstructions  # dot
        keyboardS[360:365, 475:480] = textColorInstructions  # dot
        keyboardS[360:365, 495:500] = textColorInstructions  # dot

        keyboardS[340:380, 520:560] = textColorInstructions  # +

        # text                                 x +10 , -10+y
        cv2.putText(keyboardS, "Numpad - change label", (400, 400),font, 0.8,
                    textColorInstructions, 1, cv2.LINE_AA)  # Esc
        cv2.putText(keyboardS, "1", (410, 370), font, 2, textColorLabels, 2,
                    cv2.LINE_AA)  # Esc

        cv2.putText(keyboardS, "+", (525, 370), font, 2, textColorLabels, 2,
                    cv2.LINE_AA)  # Enter

        # end
        pos = (int(instructionsWidth / 2) + 100, 460)
        cv2.putText(keyboardS, "-Thank you-", pos, font, 1, (30, 30, 200), 1,
                    cv2.LINE_AA)

        cv2.imshow("Annotation - Instructions", keyboardS)
        cv2.moveWindow("Annotation - Instructions", 200, 200)
        key = cv2.waitKey(0)
        if key == 27:  # Press [Esc] to exit
            break
        if cv2.getWindowProperty("Annotation - Instructions", cv2.WND_PROP_VISIBLE) < 1:
            break
    cv2.destroyWindow("Annotation - Instructions")


# shows window with info
def showInfoWindow():
    while True:
        keyboardInf = np.uint8(np.full((330, 400, 3), backgroundColorMain))

        # titulo
        cv2.putText(
            keyboardInf,
            "-Info-",
            (int(400 / 2) - 50, 25),
            font,
            1.6,
            (colorDict[7][0],colorDict[7][1],colorDict[7][2]),
            2,
            cv2.LINE_AA,
        )

        # Developers
        cv2.putText(
            keyboardInf,
            "Developers:",
            (int(400 / 2) - 75, 60),
            font,
            1.5,
            (colorDict[4][0],colorDict[4][1],colorDict[4][2]),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            keyboardInf,
            "Paola Canas & Juan Diego Ortega",
            (int(400 / 2) - 130, 80),
            font,
            1,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )
        # Thanks to
        cv2.putText(
            keyboardInf,
            "Thanks to:",
            (int(400 / 2) - 75, 130),
            font,
            1.5,
            (colorDict[4][0],colorDict[4][1],colorDict[4][2]),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            keyboardInf,
            "Marcos Nieto",
            (int(400 / 2) - 65, 150),
            font,
            1,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            keyboardInf,
            "Mikel Garcia",
            (int(400 / 2) - 65, 170),
            font,
            1,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            keyboardInf,
            "Eneritz Etxaniz",
            (int(400 / 2) - 65, 190),
            font,
            1,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            keyboardInf,
            "Gonzalo Pierola",
            (int(400 / 2) - 65, 210),
            font,
            1,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            keyboardInf,
            "Itziar Sagastiberri",
            (int(400 / 2) - 65, 230),
            font,
            1,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            keyboardInf,
            "Itziar Urbieta",
            (int(400 / 2) - 65, 250),
            font,
            1,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            keyboardInf,
            "Orti Senderos",
            (int(400 / 2) - 65, 270),
            font,
            1,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )
        # end
        cv2.putText(
            keyboardInf,
            "-Thank YOU-",
            (int(400 / 2) - 65, 310),
            font,
            1,
            (colorDict[7][0], colorDict[7][1], colorDict[7][2]),
            1,
            cv2.LINE_AA,
        )

        cv2.imshow("Annotation - Info", keyboardInf)
        cv2.moveWindow("Annotation - Info", 200, 200)
        key = cv2.waitKey(0)
        if key == 27:  # Press [Esc] to exit
            break
        if cv2.getWindowProperty("Annotation - Info", cv2.WND_PROP_VISIBLE) < 1:
            break
    cv2.destroyWindow("Annotation - Info")


# Change the value of the @annotations and @validations arrays when a frame label is changed
# @annotations: array of lables id per each mosaic video frame
# @validations: array of frame state id per each mosaic video frame
# @count: actual mosaic video frame position
# @mode: actual level of annotation
# @ann_value: label id of the frame to be changed
def update_annotation(annotations, validations, count, mode, ann_value):
    global key_frame
    if key_frame == -1:
        annotations[count - 1][mode] = ann_value
        validations[count - 1][mode] = 1
    # Annotate per block
    else:
        # Block annotation
        # Check starting and ending frame
        start = key_frame if key_frame <= count - 1 else count - 1
        end = count if key_frame <= count - 1 else key_frame + 1
        for ann, val in zip(annotations[start:end], validations[start:end]):
            if ann[mode] != 100:
                ann[mode] = ann_value
                val[mode] = 2
        key_frame = -1
        count -= 1
    return count


# Apply/propagate logical related annotations from level 6 to other levels
# Ex: If driver is Texting Left (Driver_actions level) then also is Only Right (hands_on_wheel level)
# @annotations: array of lables id per each mosaic video frame
# @applyLevels: True if levels have already been changed
def changeInLevels(annotations, applyLevels):
    alertWindowHeight = 160
    alertWindowWidth = 720
    alertS = np.uint8(
        np.full((alertWindowHeight, alertWindowWidth, 3), backgroundColorMain)
    )
    alertS[0:15, 0:alertWindowWidth] = colorDict[12]
    alertS[145:160, 0:alertWindowWidth] = colorDict[12]
    if not applyLevels:
        cv2.putText(
            alertS,
            "All levels of annotation will be modified",
            (25, 50), font, 2, (colorDict[7][0], colorDict[7][1], colorDict[7][2]) , 2, cv2.LINE_AA,
        )
        cv2.putText(
            alertS,
            setUpManager._interfaceTexts["mainLevelDependency"][setUpManager._annotation_mode],
            (65, 75), font, 2, (colorDict[7][0], colorDict[7]
                                [1], colorDict[7][2]), 2, cv2.LINE_AA,
        )
        cv2.putText(
            alertS,
            setUpManager._interfaceTexts["levelCompletedToAnnotate"][setUpManager._annotation_mode],
            (60, 105), font, 1, (colorDict[5][0],colorDict[5][1],colorDict[5][2]), 1, cv2.LINE_AA,
        )
        cv2.putText(
            alertS,
            "Press Y (yes) or N (no)",
            (260, 125), font, 1, (colorDict[5][0],colorDict[5][1],colorDict[5][2]), 1, cv2.LINE_AA,
        )
    else:
        cv2.putText(
            alertS,
            "You have already changed the annotations from all levels",
            (70, 60), font, 1.2, (colorDict[5][0],colorDict[5][1],colorDict[5][2]), 1, cv2.LINE_AA,
        )
        cv2.putText(
            alertS,
            "If you really need to do it again, restart the tool",
            (105, 110), font, 1.2, (colorDict[5][0],colorDict[5][1],colorDict[5][2]), 1, cv2.LINE_AA,
        )

    #validate if user really wants to perform this change
    #User accepts pressing [y]
    while True:
        cv2.imshow("Annotation - alert", alertS)
        cv2.moveWindow("Annotation - alert", 400, 400)
        keyChange = cv2.waitKey(0)
        if (
                keyChange == 27
                or keyChange == ord("y")
                or keyChange == ord("Y")
                or keyChange == ord("n")
                or keyChange == ord("N")
        ):
            break
        if cv2.getWindowProperty("Annotation - alert", cv2.WND_PROP_VISIBLE) < 1:
            break
    cv2.destroyWindow("Annotation - alert")
    if not applyLevels:
        if keyChange == ord("y") or keyChange == ord("Y"):
            newAnn = []
            for ann in annotations:
                if setUpManager._annotation_mode == "distraction":
                    newAnn.append(getDistractionAnnotationLine(ann[6], 1))
                elif setUpManager._annotation_mode == "drowsiness":
                    newAnn.append(getDrowAnnotationLine(ann, 1))
            # return new annotation array with all levels changed depending on level 0
            return newAnn, True
        else:
            return [], False
    else:
        return [], False


# Shows window with mosaic from dmd and window with Labels
# @annotations: array of class id per each body-video frame
def showMosaic(mosaicVideo, annotations, validations):
    global statics
    """
    mode = 0:A0, 1:A1, 2:A2, 3:A3, 4:A4, 5:A5, 6:A6
    """
    # @mode: annotation level
    mode = 0
    # @count: present frame number in video and in annotation array
    count = 0
    # @next_frame: True if the next frame that will be show is next in video, False otherwise
    next_frame = False
    # @applyLevels: True if all levels of annotation has been modifyed by level of actions
    applyLevels = False
    # @firstMove: True to move the windows at specific positions. To do it just once
    firstMove = True
    # @t: time from last saving
    timeSave = "Not saved!"
    # @key: the code of the key pressed
    key = ""

    global first
    global frameInfo
    global key_frame

    key_frame = -1
    last_frame = (
        count  # This value allows to jump to key_frame if selected or to last frame
    )
    while True:
        try:
            # ----SHOW MAIN WINDOW----
            # Move windows to specific positions and set ideal sizes once
            if firstMove:
                cv2.namedWindow("Annotation - Labels", flags=cv2.WINDOW_GUI_NORMAL)
                cv2.namedWindow("Annotation - main", flags=cv2.WINDOW_GUI_NORMAL)
                cv2.namedWindow(
                    "Annotation - visualization", flags=cv2.WINDOW_GUI_NORMAL
                )

                cv2.resizeWindow(
                    "Annotation - Labels", width_Labels - 10, total_height + 35
                )
                cv2.resizeWindow(
                    "Annotation - main", total_width - 10, total_height + 35
                )
                cv2.resizeWindow(
                    "Annotation - visualization", visualWidth, visualHeight + 48
                )

                cv2.moveWindow("Annotation - main", 10, 20)
                cv2.moveWindow("Annotation - visualization", 10, total_height + 110)
                cv2.moveWindow("Annotation - Labels", windowSeparation, 20)
                firstMove = False

            # If the count is not out of bounds and key is not the [BACKSPACE], then show window
            if 0 <= count <= frameNumber:
                # If the key is not [ENTER] OR [TAB], then change video frame
                if key != 9 and key != 13:
                    # If we don't have to update the frame, use the previous image
                    # or capture first image if it is the first time
                    if last_frame != count or first:
                        # if is not the next frame, then set the desired frame
                        if not next_frame:
                            mosaicVideo.set(cv2.CAP_PROP_POS_FRAMES, count)
                        retMosaic, frameMosaic = mosaicVideo.read()

                if first:
                    frameInfo = frameMosaic[108: 62 + 100,
                                w2 + 200: w2 + 200 + 162]  # 54x162
                    first = False
                    last_frame = count  # Set @last_frame for the first time
                    # show Labels window for the first time
                    showLabelsWindow(mode)
                # Get body,face,hands video rectangles
                faceRec, bodyRec, handsRec = getVideoRecs(frameMosaic)

                # --- MOSAIC VIDEO --- #
                # Draw white background
                mosaicS = np.uint8(
                    np.full((total_height, total_width, 3), backgroundColorMain)
                )

                # Draw video rectangles
                mosaicS[h2:height, 0:w2] = faceRec

                mosaicS[height - shrinkdim[1]: height, w2:total_width] = handsRec
                mosaicS[
                height - 2 * shrinkdim[1]: height - shrinkdim[1], w2:total_width
                ] = bodyRec

                # Videos frame info
                padding = 50
                cv2.putText(
                    mosaicS,
                    "Welcome :)",
                    (padding, 25), font, 0.8, (colorDict[7][0],
                                               colorDict[7][1], colorDict[7][2]), 1, cv2.LINE_AA,
                )
                cv2.putText(
                    mosaicS,
                    "Body video frame: " + str(count - shift_bf),
                    (padding, 55), font, 0.9, textColorMain, 1, cv2.LINE_AA,
                )
                cv2.putText(
                    mosaicS,
                    "Hands video frame: " + str(count - shift_bf - shift_hb),
                    (padding, 70), font, 0.9, textColorMain, 1, cv2.LINE_AA,
                )

                # --- FRAME INFO --- #
                # show "Last frames" sign on the last 5 frames
                if count > frameNumber - 5:
                    cv2.putText(
                        mosaicS,
                        "Last frames!",
                        (padding + 55, int(h2 / 2) - 40),
                        font, 1, textColorMain, 1, cv2.LINE_AA,
                    )
                if count != frameNumber:
                    cv2.putText(
                        mosaicS,
                        str(count),
                        (padding + 55, int(h2 / 2)),  # 1035
                        font, 3, (colorDict[7][0], colorDict[7][1], colorDict[7][2]), 2, cv2.LINE_AA,
                    )
                else:
                    cv2.putText(
                        mosaicS,
                        "LAST FRAME",
                        (padding + 55, int(h2 / 2) - 10),  # 1022
                        font, 1, textColorMain, 2, cv2.LINE_AA)
                cv2.putText(
                    mosaicS,
                    "Mosaic frame",
                    (padding + 55, int(h2 / 2) + 20),
                    font, 1, textColorMain, 1, cv2.LINE_AA,
                )

                # Key frame sign
                if key_frame >= 0:
                    blockSize = abs(count - key_frame) + 1
                    cv2.putText(
                        mosaicS,
                        "Frames selected: ",
                        (padding, h2 - 110),  # 1022
                        font, 1, textColorMain, 1, cv2.LINE_AA,
                    )
                    cv2.putText(
                        mosaicS,
                        str(blockSize),
                        (padding + 150, h2 - 110),  # 1022
                        font, 1.4, textColorMain, 1, cv2.LINE_AA,
                    )
                    cv2.putText(
                        mosaicS,
                        "Key Frame: " + str(key_frame),
                        (padding, h2 - 90),  # 1022
                        font, 1, textColorMain, 1, cv2.LINE_AA,
                    )
                    cv2.putText(
                        mosaicS,
                        "Press [m] to go back to key frame",
                        (padding, h2 - 70),# 1022
                        font, 0.7, textColorMain, 1, cv2.LINE_AA,
                    )
                    mosaicS[h2 - 120: h2 - 70, padding - 20: padding - 10] = \
                        keyFrameColor

                # preview video
                cv2.putText(
                    mosaicS,
                    ". To preview annotations",
                    (padding, h2 - 35),
                    font, 0.8, textColorMain, 1, cv2.LINE_AA,
                )
                cv2.putText(
                    mosaicS,
                    "press [BACKSPACE]",
                    (padding, h2 - 20),
                    font, 0.8, textColorMain, 1, cv2.LINE_AA,
                )

                # --- ACTUAL ANNOTATIONS INFO --- #
                line = 30
                h_line = 48
                bold = np.zeros(len(dic_names))
                bold[mode] = 1
                padding = int(w2 / 2) + 35
                for j, i in enumerate(bold):
                    cv2.putText(
                        mosaicS,
                        ("Level: " + dic_names[j]),
                        (padding, (line + j * h_line)),
                        font, 1, textColorMain, 1, cv2.LINE_AA,
                    )
                    
                    cv2.putText(
                        mosaicS,
                        dic_levels[j][annotations[count][j]],
                        (padding, (26 + line + j * h_line)),
                        font, 1.5, textColorMain, int((1 * i) + 1), cv2.LINE_AA,
                    )
                    # Arrow
                    cv2.putText(
                        mosaicS,
                        "->",
                        (padding - 50, (26 + line + j * h_line)),
                        font, 1.5 * i, (colorDict[7][0], colorDict[7][1], colorDict[7][2]), int((1 * i) + 1), cv2.LINE_AA,
                    )

                # --- INSTRUCTIOS AND LAST SAVED --- #
                cv2.putText(
                    mosaicS,
                    ". To OPEN INSTRUCTIONS press [P]",
                    (w2 + 110, 45),
                    font, 1, (30, 30, 200), 1, cv2.LINE_AA,
                )
                cv2.putText(
                    mosaicS,
                    "Last saved at: " + timeSave,
                    (w2 + 110, 80),
                    font, 1.4, textColorMain, 1, cv2.LINE_AA,
                )

                if not staticExists:
                    cv2.putText(
                        mosaicS,
                        "Not static annotations yet",
                        (w2 + 115, 90),
                        font,
                        1,
                        (colorDict[7][0], colorDict[7][1], colorDict[7][2]),
                        1,
                        cv2.LINE_AA,
                    )
                cv2.imshow("Annotation - main", mosaicS)

            else:
                pass

            annArray = np.array(annotations)
            validArray = np.array(validations)
            if 0 <= count <= frameNumber:
                # update color annotation bar
                showTimeLine(annArray[:, mode], count, validArray[:, mode])
            elif count - 1 == frameNumber:
                # We are at the end of the video
                # update color annotation bar
                showTimeLine(annArray[:, mode], count - 1, validArray[:, mode])

            # ----WAIT FOR INSTRUCTION----
            key = cv2.waitKeyEx(0)
            next_frame = False
            if key == 27:  # Press [ESC] to quit

                # save(annotations, validations, True)
                if not staticExists and setUpManager._pre_annotate:
                    print("Please complete the static annotations")
                    statics = setStaticAnnotations()
                save(annotations, validations, True)
                break
            # press [space] or [left arrow] to go back
            elif key == 32 or hex(key) == "0x250000" or hex(key) == "0xff51":
                # If the end of the video was reached, subtract one more frame to successfully
                # go back one frame
                if count - 1 == frameNumber:
                    count = count - 1
                last_frame = count
                if count - 1 >= 0:
                    count = count - 1
            # 84:  # press [TAB] to switch between Levels of annotation
            elif key == 9:
                if mode + 1 < num_levels:
                    mode = mode + 1
                else:
                    mode = 0
                key_frame = -1
                # refresh instruction window
                showLabelsWindow(mode)
            elif key == 13:  # press [ENTER] to save annotations
                save(annotations, validations, True)
                now = datetime.datetime.now()  # + datetime.timedelta(hours=1)
                timeSave = now.strftime("%H:%M:%S")
            elif key == 8:  # press [BACKSPACE] to open viewer
                save(annotations, validations, False)
                if setUpManager._dataset_dmd:
                    count = showLiveAnnotationsDMD(
                        count, mosaicVideo, annotations, validations, mode
                    )
                else:
                    count = showLiveAnnotationsGeneral(
                        count, mosaicVideo, annotations, validations, mode
                    )

            # press [p] to open Instructions window
            elif key == ord("p") or key == ord("P"):
                showInstructionsWindow()
            # press [o] to open Instructions window
            elif key == ord("o") or key == ord("O"):
                statics = setStaticAnnotations()
            # press [i] to open info window
            elif key == ord("i") or key == ord("I"):
                showInfoWindow()
            # press [w] to move 50 frames backwards
            elif key == ord("w") or key == ord("W"):
                last_frame = count
                if count - 50 >= 0:
                    count = count - 50
                elif count - 1 >= 0:
                    count = count - 1
            # press [e] to move 50 frames forward
            elif key == ord("e") or key == ord("E"):
                last_frame = count
                if count + 50 < frameNumber:
                    count = count + 50
            # press [q] to move 300 frames backwards
            elif key == ord("q") or key == ord("Q"):
                last_frame = count
                if count - 300 > 0:
                    count = count - 300
            # press [r] to move 300 frames forward
            elif key == ord("r") or key == ord("R"):
                last_frame = count
                if count + 300 < frameNumber:
                    count = count + 300
            # press [s] to move to next boundary change
            elif key == ord("s") or key == ord("S"):
                last_frame = count
                ann = np.array(annotations)[count:, mode]
                # Compute index of next change in state
                changes = np.where(ann[:-1] != ann[1:])[0]
                count = changes[0] + 1 + count if len(changes) > 0 else count
            # press [a] to move to prev boundary change
            elif key == ord("a") or key == ord("A"):
                last_frame = count
                ann = np.array(annotations)[:count, mode]
                # Compute index of next change in state
                changes = np.where(ann[:-1] != ann[1:])[0]
                count = changes[-1] + 1 if len(changes) > 0 else count
            # press [x] to apply annotation in other levels
            elif key == ord("x") or key == ord("X"):
                if setUpManager._default_annotation_mode:
                    changedAnn, do = changeInLevels(annotations, applyLevels)
                    # if the user pressed Y (yes)
                    if do:
                        annotations = changedAnn
                        applyLevels = True
                else:
                    print("Sorry, this is a function to be developed for non-default annotation modes.")
            # press [z] to set key frame
            elif key == ord("z") or key == ord("Z"):
                key_frame = count if count != key_frame else -1
            # press [m] to go to key frame or last frame
            elif key == ord("m") or key == ord("M"):
                if key_frame != -1 and key_frame != count:
                    last_frame = count
                    count = key_frame
                elif key_frame != -1 and key_frame == count:
                    tmp = count
                    count = last_frame
                    last_frame = tmp
            else:
                if count <= frameNumber:
                    next_frame = True
                    last_frame = count
                    count = count + 1

            # if the actual label is not NAN (there is frame information)
            # Update @annotations and @validations to the selected label with update_annotation()
            # which also substracts one from @count
            if annotations[count - 1][mode] != 100:
                if key == 46 and 99 in dic_levels[mode]:  # press [.] to write label 99 ("--")
                    count = update_annotation(annotations, validations, count, mode, 99)
                elif key == 48 and 0 in dic_levels[mode]:  # press [0] to write label 0 
                    count = update_annotation(annotations, validations, count, mode, 0)
                elif key == 49 and (1 in dic_levels[mode]):  # press [1] to write label 1
                    count = update_annotation(annotations, validations, count, mode, 1)
                elif key == 50 and 2 in dic_levels[mode]:  # press [2] to write label 2
                    count = update_annotation(annotations, validations, count, mode, 2)
                # press [3] to write label 3
                elif key == 51 and 3 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 3)
                # press [4] to write label 4
                elif key == 52 and 4 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 4)
                # press [5] to write label 5
                elif key == 53 and 5 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 5)
                # press [6] to write label 6
                elif key == 54 and 6 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 6)
                # press [7] to write label 7
                elif key == 55 and 7 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 7)
                # press [8] to write label 8
                elif key == 56 and 8 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 8)
                # press [9] to write label 9
                elif key == 57 and 9 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 9)
                # press [/] to write label 10
                elif key == 47 and 10 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 10)
                # press [*] to write label 11
                elif key == 42 and 11 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 11)
                # press [-] to write label 12
                elif key == 45 and 12 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 12)
                # press [+] to write label 13
                elif key == 43 and 13 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 13)

        except Exception as e:
            save(annotations, validations, False)
            print("Unexpected error:", sys.exc_info()[0])
            print(e)
            raise

def showGeneralVideo(mosaicVideo, annotations, validations):
    # @mode: annotation level
    mode = 0
    # @count: present frame number in video and in annotation array
    count = 0
    # @next_frame: True if the next frame that will be show is next in video, False otherwise
    next_frame = False
    # @applyLevels: True if all levels of annotation has been modifyed by level of actions
    applyLevels = False
    # @firstMove: True to move the windows at specific positions. To do it just once
    firstMove = True
    # @t: time from last saving
    timeSave = "Not saved!"
    # @key: the code of the key pressed
    key = ""

    global first
    global frameInfo
    global key_frame

    key_frame = -1
    last_frame = (
        count  # This value allows to jump to key_frame if selected or to last frame
    )
    while True:
        try:
            # ----SHOW MAIN WINDOW----
            # Move windows to specific positions and set ideal sizes once
            if firstMove:
                cv2.namedWindow("Annotation - Labels", flags=cv2.WINDOW_GUI_NORMAL)
                cv2.namedWindow("Annotation - main", flags=cv2.WINDOW_GUI_NORMAL)
                cv2.namedWindow(
                    "Annotation - visualization", flags=cv2.WINDOW_GUI_NORMAL
                )

                cv2.resizeWindow(
                    "Annotation - Labels", width_Labels - 10, total_height + 35
                )
                cv2.resizeWindow(
                    "Annotation - main", total_width - 10, total_height + 35
                )
                cv2.resizeWindow(
                    "Annotation - visualization", visualWidth, visualHeight + 48
                )

                cv2.moveWindow("Annotation - main", 10, 20)
                cv2.moveWindow("Annotation - visualization", 10, total_height + 110)
                cv2.moveWindow("Annotation - Labels", windowSeparation, 20)
                firstMove = False

            # If the count is not out of bounds and key is not the [BACKSPACE], then show window
            if 0 <= count <= frameNumber:
                # If the key is not [ENTER] OR [TAB], then change video frame
                if key != 9 and key != 13:
                    # If we don't have to update the frame, use the previous image
                    # or capture first image if it is the first time
                    if last_frame != count or first:
                        # if is not the next frame, then set the desired frame
                        if not next_frame:
                            mosaicVideo.set(cv2.CAP_PROP_POS_FRAMES, count)
                        retMosaic, frameMosaic = mosaicVideo.read()

                if first:
                    frameInfo = frameMosaic[108: 62 + 100,
                                w2 + 200: w2 + 200 + 162]  # 54x162
                    first = False
                    last_frame = count  # Set @last_frame for the first time
                    # show Labels window for the first time
                    showLabelsWindow(mode)

                

                # --- SHOW VIDEO --- #
                # Draw white background
                mosaicS = np.uint8(
                    np.full((total_height, total_width, 3), backgroundColorMain)
                )
                maxVideoWidth = total_width-300
                newHeight = int(height*maxVideoWidth/width)

                # Draw video on the left
                mosaicS[0:newHeight, infoWidth:total_width] = cv2.resize(frameMosaic,(maxVideoWidth,newHeight))

                
                padding = 60
                cv2.putText(
                    mosaicS,
                    "Welcome :)",
                    (padding, 25), font, 0.8, (colorDict[7][0],
                                               colorDict[7][1], colorDict[7][2]), 1, cv2.LINE_AA,
                )
                # --- ACTUAL ANNOTATIONS INFO --- #
                line = 80
                h_line = 48
                bold = np.zeros(len(dic_names))
                bold[mode] = 1
                #padding = int(w2 / 2) + 35
                for j, i in enumerate(bold):
                    cv2.putText(
                        mosaicS,
                        ("Level: " + dic_names[j]),
                        (padding, (line + j * h_line)),
                        font, 1, textColorMain, 1, cv2.LINE_AA,
                    )
                    
                    cv2.putText(
                        mosaicS,
                        dic_levels[j][annotations[count][j]],
                        (padding, (26 + line + j * h_line)),
                        font, 1.5, textColorMain, int((1 * i) + 1), cv2.LINE_AA,
                    )
                    # Arrow
                    cv2.putText(
                        mosaicS,
                        "->",
                        (padding - 50, (26 + line + j * h_line)),
                        font, 1.5 * i, (colorDict[7][0], colorDict[7][1], colorDict[7][2]), int((1 * i) + 1), cv2.LINE_AA,
                    )
                
                
                padding = int(w2 / 2) + 20
                
                # --- FRAME INFO --- #
                # show "Last frames" sign on the last 5 frames
                if count > frameNumber - 5:
                    cv2.putText(
                        mosaicS,
                        "Last frames!",
                        (padding , total_height-80),
                        font, 1, textColorMain, 1, cv2.LINE_AA,
                    )
                if count != frameNumber:
                    cv2.putText(
                        mosaicS,
                        str(count),
                        (padding , total_height-120),  # 1035
                        font, 3, (colorDict[7][0], colorDict[7][1], colorDict[7][2]), 2, cv2.LINE_AA,
                    )
                else:
                    cv2.putText(
                        mosaicS,
                        "LAST FRAME",
                        (padding +5, total_height-140),  # 1022
                        font, 1, textColorMain, 2, cv2.LINE_AA)
                cv2.putText(
                    mosaicS,
                    "Frame number",
                    (padding , total_height-100),
                    font, 1, textColorMain, 1, cv2.LINE_AA,
                )

                # Key frame sign
                if key_frame >= 0:
                    blockSize = abs(count - key_frame) + 1
                    cv2.putText(
                        mosaicS,
                        "Frames selected: ",
                        (padding, total_height - 70),  # 1022
                        font, 1, textColorMain, 1, cv2.LINE_AA,
                    )
                    cv2.putText(
                        mosaicS,
                        str(blockSize),
                        (padding + 150, total_height - 70),  # 1022
                        font, 1.4, textColorMain, 1, cv2.LINE_AA,
                    )
                    cv2.putText(
                        mosaicS,
                        "Key Frame: " + str(key_frame),
                        (padding, total_height - 50),  # 1022
                        font, 1, textColorMain, 1, cv2.LINE_AA,
                    )
                    cv2.putText(
                        mosaicS,
                        "Press [m] to go back to key frame",
                        (padding, total_height - 30),# 1022
                        font, 0.7, textColorMain, 1, cv2.LINE_AA,
                    )
                    mosaicS[total_height - 80: total_height - 30, padding - 20: padding - 10] = \
                        keyFrameColor

                

                # --- INSTRUCTIOS AND LAST SAVED --- #
                # preview video
                padding = int(w2 / 2) + 580
                cv2.putText(
                    mosaicS,
                    ". To preview annotations press [BACKSPACE]",
                    (padding, total_height - 70),
                    font, 0.8, textColorMain, 1, cv2.LINE_AA,
                )
                cv2.putText(
                    mosaicS,
                    ". To OPEN INSTRUCTIONS press [P]",
                    (padding, total_height - 115),
                    font, 1, (30, 30, 200), 1, cv2.LINE_AA,
                )
                padding = int(w2 / 2) + 200
                cv2.putText(
                    mosaicS,
                    "Last saved at: " + timeSave,
                    (padding, total_height - 95),
                    font, 1.4, textColorMain, 1, cv2.LINE_AA,
                )

                
                cv2.imshow("Annotation - main", mosaicS)

            else:
                pass

            annArray = np.array(annotations)
            validArray = np.array(validations)
            if 0 <= count <= frameNumber:
                # update color annotation bar
                showTimeLine(annArray[:, mode], count, validArray[:, mode])
            elif count - 1 == frameNumber:
                # We are at the end of the video
                # update color annotation bar
                showTimeLine(annArray[:, mode], count - 1, validArray[:, mode])

            # ----WAIT FOR INSTRUCTION----
            key = cv2.waitKeyEx(0)
            next_frame = False
            if key == 27:  # Press [ESC] to quit
                save(annotations, validations, True)
                break
            # press [space] or [left arrow] to go back
            elif key == 32 or hex(key) == "0x250000" or hex(key) == "0xff51":
                # If the end of the video was reached, subtract one more frame to successfully
                # go back one frame
                if count - 1 == frameNumber:
                    count = count - 1
                last_frame = count
                if count - 1 >= 0:
                    count = count - 1
            # 84:  # press [TAB] to switch between Levels of annotation
            elif key == 9:
                if mode + 1 < num_levels:
                    mode = mode + 1
                else:
                    mode = 0
                key_frame = -1
                # refresh instruction window
                showLabelsWindow(mode)
            elif key == 13:  # press [ENTER] to save annotations
                save(annotations, validations, True)
                now = datetime.datetime.now()  # + datetime.timedelta(hours=1)
                timeSave = now.strftime("%H:%M:%S")
            elif key == 8:  # press [BACKSPACE] to open viewer
                save(annotations, validations, False)
                if setUpManager._dataset_dmd:
                    count = showLiveAnnotationsDMD(
                        count, mosaicVideo, annotations, validations, mode
                    )
                else:
                    count = showLiveAnnotationsGeneral(
                        count, mosaicVideo, annotations, validations, mode
                    )
            # press [p] to open Instructions window
            elif key == ord("p") or key == ord("P"):
                showInstructionsWindow()
            # press [i] to open info window
            elif key == ord("i") or key == ord("I"):
                showInfoWindow()
            # press [w] to move 50 frames backwards
            elif key == ord("w") or key == ord("W"):
                last_frame = count
                if count - 50 >= 0:
                    count = count - 50
                elif count - 1 >= 0:
                    count = count - 1
            # press [e] to move 50 frames forward
            elif key == ord("e") or key == ord("E"):
                last_frame = count
                if count + 50 < frameNumber:
                    count = count + 50
            # press [q] to move 300 frames backwards
            elif key == ord("q") or key == ord("Q"):
                last_frame = count
                if count - 300 > 0:
                    count = count - 300
            # press [r] to move 300 frames forward
            elif key == ord("r") or key == ord("R"):
                last_frame = count
                if count + 300 < frameNumber:
                    count = count + 300
            # press [s] to move to next boundary change
            elif key == ord("s") or key == ord("S"):
                last_frame = count
                ann = np.array(annotations)[count:, mode]
                # Compute index of next change in state
                changes = np.where(ann[:-1] != ann[1:])[0]
                count = changes[0] + 1 + count if len(changes) > 0 else count
            # press [a] to move to prev boundary change
            elif key == ord("a") or key == ord("A"):
                last_frame = count
                ann = np.array(annotations)[:count, mode]
                # Compute index of next change in state
                changes = np.where(ann[:-1] != ann[1:])[0]
                count = changes[-1] + 1 if len(changes) > 0 else count
            # press [z] to set key frame
            elif key == ord("z") or key == ord("Z"):
                key_frame = count if count != key_frame else -1
            # press [m] to go to key frame or last frame
            elif key == ord("m") or key == ord("M"):
                if key_frame != -1 and key_frame != count:
                    last_frame = count
                    count = key_frame
                elif key_frame != -1 and key_frame == count:
                    tmp = count
                    count = last_frame
                    last_frame = tmp
            elif key == ord("x") or key == ord("X"):
                if setUpManager._default_annotation_mode:
                    changedAnn, do = changeInLevels(annotations, applyLevels)
                    # if the user pressed Y (yes)
                    if do:
                        annotations = changedAnn
                        applyLevels = True
                else:
                    print("Sorry, this is a function to be developed for non-default annotation modes.")
            else:
                if count <= frameNumber:
                    next_frame = True
                    last_frame = count
                    count = count + 1

            # if the actual label is not NAN (there is frame information)
            # Update @annotations and @validations to the selected label with update_annotation()
            # which also substracts one from @count
            if annotations[count - 1][mode] != 100:
                if key == 46 and 99 in dic_levels[mode]:  # press [.] to write label 99 ("--")
                    count = update_annotation(annotations, validations, count, mode, 99)
                elif key == 48 and 0 in dic_levels[mode]:  # press [0] to write label 0 
                    count = update_annotation(annotations, validations, count, mode, 0)
                elif key == 49 and (1 in dic_levels[mode]):  # press [1] to write label 1
                    count = update_annotation(annotations, validations, count, mode, 1)
                elif key == 50 and 2 in dic_levels[mode]:  # press [2] to write label 2
                    count = update_annotation(annotations, validations, count, mode, 2)
                # press [3] to write label 3
                elif key == 51 and 3 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 3)
                # press [4] to write label 4
                elif key == 52 and 4 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 4)
                # press [5] to write label 5
                elif key == 53 and 5 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 5)
                # press [6] to write label 6
                elif key == 54 and 6 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 6)
                # press [7] to write label 7
                elif key == 55 and 7 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 7)
                # press [8] to write label 8
                elif key == 56 and 8 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 8)
                # press [9] to write label 9
                elif key == 57 and 9 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 9)
                # press [/] to write label 10
                elif key == 47 and 10 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 10)
                # press [*] to write label 11
                elif key == 42 and 11 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 11)
                # press [-] to write label 12
                elif key == 45 and 12 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 12)
                # press [+] to write label 13
                elif key == 43 and 13 in dic_levels[mode]:
                    count = update_annotation(annotations, validations, count, mode, 13)

        except Exception as e:
            save(annotations, validations, False)
            print("Unexpected error:", sys.exc_info()[0])
            print(e)
            raise

def getMetadataFromFile():
    bag_name = str(setUpManager._video_file_path.name).replace("avi", "bag")
    meta = open(str(setUpManager._metadata_file_path), "r")
    with meta:
        reader = csv.DictReader(meta)
        for row in reader:
            if bag_name.replace("mosaic", "face") in str(Path(row["file"])):
                intr = row["rgb_intrinsics"].strip("][").split(", ")
                intr = np.array([float(i) for i in intr])
                mat = [
                    intr[0],
                    intr[1],
                    intr[2],
                    0.0,
                    intr[3],
                    intr[4],
                    intr[5],
                    0.0,
                    intr[6],
                    intr[7],
                    intr[8],
                    0.0,
                ]
                face_meta = [row["rgb_video_frames"], mat]
            if bag_name.replace("mosaic", "body") in str(Path(row["file"])):
                intr = row["rgb_intrinsics"].strip("][").split(", ")
                intr = np.array([float(i) for i in intr])
                mat = [
                    intr[0],
                    intr[1],
                    intr[2],
                    0.0,
                    intr[3],
                    intr[4],
                    intr[5],
                    0.0,
                    intr[6],
                    intr[7],
                    intr[8],
                    0.0,
                ]
                body_meta = [row["datetime"], row["rgb_video_frames"], mat]
            if bag_name.replace("mosaic", "hands") in str(Path(row["file"])):
                intr = row["rgb_intrinsics"].strip("][").split(", ")
                intr = np.array([float(i) for i in intr])
                mat = [
                    intr[0],
                    intr[1],
                    intr[2],
                    0.0,
                    intr[3],
                    intr[4],
                    intr[5],
                    0.0,
                    intr[6],
                    intr[7],
                    intr[8],
                    0.0,
                ]
                hands_meta = [row["rgb_video_frames"], mat]
                break
    return [face_meta, body_meta, hands_meta]

def setStaticAnnotations():
    static_temp = statics_dic
    for att in static_temp:
        print(static_temp[att]["text"], ":")
        if not static_temp[att]["type"] == "num":
            if "options" in static_temp[att].keys():
                for op in static_temp[att]["options"]:
                    print(op, static_temp[att]["options"][op])
            res = input()
            if not static_temp[att]["type"] == "boolean":

                # text
                if "options" not in static_temp[att].keys():
                    static_temp[att].update({"val": res})
                else:
                    while True:
                        if int(res) in static_temp[att]["options"].keys():
                            break
                        else:
                            print("Option not valid")
                            res = input()
                    static_temp[att].update({"val": static_temp[att]["options"][int(res)]})

            else:
                # boolean
                while True:
                    if int(res) in static_temp[att]["options"].keys():
                        break
                    else:
                        print("Option not valid")
                        res = input()
                static_temp[att].update({"val": bool(int(res))})
        else:
            res = input()
            # num
            static_temp[att].update({"val": int(res)})
    print("You're done")

    return static_temp

# ------ GLOBAL VARIABLES ------
# --Create setUp_tato object for paths and config variables--
setUpManager = ConfigTato()

external_struct = setUpManager._external_struct
metadataProvFile = Path(str(setUpManager._autoSave_file_path).replace("-A", "-B"))
statics_dic = setUpManager.get_statics_dict()
#annotations existance
existAutoSaveAnn = Path(setUpManager._autoSave_file_path).exists()
existIntelAnn = False
existPreAnn = False
if setUpManager._pre_annotate:
    existIntelAnn = Path(setUpManager._intelAnn_file_path).exists()
    existPreAnn = Path(setUpManager._preAnn_file_path).exists()

# Interval annotation
key_frame = -1

_, dic_names, dic_defaults, _, dic_levels, camera_dependencies, num_levels = setUpManager.get_annotation_config()
dic_names = list(dic_names.values())
# Create VCD Parser object, if vcd_file doesn't exist the handler will create an empty object
if (setUpManager._dataset_dmd):
    vcd_handler = DMDVcdHandler(setUpManager)
else:
    vcd_handler = VcdHandler(setUpManager)

#--Check if static annotations and metadata already exists in vcd file--
staticExists = False
metadataExists = False
if vcd_handler.file_loaded() and setUpManager._dataset_dmd:
    staticExists = vcd_handler.verify_statics(statics_dic, 0)
    metadataExists = vcd_handler.verify_metadata(0)

# -- Time --
# when the tool opens, to calculate time expended
GLOBAL_opening_time = datetime.datetime.now()
GLOBAL_opening_time = datetime.timedelta(
    hours=GLOBAL_opening_time.hour,
    minutes=GLOBAL_opening_time.minute,
    seconds=GLOBAL_opening_time.second,
)

# -- Build interface --
# load video
mosaicVideo = cv2.VideoCapture(str(setUpManager._video_file_path))
width = int(mosaicVideo.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(mosaicVideo.get(cv2.CAP_PROP_FRAME_HEIGHT))
h2 = int(height / 2)
w2 = int(width / 2)

total_width = setUpManager._dimensions["total-width"]
total_height = setUpManager._dimensions["total-height"]
up_space = 70
down_space = 50
infoWidth = 300 #Width of info visualization for no mosaic videos

# - Dimensions of the Mosaic Video -
if setUpManager._dataset_dmd:
    # @shrinkPercentage: the percentage of shrinking of the body and face video rectangles
    shrinkPercentage = 85
    # new dimensions after shrinking
    shrinkdim = (int(shrinkPercentage * w2 / 100),
                int(shrinkPercentage * h2 / 100))

    # - Dimensions of windows -
    total_height = height
    total_width = w2 + shrinkdim[0]

# @frameNumber: total number of frames. -1 for showing frames position starting from 0
frameNumber = int(mosaicVideo.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
# @first: control variable to extract the videos offset info from mosaic frame once
first = True
# @frameInfo: shifts info rectangle from mosaicVideo
frameInfo = []
# dimensions for the Labels window
windowSeparation = total_width + 20
width_Labels = 400
# dimensions for the Instructions window
instructionsWidth = 640
instructionsHeight = 500
# dimensions for Timeline window
# @visualWidth: number of pixels of the bar
visualWidth = windowSeparation + width_Labels
visualHeight = 140

# - Font and Colors -
font = cv2.FONT_HERSHEY_PLAIN
textColorMain = (setUpManager._colorConfig["textColorMain"][0], setUpManager._colorConfig[
    "textColorMain"][1], setUpManager._colorConfig["textColorMain"][2])
textColorLabels = (setUpManager._colorConfig["textColorLabels"][0], setUpManager._colorConfig[
    "textColorLabels"][1], setUpManager._colorConfig["textColorLabels"][2])
textColorInstructions = (setUpManager._colorConfig["textColorInstructions"][0], setUpManager._colorConfig[
    "textColorInstructions"][1], setUpManager._colorConfig["textColorInstructions"][2])
backgroundColorMain = setUpManager._colorConfig["backgroundColorMain"]
backgroundColorLabels = setUpManager._colorConfig["backgroundColorLabels"]
backgroundColorInstructions = setUpManager._colorConfig["backgroundColorInstructions"]
keyFrameColor = (setUpManager._colorConfig["keyFrameColor"][0], setUpManager._colorConfig[
    "keyFrameColor"][1], setUpManager._colorConfig["keyFrameColor"][2])
# color dictionary
colorDict = setUpManager._colorConfig["colorDict"]
#static and metadata info for VCD
statics = {}
metadata = {}

# ----EXECUTION ----
# Load shifts, pre annotations and validation info
# @shift_bf: indicates how many zero images need to be inserted at BODY video wrt Face
# @shift_hb: indicates how many zero images need to be inserted at HANDS video wrt Body
if setUpManager._dataset_dmd:
    shift_bf, shift_hb, \
        annotation_list, validation_list, \
        statics, metadata = loadPropertiesDMD()
else:
    shift_bf = 0
    shift_hb = 0
    annotation_list, validation_list = loadPropertiesGeneral()
# create vcd if did not exist
if not vcd_handler.file_loaded():
    save(annotation_list, validation_list, True)

if setUpManager._dataset_dmd:   
    # Show video, Labels window and timeline bar
    
    showMosaic(mosaicVideo, annotation_list, validation_list)
else:
    showGeneralVideo(mosaicVideo,annotation_list, validation_list)

mosaicVideo.release()
cv2.destroyAllWindows()

