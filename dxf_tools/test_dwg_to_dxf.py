#!pip install ezdxf
# ДЛЯ ЗАПУСКА В COLAB
import io
import re
import ezdxf
from ezdxf.addons import odafc
import os


os.environ['XDG_RUNTIME_DIR'] = '/tmp'
!apt-get install -y xvfb ffmpeg > /dev/null 2>&1
# Даем разрешение на выполнение файла ODAFileConverter.AppImage
!chmod +x /content/ODAFileConverter.AppImage
# Исправляем права доступа к /tmp
!chmod 0700 /tmp
#  путь к ODAFileConverter.AppImage
odafc.unix_exec_path = "/content/ODAFileConverter.AppImage" 
# Проверка, что ODA File Converter установлен
if not odafc.is_installed():
    raise odafc.ODAFCNotInstalledError("ODA File Converter не найден!")
OUTVER = "ACAD2018"


#Конвертирует файл DWG в DXF.
def convert_dwg_to_dxf(input_file, output_path):
    try:
        doc = odafc.readfile(input_file, version=OUTVER)
        #doc.saveas(output_path)  # тут идет сохранение на диск dxf файла
        #print(f"Файл '{input_file}' успешно конвертирован в '{output_path}'.")
        # Создаем объект StringIO для записи DXF данных
        dxf_stream = io.StringIO()
        # Записываем DXF в поток
        doc.write(dxf_stream, fmt='asc')
        # Перемещаем указатель в начало потока
        dxf_stream.seek(0)
        print(f"Файл '{input_file}' успешно конвертирован в DXF.")
        return dxf_stream  # Возвращаем объект TextIO
    except Exception as e:
        print(f"Ошибка при конвертации файла '{input_file}': {e}")


# поиск красных полилиний
def extract_red_lines(dxf_file):
    # Читаем данные DXF из потока
    doc = ezdxf.read(dxf_file)
    msp = doc.modelspace()
    lwpolyline_data = []
    # Итерируемся по всем сущностям в пространстве модели
    for entity in msp:
        # Проверяем, является ли сущность LWPOLYLINE
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


# достает все сущности с их ключевыми данными
def extract_all_entities_data(dxf_file):
    doc = ezdxf.read(dxf_file)
    msp = doc.modelspace()
    all_entities_data = []
    # Итерируемся по всем сущностям в пространстве модели
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
        # добавляем тип сущности
        entity_data['type'] = entity.dxftype()
        if entity_data:
            all_entities_data.append(entity_data)

    return all_entities_data

# Ищет сущность в списке, которая находится близко к текстовой сущности
def find_close_vec(text_entity, entities_list):
    text_coords = text_entity['coords']
    for entity in entities_list:
        if entity['type'] == 'INSERT':
            ins_coords = entity['coords']
            state = text_coords.isclose(ins_coords, abs_tol=14e-1)
            if state:
                return entity
    return None


# возвращает данные красной линии
def get_red_line_data(file):
    # Запуск конвертации
    output_path = file[:-4] + ".dxf"
    dxf_file = convert_dwg_to_dxf(file, output_path)
    # получаем инфу красных границ
    lwpolyline_data = extract_red_lines(dxf_file)
    return lwpolyline_data


# возвращает данные высоты и точки возле высот
def get_heights_data(file):
    # Запуск конвертации
    output_path = file[:-4] + ".dxf"
    dxf_file = convert_dwg_to_dxf(file, output_path)
    # достает все сущности с их ключевыми данными
    all_data = extract_all_entities_data(dxf_file)
    # паттерн для поиска высот среди текста
    pattern = r"^\d+\.\d+$" 
    # получаем коориднаты высот и точек возле них
    height_coords = []  # тут будут высоты и их координаты
    height_coords_with_inserts = []  # тут высоты, их координаты и точки рядом
    for entity_data in all_data:
        if entity_data['type'] == 'TEXT':
            if re.match(pattern, entity_data['text']):
                close_entity = find_close_vec(entity_data, all_data)
                height_coords.append((entity_data['text'],entity_data['coords']))
                if close_entity:
                    height_coords_with_inserts.append((entity_data['text'],entity_data['coords'], close_entity['coords']))
                    #print(f"Текст: {(entity_data['text'])}. Координаты текста {entity_data['coords']}. Данные сущности: {close_entity}")
    return height_coords, height_coords_with_inserts


# Пример использования:
file_path = '/content/Исходная_подоснова_с_отметками_рельефа_и_старым_корпусом.dxf'
height_data, dots_height_data = get_heights_data(file_path)
file_path_border = '/content/Границы участка.dwg'
red_data = get_red_line_data(file_path_border)
print(red_data)
print(height_data)
print(dots_height_data)








