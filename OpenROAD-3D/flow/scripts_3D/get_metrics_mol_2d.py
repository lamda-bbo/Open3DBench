import os
import re
import json
import pandas as pd
import logging

# 设置日志，方便调试
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class ReportParser:
    """
    负责解析日志文件和 JSON 文件的工具类。
    """
    
    @staticmethod
    def load_json(file_path):
        if not os.path.exists(file_path):
            logging.warning(f"File not found: {file_path}")
            return {}
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON: {file_path}")
            return {}

    @staticmethod
    def load_text(file_path):
        if not os.path.exists(file_path):
            logging.warning(f"File not found: {file_path}")
            return ""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")
            return ""

    @staticmethod
    def get_value_safe(data, key, expected_type=(int, float)):
        """从字典中安全获取值，并检查类型"""
        val = data.get(key, None)
        if val is None:
            return None
        if not isinstance(val, expected_type):
            return None
        return val

    # --- JSON Metric Extractors ---
    
    @classmethod
    def extract_metrics_from_json(cls, finish_json_data, drt_json_data):
        """统一提取 JSON 中的指标"""
        metrics = {}

        # From DRT JSON
        metrics["DRT_WL"] = cls.get_value_safe(drt_json_data, "detailedroute__route__wirelength")
        # metrics["DRT_DRC"] = cls.get_value_safe(drt_json_data, "detailedroute__route__drc_errors")

        # From Finish JSON
        metrics["FINAL_WNS"] = cls.get_value_safe(finish_json_data, "finish__timing__setup__ws")
        metrics["FINAL_TNS"] = cls.get_value_safe(finish_json_data, "finish__timing__setup__tns")
        metrics["Power"] = cls.get_value_safe(finish_json_data, "finish__power__total")
        
        return metrics

    # --- Log Regex Extractors ---

    @staticmethod
    def get_grt_wl(content):
        pattern = r"\[INFO GRT-0018\] Total wirelength: (\d+) um"
        match = re.search(pattern, content)
        return int(match.group(1)) if match else None
    
    @staticmethod
    def get_grt_ecp(content):
        """
        提取 GRT Log 中的 Effective Clock Period (ECP)。
        计算公式: Period - Slack
        """
        # 1. 定义正则模式
        # 匹配: [INFO FLW-0007] clock CLK period 2.600000
        # (\S+) 捕获时钟名, ([\d\.]+) 捕获周期值
        period_pattern = r"\[INFO FLW-0007\] clock\s+(\S+)\s+period\s+([\d\.]+)"
        
        # 匹配: [INFO FLW-0009] Clock CLK slack -0.333
        # 注意: 这里用了 [Cc]lock 兼容大小写, (-?[\d\.]+) 捕获可能带负号的 slack 值
        slack_pattern = r"\[INFO FLW-0009\] [Cc]lock\s+(\S+)\s+slack\s+(-?[\d\.]+)"

        # 2. 提取所有匹配项并存入字典
        # 结构: {'CLK': 2.6, 'CLK2': 1.5}
        periods = {}
        for match in re.finditer(period_pattern, content):
            clk_name = match.group(1)
            period_val = float(match.group(2))
            periods[clk_name] = period_val

        slacks = {}
        for match in re.finditer(slack_pattern, content):
            clk_name = match.group(1)
            slack_val = float(match.group(2))
            slacks[clk_name] = slack_val

        # 3. 计算 ECP (Period - Slack)
        # 遍历找到的周期，寻找对应的 slack 进行计算
        # 如果日志里只有一个时钟，循环只会执行一次
        for clk_name, period in periods.items():
            if clk_name in slacks:
                slack = slacks[clk_name]
                ecp = round(period - slack, 4)
                
                # 如果你需要保留小数精度，可以使用 round，例如 round(ecp, 4)
                # 这里直接返回浮点数结果
                return ecp

        # 如果没有找到成对的数据
        return None

class ExperimentManager:
    """
    负责管理实验路径、文件查找和数据聚合。
    """
    def __init__(self, base_dir="logs/nangate45_3D"):
        self.base_dir = base_dir

    def find_report_files(self, method_name):
        """
        为指定的方法查找所有 design 的报告文件路径。
        """
        report_files = {}
        
        if not os.path.exists(self.base_dir):
            logging.error(f"Base directory does not exist: {self.base_dir}")
            return {}

        for design_name in os.listdir(self.base_dir):
            # TODO: 确认目录结构。原代码假设结构是 logs/nangate45_3D/{design_name}/{method_name}/...
            root = os.path.join(self.base_dir, design_name, method_name)
            
            if os.path.isdir(root):
                report_files[design_name] = {
                    "grt_log": os.path.join(root, "5_1_grt.log"),
                    "grt_json": os.path.join(root, "5_1_grt.json"),
                    "drt_log": os.path.join(root, "5_2_route.log"),
                    "drt_json": os.path.join(root, "5_2_route.json"),
                    "finish_json": os.path.join(root, "6_report.json"),
                }
        return report_files

    def process_single_case(self, file_paths):
        """
        处理单个 design 的所有文件，返回指标字典。
        """
        # 1. 加载文件内容
        grt_log_content = ReportParser.load_text(file_paths["grt_log"])
        grt_json_data = ReportParser.load_json(file_paths["grt_json"])
        drt_json_data = ReportParser.load_json(file_paths["drt_json"])
        finish_json_data = ReportParser.load_json(file_paths["finish_json"])
        
        # 2. 提取指标
        metrics = {}
        
        # Log based metrics
        metrics["GRT_WL"] = ReportParser.get_grt_wl(grt_log_content)
        # metrics["GRT_ECP"] = ReportParser.get_grt_ecp(grt_log_content)

        # JSON based metrics (DRT & Finish)
        common_metrics = ReportParser.extract_metrics_from_json(finish_json_data, drt_json_data)
        metrics.update(common_metrics)

        return metrics

    def get_metrics_for_method(self, method_name):
        """
        获取某个 method 下所有 design 的指标。
        """
        report_files_map = self.find_report_files(method_name)
        all_metrics = {}

        for design_name, file_paths in report_files_map.items():
            all_metrics[design_name] = self.process_single_case(file_paths)
            
        return all_metrics


def main():
    # --- 1. 配置区域 ---
    BASE_LOG_DIR = "logs/nangate45"
    OUTPUT_CSV = "mol_2d.csv"

    METHODS = [
        "2D_rtlmp", 
    ]
    DESIGN_ORDER = [
        "ariane133",
        "ariane136",
        "bp",
        "bp_be",
        "bp_fe",
        "bp_multi",
        "swerv_wrapper",
        "bp_quad"
    ]

    manager = ExperimentManager(base_dir=BASE_LOG_DIR)
    
    # 收集数据结构: metrics_by_method[method_name][design_name] = {metric_key: value}
    metrics_by_method = {}
    
    # --- 2. 遍历所有方法收集数据 ---
    for method in METHODS:
        logging.info(f"Processing method: {method}")
        metrics_by_method[method] = manager.get_metrics_for_method(method)

    if not metrics_by_method or not metrics_by_method[METHODS[0]]:
        logging.error("No data found. Exiting.")
        return

    # --- 3. 确定 Design 的最终顺序 ---
    
    # 获取实际扫描到的所有 design (以第一个 method 为准)
    available_designs = list(metrics_by_method[METHODS[0]].keys())
    
    # 核心排序逻辑：
    # 1. 先从 DESIGN_ORDER 中找存在的 design
    sorted_design_names = [d for d in DESIGN_ORDER if d in available_designs]
    
    # 2. 找出那些扫描到了，但没在 DESIGN_ORDER 里配置的 design (防止漏掉)
    remaining_designs = [d for d in available_designs if d not in sorted_design_names]
    
    # 3. 将剩余的 design 按字母顺序排在后面
    sorted_design_names.extend(sorted(remaining_designs))

    logging.info(f"Final Design Order: {sorted_design_names}")

    # --- 4. 转换为 DataFrame 格式 ---
    
    dataframes = []

    # 注意：这里遍历的是我们排序好的 sorted_design_names
    for design in sorted_design_names:
        rows = []
        
        # 获取列名 (指标名)
        sample_metrics = metrics_by_method[METHODS[0]].get(design, {})
        # 如果第一个 method 没跑这个 case，尝试从其他 method 找 key，或者跳过
        if not sample_metrics:
            # 尝试在其他 method 里找 key，防止因为第一个 method 失败导致表头缺失
            for m in METHODS:
                if metrics_by_method.get(m, {}).get(design, {}):
                    sample_metrics = metrics_by_method[m][design]
                    break
        
        if not sample_metrics:
             logging.warning(f"Skipping empty design: {design}")
             continue
             
        metric_keys = list(sample_metrics.keys())

        for method in METHODS:
            # 获取该 method 该 design 的数据
            data = metrics_by_method.get(method, {}).get(design, {})
            
            # 构建一行数据
            row = [method] + [data.get(k, None) for k in metric_keys]
            rows.append(row)

        # 创建该 Design 的 DataFrame
        df = pd.DataFrame(rows, columns=['Method'] + metric_keys)
        df.insert(0, 'Dataset', design)
        
        dataframes.append(df)
        # 添加空行用于分隔
        dataframes.append(pd.DataFrame([[]]))

    # --- 5. 合并并保存 ---
    if dataframes:
        final_df = pd.concat(dataframes, ignore_index=True)
        final_df.to_csv(OUTPUT_CSV, index=False)
        logging.info(f"Saved results to {OUTPUT_CSV}")
    else:
        logging.warning("No dataframes generated.")

if __name__ == '__main__':
    main()
