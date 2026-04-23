import os
import re
import yaml
import collections

# dify
from nodes.dify.basic.code import Code
from nodes.dify.basic.document_extractor import DocumentExtractor
from nodes.dify.basic.end import End
from nodes.dify.basic.http_request import HttpRequest
from nodes.dify.basic.if_else import IfElse
from nodes.dify.basic.iteration import Iteration
from nodes.dify.basic.list_operator import ListOperator
from nodes.dify.basic.llm import LLM
from nodes.dify.basic.parameter_extractor import ParameterExtractor
from nodes.dify.basic.question_classifier import QuestionClassifier
from nodes.dify.basic.start import Start
from nodes.dify.basic.template_transform import TemplateTransform
from nodes.dify.basic.variable_aggregator import VariableAggregator
from nodes.dify.basic.iteration_start import IterationStart

from nodes.dify.tool.text2image import Text2Image
from nodes.dify.tool.tts import TTS
from nodes.dify.tool.markdown_exporter import MarkdownExporter
from nodes.dify.tool.mermaid_converter import MermaidConverter
from nodes.dify.tool.echarts import Echarts
from nodes.dify.tool.google_search import GoogleSearch

# coze
from nodes.coze.basic.code import Code as Code_coze
from nodes.coze.basic.document_extractor import DocumentExtractor as DocumentExtractor_coze
from nodes.coze.basic.end import End as End_coze
from nodes.coze.basic.http_request import HttpRequest as HttpRequest_coze
from nodes.coze.basic.if_else import IfElse as IfElse_coze
from nodes.coze.basic.iteration import Iteration as Iteration_coze

from nodes.coze.basic.llm import LLM as LLM_coze
from nodes.coze.basic.parameter_extractor import ParameterExtractor as ParameterExtractor_coze
from nodes.coze.basic.question_classifier import QuestionClassifier as QuestionClassifier_coze
from nodes.coze.basic.start import Start as Start_coze
from nodes.coze.basic.template_transform import TemplateTransform as TemplateTransform_coze
from nodes.coze.basic.variable_aggregator import VariableAggregator as VariableAggregator_coze

from nodes.coze.tool.text2image import Text2Image as Text2Image_coze
from nodes.coze.tool.tts import TTS as TTS_coze
from nodes.coze.tool.markdown_exporter import MarkdownExporter as MarkdownExporter_coze
from nodes.coze.tool.mermaid_converter import MermaidConverter as MermaidConverter_coze
from nodes.coze.tool.echarts import Echarts as Echarts_coze
from nodes.coze.tool.google_search import GoogleSearch as GoogleSearch_coze


# dify
def search_var(ref_var: str, ref_node):
    # Input: Variable name + Reference node object
    # Output: Source node ID of the variable + Type of the variable
    typee = None
    idd = ref_node.id

    # Handling special cases for 'file.type' (i.e., those containing sub-variables)
    if '.' in ref_var:
        typee = "string"

    elif ref_node.data['type'] == "start":
        for var in ref_node.data['variables']:
            if var['variable'] == ref_var:
                typee = var['type']
                break

        if typee == "paragraph": typee = "string"
        elif typee == "checkbox": typee = "boolean"
        elif typee == "file-list": typee = "array[file]"
    
    elif ref_node.data['type'] in ["question-classifier", "http-request", "llm", "template-transform", "echarts"]:
        typee = "string"
    
    elif ref_node.data['type'] == "code":
        typee = ref_node.data['outputs'][ref_var]['type']
    
    elif ref_node.data['type'] == "document-extractor":
        typee = "array[file]" if ref_node.data['is_array_file'] else "file"
    
    elif ref_node.data['type'] == "iteration":
        if ref_var == "index": typee = "number"
        elif ref_var == "item": typee = ref_node.data['iterator_input_type'].strip('array[').strip(']')
        else:
            typee = ref_node.data["output_type"]

    elif ref_node.data['type'] == "list-operator":
        typee = ref_node.data['var_type']
        if 'record' in ref_var:
            typee = typee.strip('array[').strip(']')
    
    elif ref_node.data['type'] == "parameter-extractor":
        for var in ref_node.data['parameters']:
            if var['name'] == ref_var:
                typee = var['type']
                break

    elif ref_node.data['type'] == "variable-aggregator":
        typee = ref_node.data['output_type']
    
    elif ref_node.data['tool_name'] in ["z_image_text_2_image","tts","mermaid-converter"] or 'md' in ref_node.data['tool_name']:
        typee = "array[file]"
    
    elif ref_node.data['tool_name'] == "google-search":
        typee = "array[object]"

    return idd, typee

# dify
def construct(node_type: str, param: dict, x: int, y: int, count: int, id_dict: dict):

    def batch_replace_ids(text, id_dict):
        """
        text: The original string containing {{#...#}}
        """
        pattern = r"\{\{#([^.]+)\.(.+?)#\}\}"

        def replace_callback(match):
            old_id = match.group(1)
            if '-' in old_id:
                old_id = old_id.strip("'").strip('"').strip("'")
            else:
                old_id = eval(old_id)

            new_id = id_dict[str(old_id)].id

            var_name = match.group(2) # Obtain the variable name
            return f"{{{{#{new_id}.{var_name}#}}}}"

        return re.sub(pattern, replace_callback, text)


    if node_type == 'start':
        current_node = Start(param["variables"], x, y, count)

    elif node_type == 'iteration-start':
        current_node = IterationStart(x, y)

    elif node_type == 'question-classifier':
        ref_var = param['query_variable_selector'][0]
        ref_node = id_dict[param['query_variable_selector'][1]]
        idd, typee = search_var(ref_var, ref_node)
        
        instruction = param.get('instruction', "")

        current_node = QuestionClassifier(query=[ref_var, idd], class_list=param["classes"], instruction=instruction, x=x, y=y, count=count)

    elif node_type == 'code':
        input_list = []
        for var in param['variables']:
            ref_var = var[1][0]
            ref_node = id_dict[var[1][1]]
            idd, typee = search_var(ref_var, ref_node)
            input_list.append([var[0], ref_var, typee, idd])

        current_node = Code(param["code"], input_list, param["outputs"], x, y, count)

    elif node_type == 'document-extractor':
        ref_var = param['variable_selector'][0]
        ref_node = id_dict[param['variable_selector'][1]]
        idd, typee = search_var(ref_var, ref_node)

        current_node = DocumentExtractor([ref_var, typee, idd], x, y, count)
    
    elif node_type == 'end':
        input_list = []
        for var in param['outputs']:
            ref_var = var[1][0]
            ref_node = id_dict[var[1][1]]
            idd, typee = search_var(ref_var, ref_node)
            input_list.append([var[0], ref_var, typee, idd])
            
        current_node = End(input_list, x, y, count)

    elif node_type == 'http-request':
        ref_var = param['url'][0]
        ref_node = id_dict[param['url'][1]]

        idd, typee = search_var(ref_var, ref_node)

        url = '{{#' + idd + '.' + ref_var + '#}}'

        current_node = HttpRequest(url, x, y, count)

    elif node_type == 'if-else':
        input_list = []
        for case in param['cases']:
            case_list = []
            # Handling the situation of null
            if case[0] != 'or': case[0] = 'and'

            for condition in case[1]:
                ref_var = condition[0][0]
                ref_node = id_dict[condition[0][1]]

                idd, typee = search_var(ref_var, ref_node)


                operator = condition[1]

                if len(condition) == 3:
                    value = batch_replace_ids(condition[2], id_dict)

                    case_list.append([ref_var, typee, idd, operator, value])
                else:
                    case_list.append([ref_var, typee, idd, operator])

            input_list.append([case[0], case_list])

        current_node = IfElse(input_list, x, y, count)

    elif node_type == 'iteration':
        ref_var1 = param['iterator_selector'][0]
        ref_node1 = id_dict[param['iterator_selector'][1]]
        idd1, typee1 = search_var(ref_var1, ref_node1)

        current_node = Iteration([ref_var1, typee1, idd1], x, y, count)


    elif node_type == 'list-operator':
        ref_var = param['variable'][0]
        ref_node = id_dict[param['variable'][1]]
        idd, typee = search_var(ref_var, ref_node)

        if param["operator"][0] == "filter_by" and isinstance(param["operator"][2], str):
            param["operator"][2] = batch_replace_ids(param["operator"][2], id_dict)

        current_node = ListOperator([ref_var, typee, idd], param["operator"], x, y, count)

    
    elif node_type == 'llm':
        system_prompt = batch_replace_ids(param['system'], id_dict)
        user_prompt = batch_replace_ids(param['user'], id_dict)

        current_node = LLM([['system', system_prompt], ['user', user_prompt]], x, y, count)
    
    elif node_type == 'parameter-extractor':
        ref_var = param['query'][0]
        ref_node = id_dict[param['query'][1]]
        idd, typee = search_var(ref_var, ref_node)

        instruction = batch_replace_ids(param["instruction"], id_dict)

        current_node = ParameterExtractor(query=[ref_var, idd], param_list=param["parameters"], instruction=instruction, x=x, y=y, count=count)
    
    elif node_type == 'template-transform':
        input_list = []
        for var in param['variables']:
            ref_var = var[1][0]
            ref_node = id_dict[var[1][1]]
            idd, typee = search_var(ref_var, ref_node)
            input_list.append([var[0], ref_var, typee, idd])

        current_node = TemplateTransform(input_list, param["template"], x, y, count)
    
    elif node_type == 'variable-aggregator':
        input_list = []
        for var in param['variables']:
            ref_var = var[0]
            ref_node = id_dict[var[1]]
            idd, typee = search_var(ref_var, ref_node)
            input_list.append([ref_var, typee, idd])

        current_node = VariableAggregator(input_list, x, y, count)
    
    elif node_type == 'text2image':
        image_prompt = batch_replace_ids(param['prompt'], id_dict)
        current_node = Text2Image(image_prompt, x, y, count)
    
    elif node_type == 'tts':
        text = batch_replace_ids(param['text'], id_dict)
        current_node = TTS(text, x, y, count)

    elif node_type == 'markdown-exporter':
        md_text = batch_replace_ids(param['md_text'], id_dict)
        current_node = MarkdownExporter(param['target_type'], md_text, x, y, count)
    
    elif node_type == 'mermaid-converter':
        mermaid_code = batch_replace_ids(param['mermaid_code'], id_dict)
        current_node = MermaidConverter(mermaid_code, x, y, count)
    
    elif node_type == 'echarts':
        chart_type = batch_replace_ids(param['chart_type'], id_dict)
        chart_title = batch_replace_ids(param['chart_title'], id_dict)
        data = batch_replace_ids(param['data'], id_dict)
        x_axisORcategories = batch_replace_ids(param['x_axisORcategories'], id_dict)
        current_node = Echarts(chart_type, chart_title, data, x_axisORcategories, x, y, count)
    
    elif node_type == 'google-search':
        query = batch_replace_ids(param['query'], id_dict)
        current_node = GoogleSearch(query, x, y, count)

    else:
        current_node = None
    
    return current_node


# coze
def search_var_coze(ref_var: str, ref_node):

    if "Document Extractor" in ref_node.title and ref_var == "text":
        ref_var = "data"
    elif "Iteration" in ref_node.title and ref_var == "item":
        ref_var = "iterator_selector"
    elif "Text to Speech" in ref_node.title and ref_var == "files":
        ref_var = "data.link"
    elif "Image Generator" in ref_node.title and ref_var == "files":
        ref_var = "data"
    elif "Mermaid Converter" in ref_node.title and ref_var == "files":
        ref_var = "editUrl"
    elif "Doc Maker" in ref_node.title and ref_var == "files":
        if ref_node.target_type == "png":
            ref_var = "url"
        else:
            ref_var = "data"
    elif "_charts" in ref_node.title and ref_var == "text":
        ref_var = "data"
    elif "Web Search" in ref_node.title and ref_var == "json":
        ref_var = "data"
    elif "Question Classifier" in ref_node.title and ref_var == "class_name":
        ref_var = "classificationId"

    return ref_var


# coze
def construct_coze(node_type: str, param: dict, x: int, y: int, count: int, id_dict: dict):
    def extract_and_replace_ids(text, id_dict):

        pattern = r"\{\{#([^.]+)\.(.+?)#\}\}"
        records = []

        def replace_callback(match):
            old_id = match.group(1)
            var_name = match.group(2)
            
            if '-' in old_id:
                old_id = old_id.strip("'").strip('"').strip("'")
            else:
                old_id = eval(old_id) 

            new_id = id_dict[str(old_id)].id
            
            records.append([var_name,new_id])

            return f"{{{{_{new_id}_{var_name}}}}}"

        new_text = re.sub(pattern, replace_callback, text)
    
        return new_text, records


    if node_type == 'start':
        current_node = Start_coze(param["variables"], x, y, count)

    elif node_type == 'question-classifier':
        ref_var = param['query_variable_selector'][0]
        ref_node = id_dict[param['query_variable_selector'][1]]
        ref_var = search_var_coze(ref_var, ref_node)
        idd = ref_node.id
        
        instruction = param.get('instruction', "")

        current_node = QuestionClassifier_coze(query=[ref_var, idd], class_list=param["classes"], instruction=instruction, x=x, y=y, count=count)

    elif node_type == 'code':
        input_list = []
        for var in param['variables']:
            ref_var = var[1][0]
            ref_node = id_dict[var[1][1]]
            ref_var = search_var_coze(ref_var, ref_node)
            idd = ref_node.id
            input_list.append([var[0], ref_var, "", idd])

        current_node = Code_coze(param["code"], input_list, param["outputs"], x, y, count)

    elif node_type == 'document-extractor':
        ref_var = param['variable_selector'][0]
        ref_node = id_dict[param['variable_selector'][1]]
        ref_var = search_var_coze(ref_var, ref_node)
        idd = ref_node.id

        current_node = DocumentExtractor_coze([ref_var, "", idd], x, y, count)
    
    elif node_type == 'end':
        input_list = []
        for var in param['outputs']:
            ref_var = var[1][0]
            ref_node = id_dict[var[1][1]]
            ref_var = search_var_coze(ref_var, ref_node)
            idd = ref_node.id
            input_list.append([var[0], ref_var, "", idd])
            
        current_node = End_coze(input_list, x, y, count)

    elif node_type == 'http-request':
        ref_var = param['url'][0]
        ref_node = id_dict[param['url'][1]]
        ref_var = search_var_coze(ref_var, ref_node)
        idd = ref_node.id

        url = '{{block_output_' + idd + '.' + ref_var + '}}'

        github_rest_token = _load_github_rest_token()

        current_node = HttpRequest_coze(url, x, y, count, github_rest_token)

    elif node_type == 'if-else':
        input_list = []
        for case in param['cases']:
            case_list = []

            if case[0] != 'or': case[0] = 'and'

            for condition in case[1]:
                ref_var = condition[0][0]
                ref_node = id_dict[condition[0][1]]
                ref_var = search_var_coze(ref_var, ref_node)
                idd = ref_node.id

                operator = condition[1]

                if len(condition) == 3:
                    value, records = extract_and_replace_ids(condition[2], id_dict)

                    case_list.append([ref_var, "", idd, operator, value])
                else:
                    case_list.append([ref_var, "", idd, operator])

            input_list.append([case[0], case_list])
        
        if len(records) == 0:
            current_node = IfElse_coze(input_list, x, y, count, None)
        else:
            current_node = IfElse_coze(input_list, x, y, count, records[0])

    elif node_type == 'iteration':
        ref_var1 = param['iterator_selector'][0]
        ref_node1 = id_dict[param['iterator_selector'][1]]
        ref_var1 = search_var_coze(ref_var1, ref_node1)
        idd = ref_node1.id

        current_node = Iteration_coze([ref_var1, "", idd], x, y, count)

    
    elif node_type == 'llm':
        system_prompt, records1 = extract_and_replace_ids(param['system'], id_dict)
        user_prompt, records2 = extract_and_replace_ids(param['user'], id_dict)
        
        union_set = set(tuple(item) for item in records1) | set(tuple(item) for item in records2)
        records = [list(item) for item in union_set] 

        current_node = LLM_coze([['system', system_prompt], ['user', user_prompt]], x, y, count, records)
    
    elif node_type == 'parameter-extractor':
        ref_var = param['query'][0]
        ref_node = id_dict[param['query'][1]]
        ref_var = search_var_coze(ref_var, ref_node)
        idd = ref_node.id

        instruction, records = extract_and_replace_ids(param["instruction"], id_dict)

        current_node = ParameterExtractor_coze(query=[ref_var, idd], param_list=param["parameters"], instruction=instruction, x=x, y=y, count=count, records = records)
    
    elif node_type == 'template-transform':
        input_list = []
        for var in param['variables']:
            ref_var = var[1][0]
            ref_node = id_dict[var[1][1]]
            ref_var = search_var_coze(ref_var, ref_node)
            idd = ref_node.id
            input_list.append([var[0], ref_var, "", idd])

        current_node = TemplateTransform_coze(input_list, param["template"], x, y, count)
    
    elif node_type == 'variable-aggregator':
        input_list = []
        for var in param['variables']:
            ref_var = var[0]
            ref_node = id_dict[var[1]]
            ref_var = search_var_coze(ref_var, ref_node)
            idd = ref_node.id
            input_list.append([ref_var, "", idd])

        current_node = VariableAggregator_coze(input_list, x, y, count)
    
    elif node_type == 'text2image':
        image_prompt, records = extract_and_replace_ids(param['prompt'], id_dict)
        current_node = Text2Image_coze(image_prompt, x, y, count, records)
    
    elif node_type == 'tts':
        text, records = extract_and_replace_ids(param['text'], id_dict)
        if len(records) == 0:
            current_node = TTS_coze(text, x, y, count, None)
        else:
            current_node = TTS_coze(text, x, y, count, records[0])

    elif node_type == 'markdown-exporter':
        md_text, records = extract_and_replace_ids(param['md_text'], id_dict)
        if len(records) == 0:
            current_node = MarkdownExporter_coze(param['target_type'], md_text, x, y, count, None)
        else:
            current_node = MarkdownExporter_coze(param['target_type'], md_text, x, y, count, records[0])
    
    elif node_type == 'mermaid-converter':
        mermaid_code, records = extract_and_replace_ids(param['mermaid_code'], id_dict)
        if len(records) == 0:
            current_node = MermaidConverter_coze(mermaid_code, x, y, count, None)
        else:
            current_node = MermaidConverter_coze(mermaid_code, x, y, count, records[0])
    
    elif node_type == 'echarts':
        chart_type = param['chart_type']
        chart_title, records = extract_and_replace_ids(param['chart_title'], id_dict)
        data = param['data']
        x_axisORcategories = param['x_axisORcategories']

        if len(records) == 0:
            current_node = Echarts_coze(chart_type, chart_title, data, x_axisORcategories, x, y, count, None)
        else:
            current_node = Echarts_coze(chart_type, chart_title, data, x_axisORcategories, x, y, count, records[0])
    
    elif node_type == 'google-search':
        query, records = extract_and_replace_ids(param['query'], id_dict)
        if len(records) == 0:
            current_node = GoogleSearch_coze(query, x, y, count, None)
        else:
            current_node = GoogleSearch_coze(query, x, y, count, records[0])

    else:
        current_node = None
    
    return current_node



def layout_nodes(edges, node_width=300, node_height=200, x_gap=0, y_gap=0):
    """
    Calculate the grid(x, y) layout of the nodes based on the "edges" list. 
    
    Args:
        edges: list, each item is [source_node, port, target_node]
        node_width: int, node width
        node_height: int, node height
        x_gap: int, horizontal spacing
        y_gap: int, vertical spacing
        
    Returns:
        positions: dict, {node_id: {'x': int, 'y': int, 'col': int, 'row': int}}
    """
    
    graph = collections.defaultdict(list)
    in_degree = collections.defaultdict(int)
    all_nodes = set()
    
    for source, port, target in edges:
        graph[source].append((port, target))
        in_degree[target] += 1
        all_nodes.add(source)
        all_nodes.add(target)
        
    for node in all_nodes:
        if node not in in_degree:
            in_degree[node] = 0

    for node in graph:
        graph[node].sort(key=lambda x: x[0]) 

    queue = collections.deque([n for n in all_nodes if in_degree[n] == 0])
    node_layers = {}
    
    visited = set() 
    
    while len(visited) < len(all_nodes):
        if not queue:
            remaining = [n for n in all_nodes if n not in visited]
            if not remaining: break
            queue.append(remaining[0])
            
        current_node = queue.popleft()
        
        if current_node in visited:
            continue
        visited.add(current_node)
        
        pass 

    layers = {node: 0 for node in all_nodes}
    
    for _ in range(len(all_nodes)):
        changed = False
        for source in graph:
            for _, target in graph[source]:
                if layers[target] < layers[source] + 1:
                    layers[target] = layers[source] + 1
                    changed = True
        if not changed:
            break
            
    layer_groups = collections.defaultdict(list)
    for node, layer in layers.items():
        layer_groups[layer].append(node)
        
    positions = {}
    
    sorted_layers = sorted(layer_groups.keys())
    
    for layer_idx in sorted_layers:
        nodes_in_layer = layer_groups[layer_idx]
        
        if layer_idx > 0:
            node_scores = []
            for node in nodes_in_layer:
                parents = [src for src, targets in graph.items() for _, t in targets if t == node]
                if parents:
                    parent_indices = []
                    for p in parents:
                        p_layer = layers[p]
                        if p in positions: 
                             parent_indices.append(positions[p]['row'])
                    avg_index = sum(parent_indices) / len(parent_indices) if parent_indices else 0
                else:
                    avg_index = 0
                node_scores.append((avg_index, node))
            
            nodes_in_layer = [n for _, n in sorted(node_scores, key=lambda x: x[0])]
        
        for row_idx, node in enumerate(nodes_in_layer):
            pos_x = layer_idx * (node_width + x_gap)
            pos_y = row_idx * (node_height + y_gap)
            
            positions[node] = {
                'x': pos_x,
                'y': pos_y,
                'col': layer_idx,
                'row': row_idx
            }
            
    return positions
