from binaryninja import BinaryView, log_info, log_error
from binaryninja.interaction import InteractionHandler
import revengai
from typing import Dict

class ViewFunctionInPortal:
    def __init__(self, config):
        self.config = config

    def view_function_in_portal(self, bv: BinaryView, options: Dict) -> None:
        """Match functions from the binary against RevEng.AI database"""
        try:
            log_info("RevEng.AI | Starting function searching in portal")
            function_addr = options.get("function", None)

            functions_containing = bv.get_functions_containing(function_addr)
            
            if not functions_containing:
                log_error(f"RevEng.AI | Function not found at 0x{function_addr:x}")
                raise Exception("Function not found at address")
            
            function = functions_containing[0]
            log_info(f"RevEng.AI | Function: {function.name} at 0x{function.start:x} (Clicked address: 0x{function_addr:x})")

            analysis_id = self.config.get_analysis_id(bv)
            if not analysis_id:
                raise Exception("Analysis not found. Please choose one using 'Choose Source' feature.")

            with revengai.ApiClient(self.config.api_config) as api_client:
                api_instance = revengai.AnalysesResultsMetadataApi(api_client)
                api_response = api_instance.get_functions_list(analysis_id)
                analyzed_functions = api_response.data.functions
                log_info(f"RevEng.AI | Analyzed functions: {analyzed_functions}")

            analyzed_function = next((f for f in analyzed_functions if f.function_vaddr == function.start), None)
            if not analyzed_function:
                log_error(f"RevEng.AI | Function {function.name} not found in analyzed functions")
                raise Exception("Function not found in analyzed functions")
            
            url = f"{self.config.portal_url}/function/{analyzed_function.function_id}"
            log_info(f"RevEng.AI | Opening URL: {url}")
            InteractionHandler().open_url(url)

            return True, "Function found in portal"

        except Exception as e:
            log_error(f"RevEng.AI | Error in function matching: {str(e)}")
            return False, str(e)