import json
import math
import os

import numpy as np
from tqdm import tqdm

import config


def rowConversion(row):
    ped_id, x_min, y_min, x_max, y_max, frame, _, _, _, label = row
    return float(frame), float(ped_id), (float(x_min) + float(x_max)) / (2.0), (
            float(y_min) + float(y_max)) / (2.0), label.strip("\"")


def scaleCoordinates(row):
    frame, ped_id, x, y = row
    return float(frame), float(ped_id), float(x / config.annotationXScale), float(y / config.annotationYScale)


def convertData(data, testSplit=0.15, validSplit=0.15, samplingRate=5, labels=None):
    trainingData = {}
    testData = {}
    validationData = {}
    maxTestFrame = int(math.floor(len(data) * testSplit))
    maxValidFrame = maxTestFrame + int(math.floor(len(data) * validSplit))
    frame = 0
    maxX = 0
    maxY = 0
    for label in labels:
        testData[label] = {}
    for i in range(samplingRate):
        trainingData[i] = []
        if not (labels is None):
            for label in labels:
                testData[label][i] = []
        else:
            testData[i] = []
        validationData[i] = []
    for row in data:
        row = rowConversion(row)
        if (row[2] > maxX):
            maxX = row[2]
        if (row[3] > maxY):
            maxY = row[3]

        if (labels is None or row[4] in labels):
            label = row[-1]
            row = (math.floor(row[0] / samplingRate),) + row[1:-1]
            if (frame <= maxTestFrame):
                if not (labels is None):
                    testData[label][frame % samplingRate].append(row)
                else:
                    testData[frame % samplingRate].append(row)
            elif (frame <= maxValidFrame):
                validationData[frame % samplingRate].append(scaleCoordinates(row))
            else:
                trainingData[frame % samplingRate].append(scaleCoordinates(row))

        frame += 1
    # take middle 90% of image to train, test and validate on it
    for i in range(samplingRate):
        trainingData[i] = list(filter(lambda row: ((row[2] >= (
                maxX / (config.annotationXScale * config.fractionToRemove)) and row[2] <= (maxX - maxX / (
                config.annotationXScale * config.fractionToRemove))) and (row[3] >= (
                maxY / (config.annotationYScale * config.fractionToRemove)) and row[3] <= (maxY - (
                maxY / (config.annotationYScale * config.fractionToRemove))))), trainingData[i]))
        if (labels is None):
            testData[i] = list(filter(lambda row: ((row[2] >= (maxX / config.fractionToRemove) and row[2] <= (
                    maxX - (maxX / config.fractionToRemove))) and (
                                                           row[3] >= (maxY / config.fractionToRemove) and row[3] <= (
                                                           maxY - (maxY / config.fractionToRemove)))), testData[i]))
        else:
            for label in labels:
                testData[label][i] = list(
                    filter(lambda row: ((row[2] >= (maxX / config.fractionToRemove) and row[2] <= (
                            maxX - (maxX / config.fractionToRemove))) and (
                                                row[3] >= (maxY / config.fractionToRemove) and row[
                                            3] <= (
                                                        maxY - (maxY / config.fractionToRemove)))),
                           testData[label][i]))
        validationData[i] = list(filter(lambda row: ((row[2] >= (
                maxX / (config.annotationXScale * config.fractionToRemove)) and row[2] <= (maxX - maxX / (
                config.annotationXScale * config.fractionToRemove))) and (row[3] >= (
                maxY / (config.annotationYScale * config.fractionToRemove)) and row[3] <= (maxY - (
                maxY / (config.annotationYScale * config.fractionToRemove))))), validationData[i]))
    return trainingData, testData, validationData


def read_file(_path, delim='space'):
    data = []
    if delim == 'tab':
        delim = '\t'
    elif delim == 'space':
        delim = ' '
    with open(_path, 'r') as f:
        for line in f:
            line = line.strip().split(delim)
            data.append(line)
    return np.asarray(data)


def createTrainingData(inputFolder, outputFolder, samplingRate=15, labels=None):
    new_config = {"samplingRate": config.samplingRate,
                  "labels": labels,
                  "inputFolder": inputFolder,
                  "outputFolder": outputFolder,
                  "annotationXScale": config.annotationXScale,
                  "annotationYScale": config.annotationYScale,
                  "fractionToRemove": config.fractionToRemove,
                  "annotationType": config.annotationType,
                  "complete": False
                  }
    if (os.path.exists(os.path.join(outputFolder, 'trainingDataConfig.json'))):
        with open(os.path.join(outputFolder, 'trainingDataConfig.json')) as f:
            old_config = json.load(f)
        # check if config is the same and creation completed
        new_config["complete"] = True
        if (new_config == old_config):
            print("No new config, skipping data creation")
            return
        # write json showing data is incomplete
        new_config["complete"] = False
        with open(os.path.join(outputFolder, 'trainingDataConfig.json'), 'w') as json_file:
            json.dump(new_config, json_file)
    print("Converting Data...")
    # delete any current data in output folder
    if (os.path.exists(outputFolder)):
        os.removedirs(outputFolder)
    locations = os.listdir(inputFolder)
    pbar = tqdm(total=len(locations))
    for location in locations:
        pbar.update(1)
        videos = os.listdir(os.path.join(inputFolder, location))
        for video in videos:
            path = os.path.join(inputFolder, location, video, "annotations.txt")
            data = read_file(path, 'space')

            trainingDataDict, testDataDict, validationDataDict = convertData(data, samplingRate=samplingRate,
                                                                             labels=labels)
            if (not (os.path.isdir(os.path.join(outputFolder, location, video, "train")))):
                os.makedirs(os.path.join(outputFolder, location, video, "train"))
            if (not (os.path.isdir(os.path.join(outputFolder, location, video, "test")))):
                os.makedirs(os.path.join(outputFolder, location, video, "test"))
            if (not (os.path.isdir(os.path.join(outputFolder, location, video, "val")))):
                os.makedirs(os.path.join(outputFolder, location, video, "val"))
            for i in range(samplingRate):
                trainingData = np.asarray(trainingDataDict[i])
                validationData = np.asarray(validationDataDict[i])
                if (not np.any(np.isnan(trainingData))):
                    np.savetxt(
                        os.path.join(outputFolder, location, video, "train",
                                     "stan" + "_" + location + "_" + video + "_" + str(i) + ".txt"),
                        trainingData, fmt='%.5e', delimiter='\t', newline='\n', header='', footer='', comments='# ',
                        encoding=None)
                else:
                    print("Invalid Training Data")
                if not (labels is None):
                    for label in labels:
                        if (not (os.path.isdir(os.path.join(outputFolder, location, video, "test", label)))):
                            os.makedirs(os.path.join(outputFolder, location, video, "test", label))
                        testData = np.asarray(testDataDict[label][i])
                        if (not np.any(np.isnan(testData))):
                            np.savetxt(
                                os.path.join(outputFolder, location, video, "test", label,
                                             "stan" + "_" + location + "_" + video + "_" + str(i) + ".txt"),
                                testData, fmt='%.5e', delimiter='\t', newline='\n', header='', footer='', comments='# ',
                                encoding=None)
                        else:
                            print("Invalid Test Data")
                else:
                    testData = np.asarray(testDataDict[i])

                    if (not np.any(np.isnan(testData))):
                        np.savetxt(
                            os.path.join(outputFolder, location, video, "test",
                                         "stan" + "_" + location + "_" + video + "_" + str(i) + ".txt"),
                            testData, fmt='%.5e', delimiter='\t', newline='\n', header='', footer='', comments='# ',
                            encoding=None)
                    else:
                        print("Invalid Test Data")
                if (not np.any(np.isnan(validationData))):
                    np.savetxt(
                        os.path.join(outputFolder, location, video, "val",
                                     "stan" + "_" + location + "_" + video + "_" + str(i) + ".txt"),
                        validationData, fmt='%.5e', delimiter='\t', newline='\n', header='', footer='', comments='# ',
                        encoding=None)
                else:
                    print("Invalid Validation Data")
    pbar.close()
    new_config["complete"] = True
    with open(os.path.join(outputFolder, 'trainingDataConfig.json'), 'w') as json_file:
        json.dump(new_config, json_file)
