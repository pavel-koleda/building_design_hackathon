import numpy as np

from shapely import Polygon

def scaling_object(x_array, y_array, target_area: int):

    object_polygon = Polygon(list(zip(x_array, y_array)))
    original_object_area = object_polygon.area
    scale_coeff = np.sqrt(target_area / original_object_area)

    new_object_x = [x*scale_coeff for x in x_array]
    new_object_y = [y*scale_coeff for y in y_array]
    new_object = Polygon(list(zip(new_object_x, new_object_y)))

    return (new_object, new_object.area)


def normalize_vector(vector: np.array):

    delta = None

    if min(vector) < 0:
        new_vector = vector + (abs(min(vector)) + 1)
        delta = abs(min(vector)) + 1
        return (new_vector, delta)
    
    elif min(vector) >= 0:
        new_vector = vector - abs(min(vector)) + 1
        delta = -1 * abs(min(vector))
        return (new_vector, delta)
    


