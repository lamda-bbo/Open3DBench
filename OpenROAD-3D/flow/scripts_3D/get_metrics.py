import os
import re
import json
import pdb
import pandas as pd

def get_power(data):
    
    power = data.get("finish__power__total", None)

    if power is None:
        return None

    if not isinstance(power, (int, float)):
        return None

    return power

def get_wns_tns(data):
    
    tns = data.get("finish__timing__setup__tns", None)
    wns = data.get("finish__timing__setup__ws", None)

    if wns is None or tns is None:
        return None, None

    if not isinstance(wns, (int, float)):
        return None, None
    if not isinstance(tns, (int, float)):
        return None, None

    return wns, tns

def get_GRT_wns_tns(data):
    
    tns = data.get("globalroute__timing__setup__tns", None)
    wns = data.get("globalroute__timing__setup__ws", None)

    if wns is None or tns is None:
        return None, None

    if not isinstance(wns, (int, float)):
        return None, None
    if not isinstance(tns, (int, float)):
        return None, None

    return wns, tns

def get_area(data):
    
    area = data.get("finish__design__instance__area__stdcell", None)

    if area is None:
        return None

    if not isinstance(area, (int, float)):
        return None

    return area

def get_die_area(data):
    
    area = data.get("finish__design__die__area", None)

    if area is None:
        return None

    if not isinstance(area, (int, float)):
        return None

    return area

def get_wirelength(data):
   
    wirelength = data.get("detailedroute__route__wirelength", None)

    if wirelength is None:
        return None

    if not isinstance(wirelength, (int, float)):
        return None

    return wirelength

def get_nvp(data):
    
    nvp = data.get("finish__timing__drv__setup_violation_count", None)

    if nvp is None:
        return None

    if not isinstance(nvp, (int, float)):
        return None

    return nvp

def get_statistics(data):
    macro_num = data.get("finish__design__instance__count__macros", None)
    utilization = data.get("finish__design__instance__utilization", None)
    cell_num = data.get("finish__design__instance__count__stdcell", None)

    return macro_num, cell_num, utilization

def get_net_num(data):
    net_num = data.get("detailedroute__route__net", None)
    return net_num

def get_cellHpwl(file_content):
    try:
        # Define the regex pattern to match the specific string and capture the number
        pattern = r"\[INFO DPL-0022\] HPWL after\s+([0-9]+\.[0-9]+) u"
        
        # Search for the pattern in the file content
        match = re.search(pattern, file_content)
        
        if match:
            # Extract the matched number and convert it to float
            hpwl_value = float(match.group(1))
            return hpwl_value
        else:
            return None
    
    except re.error:
        return None

def get_usage(content):
    
    # Find the specific table
    table_start_pattern = r'\[INFO GRT-0096\] Final congestion report:'
    match = re.search(table_start_pattern, content)
    if not match:
        return None
    table_start_index = match.end()
    table_content = content[table_start_index:]
    # Find the Total line and extract the Usage percentage
    total_line_pattern = r'Total\s+\d+\s+\d+\s+(\d+\.\d+%)'
    total_match = re.search(total_line_pattern, table_content)
    if not total_match:
        raise ValueError("Total usage percentage not found in the table")
    total_usage = total_match.group(1)
    return float(total_usage.replace("%", "")) / 100

def get_RESIZE_wns_tns(content):
    tns_values = re.findall(r"tns\s+(-?\d+\.\d+)", content)
    wns_values = re.findall(r"wns\s+(-?\d+\.\d+)", content)
    if tns_values and wns_values:
        return wns_values[0], tns_values[0], wns_values[1], tns_values[1]
    return None, None, None, None


def get_grt_wl(content):
    
    # Find the specific table
    pattern = r"\[INFO GRT-0018\] Total wirelength: (\d+) um"
    match = re.search(pattern, content)
    if match:
        return int(match.group(1))
    return None

def get_total_overflow(content):
    table_start_pattern = r'\[INFO GRT-0096\] Final congestion report:'
    match = re.search(table_start_pattern, content)
    if not match:
        return None
    table_start_index = match.end()
    table_content = content[table_start_index:]

    total_line_pattern = r'Total\s+\d+\s+\d+\s+(\d+\.\d+%)\s+\d+\s+\/\s+\d+\s+\/\s+(\d+)'
    total_match = re.search(total_line_pattern, table_content)
    if not total_match:
        raise ValueError("Total overflow not found in the table")

    total_overflow = total_match.group(2)
    return int(total_overflow)

def load_Json(Json):
    try:
        with open(Json, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        
        return {}  
    
def load_file(input_file):
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            data = file.read()
            return data
    except FileNotFoundError:
        
        return ""  

def get_Metric_in(finalJson, routeJson, placedpLog, gproutefile, fpjson, grouteJson, resizefile):


    final=load_Json(finalJson)
    route=load_Json(routeJson)
    place=load_file(placedpLog)
    gproute=load_file(gproutefile)
    fp=load_Json(fpjson)
    groute=load_Json(grouteJson)
    resize=load_file(resizefile)


    metric = {}
    metric["PRE_RESIZE_WNS"], metric["PRE_RESIZE_TNS"], metric["POST_RESIZE_WNS"], metric["POST_RESIZE_TNS"] = get_RESIZE_wns_tns(resize)
    metric["Congestion"] = get_usage(gproute)
    
    metric["GRT_WL"] = get_grt_wl(gproute)
    metric["GRT_WNS"], metric["GRT_TNS"] = get_GRT_wns_tns(groute)
    metric["DRT_WL"] = get_wirelength(route)
    metric["Final_WNS"], metric["Final_TNS"] = get_wns_tns(final)
    metric["Power"] = get_power(final)
    metric["#overflow"] = get_total_overflow(gproute)
    metric["NVP"]=get_nvp(final)
    metric["Die Area"] = get_die_area(final)
    metric["Cell Area"] = get_area(final)
    metric["#Macro"], metric["#Cells"], metric["Util"] = get_statistics(final)
    metric["#Net"] = get_net_num(route)
    

    return metric

def get_substring_after_underscore(input_string):
    
    underscore_index = input_string.find('_')
    
    if underscore_index != -1:
        
        result = input_string[underscore_index + 1:]
        return result
    else:
        
        return input_string

def find_reports_in_dirs(base_dir, method):
    report_files = {}

    for design_name in os.listdir(base_dir):
        root = os.path.join(base_dir, design_name, method)
        if os.path.isdir(root):
            report_files[design_name] = {
                    "report": os.path.join(root, '6_report.json'),
                    "route": os.path.join(root, '5_2_route.json'),
                    "place": os.path.join(root, '3_5_place_dp.log'),
                    "gp_route": os.path.join(root,"5_1_grt.log"),
                    "fp": os.path.join(root,"2_1_floorplan.json"),
                    "groute": os.path.join(root,"5_1_grt.json"),
                    "resize": os.path.join(root,"3_4_place_resized.log")
                }

    return report_files

def get_all_metric_json(report_files):
    all_metric_json = {}

    
    for case_name, report_file in report_files.items():
        metric = get_Metric_in(report_file["report"], report_file["route"], report_file["place"],report_file["gp_route"], report_file["fp"], report_file["groute"], report_file["resize"])
        all_metric_json[case_name] = metric

    return all_metric_json



def getMetrics(dir_path, method):

    report_files=find_reports_in_dirs(dir_path, method)
    metric_dict=get_all_metric_json(report_files)

    return metric_dict

if __name__ == '__main__':

    
    methods = ["2D", "2D_dmp", "2D_mp", "3D"]
    metrics = []
    for method in methods:
        if method == "2D":
            dir_path = f"logs/nangate45"
        elif method == "3D":
            dir_path = f"logs/nangate45_3D"
        else:
            dir_path = f"logs/nangate45"
        metric_dict = getMetrics(dir_path=dir_path, method=method)
        metrics.append(metric_dict)

    dataframes = []
    
    for dataset_name in metrics[0].keys():
        rows = []
        for idx, dataset in enumerate(metrics):
            if dataset_name == 'tinyRocket':
                continue
            method_data = dataset[dataset_name]
            method_name = methods[idx]
            row = [method_name] + list(method_data.values())
            rows.append(row)

        df = pd.DataFrame(rows, columns=['Method'] + list(metrics[0][dataset_name].keys()))
        df.insert(0, 'Dataset', dataset_name) 
        dataframes.append(df)
        dataframes.append(pd.DataFrame([[]])) 

    final_df = pd.concat(dataframes, ignore_index=True)

    final_df.to_csv(f'final.csv', index=False)