from pathlib import Path
from utils.gcodeLibrary import gcodeLibrary   # gcodeLibrary.py must be in the same directory as this file
import pandas as pd
from collections import defaultdict

class NetworkGcodeGenerator: 
    def __init__(self, input_folder=Path(__file__).parent / "Input", output_folder=Path(__file__).parent / "Output") -> None:
        self.input_folder = input_folder
        self.output_folder = output_folder

    # uses speed pressure mappings to find h, meander spacing, and layer spacing and add to input excel file
    def add_print_variables(self, inpath):
        # mapping paths for the two materials ordered by material index
        mapping_paths = ["Gcode Generator/utils/materialData/neatLCE_speed_pressure_mappings.csv",
                         "Gcode Generator/utils/materialData/azoLCE_speed_pressure_mappings.csv"]

        mapping_dfs = [pd.read_csv(mapping_path) for mapping_path in mapping_paths]
        df = pd.read_excel(io=inpath, sheet_name=['Nodes','Edges']) # reads in the two sheets of the excel file
        node_df = df['Nodes']
        edge_df = df['Edges']

        flheights = []
        lheights = []
        spacings = []
        
        for index, row in edge_df.iterrows():
            # parses information from the edge dataframe
            try:
                material_index = int(row['stimulus'])
            except:
                material_index = 0    # if the stimulus column doesn't exist, assume single material print

            mapping_df = mapping_dfs[material_index]    # selects the correct mapping dataframe based on the material index
            
            print_speed_mmps = row['print_speed_mmps']
            print_pressure_psi = row['print_pressure_psi']

            try:
                mapping = mapping_df[(mapping_df['print_speed_mmps'] == print_speed_mmps) & 
                                     (mapping_df['print_pressure_psi'] == print_pressure_psi)].iloc[0]
            except:
                raise KeyError(f"Mapping for speed {print_speed_mmps} and pressure {print_pressure_psi} for material index {material_index} not found. \
                               Please check mappings sheet under utils and try again.")
                
            flheights.append(mapping['firstlayerheight_mm'])
            lheights.append(mapping['z_layerheight_mm'])
            spacings.append(mapping['xy_spacing_mm'])

        # adds new print data columns. if columns already exist, they are overwritten instead
        try:
            edge_df.insert(2, 'xy_spacing_mm', spacings)
            edge_df.insert(3, 'firstlayerheight_mm', flheights)
            edge_df.insert(4, 'z_layerheight_mm', lheights)
        except:
            edge_df['xy_spacing_mm'] = spacings
            edge_df['firstlayerheight_mm'] = flheights
            edge_df['z_layerheight_mm'] = lheights

        # sorts the edges by print speed, fastest to slowest, to prevent material dragging
        try:
            edge_df.sort_values(by=['print_speed_mmps','stimulus'], ascending=[False, True], inplace=True)
        except:
            edge_df.sort_values(by=['print_speed_mmps'], ascending=[False], inplace=True)

        with pd.ExcelWriter(inpath) as writer:
            node_df.to_excel(writer, sheet_name='Nodes', index=False)
            edge_df.to_excel(writer, sheet_name='Edges', index=False)

    # generates the gcode to print the LCE active/passive network
    def generate_network_gcode(self, inpath, outpath, view=False): 
        self.add_print_variables(inpath)    # generates print parameters 
        df = pd.read_excel(inpath,['Nodes','Edges']) # reads in the two sheets of the excel file
        node_df = df['Nodes']
        edge_df = df['Edges']
        g = gcodeLibrary(outpath)

        # sets up data structures for layer by layer printing
        all_edges_dict = defaultdict(list) # grouped by speed

        # loops through all edges in the dataframe and reads in parameters
        for index, row in edge_df.iterrows():
            edge = {"edge_index": index, "layer_index_z": 1}    # dictionary with all the edge data
        
            try:    # if the stimulus column doesn't exist, assume single material print
                edge['material_index'] = int(row['stimulus'])
            except:
                edge['material_index'] = 0

            edge['node1_position'] = node_df.iloc[int(row['EndNodes_1']) - 1]    # subtract 1 because node numbers start at 1 in the excel file and dataframes are zero-indexed
            edge['node2_position'] = node_df.iloc[int(row['EndNodes_2']) - 1]

            edge['print_speed_mmps'] = row['print_speed_mmps']
            edge['print_pressure_psi'] = row['print_pressure_psi']
            
            edge['xy_spacing_mm'] = row['xy_spacing_mm']
            edge['numpaths_xy'] = int(row['numpaths_xy'])

            edge['firstlayerheight_mm'] = row['firstlayerheight_mm']
            edge['z_layerheight_mm'] = row['z_layerheight_mm']
            edge['numlayers_z'] = int(row['numlayers_z'])
            
            all_edges_dict[edge['print_speed_mmps']].append(edge)

        # prints the edges layer by layer, grouped by speed
        for speed, edges in sorted(all_edges_dict.items(), reverse=True):
            done = []
            while len(done) < len(edges):
                for edge in edges:
                    if edge in done:
                        continue
                    g.print_connection_layer(material_index=edge['material_index'],
                                            x0=edge['node1_position']['x'], y0=edge['node1_position']['y'], 
                                            x1=edge['node2_position']['x'], y1=edge['node2_position']['y'], 
                                            print_speed_mmps=edge['print_speed_mmps'], print_pressure_psi=edge['print_pressure_psi'], 
                                            numpaths_xy=edge['numpaths_xy'], xy_spacing_mm=edge['xy_spacing_mm'], 
                                            firstlayerheight_mm=edge['firstlayerheight_mm'], z_layerheight_mm=edge['z_layerheight_mm'], 
                                            layer_index_z=edge['layer_index_z'])
                    # marks edge as done if it has been printed on all layers otherwise increments layer index
                    if edge["layer_index_z"] == edge["numlayers_z"]:
                        done.append(edge)
                    else:
                        edge["layer_index_z"] += 1
            
        g.write_to_file(view)

    def generate_all(self, view=False):
        input_folder = self.input_folder
        output_folder = self.output_folder

        for inpath in sorted(input_folder.glob('*.xlsx')):
            print(f"\nGenerating network gcode from the input file {inpath.name}...")
            outpath = output_folder / f"{inpath.stem}_bylayer.pgm"
            self.generate_network_gcode(inpath=inpath, outpath=outpath, view=view)
            # try:
            #     self.generate_network_gcode(inpath=inpath, outpath=outpath, view=view)
            # except:
            #     print(f"Failed to generate network gcode from the input file {inpath.name}. Skipping...")

if __name__ == "__main__":
    g = NetworkGcodeGenerator()
    g.generate_all(view=True)