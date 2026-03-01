import json
import logging
import argparse
from parser import DynamicStateMachineParser

def generate_confidential_log(input_file, config_file='config.json', log_file='parser_confidential_log.txt'):
    # Setup logging to output to a file, masking printed sensitive elements
    logging.basicConfig(filename=log_file, level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        filemode='w')
    
    logging.info("==================================================")
    logging.info(f"Starting confidential parse test on target file...")
    logging.info("==================================================")

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        parser = DynamicStateMachineParser(config)
        records = parser.process_file(input_file)
        
        logging.info("Parsing engine completed successfully without fatal exceptions.")
        logging.info(f"Total operational records extracted: {len(records)}")
        logging.info(f"Global Margin Drift Detected: {parser.global_drift} spaces")
        
        # Calculate statistics without recording OR exposing actual string data
        total_cards = set()
        operations_count = len(records)
        
        field_completion_stats = {k: 0 for k in config['operation_record']['fields'].keys()}
        field_completion_stats.update({k: 0 for k in config['card_record']['fields'].keys()})
        
        for record in records:
            # Hash or track cards to get a count of unique cards processed without storing the numbers
            if record.get("card_number") and str(record["card_number"]).strip() != "":
                total_cards.add(hash(record["card_number"]))
            
            for field in field_completion_stats.keys():
                val = record.get(field)
                if val is not None and str(val).strip() != "":
                    field_completion_stats[field] += 1
                    
        logging.info(f"Total unique card clusters grouped: {len(total_cards)}")
        logging.info(f"Total operations parsed: {operations_count}")
        logging.info("\n--- Field Extraction Success Rates ---")
        
        for field, count in field_completion_stats.items():
            percentage = (count / operations_count * 100) if operations_count > 0 else 0
            logging.info(f" - {field}: {count}/{operations_count} successfully populated ({percentage:.2f}%)")
            
        logging.info("==================================================")
        logging.info("Testing Finalized. ZERO financial data recorded.")
        logging.info("==================================================")
        
        print(f"Confidential test complete. Safe logs written to: {log_file}")
        
    except Exception as e:
        logging.error(f"FATAL ERROR during parsing: {str(e)}", exc_info=True)
        print(f"Test failed. Exception details written safely to {log_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Confidential Parser Telemetry Tester')
    parser.add_argument('input_file', help='The raw live COBOL spool file to test')
    parser.add_argument('--config', default='config.json', help='Path to config.json')
    parser.add_argument('--log', default='parser_confidential_log.txt', help='Output log file name')
    
    args = parser.parse_args()
    generate_confidential_log(args.input_file, args.config, args.log)
