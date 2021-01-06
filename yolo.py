##########################################################################

# Example : performs YOLO (v3) object detection from a video file
# specified on the command line (e.g. python FILE.py video_file) or from an
# attached web camera

# Author : Toby Breckon, toby.breckon@durham.ac.uk

# Copyright (c) 2019 Toby Breckon, Durham University, UK
# License : LGPL - http://www.gnu.org/licenses/lgpl.html

# Implements the You Only Look Once (YOLO) object detection architecture decribed in full in:
# Redmon, J., & Farhadi, A. (2018). Yolov3: An incremental improvement. arXiv preprint arXiv:1804.02767.
# https://pjreddie.com/media/files/papers/YOLOv3.pdf

# This code: significant portions based in part on the tutorial and example available at:
# https://www.learnopencv.com/deep-learning-based-object-detection-using-yolov3-with-opencv-python-c/
# https://github.com/spmallick/learnopencv/blob/master/ObjectDetection-YOLO/object_detection_yolo.py
# under LICENSE:
# https://github.com/spmallick/learnopencv/blob/master/ObjectDetection-YOLO/LICENSE

# To use first download the following files:

# https://pjreddie.com/media/files/yolov3.weights
# https://github.com/pjreddie/darknet/blob/master/cfg/yolov3.cfg?raw=true
# https://github.com/pjreddie/darknet/blob/master/data/coco.names?raw=true

##########################################################################

import math

import cv2
import numpy as np

##########################################################################

keep_processing = True
config_file = "yolo/yolov3.cfg"
classesFile = "yolo/coco.names"
weights_file = "yolo/yolov3.weights"
rescale = 1.0
video_file = "videos//stmarc_video.avi"



#####################################################################
# Draw the predicted bounding box on the specified image
# image: image detection performed on
# class_name: string name of detected object_detection
# left, top, right, bottom: rectangle parameters for detection
# colour: to draw detection rectangle in


def drawPred(image, class_name, confidence, left, top, right, bottom, colour):
    # Draw a bounding box.
    cv2.rectangle(image, (left, top), (right, bottom), colour, 3)

    # construct label
    label = '%s:%.2f' % (class_name, confidence)

    # Display the label at the top of the bounding box
    labelSize, baseLine = cv2.getTextSize(
        label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    top = max(top, labelSize[1])
    cv2.rectangle(
        image,
        (left,
         top -
         round(
             1.5 *
             labelSize[1])),
        (left +
         round(
             1.5 *
             labelSize[0]),
         top +
         baseLine),
        (255,
         255,
         255),
        cv2.FILLED)
    cv2.putText(image, label, (left, top),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 1)


#####################################################################
# Remove the bounding boxes with low confidence using non-maxima suppression
# image: image detection performed on
# results: output from YOLO CNN network
# threshold_confidence: threshold on keeping detection
# threshold_nms: threshold used in non maximum suppression


def postprocess(image, results, threshold_confidence, threshold_nms):
    frameHeight = image.shape[0]
    frameWidth = image.shape[1]

    # Scan through all the bounding boxes output from the network and..
    # 1. keep only the ones with high confidence scores.
    # 2. assign the box class label as the class with the highest score.
    # 3. construct a list of bounding boxes, class labels and confidence scores

    classIds = []
    confidences = []
    boxes = []
    for result in results:
        for detection in result:
            scores = detection[5:]
            classId = np.argmax(scores)
            confidence = scores[classId]
            if confidence > threshold_confidence:
                center_x = int(detection[0] * frameWidth)
                center_y = int(detection[1] * frameHeight)
                width = int(detection[2] * frameWidth)
                height = int(detection[3] * frameHeight)
                left = int(center_x - width / 2)
                top = int(center_y - height / 2)
                classIds.append(classId)
                confidences.append(float(confidence))
                boxes.append([left, top, width, height])

    # Perform non maximum suppression to eliminate redundant overlapping boxes with
    # lower confidences
    classIds_nms = []
    confidences_nms = []
    boxes_nms = []

    indices = cv2.dnn.NMSBoxes(
        boxes,
        confidences,
        threshold_confidence,
        threshold_nms)
    for i in indices:
        i = i[0]
        classIds_nms.append(classIds[i])
        confidences_nms.append(confidences[i])
        boxes_nms.append(boxes[i])

    # return post processed lists of classIds, confidences and bounding boxes
    return (classIds_nms, confidences_nms, boxes_nms)


##########################################################################
# Get the names of the output layers of the CNN network
# net : an OpenCV DNN module network object


def getOutputsNames(net):
    # Get the names of all the layers in the network
    layersNames = net.getLayerNames()
    # Get the names of the output layers, i.e. the layers with unconnected
    # outputs
    return [layersNames[i[0] - 1] for i in net.getUnconnectedOutLayers()]


##########################################################################

# define video capture object

cap = cv2.VideoCapture()  # not needed for video files

##########################################################################

# init YOLO CNN object detection model

confThreshold = 0.5  # Confidence threshold
nmsThreshold = 0.4  # Non-maximum suppression threshold
inpWidth = 416  # Width of network's input image
inpHeight = 416  # Height of network's input image

# Load names of classes from file

classes = None
with open(classesFile, 'rt') as f:
    classes = f.read().rstrip('\n').split('\n')

# load configuration and weight files for the model and load the network
# using them

net = cv2.dnn.readNetFromDarknet(config_file, weights_file)
output_layer_names = getOutputsNames(net)

# defaults DNN_BACKEND_INFERENCE_ENGINE if Intel Inference Engine lib
# available or DNN_BACKEND_OPENCV otherwise
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)

# change to cv2.dnn.DNN_TARGET_CPU (slower) if this causes issues (should
# fail gracefully if OpenCL not available)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)

##########################################################################

# define display window name

window_name = 'YOLOv3 object detection: ' + weights_file
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

##########################################################################

# if command line arguments are provided try to read video_name
# otherwise default to capture from attached camera

if (video_file and (cap.open(str(video_file)))):

    # create window by name (as resizable)
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    while (keep_processing):

        # start a timer (to see how long processing and display takes)
        start_t = cv2.getTickCount()

        # if camera /video file successfully open then read frame
        if (cap.isOpened):
            ret, frame = cap.read()

            # when we reach the end of the video (file) exit cleanly
            if (ret == 0):
                keep_processing = False
                continue

            # rescale if specified
            if (rescale != 1.0):
                frame = cv2.resize(
                    frame, (0, 0), fx=rescale, fy=rescale)

        # create a 4D tensor (OpenCV 'blob') from image frame (pixels scaled
        # 0->1, image resized)
        tensor = cv2.dnn.blobFromImage(
            frame, 1 / 255, (inpWidth, inpHeight), [0, 0, 0], 1, crop=False)

        # set the input to the CNN network
        net.setInput(tensor)

        # runs forward inference to get output of the final output layers
        results = net.forward(output_layer_names)

        # remove the bounding boxes with low confidence
        confThreshold = 0.5
        classIDs, confidences, boxes = postprocess(
            frame, results, confThreshold, nmsThreshold)

        # draw resulting detections on image
        for detected_object in range(0, len(boxes)):
            if (classes[classIDs[detected_object]] == "person"):
                box = boxes[detected_object]
                left = box[0]
                top = box[1]
                width = box[2]
                height = box[3]
                drawPred(frame,
                         classes[classIDs[detected_object]],
                         confidences[detected_object],
                         left,
                         top,
                         left + width,
                         top + height,
                         (255,
                          178,
                          50))

        # Display efficiency information - the function getPerfProfile returns
        # the overall time for inference from the network
        t, _ = net.getPerfProfile()
        inference_t = (t * 1000.0 / cv2.getTickFrequency())
        label = ('Inference time: %.2f ms' % inference_t) + \
                (' (Framerate: %.2f fps' % (1000 / inference_t)) + ')'
        cv2.putText(frame, label, (0, 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255))

        # display image
        cv2.imshow(window_name, frame)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN,
                              cv2.WINDOW_FULLSCREEN & False)

        # stop the timer and convert to ms. (to see how long processing and
        # display takes)
        stop_t = ((cv2.getTickCount() - start_t) /
                  cv2.getTickFrequency()) * 1000

        # start the event loop + detect specific key strokes
        # wait 40ms or less depending on processing time taken (i.e. 1000ms /
        # 25 fps = 40 ms)
        key = cv2.waitKey(max(2, 40 - int(math.ceil(stop_t)))) & 0xFF

        # if user presses "x" then exit  / press "f" for fullscreen display
        if (key == ord('x')):
            keep_processing = False

    # close all windows
    cv2.destroyAllWindows()

else:
    print("No video file specified or camera connected.")

##########################################################################
