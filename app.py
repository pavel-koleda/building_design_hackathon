import os
import pickle
import tempfile
import logging
import numpy as np
import onnxruntime as ort
from io import BytesIO, StringIO
from pathlib import Path
import matplotlib.pyplot as plt
from shapely import Polygon
from shapely.affinity import translate
from viktor import File, ViktorController, ParamsFromFile
from viktor.errors import UserError, InputViolation
from viktor.parametrization import ViktorParametrization, NumberField, Text, FileField, OptionField, OptionListElement, ActionButton
from viktor.geometry import CircularExtrusion, Group, Material, Color, Point, LinearPattern, Line
from viktor.views import GeometryView, GeometryResult, IFCView, IFCResult, ImageResult, ImageView
from viktor.core import Storage

from src.generate_ifc import generate_ifc
from src.dxf_reader import extract_red_lines, get_heights_data
from src.ifc_plan_extracting import get_building_polygon
from src.normalization import scaling_object, normalize_vector
from src.polygon_placing import place_polygon, add_holes
from src.picture_processing import vec_to_features

onnx_model_path = Path(__file__).parent / 'models/resnet50.onnx'
session = ort.InferenceSession(onnx_model_path)
logging.basicConfig(level=logging.DEBUG)

kd_vectors_path = Path(__file__).parent / 'models/kd_vectors.pkl'
with open(kd_vectors_path, 'rb') as file:
    tree = pickle.load(file)

xy_coords_path = Path(__file__).parent / 'models/xy_coords.pkl'
with open(xy_coords_path, 'rb') as file:
    xy_coords = pickle.load(file)

files_dict = {
    "Модель 85.4_0_КР_R19": ('Границы участка 85.4_0_КР_R19.dxf', 
                             'Подоснова 85.4_0_КР_R19.dxf'),
    "Модель К01_КР_П_R20": ('Границы участка К01_КР_П_R20.dxf', 
                             'Подоснова К01_КР_П_R20.dxf'),
    "Модель К01_КР1_П_R20": ('Границы участка К01_КР1_П_R20.dxf', 
                             'Подоснова К01_КР1_П_R20.dxf'),
    "Модель МКСП_ВЕР12Б_К10_КР_П_R21_ДСШ": ('Границы участка МКСП_ВЕР12Б_К10_КР_П_R21_ДСШ.dxf', 
                             'Подоснова МКСП_ВЕР12Б_К10_КР_П_R21_ДСШ.dxf')
}

building_var_dict = {
    'Вариант_1': None,
    'Вариант_2': None,
    'Вариант_3': None,
}

IFC_MODEL_OPTIONS = [
    OptionListElement(label="85.4_0_КР_R19.ifc", value='85.4_0_КР_R19.ifc'),
    OptionListElement(label="К01_КР_П_R20.ifc", value='К01_КР_П_R20.ifc'),
    OptionListElement(label="К01_КР1_П_R20.ifc", value='К01_КР1_П_R20.ifc'),
    OptionListElement(label="МКСП_ВЕР12Б_К10_КР_П_R21_ДСШ.ifc", value='МКСП_ВЕР12Б_К10_КР_П_R21_ДСШ.ifc'),
]

BOUND_DXF = [
    OptionListElement(label="Модель 85.4_0_КР_R19", 
                      value="Модель 85.4_0_КР_R19"),
    OptionListElement(label="Модель К01_КР_П_R20", 
                      value="Модель К01_КР_П_R20"),
    OptionListElement(label="Модель К01_КР1_П_R20", 
                      value="Модель К01_КР1_П_R20"),
    OptionListElement(label="Модель МКСП_ВЕР12Б_К10_КР_П_R21_ДСШ", 
                      value="Модель МКСП_ВЕР12Б_К10_КР_П_R21_ДСШ"),
]

BUILDING_VAR_OPTIONS = [
    OptionListElement(label="Вариант_1", value='Вариант_1'),
    OptionListElement(label="Вариант_2", value='Вариант_2'),
    OptionListElement(label="Вариант_3", value='Вариант_3'),
]


class Parametrization(ViktorParametrization):
    text_building = Text('## Input data (Введите данные)')
    elevation_height = NumberField('Elevation height (Высота этажа), м', min=1.0, default=3.0)
    building_floors = NumberField('Number of floors (Кол-во этажей)', min=1, default=3)
    building_area = NumberField('Building area (Площадь здания), м2', min=1.0, default=2000.0)
    bound_file = OptionField("Select boundaries and elevation dxf (Выберите границы и высоты участка)", options=BOUND_DXF, default=BOUND_DXF[2].value,
                    description="Выберите из выпадающего списка необходимый файл с границами и высотами участка", flex=80)
    input_ifc_file = OptionField("Select ifc model (Выберите ifc модель КР)", options=IFC_MODEL_OPTIONS, default=IFC_MODEL_OPTIONS[2].value,
                    description="Выберите из выпадающего списка необходимую модель здания", flex=80)
    building_var = OptionField("Select building variant (Выберите вариацию здания)", options=BUILDING_VAR_OPTIONS, default=BUILDING_VAR_OPTIONS[0].value,
                    description="Выберите из выпадающего списка необходимую модель здания", flex=80)


class Controller(ViktorController):
    label = 'My Entity Type'
    parametrization = Parametrization


    @IFCView('Generated IFC model', duration_guess=3)
    def get_ifc_view(self, params, **kwargs):
        try:
            if not params.bound_file:
                raise UserError('Please upload the boundaries DWG file (Загрузите границы участка).')

            model_path = Path(__file__).parent / 'data/ifc' / params["input_ifc_file"]
            bound_file_path = Path(__file__).parent / 'data/bound_dxf' / files_dict[params["bound_file"]][0]
            elevation_baseline_file_path = Path(__file__).parent / 'data/height_dxf' / files_dict[params["bound_file"]][1]
            
            # Extracting the building polygon from the loaded IFC model
            building_polygon = get_building_polygon(model_path)
            
            # Extracting the boundaries of the site
            red_line_data = extract_red_lines(bound_file_path)
            
            # Extracting the internal bounding polygons, if there are any.
            test_holes = add_holes(red_line_data)
            
            if test_holes[0] == 0:
                print('No lines found')
                raise UserError('No bounds found (Не смог найти границы участка в файле).')

            elif test_holes[0] == 1:
                interm_polygon = test_holes[1]
                main_area_coords = list(interm_polygon.exterior.coords)

            elif test_holes[0] == 2:
                main_area_coords = list(test_holes[1][0].exterior.coords)
                holes_coords = []

                for entity in test_holes[2]:
                    holes_coords.append(list(entity[0].exterior.coords))
                    interm_polygon = Polygon(shell=main_area_coords, holes=holes_coords)
                    
            heights = get_heights_data(elevation_baseline_file_path)
            
            area_coords_x = np.array(main_area_coords)[:, 0]
            area_coords_y = np.array(main_area_coords)[:, 1]
            
            moved_area_coords_x, moved_area_coords_y = normalize_vector(area_coords_x)[0], normalize_vector(area_coords_y)[0]
            area_delta_x, area_delta_y = normalize_vector(area_coords_x)[1], normalize_vector(area_coords_y)[1]
            
            heights_coords_x = np.array(heights['coords'])[:, 0] + area_delta_x
            heights_coords_y = np.array(heights['coords'])[:, 1] + area_delta_y
            
            area_polygon_custom = translate(interm_polygon, area_delta_x, area_delta_y)
            if test_holes[0] == 2:
                x_holes = None
                y_holes = None

                for hole in area_polygon_custom.interiors:
                    hole_x, hole_y = hole.xy
                    x_holes = list(hole_x)
                    y_holes = list(hole_y)
            
            temp_pic_path = str(Path(__file__).parent)
            
            building_polygon_feature = vec_to_features(temp_pic_path, vector=building_polygon, onnx_session=session)
            
            k_nearest_indices = tree.query(building_polygon_feature, k=3)[1]
            
            for idx, key in enumerate(building_var_dict):
                building_var_dict[key] = k_nearest_indices[idx]
                
            
            object_x = xy_coords[building_var_dict[params.building_var]][1].tolist()
            object_y = xy_coords[building_var_dict[params.building_var]][0].tolist()
            
            
            scaled_object = scaling_object(object_x, object_y, target_area=params["building_area"])[0]
            
            solution_found, coords_x, coords_y = place_polygon(area_polygon=area_polygon_custom, object_polygon=scaled_object)
            if not solution_found:
                raise UserError("Can't place model (Не могу разместить здание, введите другие параметры, возможно стоит уменьшить площадь здания)")

            ground_coordinates = np.array(list(zip(heights_coords_x, heights_coords_y, heights['heights']))).reshape(-1, 3).tolist()
            raw_wall_arr = np.array(list(zip(coords_x, coords_y)))

            # Array conversion
            full_wall_arr = np.array([raw_wall_arr[i-1:i+1] for i in range(1, len(raw_wall_arr))])
            wall_coordinates = np.append(full_wall_arr, [[raw_wall_arr[-1], raw_wall_arr[0]]], axis=0).tolist()
            # IFC model generation
            ifc_model = generate_ifc(   ground_coordinates=ground_coordinates, 
                                        wall_coordinates=wall_coordinates,
                                        num_floors=params.building_floors, 
                                        elevation_height=params.elevation_height
                                    )
            # Determining the path to save the IFC file
            ifc_file_path = Path(__file__).parent / 'generated_model.ifc'
            
            # Saving a model to a file
            ifc_model.write(str(ifc_file_path))
            
            # Uploading a model to create a File object
            ifc_file = File.from_path(ifc_file_path)
            
            # Plan photo saving
            figure_path = Path(__file__).parent / 'figure.png'
            
            plt.figure()
            plt.plot(coords_x, coords_y , linestyle='-', color='b')
            plt.plot(moved_area_coords_x, moved_area_coords_y, linestyle='-', marker='o')
            if test_holes[0] == 2:
                plt.plot(x_holes, y_holes, linestyle='-', color='r')
            plt.xlabel('X')
            plt.ylabel('Y')
            plt.grid(True)
            plt.gca().set_aspect('equal')
            plt.savefig(figure_path)
        except Exception as e:
            raise UserError(e)
        return IFCResult(ifc_file)

    @ImageView("Generated Plan view", duration_guess=3, update_label='Update')
    def createPlot(self, params, **kwargs):
        self.get_ifc_view(self, params, **kwargs)
        
        figure_path_1 = Path(__file__).parent / 'figure.png'
        
        return ImageResult.from_path(figure_path_1)
    
    
    @IFCView('Input IFC model', duration_guess=3)
    def get_input_ifc_view(self, params, **kwargs):
        input_model_path = Path(__file__).parent / 'data/ifc' / params["input_ifc_file"]
        
        # Uploading a model to create a File object
        input_ifc_file = File.from_path(input_model_path)
        
        return IFCResult(input_ifc_file)