import uuid
import numpy as np
import triangle as tr
import ifcopenshell
from ifcopenshell.api import run
from ifcopenshell.util.shape_builder import ShapeBuilder, V


create_guid = lambda: ifcopenshell.guid.compress(uuid.uuid1().hex)


def generate_ifc(ground_coordinates, wall_coordinates, num_floors=3, elevation_height=3.0):
    # Create a blank model
    model = ifcopenshell.file()

    # All projects must have one IFC Project element
    project = run("root.create_entity", model, ifc_class="IfcProject", name="My Project")

    # Geometry is optional in IFC, but because we want to use geometry in this example, let's define units
    run("unit.assign_unit", model)

    # Let's create a modeling geometry context, so we can store 3D geometry (note: IFC supports 2D too!)
    context = run("context.add_context", model, context_type="Model")

    # In particular, in this example we want to store the 3D "body" geometry of objects, i.e. the body shape
    body = run("context.add_context", model, context_type="Model",
        context_identifier="Body", target_view="MODEL_VIEW", parent=context)

    # Create a site, building, and floors. Many hierarchies are possible.
    site = run("root.create_entity", model, ifc_class="IfcSite", name="My Site")
    building = run("root.create_entity", model, ifc_class="IfcBuilding", name="Building A")
    floors = []

    for i in range(0, num_floors):
        floor = run("root.create_entity", model, ifc_class="IfcBuildingStorey", name=f"Floor {i+1}")
        floors.append(floor)

    # Since the site is our top level location, assign it to the project
    run("aggregate.assign_object", model, relating_object=project, products=[site])
    run("aggregate.assign_object", model, relating_object=site, products=[building])
    run("aggregate.assign_object", model, relating_object=building, products=floors)

    context = model.by_type("IfcGeometricRepresentationContext")[0]

    def create_ifclocalplacement(ifcfile, location, axis, ref_direction, relative_to):
        axis2placement = ifcfile.createIfcAxis2Placement3D(
            ifcfile.createIfcCartesianPoint(location),
            ifcfile.createIfcDirection(axis),
            ifcfile.createIfcDirection(ref_direction)
        )
        return ifcfile.createIfcLocalPlacement(relative_to, axis2placement)

    def create_ifcaxis2placement(ifcfile, location, axis, ref_direction):
        return ifcfile.createIfcAxis2Placement3D(
            ifcfile.createIfcCartesianPoint(location),
            ifcfile.createIfcDirection(axis),
            ifcfile.createIfcDirection(ref_direction)
        )

    def create_ifcextrudedareasolid(ifcfile, point_list, placement, direction, depth):
        points = [ifcfile.createIfcCartesianPoint(point) for point in point_list]
        polyline = ifcfile.createIfcPolyline(points)
        closed_profile = ifcfile.createIfcArbitraryClosedProfileDef("AREA", None, polyline)
        return ifcfile.createIfcExtrudedAreaSolid(closed_profile, placement, ifcfile.createIfcDirection(direction), depth)

    def create_material_and_style(ifcfile, name, color):
        material = ifcfile.createIfcMaterial(name)
        surface_style_rendering = ifcfile.createIfcSurfaceStyleRendering(
            SurfaceColour=ifcfile.createIfcColourRgb(None, *color),
            Transparency=0.0,
            DiffuseColour=ifcfile.createIfcColourRgb(None, *color),
            SpecularColour=ifcfile.createIfcColourRgb(None, *color),
            ReflectanceMethod="PLASTIC"
        )
        surface_style = ifcfile.createIfcSurfaceStyle(
            Name=None, Side="BOTH", Styles=[surface_style_rendering]
        )
        pres_style = ifcfile.createIfcPresentationStyleAssignment([surface_style])
        style = ifcfile.createIfcStyledItem(None, [pres_style], None)
        return material, style


    # Function to create transformation matrix
    def create_matrix(x, y, z, rotation_angle=0, rotation_axis="Z"):
        matrix = np.eye(4)
        if rotation_angle:
            matrix = ifcopenshell.util.placement.rotation(rotation_angle, rotation_axis) @ matrix
        matrix[:, 3][0:3] = (x, y, z)
        return matrix

    # Function to add windows to a wall based on its length
    def add_windows_to_wall(model, wall, start_point, end_point, length, angle, context, body, elevation):
        window_width = 1
        window_height = 1.5
        window_sill_height = 0.4
        num_windows = max(1, length // 3)
        window_spacing = length / (num_windows + 1)
        
        for i in range(int(num_windows)):
            window_x = (i + 1) * window_spacing
            if angle % 180 == 0:
                window_position = (start_point[0] + window_x * np.cos(np.radians(angle)),
                                start_point[1] + window_x * np.sin(np.radians(angle)))
            else:
                window_position = (start_point[0] + window_x * np.cos(np.radians(angle)),
                                start_point[1] + window_x * np.sin(np.radians(angle)))

            window = run("root.create_entity", model, ifc_class="IfcWindow", name=f"Window {i+1}")
            window_matrix = create_matrix(window_position[0], window_position[1], elevation + window_sill_height, rotation_angle=angle)
            run("geometry.edit_object_placement", model, product=window, matrix=window_matrix, is_si=True)
            window_representation = run("geometry.add_wall_representation", model, context=body, length=window_width, height=window_height, thickness=-0.02)
            run("geometry.assign_representation", model, product=window, representation=window_representation)
            run("spatial.assign_container", model, relating_structure=floor, products=[window])
            run("aggregate.assign_object", model, relating_object=wall, products=[window])

            # Add color to the window
            window_material, window_style = create_material_and_style(model, "Window Material", (0.1, 0.1, 0.8))  # Blue color
            model.createIfcRelAssociatesMaterial(create_guid(), None, None, None, [window], window_material)
            model.createIfcStyledItem(window_representation, [window_style], None)
            

    def create_walls_and_slab(floor, floor_index, elevation_height, create_walls=True):
        elevation = floor_index * elevation_height
        
        # Create walls based on the provided coordinates
        if floor_index == 0:
            for i, ((x1, y1), (x2, y2)) in enumerate(wall_coordinates):
                wall_length = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
                wall = run("root.create_entity", model, ifc_class="IfcWall", name=f"Wall {i+1} Floor {floor_index+1}")
                angle = np.arctan2(y2 - y1, x2 - x1) * (180 / np.pi)
                matrix = create_matrix(x1, y1, elevation, rotation_angle=angle)
                run("geometry.edit_object_placement", model, product=wall, matrix=matrix, is_si=True)
                representation = run("geometry.add_wall_representation", model, context=body, length=wall_length, height=-2, thickness=0.4)
                run("geometry.assign_representation", model, product=wall, representation=representation)
                run("spatial.assign_container", model, relating_structure=floor, products=[wall])
                
                # Add color to the wall
                wall_material, wall_style = create_material_and_style(model, "Wall Material", (0.5, 0.5, 0.5))
                model.createIfcRelAssociatesMaterial(create_guid(), None, None, None, [wall], wall_material)
                model.createIfcStyledItem(representation, [wall_style], None)
        
        if create_walls:
            for i, ((x1, y1), (x2, y2)) in enumerate(wall_coordinates):
                wall_length = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
                wall = run("root.create_entity", model, ifc_class="IfcWall", name=f"Wall {i+1} Floor {floor_index+1}")
                angle = np.arctan2(y2 - y1, x2 - x1) * (180 / np.pi)
                matrix = create_matrix(x1, y1, elevation, rotation_angle=angle)
                run("geometry.edit_object_placement", model, product=wall, matrix=matrix, is_si=True)
                representation = run("geometry.add_wall_representation", model, context=body, length=wall_length, height=elevation_height, thickness=0.2)
                run("geometry.assign_representation", model, product=wall, representation=representation)
                run("spatial.assign_container", model, relating_structure=floor, products=[wall])
                
                # Add color to the wall
                wall_material, wall_style = create_material_and_style(model, "Wall Material", (0.8, 0.3, 0.3))  # Red color
                model.createIfcRelAssociatesMaterial(create_guid(), None, None, None, [wall], wall_material)
                model.createIfcStyledItem(representation, [wall_style], None)
                
                # Add windows to the wall based on its length
                add_windows_to_wall(model, wall, (x1, y1), (x2, y2), wall_length, angle, context, body, elevation)
        else:
            for i, ((x1, y1), (x2, y2)) in enumerate(wall_coordinates):
                wall_length = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
                wall = run("root.create_entity", model, ifc_class="IfcWall", name=f"Wall {i+1} Floor {floor_index+1}")
                angle = np.arctan2(y2 - y1, x2 - x1) * (180 / np.pi)
                matrix = create_matrix(x1, y1, elevation, rotation_angle=angle)
                run("geometry.edit_object_placement", model, product=wall, matrix=matrix, is_si=True)
                representation = run("geometry.add_wall_representation", model, context=body, length=wall_length, height=3/3, thickness=0.2)
                run("geometry.assign_representation", model, product=wall, representation=representation)
                run("spatial.assign_container", model, relating_structure=floor, products=[wall])
                
                # Add color to the wall
                wall_material, wall_style = create_material_and_style(model, "Wall Material", (0.8, 0.3, 0.3))  # Red color
                model.createIfcRelAssociatesMaterial(create_guid(), None, None, None, [wall], wall_material)
                model.createIfcStyledItem(representation, [wall_style], None)
                
        # Create slab (floor) based on wall coordinates
        builder = ShapeBuilder(model)
        thickness = 200
        vertices = [(x *1000, y*1000) for (x, y), _ in wall_coordinates]
        vertices.append(vertices[0])  # Closing the loop
        polygon_points = [V(x, y) for x, y in vertices]
        polyline = builder.polyline(polygon_points)
        slab_profile = builder.profile(polyline)
        slab_solid = builder.extrude(slab_profile, thickness, V(0, 0, 1))
        representation = builder.get_representation(context=body, items=[slab_solid])

        slab = run("root.create_entity", model, ifc_class="IfcSlab", name=f"Slab Floor {floor_index+1}")
        product_definition_shape = model.createIfcProductDefinitionShape(Representations=[representation])
        slab.Representation = product_definition_shape
        slab_matrix = create_matrix(0, 0, elevation)
        run("geometry.edit_object_placement", model, product=slab, matrix=slab_matrix, is_si=True)
        run("spatial.assign_container", model, relating_structure=floor, products=[slab])


    def create_ground(model, context, ground_coordinates, elevation):
        ground = run("root.create_entity", model, ifc_class="IfcSlab", name=f"Ground Surface")
        vertices = [(x, y, z*0.3 - elevation) for (x, y, z) in ground_coordinates]

        # Perform Delaunay triangulation
        A = np.array(vertices)[:, :2]
        B = {'vertices': A}
        triangulation = tr.triangulate(B)
        faces = triangulation['triangles'].tolist()

        edges = []

        ground_representation = run("geometry.add_mesh_representation", model, context=context, vertices=[vertices], edges=edges, faces=[faces])
        run("geometry.assign_representation", model, product=ground, representation=ground_representation)
        
        # Add color to the ground
        ground_material, ground_style = create_material_and_style(model, "Ground Material", (0.2, 0.8, 0.2))  # Green color
        model.createIfcRelAssociatesMaterial(create_guid(), None, None, None, [ground], ground_material)
        model.createIfcStyledItem(ground_representation, [ground_style], None)
        
        # Since we are not placing it within a building storey, let's create a placement
        placement = run("geometry.edit_object_placement", model, product=ground, matrix=np.eye(4).tolist(), is_si=True)
        run("spatial.assign_container", model, relating_structure=floors[0], products=[ground])

    # Create walls and slabs for each floor
    for i, floor in enumerate(floors):
        create_walls_and_slab(floor, i, elevation_height)

    create_walls_and_slab(floors[-1], num_floors, elevation_height, create_walls=False)
    
    create_ground(model, context, ground_coordinates, elevation=1.2)

    return model