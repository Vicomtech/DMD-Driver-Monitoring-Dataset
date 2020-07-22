#!/bin/bash
#Created by Paola Cañas and Juan Diego Ortega - 02-04-2020 - with <3

echo "Welcome :)"

#Capture video PATH
read -p "PATH of the video (/.../_.._mosaic.avi): " folder1

tmp_root="${folder1%.*}"
mosaic_name="${tmp_root##*/}"
echo "Loaded: "$mosaic_name

curr_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
db_path="${curr_dir}/dmd"

#regular expressions
regex_int='^([1-9]|[1-2][0-9]|[3][0-7]+)_([a-z]{1,}|[a-z]{1,}2+)_mosaic_([0-9]{2}-[0-9]{2}$)'
regex_ext='^(g[A-Z]+)_([1-9]|[1-2][0-9]|[3][0-7]+)_s([1-9]|[1-2][0-9]+)_(([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2};[0-9]{2};[0-9]{2})\+([0-9]{2};[0-9]{2})+)_(rgb|depth|ir)_mosaic'

if [[ $mosaic_name =~ $regex_int ]]; then
    echo "Video in internal structure"
    # Internal file structure
    external_struct=0
    # Get group
    tmp="${folder1%/*/*/*.*}"
    group="${tmp##*/}"
    # Get Date
    tmp="${folder1%/*/*.*}"
    date="${tmp##*/}"
    # Get User
    tmp="${folder1%/*.*}"
    user="${tmp##*/}"
    # Get video filename with extension
    mosaic_name_ext="${folder1##*/}"
    
    #Get shifts file
    sync_file="shifts-${group}.txt"
    # Replace "mosaic" word with "body"
    file_name="${mosaic_name/mosaic/body}"
    vcd_file="${mosaic_name/mosaic_/}_ann.json"
    pre_ann="${file_name}_ann.txt"
    intel_ann="${file_name}_ann_intel.txt"
    time_file="${file_name}_annTime.txt"        
    
    #Get location paths
    local_video_path="${db_path}/${group}/${date}/${user}"    
    local_shift_path="${db_path}/logs-sync"
    #AutoSave annotation
    manual_ann="${file_name}_autoSaveAnn-A.txt"
     
elif [[ $mosaic_name =~ $regex_ext ]]; then
    echo "Video in external structure"
    # External file structure
    external_struct=1

    # Build expected VCD file path and name for the external file structure

    # Get group
    tmp="${folder1%/*/*/*.*}"
    group="${tmp##*/}"
    # Get User
    tmp="${folder1%/*/*.*}"
    user="${tmp##*/}"
    # Get Session
    tmp="${folder1%/*.*}"
    session="${tmp##*/}"
    # Get video filename with extension
    mosaic_name_ext="${folder1##*/}"

    vcd_file="${mosaic_name/mosaic/ann}.json"       
    manual_ann="${mosaic_name/mosaic/autoSaveAnn-A}.txt"

    #Get location paths
    local_video_path="${tmp}/"


else
    echo "Incompatible file name. Please check your file name or folder structure."
fi

if [ "$external_struct" = 1 ]; then

    vcd_file_full="${local_video_path}/${vcd_file}"
    manual_ann_full="${local_video_path}/${manual_ann}"
    #run script
    python3 display_annotation.py $folder1 $external_struct $vcd_file_full $manual_ann_full

fi
echo "Oki :) ---------------------------------"
