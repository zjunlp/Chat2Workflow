import re
import json
import yaml
import os
import requests
import time

import argparse
from llm_api import OpenAIAgent

from tools import layout_nodes, construct, search_var

def convert_to_yaml(workflow_str, task, round, yaml_dir):
    try:
        data = json.loads(workflow_str)
        app_name = task + "_" + str(round)

        app_mode = "workflow"
        plugin_list = ["langgenius/tongyi:0.1.13@10cbfe851fdf27f3c50ca2ca86293eb0c27da51ee74e58acebafd92b71c8d518","wwwzhouhui/qwen_text2image:0.0.3@aa7a36deeffbea382c8388f236bc1caf2899e560d0bdca2980b4733278f85fff","bowenliang123/md_exporter:2.2.0@9f39c2c2c1cd09180e2cc053090adc9886019483f502727467f136712b8b9639","hjlarry/mermaid_converter:0.0.1@46e755f0d92566a1f7a6e85086eac02a735afaa41479e7a2277b150abda70b18","langgenius/echarts:0.0.1@e390de4320a5ab32ef24899983f84c31aa39e4690c7b294be11f2c10268c3a68","langgenius/google:0.1.0@c73cdc3dda5de500974ece93ce38eb6fc6bbf1399d38f1dbbbd70745ce154d0e"]
        
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


def extract_and_format_data(data):
    pat_node = re.compile(r"<node_selection>(.*?)</node_selection>", re.DOTALL | re.IGNORECASE)
    pat_design = re.compile(r"<design_principle>(.*?)</design_principle>", re.DOTALL | re.IGNORECASE)
    pat_workflow = re.compile(r"<workflow>(.*?)</workflow>", re.DOTALL | re.IGNORECASE)
    
    formatted_results = []
    
    for task_item in data:
        task_name = task_item.get("task")
        
        for key, value in task_item.items():
            if key.startswith("answer"):
                match_round = re.search(r"(\d+)", key)
                round_num = int(match_round.group(1)) if match_round else 0
                
                result_obj = {
                    "task": task_name,
                    "round": round_num,
                    "node_selection": None,
                    "design_principle": None,
                    "workflow": None,
                    "valid": False,
                    "has_been_judged": False
                }
                
                match_node = pat_node.search(value)
                match_design = pat_design.search(value)
                match_workflow = pat_workflow.search(value)
                
                if match_node and match_design and match_workflow:
                    node_str = match_node.group(1).strip()
                    design_str = match_design.group(1).strip()
                    workflow_str = match_workflow.group(1).strip()
                    
                    result_obj["node_selection"] = node_str
                    result_obj["design_principle"] = design_str
                    
                    try:
                        workflow_json = json.loads(workflow_str)
                        result_obj["workflow"] = workflow_str
                        result_obj["valid"] = True
                    except json.JSONDecodeError:
                        result_obj["workflow"] = workflow_str
                        result_obj["valid"] = False
                        result_obj["fail_step"] = "step_1_1"
                else:
                    result_obj["valid"] = False
                    result_obj["fail_step"] = "step_1_1"
                
                formatted_results.append(result_obj)
                
    formatted_results.sort(key=lambda x: (x['task'], x['round']))

    return formatted_results


def check_var_name(workflow: str, ground_var_in: list, ground_var_out: list) -> bool:
    try:
        wf_data = json.loads(workflow)
        nodes = wf_data.get("nodes_info", [])
    except (json.JSONDecodeError, AttributeError):
        return False

    # 1. Check the input variables
    start_node = next((node for node in nodes if node.get("type") == "start"), None)
    
    if not start_node:
        return False

    start_vars = start_node.get("param", {}).get("variables", [])
    actual_in_names = [item[0] for item in start_vars if isinstance(item, list) and len(item) > 0]

    if set(actual_in_names) != set(ground_var_in):
        print(f"The actual input variable name does not match the target: {actual_in_names} != {ground_var_in}")
        return False

    # 2. Check output variables
    # There may be multiple end nodes.
    end_nodes = [node for node in nodes if node.get("type") == "end"]
    
    actual_out_configs = []
    for node in end_nodes:
        outputs = node.get("param", {}).get("outputs", [])
        # Extract variable names and sort them (internal sorting ensures that ["a", "b"] == ["b", "a"])
        out_names = sorted([item[0] for item in outputs if isinstance(item, list) and len(item) > 0])
        actual_out_configs.append(out_names)
    
    # Sort the order of end nodes (ensure end node 1, 2 and end node 2, 1 are treated as the same)
    actual_out_configs.sort()

    target_out_configs = []
    if ground_var_out:
        if isinstance(ground_var_out[0], str):
            # single end node
            target_out_configs = [sorted(ground_var_out)]
        else:
            # multi end nodes
            target_out_configs = [sorted(sublist) for sublist in ground_var_out]
    
    target_out_configs.sort()

    # Final comparison of output structures
    if actual_out_configs != target_out_configs:
        print(f"The actual output structure does not match the target structure: {actual_out_configs} != {target_out_configs}")
        return False

    return True


def import_and_publish(base_url, dsl_file_path):
    # Returning False indicates that the failure was caused by the file import.
    # Returning a string containing False signifies failures due to other reasons such as authentication or network issues.
    # Returning the app_id indicates a successful import.
    
    # === 1. Workflow Import ===
    with open(dsl_file_path, 'r', encoding='utf-8') as f:
        dsl_content = f.read()

    target_url = f"{base_url}/apps/imports"
    
    payload = {
        "mode": "yaml-content",
        "yaml_content": dsl_content
    }
    
    try:
        app_id = None
        response = session.post(target_url, json=payload)
        
        if response.status_code == 200:
            res_json = response.json()
            app_id = res_json.get('app_id')
            
        elif response.status_code == 202:
            res_json = response.json()
            import_id = res_json.get('id')
            print("\n⚠️ === Pending ===")
            print("The versions are inconsistent and require a second confirmation. The automatic confirmation is in progress....")
            
            confirm_url = f"{base_url}/apps/imports/{import_id}/confirm"
            confirm_resp = session.post(confirm_url, json={})
            
            if confirm_resp.status_code == 200:
                 app_id = confirm_resp.json().get('app_id')
                 print(f"🎉 Second confirmation successful！App ID: {app_id}")
            else:
                 print(f"❌ Second confirmation failed: {confirm_resp.text}")
                 return False

        elif response.status_code == 401:
            print(f"\n❌ Authentication failed (401)")
            return "FALSE-Unauthorized"
            
        else:
            print(f"\n❌ Request failed (HTTP {response.status_code})")
            print(f"Error details: {response.text}")
            return False
        
        # === 2. Workflow Publication ===
        publish_url = f"{base_url}/apps/{app_id}/workflows/publish"

        pub_resp = session.post(publish_url, json={})
        
        if pub_resp.status_code == 200:
            pass # print("✅ Workflow published successfully！")
        else:
            print(f"❌ Publication failed (HTTP {pub_resp.status_code}): {pub_resp.text}")
            return "FALSE-PUBLISH"

        # === 3. API Key ===
        keys_url = f"{base_url}/apps/{app_id}/api-keys"
        
        key_resp = session.post(keys_url, json={})
        
        if key_resp.status_code == 200 or key_resp.status_code == 201:
            key_data = key_resp.json()
            
            new_token = key_data.get('token')
            key_id = key_data.get('id')
            
            return new_token

        else:
            print(f"❌ Failed to create Key (HTTP {key_resp.status_code}): {key_resp.text}")
            return "FALSE-CREATE-KEY"
                
    except Exception as e:
        print(f"❌ Request exception: {e}")
        return "FALSE-Exception"


def llm_judge(agent, node_selection, design_principle, workflow, gt_nodes):
    user_prompt = '''
    node_selection: {node_selection}
    design_principle: {design_principle}
    workflow: {workflow}
    gt_nodes: {gt_nodes}
    '''

    query = user_prompt.format(node_selection=node_selection, design_principle=design_principle, workflow=workflow, gt_nodes=gt_nodes)

    resp = agent.generate(query=query)
    # response = resp['response']
    response = resp
    print(response)
    return response

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="pass stage")

    parser.add_argument('--model_name', type=str, required=True, help='model name')
    parser.add_argument('--config', type=str, required=True, help='Configuration file path')
    parser.add_argument('--temperature', type=float, required=True, help='LLM Temperature')
    parser.add_argument('--max_tokens', type=int, required=True, help='Max tokens')
    args = parser.parse_args()

    # agent = OpenAIAgent(args.model_name, system_prompt, args.temperature, args.max_tokens)

    base_url = "http://localhost:5001/console/api"

    input_file = f'output/llm_response/response_{args.model_name}.json'
    check_file = 'dataset/check_pass_stage.json'
    yaml_dir = f"output/yaml/{args.model_name}"
    out_dir = f"output/pass_eval"

    os.makedirs(yaml_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    output_file = f"{out_dir}/pass_eval_{args.model_name}.json"

    # ——————————————————————————————————————————————————————————————————————————————————————————————
    # Step 1: Extraction - Verify if the label is complete and extract the content. Check if the workflow_json is a valid JSON. If any of the conditions are not met, it is considered invalid.
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
        
    formatted_results = extract_and_format_data(raw_data)

    # ——————————————————————————————————————————————————————————————————————————————————————————————
    # Step 2: Conversion - Convert the extracted workflow_json to YAML format. If the conversion fails, set valid to False
    for item in formatted_results:
        if item["valid"]:
            result = convert_to_yaml(item["workflow"], item["task"], item["round"], yaml_dir)
            if result:
                item["valid"] = True
            else:
                item["valid"] = False
                item["fail_step"] = "step_1_2"
    
    # ——————————————————————————————————————————————————————————————————————————————————————————————
    # Step 3: Variable consistency check - Verify whether the input and output variable names are consistent with the given variable names. If they are not consistent, set the "valid" flag to False.
    with open(check_file, 'r', encoding='utf-8') as f:
        check_list = json.load(f)

    for item in formatted_results:
        if item["valid"]:

            item_name = item["task"] + "_" + str(item["round"])
            gt_var_in = check_list[item_name]["input_var"]
            gt_var_out = check_list[item_name]["output_var"]

            result = check_var_name(item["workflow"], gt_var_in, gt_var_out)
            if result:
                item["valid"] = True
            else:
                item["valid"] = False
                item["fail_step"] = "step_1_3"
    
    # ——————————————————————————————————————————————————————————————————————————————————————————————
    # Step 4: Logical validity check - I. Key nodes should be included    II. The descriptions of the same nodes in the three labels should be consistent.
    with open("prompts/evaluation_pass_system.txt",'r', encoding='utf-8') as f:
        system_prompt = f.read().strip()

    with open(args.config, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    agent = OpenAIAgent(cfg['evaluation_model'], system_prompt, args.temperature, args.max_tokens)

    for item in formatted_results:
        if item["valid"]:
            if item["has_been_judged"] == True:
                continue

            item_name = item["task"] + "_" + str(item["round"])

            node_selection = item["node_selection"]
            design_principle = item["design_principle"]
            workflow = item["workflow"]

            gt_nodes = check_list[item_name]["related_nodes"]

            result = llm_judge(agent ,node_selection, design_principle, workflow, gt_nodes)
            answer = result.split('<result>')[-1].split('</result>')[0]

            if 'false' in answer.lower():
                item["valid"] = False
                item["fail_step"] = "step_1_4"
            
            item["has_been_judged"] = True
            item["reason"] = result.split('<reason>')[-1].split('</reason>')[0]
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(formatted_results, f, ensure_ascii=False, indent=2)

    # ——————————————————————————————————————————————————————————————————————————————————————————————
    # step 5: Import into the Dify platform and publish - If successful, set valid to True; otherwise, set it to False. 
    session = requests.Session()

    try:
        login_resp = session.post(f"{base_url}/login", json={
            "email": cfg['admin_email'], 
            "password": cfg['admin_password']
        })
        login_resp.raise_for_status()
        
        csrf_token = session.cookies.get('csrf_token')
        if csrf_token:
            session.headers.update({"X-CSRF-Token": csrf_token})
            print("✅ Login successful")

    except Exception as e:
        print(f"❌ Login failed: {e}")
    
    for item in formatted_results:
        if item["valid"]:
            if "api_key" in item and item["api_key"] != "Other-Error":
                continue

            time.sleep(0.5)
            dsl_file_path = os.path.join(yaml_dir, item["task"] + "_" + str(item["round"]) + ".yaml")
            api_key = import_and_publish(base_url, dsl_file_path)
            if api_key == False:
                item["valid"] = False
                item["fail_step"] = "step_1_5"
            elif 'FALSE' in api_key:
                item["api_key"] = "Other-Error"
                print("Other Error. Please check the error message and retry.")
            else:
                item["api_key"] = api_key
    
        with open(output_file, "w", encoding="utf-8") as f:
                json.dump(formatted_results, f, ensure_ascii=False, indent=2)
    
    # ——————————————————————————————————————————————————————————————————————————————————————————————
    # pass rate
    num_total = 0
    num_correct = 0
    for item in formatted_results:
        if item["valid"] == True:
            num_correct += 1
        num_total += 1
    print(f"model: {args.model_name}, num_total: {num_total}, num_correct: {num_correct}, pass_rate: {num_correct / num_total}")
            
