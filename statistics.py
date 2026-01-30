import os
import json


category_dict = {
    "PaperDeepReader": "Research",
    "PaperQA": "Research",
    "SciencePopularization": "Research",
    "BookCharacter": "Research",
    "DeepResearch": "Research",
    "BatchFiles": "Document",
    "InvoiceParsing": "Document",
    "ExcelExtract": "Document",
    "FormulaOCR": "Document",
    "Translation": "Document",
    "ContractReview": "Enterprise",
    "ResumeScreening": "Enterprise",
    "MeetingSummary": "Enterprise",
    "PerformanceChart": "Enterprise",
    "GithubSummary": "Developer",
    "Mermaid": "Developer",
    "Code": "Developer",
    "StudyPlanner": "Education",
    "ExamQuestion": "Education",
    "ErrorNotebook": "Education",
    "HomeworkGrading": "Education",
    "StoryPPT": "AIGC",
    "HTML": "AIGC",
    "LogoSVG": "AIGC",
    "Podcast": "AIGC",
    "Creation": "AIGC",
    "Copywriting": "AIGC"
}


category_list = ["Research","Document","Enterprise","Developer","Education","AIGC"]
model_list = ["claude_sonnet4d5","deepseek_v3d1","deepseek_v3d2","gemini3_propreview","glm_4d6","glm_4d7","gpt_5d1","gpt_5d2","k2_instruct","k2_thinking","qwen3_8B", "qwen3_14B","qwen3_32B","qwen3_235B_A22B","qwen3_coder_480B_A35B_instruct"]
target_dir = "experiment_result"



# pass_rate（category）
print("——————————————————————————————————pass rate by category——————————————————————————————————")
for model in model_list:
    count_file = os.path.join(target_dir, f"final_{model}.json")

    all_count_list = []
    right_count_list = []

    with open(count_file, 'r', encoding='utf-8') as f:
        formatted_results = json.load(f)

    for category in category_list:

        all_count = 0
        right_count = 0

        for item in formatted_results:
            if category_dict[item["task"]] == category:

                if item["valid"] == True:
                    right_count += 1

                all_count += 1

        all_count_list.append(all_count)
        right_count_list.append(right_count)    
        print(f"model: {model}, category: {category}, num_total: {all_count}, num_correct: {right_count}, pass_rate: {right_count / all_count}")
    
    print(f"\nmodel: {model}, num_total: {sum(all_count_list)}, num_correct: {sum(right_count_list)}, pass_rate: {sum(right_count_list) / sum(all_count_list)}\n")



# resolve_rate (category)
print("——————————————————————————————————resolve rate by category——————————————————————————————————")
for model in model_list:
    count_file = os.path.join(target_dir, f"final_{model}.json")

    all_count_list = []
    right_count_list = []

    with open(count_file, 'r', encoding='utf-8') as f:
        formatted_results = json.load(f)

    for category in category_list:
        all_count = 0
        right_count = 0
        for item in formatted_results:
            if category_dict[item["task"]] == category:
                for i in range(3):
                    index = "test" + str(i + 1)
                    if index in item and item[index] == True:
                        right_count += 1
                    all_count += 1
        
        all_count_list.append(all_count)
        right_count_list.append(right_count) 
        print(f"model: {model}, category: {category}, num_total: {all_count}, num_correct: {right_count}, resolve_rate: {right_count / all_count}")

    print(f"\nmodel: {model}, num_total: {sum(all_count_list)}, num_correct: {sum(right_count_list)}, resolve_rate: {sum(right_count_list) / sum(all_count_list)}\n")



# pass_rate (round)
print("——————————————————————————————————pass rate by round——————————————————————————————————")
for model in model_list:
    count_file = os.path.join(target_dir, f"final_{model}.json")

    with open(count_file, 'r', encoding='utf-8') as f:
        formatted_results = json.load(f)

    for turn in range(1,4):
        all_count = 0
        right_count = 0

        for item in formatted_results:
            if item["round"] == turn:

                if item["valid"] == True:
                    right_count += 1

                all_count += 1
            

        print(f"model: {model}, round: {turn}, num_total: {all_count}, num_correct: {right_count}, pass_rate: {right_count / all_count}")
    print(" ")




#  resolve_rate (round)
print("——————————————————————————————————resolve rate by round——————————————————————————————————")
for model in model_list:
    count_file = os.path.join(target_dir, f"final_{model}.json")

    with open(count_file, 'r', encoding='utf-8') as f:
        formatted_results = json.load(f)

    for turn in range(1,4):
        all_count = 0
        right_count = 0
        for item in formatted_results:
            if item["round"] == turn:
                for i in range(3):
                    index = "test" + str(i + 1)
                    if index in item and item[index] == True:
                        right_count += 1
                    all_count += 1
        
    
        print(f"model: {model}, round: {turn}, num_total: {all_count}, num_correct: {right_count}, resolve_rate: {right_count / all_count}")
    print(" ")

