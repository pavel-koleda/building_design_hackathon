import ifcopenshell
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon, MultiPoint
from shapely.ops import unary_union, polygonize
from typing import List, Optional, Tuple, Any



def get_building_polygon(model_path):
    model = ifcopenshell.open(model_path)
    levels = model.by_type("IfcBuildingStorey")

    # Level that captures the -100 mark
    target_elevation = -100
    selected_level = None

    # Sort the levels by height
    selected_levels = sorted(levels, key=lambda x: x.Elevation)
    result_building_polygon = None
    
    for selected_level in selected_levels:
        if not selected_level:
            continue
        else:
            # Find all walls belonging to the selected level
            walls_on_selected_level = []

            for rel in selected_level.ContainsElements:
                for element in rel.RelatedElements:
                    if element.is_a("IfcWall") or element.is_a("IfcWallStandardCase"):
                        walls_on_selected_level.append(element)

            def get_global_transform(instance):
                transform = np.identity(4)
                while instance:
                    if instance.ObjectPlacement:
                        placement = instance.ObjectPlacement
                        if placement.is_a('IfcLocalPlacement'):
                            rel_placement = placement.RelativePlacement
                            if rel_placement.is_a('IfcAxis2Placement3D'):
                                location = np.array(rel_placement.Location.Coordinates)
                                local_transform = np.identity(4)
                                local_transform[:3, 3] = location
                                if rel_placement.RefDirection:
                                    direction1 = np.array(rel_placement.RefDirection.DirectionRatios)
                                    local_transform[:3, 0] = direction1
                                if rel_placement.Axis:
                                    direction2 = np.array(rel_placement.Axis.DirectionRatios)
                                    local_transform[:3, 2] = direction2
                                transform = np.dot(local_transform, transform)
                    instance = instance.Decomposes[0].RelatingObject if instance.Decomposes else None
                return transform

            def transform_coordinates(coords, transform):
                if coords.shape[1] != 3:
                    raise ValueError("Input coordinates must have 3 columns (x, y, z).")
                coords_homogeneous = np.hstack((coords, np.ones((coords.shape[0], 1))))
                transformed_coords = transform.dot(coords_homogeneous.T).T
                return transformed_coords[:, :3]

            def get_wall_coordinates(wall):
                ifc_representation = wall.Representation
                if ifc_representation:
                    for representation in ifc_representation.Representations:
                        if representation.RepresentationType in ['Curve2D', 'Curve3D']:
                            for item in representation.Items:
                                if item.is_a('IfcIndexedPolyCurve'):
                                    points_list = item.Points
                                    points = np.array(points_list.CoordList)
                                    transform = get_global_transform(wall)
                                    global_coords = transform_coordinates(points, transform)
                                    coordinates = [(coord[0], coord[1]) for coord in global_coords]
                                    return coordinates
                                if item.is_a('IfcPolyline'):
                                    points = [pt.Coordinates for pt in item.Points]
                                    points = np.array(points)
                                    if points.shape[1] == 2:
                                        points = np.hstack((points, np.zeros((points.shape[0], 1))))
                                    transform = get_global_transform(wall)
                                    global_coords = transform_coordinates(points, transform)
                                    coordinates = [(coord[0], coord[1]) for coord in global_coords]
                                    return coordinates
                        elif representation.RepresentationType == 'SweptSolid':
                            for item in representation.Items:
                                if item.is_a('IfcExtrudedAreaSolid'):
                                    profile = item.SweptArea
                                    if profile.is_a('IfcArbitraryClosedProfileDef'):
                                        outer_curve = profile.OuterCurve
                                        if outer_curve.is_a('IfcPolyline'):
                                            points = np.array([point.Coordinates for point in outer_curve.Points])
                                            if points.shape[1] == 2:
                                                points = np.hstack((points, np.zeros((points.shape[0], 1))))
                                            transform = get_global_transform(wall)
                                            global_coords = transform_coordinates(points, transform)
                                            coordinates = [(coord[0], coord[1]) for coord in global_coords]
                                            return coordinates
                return None

            wall_coordinates_list = []

            for wall in walls_on_selected_level:
                coordinates = get_wall_coordinates(wall)
                if coordinates:
                    wall_coordinates_list.append(coordinates)
            if wall_coordinates_list:
                all_points = [point for line in wall_coordinates_list for point in line]
                multipoint = MultiPoint(all_points)
                merged_polygon = unary_union(multipoint)
                exterior = merged_polygon.convex_hull.exterior
                result_building_polygon = list(exterior.coords)
                break
            
    return result_building_polygon
