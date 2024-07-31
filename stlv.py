"""
Simple Binary STL Viewer using pyqtgraph
This script is designed to visualize binary STL files using pyqtgraph and provides various rendering options based on user input.

Usage
Running the script without arguments will prompt the user to enter a model filename:
""   python stlv.py    ""

Arguments
You can provide up to three additional arguments:

1 Additional Argument
This disables the measuring planes and changes the render mode of the object. The options are:
    1, "plain", or OTHER    : Renders the object in white.
    2 or "sharp"            : Renders the object in white without smoothing.
    3 or "wire"             : Renders the object as a wireframe.
    4, "balloon", or "xray" : Renders a transparent version of the object.
    5, "shaded", or "xrays" : Renders a shaded x-ray.
    6 or "edge"             : Renders the object based on edges.
   -1                       : Randomizes face colors.

2 Additional Arguments [xBed] [yBed]
This scales the xy plane to match the user-provided dimensions, which is useful for showing the object relative to a specific bed size.

3 Additional Arguments [xBed] [yBed] [zBed]
This adds the xz and yz planes for vertical height, allowing a more comprehensive view of the object's dimensions.

Example
To run the script with specific dimensions and render options:

python stlv.py your_model.stl 50 100 150
This command will render the model with a in a plane that is 50 units in the x direction, 100 units in the y direction, and 150 units in the z direction.

"""

import pyqtgraph as pg
import pyqtgraph.opengl as gl
import struct
from PyQt6.QtGui import QQuaternion, QVector3D
import numpy as np
import os.path
import sys

def check_and_get_filename():
    while True:
        filename = input("your file: ") if len(sys.argv) < 2 else sys.argv[1]
        if not filename.endswith('.stl'):
            filename += '.stl'
        if os.path.isfile(filename):
            return filename
        print('File does not exist!')

def read_stl_file(filename):
    with open(filename, "rb") as file:
        file.read(80)
        num_of_triangles = struct.unpack("<I", file.read(4))[0]
        print('Num. Faces:', num_of_triangles)
        
        record_dtype = np.dtype([
            ('Normals', np.float32, (3,)),
            ('Vertex1', np.float32, (3,)),
            ('Vertex2', np.float32, (3,)),
            ('Vertex3', np.float32, (3,)),
            ('atttr', '<i2', (1,))
        ])
        
        data = np.fromfile(file, dtype=record_dtype, count=num_of_triangles)
    return data

def calculate_model_info(tri):
    model_min = np.min(tri, axis=(0, 1))
    model_max = np.max(tri, axis=(0, 1))
    dimensions = model_max - model_min
    return dimensions, model_min

def create_grid(size, pos, rotation=None):
    grid = gl.GLGridItem(size=size)
    if rotation:
        axis, angle = rotation.getAxisAndAngle()
        grid.rotate(angle, axis.x(), axis.y(), axis.z())
    grid.translate(*pos)
    return grid

filename = check_and_get_filename()
print('Reading....', filename)
data = read_stl_file(filename)

v1, v2, v3 = data['Vertex1'], data['Vertex2'], data['Vertex3']
tri = np.hstack((v1[:, np.newaxis, :], v2[:, np.newaxis, :], v3[:, np.newaxis, :]))

dimensions, model_min = calculate_model_info(tri)
print(f'xDim: {dimensions[0]}\nyDim: {dimensions[1]}\nzDim: {dimensions[2]}')

app = pg.mkQApp("STL Renderer")
my_widget = gl.GLViewWidget()
my_widget.show()
my_widget.setWindowTitle('Render')
my_widget.setCameraPosition(distance=np.sqrt(dimensions[0]**2 + dimensions[1]**2 + dimensions[2]**2))

if len(sys.argv) >= 4:
    x_bed = float(sys.argv[2])
    y_bed = float(sys.argv[3])
    z_bed = float(sys.argv[4]) if len(sys.argv) >= 5 else dimensions[2]
else:
    x_bed, y_bed, z_bed = dimensions[0], dimensions[1], dimensions[2]

if len(sys.argv) == 3:
    mode = sys.argv[2]
    if mode == '-1':
        colors = np.random.random(size=(tri.shape[0], 3, 4))
        model = gl.GLMeshItem(vertexes=tri, vertexColors=colors, drawEdges=False, computeNormals=False)
    else:
        model = gl.GLMeshItem(vertexes=tri, smooth=mode not in ['sharp', '2','wire','3'], drawEdges=mode in ['plain','1','wire', '3'], computeNormals=True,drawFaces=mode not in ['wire', '3'])
        if  mode in ['balloon', 'xray', '4']:
            model.setColor((0, 1, 0, 0.2))
            model.setShader('balloon')
            model.setGLOptions('additive')
        elif mode in ['shade', 'xrays', '5']:
            model.setColor((1, 1, 1, 0.2))
            model.setShader('shaded')
            model.setGLOptions('additive')
        elif mode == 'edge' or mode == '6':
            model.setColor((1, 0, 0, 1))
            model.setShader('normalColor')
            model.setGLOptions('opaque')

else:
    grid_xy = create_grid(QVector3D(x_bed, y_bed, 1), (0, 0, -dimensions[2] / 2))
    my_widget.addItem(grid_xy)
    my_widget.addItem(gl.GLTextItem(pos=(x_bed / 2, 0.0, -dimensions[2] / 2), text=str(y_bed)))
    my_widget.addItem(gl.GLTextItem(pos=(0.0, y_bed / 2, -dimensions[2] / 2), text=str(x_bed)))

    if len(sys.argv) == 5:
        grid_xz = create_grid(QVector3D(x_bed, z_bed, 1), (0, -y_bed / 2, (z_bed - dimensions[2]) / 2), QQuaternion(0, 0, np.pi / 2, np.pi / 2))
        grid_yz = create_grid(QVector3D(z_bed, y_bed, 1), (-x_bed / 2, 0, (z_bed - dimensions[2]) / 2), QQuaternion(0, np.pi / 2, 0, np.pi / 2))
        my_widget.addItem(grid_xz)
        my_widget.addItem(grid_yz)
        my_widget.addItem(gl.GLTextItem(pos=(-x_bed / 2, 0.0, z_bed / 2), text=str(z_bed)))

    # for those who want a fast stl viewer, it is recommended to use the following script that just randomizes the face colors rather than using shaders
    # colors = np.random.random(size=(tri.shape[0], 3, 4))
    # model = gl.GLMeshItem(vertexes=tri, vertexColors=colors, computeNormals=True,setShader='normalColor',setGLOptions='opaque')
    model = gl.GLMeshItem(vertexes=tri, smooth=True, computeNormals=True, shader='normalColor', setGLOptions='opaque')


model.translate(-((dimensions[0]) / 2 + model_min[0]), -((dimensions[1]) / 2 + model_min[1]), -((dimensions[2]) / 2 + model_min[2]))
my_widget.addItem(model)

print('Directions:\n  Rotate view using M1\n  Pan using M3\n  Zoom using scroll\n  Or use arrow keys')

if __name__ == '__main__':
    pg.exec()
