# Building Design  - AI-Конфигуратор размещения проектируемых зданий на заданной территории
[![VIKTOR](https://img.shields.io/badge/VIKTOR-Engineering%20Apps-blue)](https://www.viktor.ai/)  [![IFC OpenShell](https://img.shields.io/badge/IFC%20OpenShell-BIM-red)](http://ifcopenshell.org/)  [![ONNX Runtime](https://img.shields.io/badge/ONNX%20Runtime-Machine%20Learning-green)](https://onnxruntime.ai/)  [![ezdxf](https://img.shields.io/badge/ezdxf-DXF%20Files-yellow)](https://ezdxf.readthedocs.io/)  [![Python](https://img.shields.io/badge/Python-Programming%20Language-brightgreen)](https://www.python.org/)
## Описание 
Данный сервис на основе ML-подхода предназначен для автоматизация рутинных задач по выбору вариантов размещения зданий на заданной территории в процессе проектирования.

Цель приложения - продемонстрировать в упрощенной форме, как инженеры могут создавать 3D-модель в соответствии с заданными параметрами и условиями на базе уже готовых моделей зданий и сооружений на заданной территории и адаптивно размещать 3D-модель  в пределах заданной территории, а также предлагать альтернативные варианты со схожими параметрами за более короткий период времени, чем при обычных подходах проектирования.  

С поолныи описание приложения, руководством пользования и описанием используемых технологий  можно ознакомится [здесь.](tech_guideline.pdf)
## Демо 
Демонстрационная версия этого приложения доступна на [AI-Конфигуратор зданий](https://cloud.viktor.ai/public/building-design)
![Alt Text](workflow_example-resize.gif)
> **_Ограничение демонстрационной модели:_**
>- _возможен выбор только заранее предустановленных планов территории и типовых зданий._
>- _загрузка собственных планов и моделей доступен в полнофункциональной версии приложения._

## Порядок работы с приложением: 
Для работы приложения перейдите по ссылке  [AI-Конфигуратор зданий](https://cloud.viktor.ai/public/building-design)  
### Выбор базовых параметров:
1. В выпадающем меню `Выберите границы и высоты участка (Select boundaries and elevation dxf)` - вариант участка территории в формате .dxf
2. В меню `Выберите ifc модель КР (Select ifc model)` - вариант типовой модели здания в формате .ifc
3. В меню  `Выберите вариацию здания(Select building variant)` - вариант генерируемого альтернативного плана 
модели здания.
### Доступные для корректировки параметры:
`Высота этажа, м (Elevation height)` - корректировка высоты этажа в метрах  
`Количество этажей (Number of floors)` - корректировка этажности  
`Площадь здания, м2 (Building area)` - корректировка общей площади здания (при невозможности размещения указанной площади будет выведено предупреждающее сообщение)  

### Отображение результатов:  
Трехмерная визуализация пространственной концепции размещения сгенерированного здания отображается в правом окне автоматически при выборе новых или изменении ранее выбранных параметров в следующих доступных к просмотру вкладках:  
`Generated IFC model` - сгенерированная модель здания,  
`Generated Plan view` - размещение модели на заданной территории в плане,  
`Input IFC model` - загруженная исходная типовая IFC модель.  

## Используемые технологии и инструменты:
[![VIKTOR](https://img.shields.io/badge/VIKTOR-Engineering%20Apps-blue)](https://www.viktor.ai/)
  [VIKTOR](https://www.viktor.ai/) - Платформа для создания инженерных приложений.  
[![IFC OpenShell](https://img.shields.io/badge/IFC%20OpenShell-BIM-red)](http://ifcopenshell.org/)
  [IFC OpenShell](http://ifcopenshell.org/) - Библиотека с открытым исходным кодом для работы с IFC файлами в BIM.  
[![ONNX Runtime](https://img.shields.io/badge/ONNX%20Runtime-Machine%20Learning-green)](https://onnxruntime.ai/)
  [ONNX Runtime](https://onnxruntime.ai/) - Высокопроизводительная среда выполнения для моделей ONNX.  
[![ezdxf](https://img.shields.io/badge/ezdxf-DXF%20Files-yellow)](https://ezdxf.readthedocs.io/)
  [ezdxf](https://ezdxf.readthedocs.io/) - Библиотека Python для работы с файлами DXF.  


