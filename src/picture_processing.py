import uuid
import os
import numpy as np
import onnxruntime as ort
import matplotlib.pyplot as plt
from PIL import Image


def image_features_onnx(path, onnx_session: ort.InferenceSession):

    input_name = onnx_session.get_inputs()[0].name
    output_name = onnx_session.get_outputs()[0].name

    image = Image.open(path)
    image = image.convert('RGB')

    image = image.resize((224, 224))
    image = np.array(image) / 255.0

    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    image = (image - mean) / std

    image = image.astype(np.float32)

    image = np.transpose(image, (2, 0, 1))
    image = np.expand_dims(image, axis=0)

    result = onnx_session.run([output_name], {input_name: image})

    return result


def vec_to_features(temp_pic_path: str, vector: list, onnx_session: ort.InferenceSession):

    uid = str(uuid.uuid4())

    x = np.array(vector)[:, 0]
    y = np.array(vector)[:, 1]

    x_scaled = (x - np.min(x)) / (np.max(x) - np.min(x)) + 1
    y_scaled = (y - np.min(y)) / (np.max(y) - np.min(y)) + 1

    plt.figure()
    ax = plt.gca()
    plt.axis('off')
    plt.plot(x_scaled, y_scaled, linestyle='-', color='b')
    plt.savefig(f"{temp_pic_path}/temp_pic/pic_{uid}.png")

    raw_features = image_features_onnx(path=f"{temp_pic_path}/temp_pic/pic_{uid}.png", onnx_session=onnx_session)
    feature_scipy = np.array(raw_features).flatten()

    os.remove(f"{temp_pic_path}/temp_pic/pic_{uid}.png")

    return feature_scipy