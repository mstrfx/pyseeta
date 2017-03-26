""" This is license
"""
from ctypes import *
from .common import _Face, _Image, _LandMarks
import copy as cp
import numpy as np
import sys
from ctypes.util import find_library


DYLIB_EXT = {
    'darwin': 'libseeta_fi_lib.dylib',
    'win32' : '/release/libseeta_fi_lib.dll',
    'linux' : 'libseeta_fi_lib.so'
    }

SEETA_LIB_PATH = '../SeetaFaceEngine/library'

if DYLIB_EXT.get(sys.platform) is None:
    raise EnvironmentError('System not support!')

lib_path = find_library('seeta_fi_lib')

if lib_path is not None:
    identi_lib = cdll.LoadLibrary(lib_path)
else:
    identi_lib = cdll.LoadLibrary('{}/{}'.format(SEETA_LIB_PATH, DYLIB_EXT[sys.platform]))

c_float_p = POINTER(c_float)

identi_lib.get_face_identifier.restype = c_void_p
identi_lib.get_face_identifier.argtypes = [c_char_p]
identi_lib.extract_feature_with_crop.restype = c_float_p
identi_lib.extract_feature_with_crop.argtypes = [c_void_p, POINTER(_Image), POINTER(_LandMarks)]
identi_lib.crop_face.restype = POINTER(_Image)
identi_lib.crop_face.argtypes = [c_void_p, POINTER(_Image), POINTER(_LandMarks)]
identi_lib.extract_feature.restype = c_float_p
identi_lib.extract_feature.argtypes = [c_void_p, POINTER(_Image)]
identi_lib.calc_similarity.restype = c_float
identi_lib.calc_similarity.argtypes = [c_void_p, c_float_p, c_float_p]
identi_lib.free_feature.restype = None
identi_lib.free_feature.argtypes = [c_float_p]
identi_lib.free_image_data.restype = None
identi_lib.free_image_data.argtypes = [POINTER(_Image)]
identi_lib.free_identifier.restype = None
identi_lib.free_identifier.argtypes = [c_void_p]


class Identifier(object):
    """ Class for Face identification
    """
    def __init__(self, model_path):
        byte_model_path = bytes(model_path, encoding='utf-8')
        self.identifier = identi_lib.get_face_identifier(byte_model_path)

    def crop_face(self, image, landmarks):
        """ Crop face image from original image
        """
        # prepare image data
        image_data = _Image()
        image_data.height, image_data.width = image.shape[:2]
        image_data.channels = 1 if image.ndim == 2 else image.shape[2]
        byte_data = (c_ubyte * image.size)(*image.tobytes())
        image_data.data = cast(byte_data, c_void_p)
        # prepare landmarks
        marks_data = _LandMarks()
        for i in range(5):
            marks_data.x[i], marks_data.y[i] =  landmarks[i]
        # call crop face function
        crop_data = identi_lib.crop_face(self.identifier, byref(image_data), byref(marks_data))
        # read crop data
        contents = crop_data.contents
        crop_shape = (contents.height, contents.width, contents.channels)
        nb_pixels = crop_shape[0] * crop_shape[1] * crop_shape[2]
        byte_data = cast(contents.data, POINTER(c_ubyte))
        byte_data = (c_ubyte * nb_pixels)(*byte_data[:nb_pixels])
        image_crop = np.fromstring(byte_data, dtype=np.uint8).reshape(crop_shape)
        # free crop data
        identi_lib.free_image_data(crop_data)
        return image_crop

    def extract_feature(self, image):
        """ Extract feature of cropped face image
        """
        # prepare image data
        image_data = _Image()
        image_data.height, image_data.width = image.shape[0:2]
        image_data.channels = 1 if image.ndim == 2 else image.shape[2]
        byte_data = (c_ubyte * image.size)(*image.tobytes())
        image_data.data = cast(byte_data, c_void_p)
        # call extract_feature function
        root = identi_lib.extract_feature(self.identifier, byref(image_data))
        # read feature
        feat = [root[i] for i in range(2048)]
        # free feature
        identi_lib.free_feature(root)
        return feat

    def extract_feature_with_crop(self, image, landmarks):
        """ Extract feature of face
        """
        # prepare image data
        image_data = _Image()
        image_data.height, image_data.width = image.shape[:2]
        image_data.channels = 1 if image.ndim == 2 else image.shape[2]
        byte_data = (c_ubyte * image.size)(*image.tobytes())
        image_data.data = cast(byte_data, c_void_p)
        # prepare landmarks
        marks_data = _LandMarks()
        for i in range(5):
            marks_data.x[i], marks_data.y[i] =  landmarks[i]
        # call extract_feature_with_crop function
        root = identi_lib.extract_feature_with_crop(self.identifier, byref(image_data), byref(marks_data))
        # read feature
        feat = [root[i] for i in range(2048)]
        # free feature
        identi_lib.free_feature(root)
        return feat

    def calc_similarity(self, featA, featB):
        """ Calculate similarity of 2 feature
        """
        # prepare feature array
        feat_a = (c_float * 2048)(*featA)
        feat_b = (c_float * 2048)(*featB)
        # call calc_similarity function
        similarity = identi_lib.calc_similarity(self.identifier, feat_a, feat_b)
        return similarity

    def release(self):
        """
        release identifier memory
        """
        identi_lib.free_identifier(self.identifier)