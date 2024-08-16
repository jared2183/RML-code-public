from mecode import G
from pathlib import Path
import json

# Printer default constants
LCE_PRESSURE = 40  # psi
POST_EXTRUSION_DWELL = 0  # s, 1 second
TRAVEL_SPEED = 15  # mm/s, this is just for moving, not for printing
TRAVEL_HEIGHT = 10 # mm, height above the substrate that the print head will be traveling at
DEFAULT_PRINT_SPEED = 1  # mm/s, this will be changing throughout the process, likely between 4-10 mm/s needed
DEFAULT_PRINT_HEIGHT = 0.1 # mm, height above the substrate that the print head will be printing on

# data for each material index
material_data = json.load(open(Path(__file__).parent / 'materialData' / 'material_data.json'))

class gcodeLibrary:
    def __init__(self, outpath=Path(__file__).parent / 'output'):
        self.outpath = outpath
        self.material_index = 0
        global g
        g = G(outfile=str(self.outpath), aerotech_include=True)
        g.rename_axis(z='A') # 'A' is our default starting nozzle axis. Will swap if first edge printed is with 'B'
        g.feed(TRAVEL_SPEED)

    def __swap_material(self, material_index):
        g.abs_move(z=TRAVEL_HEIGHT, C=TRAVEL_HEIGHT) # moves z stage of prev material back up before swapping

        prev_mat = material_data[self.material_index]
        self.material_index = material_index
        mat = material_data[material_index]
        g.rename_axis(z=mat["axis_name"])

        # sets the new home position for the swapped to nozzle
        dx = mat["x_home_position"] - prev_mat["x_home_position"]
        dy = mat["y_home_position"] - prev_mat["y_home_position"] # each z axis has its own home position so dont need to shift z

        new_x = g.current_position['x'] - dx
        new_y = g.current_position['y'] - dy

        g.set_home(x=new_x, y=new_y)   # sets current position to new x,y coordinates

    def __start_printing(self, print_height_mm=0.1, print_speed_mmps=DEFAULT_PRINT_SPEED, print_pressure_psi=LCE_PRESSURE):
        if print_height_mm <= 0:
            raise Exception("ERROR: Print height has to be greater than 0.")
        
        mat = material_data[self.material_index]
        COM = mat["pressure_COM"]
        dwell = mat["dwell_time"]
        g.set_pressure(COM, print_pressure_psi)  # set pressure of LCE
        g.dwell(dwell)

        g.abs_move(z=print_height_mm, C=print_height_mm)   # lowers Z stage, assuming 0.1mm layer height
        g.feed(print_speed_mmps)    # sets print speed
        g.toggle_pressure(COM)  # turn on the LCE pressure box

    def __stop_printing(self):
        COM = material_data[self.material_index]["pressure_COM"]
        g.toggle_pressure(COM)  # turn off the core

        g.feed(TRAVEL_SPEED)
        g.abs_move(z=TRAVEL_HEIGHT, C=TRAVEL_HEIGHT)

        if POST_EXTRUSION_DWELL > 0:
            g.dwell(POST_EXTRUSION_DWELL)

    # prints a single straight line from (x0, y0) to (x1, y1)
    def print_single_line(self, x0, y0, x1, y1, print_height_mm=DEFAULT_PRINT_HEIGHT, print_speed_mmps=DEFAULT_PRINT_SPEED, print_pressure_psi=LCE_PRESSURE):
        g.abs_move(x=x0, y=y0)
        self.__start_printing(print_height_mm, print_speed_mmps, print_pressure_psi)
        g.abs_move(x=x1, y=y1)
        self.__stop_printing()
        print(g.current_position['x'], g.current_position['y'])

    # meanders back and forth to print a wide line
    # x0, y0, x1, y1 are the start and end points of the middle of the line
    # spacing_mm is the distance between each meander and width is the total width of the line
    def print_wide_line(self, x0, y0, x1, y1, spacing_mm, numpaths_xy, print_height_mm=DEFAULT_PRINT_HEIGHT, print_speed_mmps=DEFAULT_PRINT_SPEED, print_pressure_psi=LCE_PRESSURE):
        line_unit_vect = ((x1-x0)/((x1-x0)**2+(y1-y0)**2)**0.5, (y1-y0)/((x1-x0)**2+(y1-y0)**2)**0.5)  # unit vector in the direction of the line
        line_magnitude = ((x1-x0)**2+(y1-y0)**2)**0.5
        perp_vect = (-line_unit_vect[1], line_unit_vect[0])  # unit vector perpendicular to the line
        direction = 1

        start_point = {'x': x0 + perp_vect[0]*spacing_mm*numpaths_xy/2, 'y': y0 + perp_vect[1]*spacing_mm*numpaths_xy/2}
        g.abs_move(x=start_point['x'], y=start_point['y'])
        self.__start_printing(print_height_mm, print_speed_mmps, print_pressure_psi)

        # meanders back and forth to print the line
        for i in range(numpaths_xy):
            end_point = {'x': start_point['x'] + line_unit_vect[0]*line_magnitude*direction, 'y': start_point['y'] + line_unit_vect[1]*line_magnitude*direction}
            g.abs_move(x=end_point['x'], y=end_point['y']) # moves parallel to line

            if i == numpaths_xy-1: break # if it's the last meander, it doesn't need to move perpendicularly
            start_point = {'x': end_point['x'] - perp_vect[0]*spacing_mm, 'y': end_point['y'] - perp_vect[1]*spacing_mm} # moves perpendicularly to start of next line
            g.abs_move(x=start_point['x'], y=start_point['y'])

            direction *= -1 # switches line direction to go back the other way
        
        self.__stop_printing()

    # prints a connection with all input parameters, intended for Liwei output format
    def print_connection(self, material_index, x0, y0, x1, y1, print_speed_mmps, print_pressure_psi, numlayers_z, numpaths_xy, xy_spacing_mm, firstlayerheight_mm, z_layerheight_mm):
        if not (numlayers_z > 0 and numpaths_xy > 0 and xy_spacing_mm > 0 and z_layerheight_mm > 0 and print_speed_mmps > 0 and print_pressure_psi > 0):
            raise Exception(f"ERROR: Number of paths, spacing, speed, pressure, and layer height must be greater than 0.")

        # checks material index and swaps if necessary
        if self.material_index != material_index:
            self.__swap_material(material_index)

        for i in range(0, numlayers_z):
            print_height_mm = z_layerheight_mm * i + firstlayerheight_mm
            self.print_wide_line(x0, y0, x1, y1, spacing_mm=xy_spacing_mm, numpaths_xy=numpaths_xy, 
                                 print_height_mm=print_height_mm, print_speed_mmps=print_speed_mmps, print_pressure_psi=print_pressure_psi)

    # prints a single layer of a connection
    # layer index z is 1 indexed (first layer has index 1, etc)
    def print_connection_layer(self, material_index, x0, y0, x1, y1, print_speed_mmps, print_pressure_psi, layer_index_z, numpaths_xy, xy_spacing_mm, firstlayerheight_mm, z_layerheight_mm):
        if not (layer_index_z > 0 and numpaths_xy > 0 and xy_spacing_mm > 0 and z_layerheight_mm > 0 and print_speed_mmps > 0 and print_pressure_psi > 0):
            raise Exception(f"ERROR: Number of paths, spacing, speed, pressure, layer index, and layer height must be greater than 0.")

        # checks material index and swaps if necessary
        if self.material_index != material_index:
            self.__swap_material(material_index)

        print_height_mm = z_layerheight_mm * (layer_index_z - 1) + firstlayerheight_mm
        self.print_wide_line(x0, y0, x1, y1, spacing_mm=xy_spacing_mm, numpaths_xy=numpaths_xy, 
                                print_height_mm=print_height_mm, print_speed_mmps=print_speed_mmps, print_pressure_psi=print_pressure_psi)

    def write_to_file(self, view=False):
        # only works with matplotlib version 3.5.1
        if view:
            g.view(backend='matplotlib')
        g.teardown()
        print(f'Gcode file written to {self.outpath}')

if __name__ == "__main__":
    print("u ran the wrong file dummy")
    # g = gcodeLibrary('curing_sweep_test.pgm')

    # g.print_connection(print_pressure_psi=55, print_speed_mmps=10, x0=0,y0=0)

    # g.view(backend='matplotlib')
    # g.teardown()