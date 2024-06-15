import re
import numpy as np
import ezdxf
from typing import List, Dict


def extract_red_lines(dxf_file) -> List:

    doc = ezdxf.readfile(dxf_file)
    msp = doc.modelspace()
    lwpolyline_data = []  
    # Iterate over all entities in the model space
    for entity in msp:
        # Checking if the entity is LWPOLYLINE and if it is red
        if entity.dxftype() == 'LWPOLYLINE' and entity.dxf.color == 1:
            # Extracting data
            lwpolyline_info = {
                'handle': entity.dxf.handle,
                'layer': entity.dxf.layer,
                'points': entity.get_points(),
                'linetype': entity.dxf.linetype,
                'color': entity.dxf.color,
                'lineweight': entity.dxf.lineweight
            }
            lwpolyline_data.append(lwpolyline_info)
    return lwpolyline_data 


def extract_all_entities_data(dxf_file) -> List:
    doc = ezdxf.readfile(dxf_file)
    msp = doc.modelspace()
    all_entities_data = []
    # Iterate over all entities in the model space
    for entity in msp:
        entity_data = {}
        if entity.dxftype() == 'TEXT':
            entity_data['text'] = entity.dxf.text
            entity_data['coords'] = entity.dxf.insert
        elif  entity.dxftype() == 'INSERT':
            entity_data['coords'] = entity.dxf.insert
        elif entity.dxftype() == 'LINE':
            entity_data['start'] = entity.dxf.get('start')
            entity_data['end'] = entity.dxf.end
        elif entity.dxftype() == 'LWPOLYLINE':
            entity_data['points'] = entity.get_points()
        # Add entity type
        entity_data['type'] = entity.dxftype()
        if entity_data:
            all_entities_data.append(entity_data)
    return all_entities_data



def find_close_vec(text_entity, entities_list: List):
    text_coords = text_entity['coords']
    
    # Throughout the list we look for one point close to the text
    for entity in entities_list:
        # Select entities of type INSERT (usually points)
        if entity['type'] == 'INSERT':
            ins_coords = entity['coords']
            # Вetermine whether the INSERT entity is at a certain distance
            state = text_coords.isclose(ins_coords, abs_tol=14e-1)
            if state:
                return entity
    return None


def get_heights_data(file):
    all_data = extract_all_entities_data(file)
    # Pattern for finding heights among text
    pattern = r"^\d+\.\d+$" 
    # Get the coordinates of the heights and points near them
    height_coords = []
    height_coords_with_inserts = []
    
    for entity_data in all_data:
        if entity_data['type'] == 'TEXT':
            if re.match(pattern, entity_data['text']):
                height_coords.append((entity_data['text'],entity_data['coords']))
                close_entity = find_close_vec(entity_data, all_data)
                if close_entity:
                    height_coords_with_inserts.append((entity_data['text'],entity_data['coords'], close_entity['coords']))
    heights = np.array([float(point[0].replace(',', '.')) for point in height_coords])
    heights = (heights[heights > 100]) - heights.mean()
    
    result_points = {   'heights': heights.tolist(),
                        'coords': [(point[1].x, point[1].y) for point in height_coords],
                    }
    return result_points