!pip install ezdxf

import re
import ezdxf
from typing import List, Dict

# поиск красных полилиний
def extract_red_lines(dxf_file) -> List:
    # Читаем данные DXF 
    #doc = ezdxf.read(dxf_file)  #для бинарного 
    doc = ezdxf.readfile(dxf_file)  #для файла из хранилища
    msp = doc.modelspace()  # Пространство модели
    lwpolyline_data = []  
    # Итерируемся по всем сущностям в пространстве модели
    for entity in msp:
        # Проверяем, является ли сущность LWPOLYLINE и красного ли она цвета 
        # entity.dxf.color == 2 - жёлтый
        if entity.dxftype() == 'LWPOLYLINE' and entity.dxf.color == 1:
            # Извлекаем данные (тут может есть и лишние, но лишним :) не будет)
            lwpolyline_info = {
                'handle': entity.dxf.handle,
                'layer': entity.dxf.layer,
                'points': entity.get_points(),   # Список координат вершин
                'linetype': entity.dxf.linetype,
                'color': entity.dxf.color,
                'lineweight': entity.dxf.lineweight
            }
            lwpolyline_data.append(lwpolyline_info)
    return lwpolyline_data 


# достает все сущности с их ключевыми данными, важными для данной задачи
def extract_all_entities_data(dxf_file) -> List:
    #doc = ezdxf.read(dxf_file)  #для бинарного 
    doc = ezdxf.readfile(dxf_file)  #для файла из хранилища
    msp = doc.modelspace()
    all_entities_data = []
    # Итерируемся по всем сущностям в пространстве модели
    for entity in msp:
        entity_data = {}
        if entity.dxftype() == 'TEXT':
            entity_data['text'] = entity.dxf.text  # текст
            entity_data['coords'] = entity.dxf.insert  # координаты (в виде Vec3)
        elif  entity.dxftype() == 'INSERT':
            entity_data['coords'] = entity.dxf.insert  # координаты (в виде Vec3)
        elif entity.dxftype() == 'LINE':
            entity_data['start'] = entity.dxf.get('start')  # координаты начала (в виде Vec3)
            entity_data['end'] = entity.dxf.end  # координаты конца (в виде Vec3)
        elif entity.dxftype() == 'LWPOLYLINE':
            entity_data['points'] = entity.get_points()  # координаты вершин (в виде Vec3)
        # добавляем тип сущности
        entity_data['type'] = entity.dxftype()
        if entity_data:
            all_entities_data.append(entity_data)
    return all_entities_data


# Ищет сущность в списке, которая находится близко к текстовой сущности
def find_close_vec(text_entity, entities_list: List):
    text_coords = text_entity['coords']  # координаты текстовой сущности
    
    # по всему списку ищем одну точку близко от текста
    for entity in entities_list:
        # отбираем сущности типа INSERT (обычно это точки)
        if entity['type'] == 'INSERT':
            ins_coords = entity['coords']
            # определяем, находится на определенном расстоянии сущность insert
            state = text_coords.isclose(ins_coords, abs_tol=14e-1)  # bool
            if state:
                return entity
    return None


# для получения координат высот и координат точек рядом, если есть
def get_heights_data(file):
    # достает все сущности с их ключевыми данными
    all_data = extract_all_entities_data(file)
    # паттерн для поиска высот среди текста
    pattern = r"^\d+\.\d+$" 
    # получаем коориднаты высот и точек возле них
    height_coords = []  # тут будут высоты и их координаты
    height_coords_with_inserts = []  # тут высоты, их координаты и точки рядом
    # проходим по списку со всеми найденными сущностями
    for entity_data in all_data:
        #  взяли только текстовые сущности
        if entity_data['type'] == 'TEXT':
            # фильтруем только высоты (число.число)
            if re.match(pattern, entity_data['text']):
                # добавляем в список высоты и их координаты
                height_coords.append((entity_data['text'],entity_data['coords']))
                # оправляем на поиск близких точек
                close_entity = find_close_vec(entity_data, all_data)
                # добавляем в список высоты, их координаты и точки рядом (с координатами)
                if close_entity:
                    height_coords_with_inserts.append((entity_data['text'],entity_data['coords'], close_entity['coords']))
    return height_coords, height_coords_with_inserts


# достает высоты и их координаты, а также точки (и их координаты) рядом с ними
file_path = '/content/Исходная_подоснова_с_отметками_рельефа_и_старым_корпусом.dxf'
height_data, dots_height_data = get_heights_data(file_path)

# достает красную границу
file_path_border = '/content/Границы участка.dxf'
red_data = extract_red_lines(file_path_border)

print(f"Все данные красных границ - {red_data}")
print(f"Высоты и их координаты - {height_data}")
print(f"Высоты и их координаты, а также координаты точек рядом с ними -  {dots_height_data}")
