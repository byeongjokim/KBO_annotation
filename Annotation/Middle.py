import time
import random
import cv2
import tensorflow as tf
import numpy as np
import owlready2
from Annotation.Rule_Annotation import RuleData
from Annotation.Scene_Annotation import SceneData
from Annotation.position import Position
from Annotation.Ontology_String import *
from skimage.measure import compare_ssim as ssim
from NN.detect_model import Detect_Model
from NN.motion_model import Classifier, TRN
import queue

class Middle():
    frame_no = 0
    frame = []

    def __init__(self, gameName, Resources):
        print("init annotation")
        self.sess = tf.Session()
        self.resources = Resources

        owlready2.onto_path.append("_data/_owl/")
        self.onto = owlready2.get_ontology("baseball.owl")
        self.onto.load()

        self.ruleData = RuleData(gameName, Resources, self.onto)

        self.motion = Classifier(self.sess, istest=1)
        self.sceneData = SceneData(Resources, self.onto, self.sess)
        self.detect = Detect_Model(self.sess, istest=1)

        num_prev_annotation = 10
        self.prev_annotaion = queue.Queue(num_prev_annotation)

    def generate_Annotation_with_Rule(self, count_delta, fps, o_start):
        self.ruleData.set_Start(count_delta, fps, o_start)
        self.ruleData.get_Annotation()
        return 1

    def generate_Annotation_with_Scene(self):
        counter = 0

        time.sleep(40)
        print('start')
        pre_label = -1
        h, w, c = self.resources.frame.shape
        frame = np.zeros((h, w, c), dtype=np.uint8)
        position = Position(motion=self.motion, frame_shape=(h, w), resource=self.resources)

        game_counter = 0

        flag = 0
        while( not self.resources.exit ):
            label, score = self.sceneData.get_score_label(self.resources.frame)
            #print(label, score, counter)
            """
            if(score > 0.8):
                self.resources.set_annotation_2(label)
            """
            #print(label)
            if(label != pre_label and ssim(self.resources.frame, frame, multichannel=True) < 0.6): #scene changed
                #print("refresh")
                counter = 0
                frame = self.resources.frame
                position.clear()

            if(label == 11 and flag == 0):
                annotation = "좌익수 이형종선수 쪽 입니다."
                print(annotation)
                self.resources.set_annotation(annotation)
                flag = 1

            """
            if(label == 5 and flag == 0):
                annotation = "1루수 공을 잡았습니다."
                print(annotation)
                self.resources.set_annotation(annotation)
                flag = 1
            """


            if(counter == 9):
                annotation = self.sceneData.get_Annotation(label)
                if(annotation):
                    annotation = self.get_random_annotation(annotation)

                    print("from scene \t\t" + annotation)
                    self.resources.set_annotation(annotation)

            if(counter > 13):
                if(label == 2):
                    pitcher_annotation = self.sceneData.pitcher()
                    pitcher_annotation = self.get_random_annotation(pitcher_annotation)

                    print("from pitcher \t\t" + pitcher_annotation)
                    self.resources.set_annotation(pitcher_annotation)
                    counter = 0

            if(game_counter > 17):
                gameinfo_annotation = self.sceneData.gameinfo()
                gameinfo_annotation = self.get_random_annotation(gameinfo_annotation)

                #print("from gameinfo \t\t" + gameinfo_annotation)
                #self.resources.set_annotation(gameinfo_annotation)
                game_counter = 0

            bboxes = self.detect.predict(self.resources.frame)
            if (bboxes):
                position.insert_person(self.resources.frame, bboxes, label)

            motion_annotation = position.annotation(label, position.get_bbox())
            if(motion_annotation):
                motion_annotation = self.get_random_annotation(motion_annotation)

                print("from motion\t\t"+ motion_annotation)
                self.resources.set_annotation(motion_annotation)
            pre_label = label
            counter = counter + 1
            game_counter = game_counter + 1

        return 1

    def get_random_annotation(self, annotation):
        #print(list(self.prev_annotaion.queue))
        counter = 0
        while(1):
            output = random.choice(annotation)

            if counter > 5:
                if (self.prev_annotaion.full()):
                    self.prev_annotaion.get_nowait()
                self.prev_annotaion.put(output)
                return output

            if not (output in list(self.prev_annotaion.queue) or self.is_same_prefix(output, list(self.prev_annotaion.queue))):
                if(self.prev_annotaion.full()):
                    self.prev_annotaion.get_nowait()
                self.prev_annotaion.put(output)
                return output

            counter = counter + 1

    def is_same_prefix(self, output, l):
        for i in l[-2:]:
            #print(output[:2], i[:2])
            if(output[:2] == i[:2]):
                return True
        return False
