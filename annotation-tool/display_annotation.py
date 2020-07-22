# -*- coding: utf-8 -*-
import datetime
import json
import sys
from pathlib import Path  # To handle paths independent of OS

import cv2
import numpy as np

# Import local class to parse VCD content
from vcd4parser import VcdHandler


# ----A2-DTool----
# Written by Paola Cañas and Juan Diego Ortega - 07-02-2020 - with <3


# Python and Opencv script to make corrections to the pre annotations or/and annotate the DMD.
# Displays one mosaic video and offers a frame-per-frame annotation of differen levels of annotation
# Starts with pre-annotations from model inference (not available for external structures)
# Reads and writes annotations in VCD, saving temporary backups in txt.
# The annotation data for the tool is represented in lists/arrays where each row is a frame and a column is an annotation level.

#This tool is prepared to work inside DMD Developers internal structure and external structure. 

# Run it through bash script ./annotate.sh

#-----

# Set up annotations in all levels depending on driver_actions level annotation.
# For the annotation of DMD, some dependencies and relations have been stablished between labels from different levels.
# This functions contains those relations and constrains between labels. 
# In case of other applications of the tool, these must be changed. 
# @bodyAnnId: id of the annotation from level 6
# @frameInfoId: id to identify what frames are avaliable
def getAnnotationLine(bodyAnnId, frameInfoId):
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


# Load shifts, annotations, and validation info of the mosaic video
# shifts are in "shifts_group.txt" and annotations and validation info are in ".._ann.txt"
def loadProperties():
    shift_bf = 0
    shift_hb = 0
    annotation = []
    validation = []
    global staticExists
    # ---- SHIFTS ----
    # Find shifts
    if vcd_handler.fileLoaded():
        # Load shifts from VCD
        shift_bf, _, shift_hb = vcd_handler.getShifts()
        print("\nLoading shifts from VCD..")
    # To read the shifts of body, face and hands videos
    elif not vcd_handler.fileLoaded() and not external_struct:
        print("\nLoading shifts from txt..")

        shifts = open(str(shiftsFile))
        # Find the shifts for the current video
        for shift_line in shifts:
            spl_str = shift_line.split(":")
            if str(actualVideo) in spl_str[0]:
                shift_bf = int(spl_str[1])
                shift_hb = int(spl_str[2])
        shifts.close()
        # Set this shifts files in the vcd handler
        vcd_handler.setShifts(
            body_face_shift=shift_bf,
            hands_body_shift=shift_hb,
            hands_face_shift=shift_bf + shift_hb)
    elif not createNewAnn and external_struct:
    #Load shifts from metadata autoSave file (..autoSaveAnn-B.txt)
    #done later when metadata is recovered from autosave file 
        pass

    else:
        raise RuntimeError("There was a problem loading stream shifts")

    # ---- STATIC ANN ----
    if vcd_handler.fileLoaded():
        # Check if there are static annotations:
        if staticExists:
            # !!In this case is a Dictionary
            print("\nThese are the static annotations ->")
            # (dic, object_id)
            static = vcd_handler.getStaticVector(statics_dic, 0)
            meta = vcd_handler.getMetadataVector(0)
            for val in static:
                print(val["name"], ":", val["val"])
            print("record_time:", meta[1][0])
            print("face_frames:", meta[0][0])
            print("body_frames:", meta[1][1])
            print("hands_frames:", meta[2][0])

    # ---- ANNOTATIONS ----
    # If there is a valid VCD file loaded then use this information to get @annotation and
    # @validation matrices. When a external file structure is detected only VCD files are allowed.
    if vcd_handler.fileLoaded():

        # If there is also a autoSaveAnn.txt, there must be a confusion of annotations
        if not createNewAnn:
            raise RuntimeError(
                "/n There are two annotation files: vcd and txt. Please, keep only"
                "the most recent one. \n You can delete '..ann.json' file or '..autoSaveAnnA.txt and ..autoSaveAnnB.txt' files"
            )
        else:
            print("\nLoading VCD...")
            # get @annotation and @validation vectors
            annotation, validation = vcd_handler.getAnnotationVectors()

    # else If there is not VCD:
    # if @createNewAnn is True, load preannotations(..ann.txt) and create new matrix for
    # @annotation and other for @validation
    elif createNewAnn and not external_struct:
        print("\nCreating new annotations...")
        # open files and create arrays
        # @file_ann: pre-annotations of body video
        file_ann = open(str(annotationsFile))
        ann = []
        for line1 in file_ann:
            ann.append(line1)
        file_ann.close()

        # First check on @intelAnn
        # @intelAnn: intel annotations for body video
        # @existIntelAnn: boolean if intelAnnotationsFile exist
        intelAnn = []
        if existIntelAnn:
            fileIntelAnn = open(str(intelAnnotationsFile))
            for lineIn in fileIntelAnn:
                intelAnn.append(lineIn)
            fileIntelAnn.close()

        intelFrameAnn = 99
        frameAnn = 0
        # len(ann): num of annotations in file = num of frames in body video
        # set number of frames in vcd
        vcd_handler.setBodyFrames(len(ann))
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
                    line = getAnnotationLine(100, 3)
                else:
                    # [A0,  A1,  A2,  A3, A4, A5,   A6]
                    # ["--",0   ,"--",NA, NA, "--",  0]
                    # Fist check intel annotation, if not available, check pre-annotation
                    if intelFrameAnn != 99:
                        line = getAnnotationLine(intelFrameAnn, 0)
                    else:
                        line = getAnnotationLine(frameAnn, 0)
            # from here there is information from the three cameras
            else:
                # [A0,  A1,  A2,  A3, A4,  A5,  A6]
                # ["--",0   ,"--",0,  "--","--", 0]
                # Fist check intel annotation, if not available, check pre-annotation
                if intelFrameAnn != 99:
                    line = getAnnotationLine(intelFrameAnn, 1)
                else:
                    line = getAnnotationLine(frameAnn, 1)

            annotation.append(line)
            # Append 7 zeros to initial validation state for all levels
            validation.append([0, 0, 0, 0, 0, 0, 0])

    # else load old annotations(...autoSaveAnnA-B.txt) and save them in array    
    elif not createNewAnn :
        print("\nLoading provisional txt annotation files...")
              
        if metadataProvFile.exists():

            f = open(str(metadataProvFile))
            lines = f.readlines()

            # --get SHIFTS--
            if not createNewAnn and external_struct:
                line = lines[2].split("-")
                shift_bf = int(line[0]) 
                shift_hb = int(line[1])
                vcd_handler.setShifts(body_face_shift=shift_bf, hands_body_shift=shift_hb, hands_face_shift=shift_bf + shift_hb)
                

            # --get STATIC ANN AND METADATA--
            # static
            line = lines[0].split("-")
            staticsFromTxt = statics_dic
            num = 0
            for att in staticsFromTxt:
                #for glasses boolean field
                if line[num]=="False" or line[num]=="false":
                    att.update({"val": False})
                else:
                    att.update({"val": line[num]})
                num += 1
            
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
           
            #@metadata: [sub, group, session, date, --, face_meta, body_meta,
            #             hands_meta]
            metadata_full = [metadata[0], metadata[1], metadata[2],
                             metadata[3], metadata[4], face_meta, body_meta,
                             hands_meta]
            

        elif not metadataProvFile.exists() and external_struct:
            raise RuntimeError("No Metadata found. Could not load shifts.")

        
        # --get ANNOTATIONS AND VALIDATIONS--
        # [frame,A0,A1,A2,A3,A4,A5,A6]
        #    0   -0 -0 -0 -0 -0 -0 -0

        ann = open(str(annotationsFile))
        body_count = 0
        for ann_line in ann:
            if not "|" in ann_line:
                ann_line = ann_line.rstrip(" \n") + "|0-0-0-0-0-0-0"
            annPart, validPart = ann_line.split("|")
            part = annPart.split("-")
            annotation.append([int(part[1]), int(part[2]), int(part[3]),
                               int(part[4]), int(part[5]), int(part[6]),
                               int(part[7])])
            if int(part[7]) != 100:
                body_count += 1
            part = validPart.split("-")
            validation.append([int(part[0]), int(part[1]), int(part[2]),
                               int(part[3]), int(part[4]), int(part[5]),
                               int(part[6])])
        ann.close()

        # set number of body frames in vcd
        vcd_handler.setBodyFrames(body_count)

        vcd_handler.updateAndSaveVCD(annotation, validation,
                                        staticsFromTxt, metadata_full,
                                        external_struct, False)

        staticExists = vcd_handler.isStaticAnnotation(statics_dic,0)

    else:
        raise RuntimeError("Unknown situation when loading annotation files")

    return shift_bf, shift_hb, annotation, validation


# Called when [SPACE] or [ENTER] or [ESC] is pressed
# @annotations: array of current manual corrections/annotations
# @validations: array of current validation state of frames
# @toVCD: if True, save annotations in vcd format and delete txt, else write in txt
def save(annotations, validations, toVCD):
    # Save time expended during the annotation process

    """ If you want to save annotation time:
    -Declare a annTimeFile Path down at the global variables
    -Delete "if not external_struct" line
    -Format document :)
    """
    if not external_struct:
        saveHour()

    if toVCD:
        # Show "saving" window
        cv2.namedWindow("Annotation - Saving", flags=cv2.WINDOW_NORMAL)
        alertWindowHeight = 160
        alertSWindowWidth = 400
        alertSave = np.uint8(
            np.full((alertWindowHeight, alertSWindowWidth, 3), backgroundColorMain))
        alertSave[0:15, 0:alertSWindowWidth] = colorDict[12]
        alertSave[145:160, 0:alertSWindowWidth] = colorDict[12]
        cv2.putText(
            alertSave, "Saving...", (130, 85), font, 2, colorDict[7], 2, cv2.LINE_AA
        )
        while True:
            cv2.imshow("Annotation - Saving", alertSave)
            cv2.moveWindow("Annotation - Saving", 400, 400)
            key = cv2.waitKey(3)
            # Update VCD
            if staticExists:
                #Get static annotations and metadata from VCD
                statics = vcd_handler.getStaticVector(statics_dic, 0)
                metaVCD = vcd_handler.getMetadataVector(0)
                metadata_full = [
                    metadata[0],
                    metadata[1],
                    metadata[2],
                    metadata[3],
                    metadata[4],
                    metaVCD[0],
                    metaVCD[1],
                    metaVCD[2],
                ]
                #create vcd
                vcd_handler.updateAndSaveVCD(
                    annotations,
                    validations,
                    statics,
                    metadata_full,
                    external_struct,
                    False
                )
            else:
                #create vcd with empty static annotations
                vcd_handler.updateAndSaveVCD(
                    annotations,
                    validations,
                    {},
                    metadata,
                    external_struct,
                    False
                )

            # Delete (autoSaveAnnA.txt)
            file_to_rem = Path(autoSaveAnnotationFile)
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
        f = open(str(autoSaveAnnotationFile), "w")
        # Save annotations and validation states in the same file. Separated by "|" character
        for i, clas in enumerate(annotations):
            val = validations[i]
            f.write(
                str(i)
                + "-"
                + str(clas[0])
                + "-"
                + str(clas[1])
                + "-"
                + str(clas[2])
                + "-"
                + str(clas[3])
                + "-"
                + str(clas[4])
                + "-"
                + str(clas[5])
                + "-"
                + str(clas[6])
                + "|"
                + str(val[0])
                + "-"
                + str(val[1])
                + "-"
                + str(val[2])
                + "-"
                + str(val[3])
                + "-"
                + str(val[4])
                + "-"
                + str(val[5])
                + "-"
                + str(val[6])
                + " \n"
            )
        f.close()
        if vcd_handler.fileLoaded():
            # save metadata and staticAnn to txt 
            # Open file
            f = open(str(metadataProvFile), "w")
            # Save metadata and static annotations the same file in three lines
            static = vcd_handler.getStaticVector(statics_dic, 0)
            line = ""
            #static annotations separated by "-" character
            for val in static:
                line = line + str(val["val"]) + "-"
            line = line + "\n"
            f.write(line)
            #metadata separated by "|" character
            meta = vcd_handler.getMetadataVector(0)
            line = (
                    str(meta[0][0])
                    + "|"
                    + str(meta[0][1])
                    + "|"
                    + str(meta[1][0])
                    + "|"
                    + str(meta[1][1])
                    + "|"
                    + str(meta[1][2])
                    + "|"
                    + str(meta[2][0])
                    + "|"
                    + str(meta[2][1])
                    + "\n"
            )
            f.write(line)
            #shifts separated by "-" character
            line = str(shift_bf)+"-"+str(shift_hb)
            f.write(line)


# Saves the accumulated elapsed time using the tool for the actual video
def saveHour():
    global GLOBAL_opening_time
    delta = datetime.timedelta(hours=0, minutes=0, seconds=0)
    # If there is an old time, load it
    if annTimeFile.exists():
        timeF = open(str(annTimeFile))
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
    f = open(str(annTimeFile), "w")
    f.write(str(elapsed_time))
    f.close()
    # update opening_time to the last saved time (now)
    GLOBAL_opening_time = datetime.datetime.now()
    GLOBAL_opening_time = datetime.timedelta(
        hours=GLOBAL_opening_time.hour,
        minutes=GLOBAL_opening_time.minute,
        seconds=GLOBAL_opening_time.second)


# Create new window to play the actual video along with its annotations
# @count: the frame number to begin the video playing
# @mosaicVideo: actual video
# @annotations: annotations array to show along with the video
# @validations: validations array to show along with the video
# @mode: current level of annotation
def showLiveAnnotations(countm, mosaicVideo, annotations, validations, mode):
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
                dic[j][annotations[countm][j]],
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
    frameInfo_resize = cv2.resize(
        cv2.UMat(frameInfo), (81, 27), interpolation=cv2.INTER_AREA
    )
    labelS[padVer - 10: 47, padding: 81 + padding] = frameInfo_resize.get()  # 54x162
    cv2.putText(
        labelS,
        "=",
        (int(width_Labels / 2) - 15, padVer + 10),
        font,
        2,
        textColorLabels,
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        labelS,
        "Body: " + str(shift_bf),
        (int(width_Labels / 2) + padding, padVer),
        font,
        1,
        textColorLabels,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        labelS,
        "Hands: " + str(shift_hb) + "=" + str(shift_bf + shift_hb),
        (int(width_Labels / 2) + padding, padVer + 14),
        font,
        1,
        textColorLabels,
        1,
        cv2.LINE_AA,
    )

    # Get mosaic video with preceding 4 folders
    cv2.putText(
        labelS,
        str(actualVideo),
        (padding, padVer + 40),
        font,
        0.8,
        textColorLabels,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        labelS,
        "Total frames: " + str(frameNumber),
        (padding + 90, padVer + 65),
        font,
        1,
        textColorLabels,
        1,
        cv2.LINE_AA,
    )

    # Annotation Id's info
    pad_class = 210
    cv2.putText(
        labelS,
        "Labels: ",
        (padding, pad_class - 75),
        font,
        1.8,
        textColorLabels,
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        labelS,
        "To overwrite the label",
        (padding, pad_class - 50),
        font,
        1,
        textColorLabels,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        labelS,
        "press the corresponding key:",
        (padding, pad_class - 30),
        font,
        1,
        textColorLabels,
        1,
        cv2.LINE_AA,
    )

    # Display each label of the actual label
    for j, i in enumerate(dic[mode]):
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
            ] = colorDict[i]
            cv2.putText(
                labelS,
                "[" + str(j) + "]: " + str(dic[mode][i]),
                (padding + 30, pad_class + (20 * int(num))),
                font,
                1,
                textColorLabels,
                1,
                cv2.LINE_AA,
            )
    cv2.putText(
        labelS,
        "NAN: not frame information",
        (padding, pad_class + 315),
        font,
        1,
        textColorLabels,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        labelS,
        "--: no label",
        (padding, pad_class + 337),
        font,
        1,
        textColorLabels,
        1,
        cv2.LINE_AA,
    )
    # Validation colors info
    pad_class = 620
    cv2.putText(
        labelS,
        "Validation: ",
        (padding, pad_class - 30),
        font,
        1.7,
        textColorLabels,
        2,
        cv2.LINE_AA,
    )
    labelS[pad_class - 10: pad_class, padding: padding + 10] = colorDict["val_0"]
    cv2.putText(
        labelS,
        ": frame not changed",
        (padding + 20, pad_class),
        font,
        1,
        textColorLabels,
        1,
        cv2.LINE_AA,
    )
    labelS[pad_class - 10 + 20: pad_class + 20, padding: padding + 10] = colorDict[
        "val_1"
    ]
    cv2.putText(
        labelS,
        ": manual change",
        (padding + 20, pad_class + 20),
        font,
        1,
        textColorLabels,
        1,
        cv2.LINE_AA,
    )
    labelS[pad_class - 10 + 40: pad_class + 40, padding: padding + 10] = colorDict[
        "val_2"
    ]
    cv2.putText(
        labelS,
        ": block change",
        (padding + 20, pad_class + 40),
        font,
        1,
        textColorLabels,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        labelS,
        "Happy labelling :)",
        (padding, total_height - 25),
        font,
        0.8,
        textColorLabels,
        1,
        cv2.LINE_AA,
    )

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

    visualS = np.uint8(np.full((visualHeight, visualWidth, 3), backgroundColorMain))

    # --- MAIN (WHOLE) ANNOTATION BAR ---
    # title
    cv2.putText(
        visualS,
        "Total annotation timeline",
        (visWidth2 - 90, 20),
        font,
        0.9,
        textColorMain,
        1,
        cv2.LINE_AA,
    )
    # Draw annotation bar with colors
    for linePos in range(visualWidth):
        # @index: extrapolate the pixel number to an index in the @annArray
        index = int(linePos * (frameNumber + 1) / visualWidth)
        # draw a 20pixel vertical line with the correspondent label color
        visualS[30:50, linePos] = colorDict[annArray[index]]
        visualS[50:57, linePos] = colorDict["val_" + str(validArray[index])]
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
        font,
        0.8,
        textColorMain,
        1,
        cv2.LINE_AA,
    )
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
            visualS[90:120, pixel: pixel + pixelPerFrame] = colorDict[
                annArray[annCounter]
            ]
            visualS[120:127, pixel: pixel + pixelPerFrame] = colorDict[
                "val_" + str(validArray[annCounter])
                ]
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
                (instructionsHeight, instructionsWidth, 3), backgroundColorInstructions
            )
        )
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
            keyboardS,
            "<-300",
            (80, 70),
            font,
            0.8,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )  # Q
        cv2.putText(
            keyboardS, "Q", (90, 110), font, 2, textColorLabels, 2, cv2.LINE_AA
        )  # Q

        cv2.putText(
            keyboardS,
            "<-50",
            (140, 70),
            font,
            0.8,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )  # W
        cv2.putText(
            keyboardS, "W", (150, 110), font, 2, textColorLabels, 2, cv2.LINE_AA
        )  # W

        cv2.putText(
            keyboardS,
            "+50>",
            (200, 70),
            font,
            0.8,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )  # E
        cv2.putText(
            keyboardS, "E", (210, 110), font, 2, textColorLabels, 2, cv2.LINE_AA
        )  # E

        cv2.putText(
            keyboardS,
            "+300>",
            (260, 70),
            font,
            0.8,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )  # R
        cv2.putText(
            keyboardS, "R", (270, 110), font, 2, textColorLabels, 2, cv2.LINE_AA
        )  # R

        cv2.putText(
            keyboardS,
            "[<",
            (150, 150),
            font,
            0.8,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )  # A
        cv2.putText(
            keyboardS, "A", (150, 190), font, 2, textColorLabels, 2, cv2.LINE_AA
        )  # A

        cv2.putText(keyboardS, ">]", (210, 150), font, 0.8,
                    textColorInstructions, 1, cv2.LINE_AA)  # S
        cv2.putText(keyboardS, "S", (210, 190), font, 2, textColorLabels, 2,
                    cv2.LINE_AA)  # S

        cv2.putText(
            keyboardS, "<", (160, 230), font, 0.8, textColorInstructions, 1, cv2.LINE_AA
        )  # space
        cv2.putText(
            keyboardS, "SPACE", (110, 270), font, 2, textColorLabels, 2, cv2.LINE_AA
        )  # space

        cv2.putText(
            keyboardS, ">", (270, 230), font, 0.8, textColorInstructions, 1, cv2.LINE_AA
        )  # ?
        cv2.putText(
            keyboardS, "?", (270, 270), font, 2, textColorLabels, 2, cv2.LINE_AA
        )  # ?

        # -- segundo cuadrante --             y, x

        # teclas
        keyboardS[60:100, 400:440] = textColorInstructions  # Esc

        keyboardS[120:160, 400:460] = textColorInstructions  # Enter
        keyboardS[160:180, 420:460] = textColorInstructions  # Enter

        keyboardS[120:160, 480:560] = textColorInstructions  # Backspace

        keyboardS[220:260, 400:460] = textColorInstructions  # Tab

        keyboardS[220:260, 500:540] = textColorInstructions  # P

        # text                                 x +10 , -10+y
        cv2.putText(
            keyboardS,
            "Exit window",
            (450, 80),
            font,
            0.8,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )  # Esc
        cv2.putText(
            keyboardS, "Esc", (405, 85), font, 1, textColorLabels, 1, cv2.LINE_AA
        )  # Esc

        cv2.putText(
            keyboardS,
            "Save",
            (415, 200),
            font,
            0.8,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )  # Enter
        cv2.putText(
            keyboardS, "Enter", (405, 145), font, 1, textColorLabels, 1, cv2.LINE_AA
        )  # Enter

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
        cv2.putText(
            keyboardS,
            "Set Keyframe",
            (72, 400),
            font,
            0.8,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )  # Esc
        cv2.putText(
            keyboardS, "Z", (110, 370), font, 2, textColorLabels, 2, cv2.LINE_AA
        )  # Esc

        cv2.putText(
            keyboardS,
            "Go back to Keyframe",
            (175, 400),
            font,
            0.8,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )  # Enter
        cv2.putText(
            keyboardS, "M", (228, 370), font, 2, textColorLabels, 2, cv2.LINE_AA
        )  # Enter

        cv2.putText(
            keyboardS,
            "Apply annotations to other levels",
            (75, 465),
            font,
            0.8,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )  # Enter
        cv2.putText(
            keyboardS, "X", (168, 440), font, 2, textColorLabels, 2, cv2.LINE_AA
        )  # Enter

        # -- cuarto cuadrante --             y, x

        # teclas
        keyboardS[340:380, 400:440] = textColorInstructions  # 1

        keyboardS[360:365, 455:460] = textColorInstructions  # dot
        keyboardS[360:365, 475:480] = textColorInstructions  # dot
        keyboardS[360:365, 495:500] = textColorInstructions  # dot

        keyboardS[340:380, 520:560] = textColorInstructions  # +

        # text                                 x +10 , -10+y
        cv2.putText(
            keyboardS,
            "Numpad - change label",
            (400, 400),
            font,
            0.8,
            textColorInstructions,
            1,
            cv2.LINE_AA,
        )  # Esc
        cv2.putText(
            keyboardS, "1", (410, 370), font, 2, textColorLabels, 2, cv2.LINE_AA
        )  # Esc

        cv2.putText(
            keyboardS, "+", (525, 370), font, 2, textColorLabels, 2, cv2.LINE_AA
        )  # Enter

        # end
        cv2.putText(
            keyboardS,
            "-Thank you-",
            (int(instructionsWidth / 2) + 100, 460),
            font,
            1,
            (30, 30, 200),
            1,
            cv2.LINE_AA,
        )

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
            colorDict[7],
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
            colorDict[4],
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
            colorDict[4],
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
            colorDict[7],
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
            (25, 50),
            font,
            2,
            colorDict[7],
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            alertS,
            "depending on Driver Actions level!",
            (65, 75),
            font,
            2,
            colorDict[7],
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            alertS,
            "Only do this when you have completed the Driver_Actions Annotations",
            (60, 105),
            font,
            1,
            colorDict[5],
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            alertS,
            "Press Y (yes) or N (no)",
            (260, 125),
            font,
            1,
            colorDict[5],
            1,
            cv2.LINE_AA,
        )
    else:
        cv2.putText(
            alertS,
            "You have already changed the annotations from all levels",
            (70, 60),
            font,
            1.2,
            colorDict[5],
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            alertS,
            "If you really need to do it again, restart the tool",
            (105, 110),
            font,
            1.2,
            colorDict[5],
            1,
            cv2.LINE_AA,
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
                newAnn.append(getAnnotationLine(ann[6], 1))
            # return new annotation array with all levels changed depending on level 6
            return newAnn, True
        else:
            return [], False
    else:
        return [], False


# Shows window with mosaic and window with Labels
# @annotations: array of class id per each body-video frame
# @shift_bf: indicates how many zero images need to be inserted at BODY video wrt Face
# @shift_hb: indicates how many zero images need to be inserted at HANDS video wrt Body
def showMosaic(mosaicVideo, shift_bf, shift_hb, annotations, validations):
    """
    mode = 0:A0, 1:A1, 2:A2, 3:A3, 4:A4, 5:A5, 6:A6
    """
    # @mode: annotation level. Initialize in 6 (actions)
    mode = 6
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
                    frameInfo = frameMosaic[
                                108: 62 + 100, w2 + 200: w2 + 200 + 162
                                ]  # 54x162
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
                    (padding, 25),
                    font,
                    0.8,
                    colorDict[7],
                    1,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    mosaicS,
                    "Body video frame: " + str(count - shift_bf),
                    (padding, 55),
                    font,
                    0.9,
                    textColorMain,
                    1,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    mosaicS,
                    "Hands video frame: " + str(count - shift_bf - shift_hb),
                    (padding, 70),
                    font,
                    0.9,
                    textColorMain,
                    1,
                    cv2.LINE_AA,
                )

                # --- FRAME INFO --- #
                # show "Last frames" sign on the last 5 frames
                if count > frameNumber - 5:
                    cv2.putText(
                        mosaicS,
                        "Last frames!",
                        (padding + 55, int(h2 / 2) - 40),
                        font,
                        1,
                        textColorMain,
                        1,
                        cv2.LINE_AA,
                    )
                if count != frameNumber:
                    cv2.putText(
                        mosaicS,
                        str(count),
                        (padding + 55, int(h2 / 2)),  # 1035
                        font,
                        3,
                        colorDict[7],
                        2,
                        cv2.LINE_AA,
                    )
                else:
                    cv2.putText(
                        mosaicS,
                        "LAST FRAME",
                        (padding + 55, int(h2 / 2) - 10),  # 1022
                        font,
                        1,
                        textColorMain,
                        2,
                        cv2.LINE_AA,
                    )
                cv2.putText(
                    mosaicS,
                    "Mosaic frame",
                    (padding + 55, int(h2 / 2) + 20),
                    font,
                    1,
                    textColorMain,
                    1,
                    cv2.LINE_AA,
                )

                # Key frame sign
                if key_frame >= 0:
                    blockSize = abs(count - key_frame) + 1
                    cv2.putText(
                        mosaicS,
                        "Frames selected: ",
                        (padding, h2 - 110),  # 1022
                        font,
                        1,
                        textColorMain,
                        1,
                        cv2.LINE_AA,
                    )
                    cv2.putText(
                        mosaicS,
                        str(blockSize),
                        (padding + 150, h2 - 110),  # 1022
                        font,
                        1.4,
                        textColorMain,
                        1,
                        cv2.LINE_AA,
                    )
                    cv2.putText(
                        mosaicS,
                        "Key Frame: " + str(key_frame),
                        (padding, h2 - 90),  # 1022
                        font,
                        1,
                        textColorMain,
                        1,
                        cv2.LINE_AA,
                    )
                    cv2.putText(
                        mosaicS,
                        "Press [m] to go back to key frame",
                        (padding, h2 - 70),
                        # 1022
                        font,
                        0.7,
                        textColorMain,
                        1,
                        cv2.LINE_AA,
                    )
                    mosaicS[
                    h2 - 120: h2 - 70, padding - 20: padding - 10
                    ] = keyFrameColor

                # preview video
                cv2.putText(
                    mosaicS,
                    ". To preview annotations",
                    (padding, h2 - 35),
                    font,
                    0.8,
                    textColorMain,
                    1,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    mosaicS,
                    "press [BACKSPACE]",
                    (padding, h2 - 20),
                    font,
                    0.8,
                    textColorMain,
                    1,
                    cv2.LINE_AA,
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
                        font,
                        1,
                        textColorMain,
                        1,
                        cv2.LINE_AA,
                    )
                    cv2.putText(
                        mosaicS,
                        dic[j][annotations[count][j]],
                        (padding, (26 + line + j * h_line)),
                        font,
                        1.5,
                        textColorMain,
                        int((1 * i) + 1),
                        cv2.LINE_AA,
                    )
                    # Arrow
                    cv2.putText(
                        mosaicS,
                        "->",
                        (padding - 50, (26 + line + j * h_line)),
                        font,
                        1.5 * i,
                        colorDict[7],
                        int((1 * i) + 1),
                        cv2.LINE_AA,
                    )

                # --- INSTRUCTIOS AND LAST SAVED --- #
                cv2.putText(
                    mosaicS,
                    ". To OPEN INSTRUCTIONS press [P]",
                    (w2 + 110, 45),
                    font,
                    1,
                    (30, 30, 200),
                    1,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    mosaicS,
                    "Last saved at: " + timeSave,
                    (w2 + 110, 80),
                    font,
                    1.4,
                    textColorMain,
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
                mode = mode + 1
                if mode > 6:
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
                count = showLiveAnnotations(
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
            # press [x] to apply annotation in other levels
            elif key == ord("x") or key == ord("X"):
                changedAnn, do = changeInLevels(annotations, applyLevels)
                # if the user pressed Y (yes)
                if do:
                    annotations = changedAnn
                    applyLevels = True
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
                if key == 46 and 99 in dic[mode]:  # press [.] to write label 99 ("--")
                    count = update_annotation(annotations, validations, count, mode, 99)
                elif key == 48 and 0 in dic[mode]:  # press [0] to write label 0 
                    count = update_annotation(annotations, validations, count, mode, 0)
                elif key == 49 and (1 in dic[mode]):  # press [1] to write label 1
                    count = update_annotation(annotations, validations, count, mode, 1)
                elif key == 50 and 2 in dic[mode]:  # press [2] to write label 2
                    count = update_annotation(annotations, validations, count, mode, 2)
                elif key == 51 and 3 in dic[mode]: # press [3] to write label 3
                    count = update_annotation(annotations, validations, count, mode, 3)
                elif key == 52 and 4 in dic[mode]: # press [4] to write label 4
                    count = update_annotation(annotations, validations, count, mode, 4)
                elif key == 53 and 5 in dic[mode]:  # press [5] to write label 5
                    count = update_annotation(annotations, validations, count, mode, 5)
                elif key == 54 and 6 in dic[mode]:  # press [6] to write label 6
                    count = update_annotation(annotations, validations, count, mode, 6)
                elif key == 55 and 7 in dic[mode]: # press [7] to write label 7
                    count = update_annotation(annotations, validations, count, mode, 7)
                elif key == 56 and 8 in dic[mode]: # press [8] to write label 8
                    count = update_annotation(annotations, validations, count, mode, 8)
                elif key == 57 and 9 in dic[mode]:  # press [9] to write label 9
                    count = update_annotation(annotations, validations, count, mode, 9)
                elif key == 47 and 10 in dic[mode]:# press [/] to write label 10
                    count = update_annotation(annotations, validations, count, mode, 10)
                elif key == 42 and 11 in dic[mode]: # press [*] to write label 11
                    count = update_annotation(annotations, validations, count, mode, 11)
                elif key == 45 and 12 in dic[mode]: # press [-] to write label 12
                    count = update_annotation(annotations, validations, count, mode, 12)
                elif key == 43 and 13 in dic[mode]: # press [+] to write label 13
                    count = update_annotation(annotations, validations, count, mode, 13)

        except Exception as e:
            save(annotations, validations, False)
            print("Unexpected error:", sys.exc_info()[0])
            print(e)
            raise


def is_string_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


# Function to transform int keys to integer if possible
def keys_to_int(x):
    return {int(k) if is_string_int(k) else k: v for k, v in x}


# ------ GLOBAL VARIABLES ------

"""Most of the paths specified are necesary for internal compability, also for the construction of preanotations
If its running in external structure, the .json and .avi video paths should be enough
Run the tool through the ./annotate.sh script to avoid confussions with paths"""

# - Paths -
# Input: video_file, external_struct, vcd_file, pre_ann, intel_ann, time_file, shifts, autoSave_ann
# @mosaicFileName: path of the mosaic video (/../.../mosaic_..avi)
mosaicFileName = Path(sys.argv[1])  # 'mosaic.avi'

# @external_struct: flag to know if is running in internal or external extructure
external_struct = bool(int(sys.argv[2]))

vcd_file = Path(sys.argv[3])

# @createNewAnn: Control variable to create a new annotation file from pre-annotation or load the last one if False
createNewAnn = True

# Verify video file exists
if not mosaicFileName.exists():
    raise RuntimeError("Video file doesn't exist: " + str(mosaicFileName.resolve()))
actualVideo = Path(*mosaicFileName.parts[-4:])

# if internal structure
if not external_struct:
    # @existIntelAnn: Flag that shows if a valid Intel Annotation file was found
    existIntelAnn = False

    annotationsFile = Path(sys.argv[4])
    intelAnnotationsFile = Path(sys.argv[5])
    annTimeFile = Path(sys.argv[6])
    shiftsFile = Path(sys.argv[7])
    #@autoSaveAnnotationFile: path of the file for saving annotations and validations in txt 
    autoSaveAnnotationFile = Path(sys.argv[8])

    if intelAnnotationsFile.exists():
        existIntelAnn = True

    if autoSaveAnnotationFile.exists():
        createNewAnn = False
        annotationsFile = autoSaveAnnotationFile

    if not shiftsFile.exists():
        raise RuntimeError("Shift file doesn't exist: " + str(shiftsFile.resolve()))

else:
    #@autoSaveAnnotationFile: path of the file for saving annotations and validations in txt 
    autoSaveAnnotationFile = Path(sys.argv[4])
    annotationsFile = autoSaveAnnotationFile
    if autoSaveAnnotationFile.exists():
        createNewAnn = False

    if not vcd_file.exists() and createNewAnn:
        raise RuntimeError("VCD file doesn't exist: " + str(vcd_file.resolve(), "nor autoSave files"))

#@metadataProvFile: path of the file for saving static annotations and metadata in txt
# same from @autoSaveAnnotationFile but part B instead of A 
metadataProvFile = Path(str(autoSaveAnnotationFile).replace("-A", "-B"))


# Interval annotation
key_frame = -1

# - Dictionaries -
# Path to file containing classes label dictionaries
dict_json = "config.json"
# From json to python dictionaries
with open(dict_json) as dict_file:
    dicts = json.load(dict_file, object_pairs_hook=keys_to_int)

dic = [
    dicts["A0_dict"],
    dicts["A1_dict"],
    dicts["A2_dict"],
    dicts["A3_dict"],
    dicts["A4_dict"],
    dicts["A5_dict"],
    dicts["A6_dict"],
]
#dict for each of the static annotations fields
statics_dic = [dicts["static_dict"][x] for x in range(len(dicts["static_dict"]))]
dic_names = dicts["dict_names"]

# ---TEMP VAR---
# metadata for VCD
parts = mosaicFileName.parts
le = len(parts)
# @metadata: [sub, group, session, date, --]
metadata = [
    parts[le - 2],
    parts[le - 4],
    parts[le - 1].split("_")[1],
    parts[le - 3],
    parts[le - 1].split("_")[3],
]

# Create VCD Parser object, if vcd_file doesn't exist the handler will create an empty object
vcd_handler = VcdHandler(vcd_file=Path(vcd_file), dict_file=Path(dict_json))

#Check if static annotations and metadata already exists in vcd file
staticExists = False
if vcd_handler.fileLoaded():
    staticExists = vcd_handler.isStaticAnnotation(statics_dic, 0)

# - Time -
# when the tool opens, to calculate time expended
GLOBAL_opening_time = datetime.datetime.now()
GLOBAL_opening_time = datetime.timedelta(
    hours=GLOBAL_opening_time.hour,
    minutes=GLOBAL_opening_time.minute,
    seconds=GLOBAL_opening_time.second,
)

# - Dimensions of the Mosaic Video -
# load video
mosaicVideo = cv2.VideoCapture(str(mosaicFileName))
# @frameNumber: total number of frames. -1 for showing frames position starting from 0
frameNumber = int(mosaicVideo.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
width = int(mosaicVideo.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(mosaicVideo.get(cv2.CAP_PROP_FRAME_HEIGHT))
h2 = int(height / 2)
w2 = int(width / 2)
# @shrinkPercentage: the percentage of shrinking of the body and face video rectangles
shrinkPercentage = 85
# new dimensions after shrinking
shrinkdim = (int(shrinkPercentage * w2 / 100), int(shrinkPercentage * h2 / 100))

# - Dimensions of windows -
up_space = 70
down_space = 50
total_height = height
total_width = w2 + shrinkdim[0]
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
textColorMain = (60, 60, 60)
textColorLabels = (255, 255, 255)
textColorInstructions = (60, 60, 60)
backgroundColorMain = 255
backgroundColorLabels = 40
backgroundColorInstructions = 230
keyFrameColor = (131, 255, 167)
# color dictionary
colorDict = {
    # bgr
    0: (223, 215, 195),  # azul  claro
    1: (105, 237, 249),  # amarillo
    2: (201, 193, 63),  # aquamarina
    3: (6, 214, 160),  # verde claro
    4: (233, 187, 202),  # lila
    5: (133, 81, 252),  # rosa
    6: (0, 154, 255),  # naranja
    7: (181, 107, 69),  # azul opaco
    8: (137, 171, 31),  # verde oscuro
    9: (224, 119, 125),  # morado
    10: (153, 153, 255),  # piel
    11: (83, 73, 193),  # rojo oscuro
    12: (107, 79, 54),  # azul oscuro
    13: (106, 107, 131),  # cafe
    99: (245, 245, 245),  # blanco
    100: (80, 80, 80),  # negro
    "val_0": (245, 245, 245),  # not change
    "val_1": (223, 187, 185),  # (220, 180, 190),  # manual_change
    "val_2": (250, 210, 170),  # block_change
}

# ----EXECUTION ----

# Load shifts, pre annotations and validation info
shift_bf, shift_hb, annotation_list, validation_list = loadProperties()
#create vcd if did not exist
if not createNewAnn:
    save(annotation_list, validation_list, True)
# Show video, Labels window and timeline bar
showMosaic(mosaicVideo, shift_bf, shift_hb, annotation_list, validation_list)

mosaicVideo.release()
cv2.destroyAllWindows()
