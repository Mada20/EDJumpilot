import cv2
import numpy as np
from PIL import ImageGrab


def join_images(image1, image2, horizontaly=False):
    h1, w1 = image1.shape[:2]
    h2, w2 = image2.shape[:2]
    if not horizontaly:
        vis = np.zeros((max(h1, h2), w1+w2, 3), np.uint8)
        vis[:h1, :w1, :3] = image1
        vis[:h2, w1:w1+w2, :3] = image2
    else:
        vis = np.zeros((h1+h2, max(w1, w2), 3), np.uint8)
        vis[:h1, :w1, :3] = image1
        vis[h1:h1+h2, :w2, :3] = image2
    return vis


def match_template(image, template_name, threshold):
    template = cv2.imread(template_name,0)
    res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where( res >= threshold)
    return len(zip(*loc[::-1])) > 0, loc


def get_frame():
    img = ImageGrab.grab()
    img_numpy = np.array(img)
    frame = cv2.cvtColor(img_numpy, cv2.COLOR_BGR2RGB)
    return frame


def show_images(images):
    if len(images) > 0:
        imshow = None
        for index, image in enumerate(images):
            if (index is 0):
                imshow = image
            else:
                imshow = join_images(imshow, image)

        cv2.imshow('Debug', imshow)

def get_contour_by_size(contours, width, height, margin):
    if len(contours) > 1:
        for _, cnt in enumerate(contours):
            (_, _, w, h) = cv2.boundingRect(cnt)
            if w < width + margin and w > width - margin and h < height + margin and h > height - margin:
                return cnt
    return max(contours, key=cv2.contourArea)