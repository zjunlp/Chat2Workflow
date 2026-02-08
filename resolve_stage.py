import os
import json
import yaml
import requests
import argparse
from time import sleep
from llm_api import OpenAIAgent


def file_upload(user, api_key, file_name, mime_type, case_files_dir, port):
    url = f'http://localhost:{port}/v1/files/upload'
    file_path = os.path.join(case_files_dir, file_name)

    part1, part2 = mime_type.split('/')
    value = f'{part1}.{part2}'

    headers = {'Authorization': f'Bearer {api_key}'}
    data = {'user': user}
    files = {'file': (value , open(file_path, 'rb'), mime_type)}

    try:
        response = requests.post(url, headers=headers, data=data, files=files)

        response.raise_for_status()
        
        file_id = response.json().get('id')
        print(f"Upload successful! File ID: {file_id}")
        return file_id

    except requests.exceptions.RequestException as e:
        print(f"File upload failed: {e}")
        if 'response' in locals():
            print(response.text)
        
        return None

    finally:
        files['file'][1].close()

def llm_evaluate(agent, queries, input_text ,output_text, ground_truth):
    user_prompt = '''
    <queries>
    {queries}
    </queries>

    <input>
    {input_text}
    </input>

    <output>
    {output_text}
    </output>
    
    <reference_answer>
    {ground_truth}
    </reference_answer>
    '''

    query = user_prompt.format(queries=queries, input_text=input_text ,output_text=output_text, ground_truth=ground_truth)

    resp = agent.generate(query=query)
    # response = resp['response']
    response = resp
    print(response)
    return response



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="resolve stage")
    
    parser.add_argument('--model_name', type=str, required=True, help='model name')
    parser.add_argument('--config', type=str, required=True, help='Configuration file path')
    parser.add_argument('--temperature', type=float, required=True, help='LLM Temperature')
    parser.add_argument('--max_tokens', type=int, required=True, help='Max new tokens')
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    base_url = f"http://localhost:{cfg['port']}/v1/workflows/run"

    input_file = f'output/pass_eval/pass_eval_{args.model_name}.json'
    output_file = f"output/resolve_eval/resolve_eval_{args.model_name}.json"

    check_file = 'dataset/check_pass_stage.json'
    outfile_check = 'dataset/check_resolve_stage.json'
    task_query_file = 'dataset/query.json'
    case_files_dir = 'case_files'

    with open(check_file, 'r', encoding='utf-8') as f:
        check_list = json.load(f)
    
    with open(outfile_check, 'r', encoding='utf-8') as f:
        outfile_check_list = json.load(f)

    with open(input_file, 'r', encoding='utf-8') as f:
        formatted_results = json.load(f)

    with open(task_query_file, 'r', encoding='utf-8') as f:
        task_query_list = json.load(f)
    

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    for item in formatted_results:
        if item["valid"]:
            item_name = item["task"] + "_" + str(item["round"])
            api_key = item["api_key"]
            task_dict = check_list[item_name]

            # 3 test cases
            for i in range(3):
                round_num = i + 1
                test_key = "test" + str(round_num)
                test_dict = task_dict[test_key]

                input_data = {}


                if test_key in item:
                    print(f"{item['task']}_round{item['round']}_{test_key} has been processed, skipping")
                    continue
                
                
                print(f"  - Processing {item['task']}_round{item['round']}_{test_key}...")
                for key, value in test_dict.items():
                    if key == "ground_truth" or value == "":
                        continue
                    
                    if isinstance(value, dict):
                        file_id = file_upload(cfg['user'], api_key, value["value"], value["mime_type"], case_files_dir, cfg['port'])
                        input_data[key] = {
                            "transfer_method": "local_file",
                            "upload_file_id": file_id,
                            "type": value["mime_type"].split('/')[0]
                        }
                    
                    elif isinstance(value, list):
                        all_file = []

                        for file_item in value:
                            file_id = file_upload(cfg['user'], api_key, file_item["value"], file_item["mime_type"], case_files_dir, cfg['port'])
                            all_file.append({
                                "transfer_method": "local_file",
                                "upload_file_id": file_id,
                                "type": file_item["mime_type"].split('/')[0]
                            })
                        
                        input_data[key] = all_file

                    else:
                        input_data[key] = value
                    
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "inputs": input_data,
                    "response_mode": "blocking",
                    "user": cfg['user']
                }

                try:
                    # Step 1: Send POST request - The workflow can run and return normal values.
                    print(f"api_key: {api_key}")
                    response = requests.post(base_url, headers=headers, json=payload)
                    print("The workflow execution response has been obtained.")
                    # sleep(0.1)

                    response.raise_for_status()  # If the status code is not within the range of 200-299, an exception will be thrown.

                    result_json = response.json()
                    output_dict = result_json['data']['outputs']

                    print(f"response_json: {result_json}")

                    if not output_dict:
                        item[test_key] = False
                        print(f"{item['task']}_round{item['round']}_{test_key} has no output, test failed")
                        print(f"\n  - Processing {item['task']}_round{item['round']}_{test_key}... Done\n")
                        continue

                except requests.exceptions.RequestException as e:
                    item[test_key] = False

                    print(f"{item['task']}_round{item['round']}_{test_key} Request failed: {e}")
                    print("Status Code:", response.status_code)
                    print(f"  - Processing {item['task']}_round{item['round']}_{test_key}... Done\n")
                    continue


                # Step 2: Check whether the output result meets the requirements.
                if item_name in outfile_check_list:
                    for key, value in outfile_check_list[item_name].items():
                        # Check one by one whether the generated files have been created successfully.

                        # non-file
                        if key not in output_dict:
                            item[test_key] = False
                            print(f"{item['task']}_round{item['round']}_{test_key} does not meet the requirements for file output, test failed")
                            print(f"  - Processing {item['task']}_round{item['round']}_{test_key}... Done\n")
                            break

                        # single file
                        if isinstance(output_dict[key], dict):
                            if output_dict[key].get('extension', -1) == -1 or output_dict[key].get('extension', -1) != value:
                                item[test_key] = False
                                print(f"{item['task']}_round{item['round']}_{test_key} does not meet the requirements for file output, test failed")
                                print(f"  - Processing {item['task']}_round{item['round']}_{test_key}... Done\n")
                                break
                        
                        # multiple files
                        elif isinstance(output_dict[key], list):
                            for file_item in output_dict[key]:
                                if file_item.get('extension', -1) == -1 or file_item.get('extension', -1) != value:
                                    item[test_key] = False
                                    print(f"{item['task']}_round{item['round']}_{test_key} does not meet the requirements for file output, test failed")
                                    print(f"  - Processing {item['task']}_round{item['round']}_{test_key}... Done\n")
                                    break
                        else:
                            item[test_key] = False
                            print(f"{item['task']}_round{item['round']}_{test_key} does not meet the requirements for file output, test failed")
                            print(f"  - Processing {item['task']}_round{item['round']}_{test_key}... Done\n")
                            break
                
                if test_key in item and item[test_key] == False:
                    continue

                item[test_key] = True
                
                # LLM Evaluation

                ## Find all non-file parts of the output
                provide_to_llm = []

                for key, value in output_dict.items():
                    if item_name in outfile_check_list and key in outfile_check_list[item_name]:
                        continue
                    
                    provide_to_llm.append([key,value])
                
                if len(provide_to_llm) == 0:
                    item[test_key] = True
                    print(f"{item['task']}_round{item['round']}_{test_key} has no other output apart from files, test passed")
                    print(f"  - Processing {item['task']}_round{item['round']}_{test_key}... Done\n")
                    continue

                output_text = "\n".join([f"{item[0]}: {item[1]}" for item in provide_to_llm])


                ## Find all non-file parts of the input
                input_text = ""

                for key, value in input_data.items():
                    if isinstance(value, dict) or isinstance(value, list):
                        continue
                    else:
                        input_text += f"{key}: {value}\n"
                

                ## Find all queries of history
                current_task = None
                queries = ""

                for task in task_query_list:
                    if task['task'] == item["task"]:
                        current_task = task
                        break
                
                for i in range(item["round"]):
                    queries += "query" + str(i + 1) + ": " + current_task["query" + str(i + 1)] + "\n"
                

                ## Find ground_truth
                ground_truth = test_dict.get("ground_truth", "")

                print(f">> Processing LLM evaluation...")

                with open("prompts/evaluation_resolve_system.txt",'r', encoding='utf-8') as f:
                    system_prompt = f.read().strip()

                agent = OpenAIAgent(cfg['evaluation_model'], system_prompt, args.temperature, args.max_tokens)
                
                result = llm_evaluate(agent, queries, input_text, output_text, ground_truth)
                answer = result.split('<result>')[-1].split('</result>')[0]

                print(f">> Processing LLM evaluation...Done")


                if 'false' in answer.lower():
                    item[test_key] = False
                    print(f"{item['task']}_round{item['round']}_{test_key} failed the evaluation of LLM, test failed")
                    print(f"  - Processing {item['task']}_round{item['round']}_{test_key}... Done\n")
                else:
                    item[test_key] = True
                    print(f"{item['task']}_round{item['round']}_{test_key} completed the evaluation of LLM, test passed")
                    print(f"  - Processing {item['task']}_round{item['round']}_{test_key}... Done\n")

                tag = 'llm_evaluate_reason_' + test_key
                tag_1 = "llm_output_" + test_key 
                item[tag] = result.split('<reason>')[-1].split('</reason>')[0]
                item[tag_1] = output_text

                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(formatted_results, f, ensure_ascii=False, indent=2)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(formatted_results, f, ensure_ascii=False, indent=2)
        
    # resolve rate
    num_total = 0
    num_correct = 0
    for item in formatted_results:
        for i in range(3):
            index = "test" + str(i + 1)
            if index in item and item[index] == True:
                num_correct += 1
            num_total += 1
    print(f"model: {args.model_name}, num_total: {num_total}, num_correct: {num_correct}, resolve_rate: {num_correct / num_total}")
                    