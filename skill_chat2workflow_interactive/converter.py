import json
import yaml
import os
import shutil
import zipfile

from tools import layout_nodes, construct, search_var, construct_coze

# dify
def convert_to_dify(data, name, yaml_dir):
    try:
        app_name = name

        app_mode = "workflow"
        plugin_list = ["langgenius/tongyi:0.1.13@10cbfe851fdf27f3c50ca2ca86293eb0c27da51ee74e58acebafd92b71c8d518","sawyer-shi/tongyi_aigc:0.0.1@01f2e5f8c3226e1bab678eed70baef4503d46aabf96c767ba58eaa48a6a8e290","bowenliang123/md_exporter:2.2.0@9f39c2c2c1cd09180e2cc053090adc9886019483f502727467f136712b8b9639","hjlarry/mermaid_converter:0.0.1@46e755f0d92566a1f7a6e85086eac02a735afaa41479e7a2277b150abda70b18","langgenius/echarts:0.0.1@e390de4320a5ab32ef24899983f84c31aa39e4690c7b294be11f2c10268c3a68","langgenius/google:0.1.0@c73cdc3dda5de500974ece93ce38eb6fc6bbf1399d38f1dbbbd70745ce154d0e"]
        
        output_file = os.path.join(yaml_dir, app_name + ".yaml")

        node_list = []
        edge_list = []
        type_num = {}
        id_dict = {}

        out_iteration_edges = []
        for edge in data['edges']:
            if '-' not in edge[0]:  
                out_iteration_edges.append(edge)

        out_positions = layout_nodes(out_iteration_edges)

        outputvar_iteration = None

        for i in range(len(data['nodes_info'])):
            node = data['nodes_info'][i]

            if node['type'] not in type_num:
                type_num[node['type']] = 1
            else:
                type_num[node['type']] += 1

            count = type_num[node['type']]
            
            param = node['param']

            if '-' in node['id']:
                x = (int(node['id'].split('-')[1])-2)*300 + 100
                y = 68
                if node['type'] == "iteration-start":
                    x = 24

            else:
                x = out_positions[node['id']]['x']
                y = out_positions[node['id']]['y']

                if node['type'] == "iteration":
                    y = -400 * count
                    outputvar_iteration = param['output_selector']

            current_node = construct(node['type'], param, x, y, count, id_dict)

            # The interior of the iterative node canvas
            if '-' in node['id']:
                current_node.data['isInIteration'] = True

                if node['type'] != "iteration-start":
                    current_node.data['iteration_id'] = id_dict[node['id'].split('-')[0]].id
                else:
                    current_node.parentId = id_dict[node['id'].split('-')[0]].id
                    current_node.id = current_node.parentId + 'start'
                
            id_dict[node['id']] = current_node
            node_list.append(current_node)


            if outputvar_iteration is not None and outputvar_iteration[1] == node['id']:

                ref_id ,reverse_num = node['id'].split('-')
                reverse_num = int(reverse_num)

                idd, typee = search_var(outputvar_iteration[0], current_node)
                typee = f"array[{typee}]"

                id_dict[ref_id].data['output_selector'] = [idd, outputvar_iteration[0]]
                id_dict[ref_id].data['output_type'] = typee
            
                node_list[-(reverse_num+1)].data['output_selector'] = [idd, outputvar_iteration[0]]
                node_list[-(reverse_num+1)].data['output_type'] = typee
                
                outputvar_iteration = None
            
        for edge in data['edges']:
            edge_list.append([id_dict[edge[0]], edge[1], id_dict[edge[2]]])
        
        general_template = {
        "app":{
            "description" : "",
            "icon": "🤖",
            "icon_background": "#FFEAD5",
            "mode": app_mode,
            "name": app_name,
            "use_icon_as_answer_icon": False
        },
        "dependencies": [],
        "kind": "app",
        "version": "0.4.0",
        "workflow":{
            "conversation_variables": [],
            "environment_variables": [],
            "features":{
                "file_upload": {"enabled": False},
                "opening_statement": "",
                "retriever_resource": {"enabled": False},
                "sensitive_word_avoidance":{"enabled": False},
                "speech_to_text":{"enabled": False},
                "suggested_questions": [],
                "suggested_questions_after_answer": {"enabled": False},
                "text_to_speech": {"enabled": False}
            },
            "graph":{
                "edges": [],
                "nodes": [],
                "viewport": {
                    "x": 0,
                    "y": 0,
                    "zoom": 1
                }
            },
            "rag_pipeline_variables": []
        }
        }

        # dependencies
        for plugin in plugin_list:
            depend_template = {
                "current_identifier": None,
                "type": "marketplace",
                "value": {
                    "marketplace_plugin_unique_identifier": plugin,
                    "version": None
                }
            }
            general_template["dependencies"].append(depend_template)
            
        # edges
        for edge in edge_list:
            # Indicate the branch port
            if hasattr(edge[0], 'sourceHandle_list'):
                sourceHandle = edge[0].sourceHandle_list[edge[1]]
            else:
                sourceHandle = "source"


            edge_template = {
                "data":{
                    "isInIteration": False,
                    "sourceType": edge[0].data['type'],
                    "targetType": edge[2].data['type'],
                },
                "id": edge[0].id + "-" + sourceHandle + "-" + edge[2].id + "-" + "target",
                "source": edge[0].id,
                "sourceHandle": sourceHandle,
                "target": edge[2].id,
                "targetHandle": "target",
                "type": "custom",
                "zIndex": 0
            }

            if 'isInIteration' in edge[0].data:
                edge_template['data']['isInIteration'] = edge[0].data['isInIteration']
                edge_template['zIndex'] = 1002

                if edge[0].data['type'] != "iteration-start":
                    edge_template['data']['iteration_id'] = edge[0].data['iteration_id']
                else:
                    edge_template['data']['iteration_id'] = edge[0].parentId
                

            general_template["workflow"]["graph"]["edges"].append(edge_template)


        # nodes
        for node in node_list:
            node_template = {
                "data": node.data,
                "height": 52,
                "id": node.id,
                "position": {
                    "x": node.x,
                    "y": node.y
                },
                "positionAbsolute":{
                    "x": node.x_ab,
                    "y": node.y_ab
                },
                "selected": False,
                "sourcePosition": "right",
                "targetPosition": "left",
                "type": "custom",
                "width": 242
            }

            if 'isInIteration' in node.data and node.data['isInIteration']:
                node_template["zIndex"] = 1002

                if node.data['type'] == 'iteration-start':
                    node_template["parentId"] = node.parentId
                    node_template["type"] = "custom-iteration-start"
                    node_template["draggable"] = False
                    node_template["selectable"] = False
                    del node_template["selected"]

                else:
                    node_template["parentId"] = node.data['iteration_id']


            general_template["workflow"]["graph"]["nodes"].append(node_template)

        with open(output_file, 'w', encoding='utf-8') as yaml_file:
            yaml.dump(general_template, yaml_file, allow_unicode=True, default_flow_style=False)    
        
        print(f"{app_name} - Conversion successful!")
        return True
        
    except Exception as e:
        print(f"{app_name} - Conversion error occurred: {e}")
        return False



# coze
def convert_to_coze(data, name, yaml_dir, manifest_path=None):
    try:
        app_name = name + "-draft"
        
        output_file = os.path.join(yaml_dir, app_name + ".yaml")

        node_list = []
        edge_list = []
        type_num = {}
        id_dict = {}
        batch_id_record = []

        out_iteration_edges = []
        for edge in data['edges']:
            if '-' not in edge[0]:  
                out_iteration_edges.append(edge)

        out_positions = layout_nodes(out_iteration_edges, node_width = 460, node_height = 260)

        outputvar_iteration = None

        for i in range(len(data['nodes_info'])):
            node = data['nodes_info'][i]

            if node['type'] not in type_num:
                type_num[node['type']] = 1
            else:
                type_num[node['type']] += 1

            count = type_num[node['type']]
            
            param = node['param']


            if '-' in node['id']:
                x = (int(node['id'].split('-')[1])-2)*460
                y = 100
            
            else:
                x = out_positions[node['id']]['x']
                y = out_positions[node['id']]['y']

                if node['type'] == "iteration":
                    outputvar_iteration = param['output_selector']

            if node['type'] != "iteration-start":
                current_node = construct_coze(node['type'], param, x, y, count, id_dict)
                
            if '-' in node['id']:

                if node['type'] != "iteration-start":
                    id_dict[node['id'].split('-')[0]].internal_ori_id.append(node['id'])
                    batch_id_record.append(current_node.id)


            if node['type'] != "iteration-start":
                id_dict[node['id']] = current_node
                node_list.append(current_node)
            
            if outputvar_iteration is not None and outputvar_iteration[1] == node['id']:

                ref_id ,reverse_num = node['id'].split('-')
                reverse_num = int(reverse_num)

                idd = current_node.id

                id_dict[ref_id].parameters['node_outputs']['output']['value']['value']['path'] = outputvar_iteration[0]
                id_dict[ref_id].parameters['node_outputs']['output']['value']['value']['ref_node'] = idd


                node_list[-(reverse_num)].parameters['node_outputs']['output']['value']['value']['path'] = outputvar_iteration[0]
                node_list[-(reverse_num)].parameters['node_outputs']['output']['value']['value']['ref_node'] = idd

                
                outputvar_iteration = None
        
        for edge in data['edges']:

            if "-1" in edge[0] or "-1" in edge[2]:
                continue
            
            if "-" in edge[0] or "-" in edge[2]:
                main_node = id_dict[edge[0].split('-')[0]]
                main_node.internal_edges.append([id_dict[edge[0]], edge[1], id_dict[edge[2]]])
            else:
                edge_list.append([id_dict[edge[0]], edge[1], id_dict[edge[2]]])
        

        general_template = {
            "schema_version": "1.0.0",
            "name": name,
            "id": 1,
            "description": "coze workflow",
            "mode": "workflow",
            "icon": "plugin_icon/workflow.png",
            "nodes": [],
            "edges": []
        }

        # nodes
        for node in node_list:
            if node.id in batch_id_record:
                continue

            node_template = {
                "id": node.id,
                "type": node.type,
                "title": node.title,
                "icon": node.icon,
                "description": node.description,
                "position":{
                    "x": node.x,
                    "y": node.y
                },
                "parameters": node.parameters
            }

            if node.type == 'batch':
                node_template["canvas_position"] = node.canvas_position
                node_template["nodes"] = []
                node_template["edges"] = []

                for inner_id in node.internal_ori_id:
                    inner_node = id_dict[inner_id]
                    node_template["nodes"].append({
                        "id": inner_node.id,
                        "type": inner_node.type,
                        "title": inner_node.title,
                        "icon": inner_node.icon,
                        "description": inner_node.description,
                        "position":{
                            "x": inner_node.x,
                            "y": inner_node.y
                        },
                        "parameters": inner_node.parameters
                    })
                
                for inner_edge in node.internal_edges:

                    batch_edge_template = {
                        "source_node": inner_edge[0].id,
                        "target_node": inner_edge[2].id
                    }

                    if inner_edge[0].type == "condition":
                        if int(inner_edge[1]) == 0:
                            batch_edge_template["source_port"] = "true"
                        elif int(inner_edge[1]) == len(inner_edge[0].parameters['branches'])-1:
                            batch_edge_template["source_port"] = "false"
                        else:
                            batch_edge_template["source_port"] = f"true_{int(inner_edge[1])}"

                    elif inner_edge[0].type == "intent":
                        if int(edge[1]) == len(inner_edge[0].parameters['intents'])-1:
                            batch_edge_template["source_port"] = "default"
                        else:
                            batch_edge_template["source_port"] = f"branch_{int(inner_edge[1])}"

                    elif inner_edge[0].type == "batch":
                        batch_edge_template["source_port"] = "batch-output"

                    node_template["edges"].append(batch_edge_template)
                
                sorted_list = sorted(node.internal_ori_id, key = lambda x: int(x.split('-')[1]))

                node_template["edges"].append({
                    "source_node": node.id,
                    "target_node": id_dict[sorted_list[0]].id,
                    "source_port": "batch-function-inline-output"
                })

                node_template["edges"].append({
                    "source_node": id_dict[sorted_list[-1]].id,
                    "target_node": node.id,
                    "target_port": "batch-function-inline-input"
                })

            general_template["nodes"].append(node_template)

        # edges
        for edge in edge_list:

            edge_template = {
                "source_node": edge[0].id,
                "target_node": edge[2].id
            }

            if edge[0].type == "condition":
                if int(edge[1]) == 0:
                    edge_template["source_port"] = "true"
                elif int(edge[1]) == len(edge[0].parameters['branches']):
                    edge_template["source_port"] = "false"
                else:
                    edge_template["source_port"] = f"true_{int(edge[1])}"

            elif edge[0].type == "intent":
                if int(edge[1]) == len(edge[0].parameters['intents']):
                    edge_template["source_port"] = "default"
                else:
                    edge_template["source_port"] = f"branch_{int(edge[1])}"

            elif edge[0].type == "batch":
                edge_template["source_port"] = "batch-output"
            
            general_template["edges"].append(edge_template)

        with open(output_file, 'w', encoding='utf-8') as yaml_file:
            yaml.dump(general_template, yaml_file, allow_unicode=True, default_flow_style=False)    
        
        print(f"{app_name} - Conversion successful!")
        
        workflow_dir = os.path.join(yaml_dir, f"Workflow-{app_name}")
        workflow_subdir = os.path.join(workflow_dir, "workflow")
        os.makedirs(workflow_subdir, exist_ok=True)
        
        manifest_dest = os.path.join(workflow_dir, "MANIFEST.yml")
        shutil.copy(manifest_path, manifest_dest)
        
        # Update the "name" field in MANIFEST.yml to match the workflow name 
        with open(manifest_dest, 'r', encoding='utf-8') as mf:
            manifest_data = yaml.safe_load(mf)
        manifest_data['main']['name'] = name
        with open(manifest_dest, 'w', encoding='utf-8') as mf:
            yaml.dump(manifest_data, mf, allow_unicode=True, default_flow_style=False)
        
        yaml_dest = os.path.join(workflow_subdir, f"{app_name}.yaml")
        shutil.move(output_file, yaml_dest)
        
        zip_path = os.path.join(yaml_dir, f"Workflow-{app_name}")
        with zipfile.ZipFile(f"{zip_path}.zip", 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(workflow_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, yaml_dir)
                    zipf.write(file_path, arcname)
        
        shutil.rmtree(workflow_dir)
        
        print(f"Created zip file: Workflow-{app_name}.zip")
        return True
        
    except Exception as e:
        print(f"{app_name} - Conversion error occurred: {e}")
        return False



if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert workflow JSON to Dify or Coze YAML format')
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--json_path', type=str, help='Path to the JSON file')
    input_group.add_argument('--json_str', type=str, help='JSON string content')
    
    parser.add_argument('--name', type=str, required=True, help='Workflow name')
    parser.add_argument('--output_path', type=str, required=True, help='Output directory path for YAML file')
    parser.add_argument('--type', type=str, required=True, choices=['dify', 'coze'], help='Target type: dify or coze')
    
    args = parser.parse_args()

    manifest_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "nodes", "coze", "MANIFEST.yml",
    )
    
    if args.json_path:
        with open(args.json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    else:
        data = json.loads(args.json_str)
    
    os.makedirs(args.output_path, exist_ok=True)
    
    if args.type == 'dify':
        convert_to_dify(data, args.name, args.output_path)
    elif args.type == 'coze':
        convert_to_coze(data, args.name, args.output_path, manifest_path)
