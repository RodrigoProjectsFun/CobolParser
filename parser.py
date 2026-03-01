import re
import json
import csv
from enum import Enum

class ParserState(Enum):
    SCANNING = 1
    IN_OPERATION = 2
    IGNORING_BLOCK = 3

class DynamicStateMachineParser:
    def __init__(self, config_dict):
        self.config = config_dict
        self.state = ParserState.SCANNING
        self.previous_state = ParserState.SCANNING
        
        # New variables to track the end condition counts
        self.active_ignore_end_pattern = None
        self.active_ignore_target_count = 1
        self.current_ignore_match_count = 0
        
        self.ignore_blocks = []
        for block in self.config.get("ignore_blocks", []):
            self.ignore_blocks.append({
                "name": block["name"],
                "start": re.compile(block["start_condition"]),
                "end": re.compile(block["end_condition"]),
                "end_count": block.get("end_count", 1) # Default to 1 if omitted
            })

        self.op_start_pattern = re.compile(self.config["operation_record"]["start_regex"])
        self.card_identifier = self.config["card_record"]["identifier"]
        
        self.current_card = None
        self.current_op_lines = []
        self.final_records = []

    def extract_fields(self, lines, field_config):
        extracted_data = {}
        for field_name, rules in field_config.items():
            line_idx = rules["line_index"]
            start = rules["start"]
            end = rules["end"]

            if line_idx < len(lines):
                target_line = lines[line_idx]
                if end is None:
                    extracted_data[field_name] = target_line[start:].strip()
                else:
                    extracted_data[field_name] = target_line[start:end].strip()
            else:
                extracted_data[field_name] = None 
                
        return extracted_data

    def flush_current_operation(self):
        if self.current_op_lines:
            op_data = self.extract_fields(self.current_op_lines, self.config["operation_record"]["fields"])
            if self.current_card:
                combined_record = {**self.current_card, **op_data}
            else:
                combined_record = op_data
            self.final_records.append(combined_record)
            self.current_op_lines = []

    def process_file(self, file_path):
        self.previous_state = ParserState.SCANNING 

        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                clean_line = line.rstrip('\n')

                # ---------------------------------------------------------
                # 1. ARE WE CURRENTLY IGNORING A BLOCK?
                # ---------------------------------------------------------
                if self.state == ParserState.IGNORING_BLOCK:
                    if self.active_ignore_end_pattern.search(clean_line):
                        self.current_ignore_match_count += 1
                        
                        # Only exit if we've hit the required number of matches
                        if self.current_ignore_match_count >= self.active_ignore_target_count:
                            self.state = self.previous_state 
                            self.active_ignore_end_pattern = None
                            self.active_ignore_target_count = 1
                            self.current_ignore_match_count = 0
                            
                    continue # Skip the line regardless

                # ---------------------------------------------------------
                # 2. ARE WE ENTERING A NEW IGNORE BLOCK?
                # ---------------------------------------------------------
                entered_ignore_block = False
                for block in self.ignore_blocks:
                    if block["start"].search(clean_line):
                        self.previous_state = self.state 
                        self.state = ParserState.IGNORING_BLOCK
                        
                        # Load the pattern and target count, reset the current count
                        self.active_ignore_end_pattern = block["end"]
                        self.active_ignore_target_count = block["end_count"]
                        self.current_ignore_match_count = 0
                        
                        entered_ignore_block = True
                        break 
                
                if entered_ignore_block:
                    continue

                # ---------------------------------------------------------
                # 3. HANDLE NOISE (Empty Lines)
                # ---------------------------------------------------------
                if not clean_line.strip():
                    continue 

                # ---------------------------------------------------------
                # 4. NORMAL PROCESSING (Cards & Operations)
                # ---------------------------------------------------------
                if self.card_identifier in clean_line:
                    self.flush_current_operation()
                    self.state = ParserState.SCANNING
                    self.current_card = self.extract_fields([clean_line], self.config["card_record"]["fields"])
                    continue

                if self.op_start_pattern.search(clean_line):
                    self.flush_current_operation()
                    self.current_op_lines.append(clean_line)
                    self.state = ParserState.IN_OPERATION 
                    continue

                if self.state == ParserState.IN_OPERATION:
                    self.current_op_lines.append(clean_line)

        self.flush_current_operation()
        return self.final_records

def export_to_csv(data, output_filename):
    if not data:
        print("No data found to export!")
        return
    
    # Grab the headers from the first dictionary
    keys = data[0].keys()
    with open(output_filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(data)
    print(f"Successfully exported {len(data)} records to {output_filename}")

import sys

if __name__ == "__main__":
    # Load the configuration
    with open('config.json', 'r') as f:
        config = json.load(f)

    # Initialize and run the parser
    parser = DynamicStateMachineParser(config)
    
    # Use CLI arg for filename if provided, otherwise default to report.txt
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'report.txt'
    parsed_data = parser.process_file(input_file)
    
    # Export the results
    export_to_csv(parsed_data, 'parsed_report.csv')