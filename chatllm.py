import json
import os
import argparse
from llm_api import OpenAIAgent

def process_tasks(agent, input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        tasks_data = json.load(f)

    processed_results = []
    
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            processed_results = json.load(f)

    task_map = {item["task"]: item for item in processed_results}

    for item in tasks_data:
        task_name = item.get("task")
        item_id = item.get("id")
        item_category = item.get("category")

        if task_name in task_map:
            task_result = task_map[task_name]
        else:
            task_result = {"id": item_id, "category": item_category, "task": task_name}
            processed_results.append(task_result)
            task_map[task_name] = task_result

        query_keys = sorted(
            [k for k in item.keys() if k.startswith("query") and item[k]], 
            key=lambda x: int(x.replace("query", ""))
        )
        
        history = []
        
        try:
            print(f">> Task {task_name} is currently being processed.")
            for i, q_key in enumerate(query_keys, 1):
                current_query = item[q_key]
                answer_key = f"answer{i}"

                if answer_key in task_result and task_result[answer_key]:
                    print(f"  - Query {i} already exists, skipping...")
                    history.append((current_query, task_result[answer_key].split('</think>')[-1]))
                    continue

                print(f"  - Processing Query {i}...")
                
                print(f"\n[current_query]\n{current_query}\n")

                resp = agent.generate(
                    query=current_query,
                    history=history
                )           
                
                # For Kalm api
                # answer = resp["response"]
                answer = resp

                print(f"[llm_response]\n{answer}\n")

                task_result[answer_key] = answer.split('</think>')[-1]
                history.append((current_query, answer.split('</think>')[-1]))

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(processed_results, f, ensure_ascii=False, indent=4)
                
                print(f"  - Processing Query {i}... Done")
            
            print(f">> All the queries for task {task_name} have been processed.")

        except Exception as e:
            print(f"An error occurred while handling task {task_name}: {e}")
            print("The program has saved the current progress. You can fix the issue and rerun the program.")
            break

    print(f"\n--- All tasks have been processed ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kalm Agent batch processing script")
    
    parser.add_argument('--input_file', type=str, required=True, help='Input JSON file path')
    parser.add_argument('--model_name', type=str, required=True, help='model name')
    parser.add_argument('--temperature', type=float, required=True, help='LLM Temperature')
    parser.add_argument('--max_tokens', type=int, required=True, help='Max tokens')

    args = parser.parse_args()
    output_file = f"output/llm_response/response_{args.model_name}.json"
    print(f"Input file: {args.input_file}")
    print(f"Output file: {output_file}")

    with open("prompts/builder_prompt.txt",'r', encoding='utf-8') as f:
        system_prompt = f.read().strip()

    agent = OpenAIAgent(args.model_name, system_prompt, args.temperature, args.max_tokens)

    process_tasks(agent, args.input_file, output_file)
