import math
import numpy as np
from shapely import Polygon


def rotatePolygon(polygon, theta, center=(0, 0)):
    theta = math.radians(theta)
    rotatedPolygon = []
    cx, cy = center

    for corner in polygon:
        x, y = corner
        new_x = (x - cx) * math.cos(theta) - (y - cy) * math.sin(theta) + cx
        new_y = (x - cx) * math.sin(theta) + (y - cy) * math.cos(theta) + cy
        rotatedPolygon.append((new_x, new_y))

    return rotatedPolygon


def place_polygon(area_polygon: Polygon, object_polygon: Polygon):
    area_center = area_polygon.centroid
    area_center_x = area_center.x
    area_center_y = area_center.y
    area_x_array = list(area_polygon.exterior.coords.xy[0])
    area_y_array = list(area_polygon.exterior.coords.xy[1])

    object_center = object_polygon.centroid
    object_center_x = object_center.x
    object_center_y = object_center.y
    object_x_array = list(object_polygon.exterior.coords.xy[0])
    object_y_array = list(object_polygon.exterior.coords.xy[1])

    d_vector = np.array([area_center_x, area_center_y]) - np.array([object_center_x, object_center_y])
    object_shifted = np.array(list(zip(object_x_array, object_y_array))) + d_vector
    object_shifted_x, object_shifted_y = list(object_shifted[:, 0]), list(object_shifted[:, 1])

    if area_polygon.contains(Polygon(list(zip(object_shifted_x, object_shifted_y)))):
        # print('From the first pass')

        return (True, object_shifted_x, object_shifted_y)
    
    else:
        interval = max(area_polygon.exterior.coords.xy[0]) - min(area_polygon.exterior.coords.xy[0])
        num_points = 500
        num_turns = 10
        spiral_theta = np.linspace(0, 2.*np.pi*num_turns, num_points)
        r = np.sqrt(1.0 + interval*spiral_theta)

        spiral_x, spiral_y = area_center_x, area_center_y
        x_spiral_points = r * np.cos(spiral_theta) + spiral_x
        y_spiral_points = r * np.sin(spiral_theta) + spiral_y

        solution_found = False
        solution_x = None
        solution_y = None

        for i in range(num_points):
            # print(f'Try for the point {i}')
            if solution_found == True:
                break
            else:

                move_vector = np.array([area_center_x, area_center_y]) - np.array([x_spiral_points[i], y_spiral_points[i]])
                object_moved = np.array(list(zip(object_shifted_x, object_shifted_y))) + move_vector
                object_moved_x, object_moved_y = list(object_moved[:, 0]), list(object_moved[:, 1])
                new_position = list(zip(object_moved_x, object_moved_y))

                for _ in range(360):

                    rotated_polygon = rotatePolygon(new_position, theta=1, center=(x_spiral_points[i], y_spiral_points[i]))
                    rotated_x = [item[0] for item in rotated_polygon]
                    rotated_y = [item[1] for item in rotated_polygon]
                    rotated_object = Polygon(list(zip(rotated_x, rotated_y)))

                    if area_polygon.contains(rotated_object):
                        solution_found = True
                        solution_x = rotated_x
                        solution_y = rotated_y
                        break
                    else:
                        new_position = list(zip(rotated_x, rotated_y))

        return (solution_found, solution_x, solution_y)


def add_holes(red_lines: list):

    objects = []

    for entity_data in red_lines:
        coords_x = np.array(entity_data['points'])[:, 0]
        coords_y = np.array(entity_data['points'])[:, 1]
        polygon_to_check = Polygon(list(zip(coords_x, coords_y)))
        objects.append((polygon_to_check, polygon_to_check.area))

    if len(objects) == 0:
        return(0)
    elif len(objects) == 1:
        return(1, objects[0][0])
    
    elif len(objects) > 1:
        max_tuple = max(objects, key=lambda item: item[1])
        index_of_max_tuple = objects.index(max_tuple)
        biggest_object = objects[index_of_max_tuple]
        objects.pop(index_of_max_tuple)

        return(2, biggest_object, objects)