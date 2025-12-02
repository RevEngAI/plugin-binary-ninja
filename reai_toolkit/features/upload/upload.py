import revengai
from pathlib import Path
from binaryninja import BinaryView, log_info, log_error
from os.path import basename
from reai_toolkit.utils import PeriodicChecker

class BinaryUploader:
    def __init__(self, config):
        self.config = config
 
    def get_models(self, bv: BinaryView):
        try:
            with revengai.ApiClient(self.config.api_config) as api_client:
                api_instance = revengai.ModelsApi(api_client)
                api_response = api_instance.get_models()
                models = api_response.data.models
            log_info(f"RevEng.AI | Models: {models}")
            return True, models
        except Exception as e:
            log_error(f"RevEng.AI | Failed to get models: {str(e)}")
            return False, []

    def upload_file(self, file_path: str, file_type: revengai.UploadFileType):
        try:
            file = Path(file_path).read_bytes()
            with revengai.ApiClient(self.config.api_config) as api_client:
                api_instance = revengai.AnalysesCoreApi(api_client)
                api_response = api_instance.upload_file(file_type, file, force_overwrite=True)
                log_info(f"RevEng.AI | File uploaded successfully.")
            return True, api_response.data.sha_256_hash
        except Exception as e:
            log_error(f"RevEng.AI | Failed to upload file {file_path}: {str(e)}")
            return False, str(e)
                
    def upload_binary(self, bv: BinaryView, options: dict):
        try:

            log_info(f"RevEng.AI | Uploading binary {bv.file.filename}.")
            log_info(f"RevEng.AI | File size: {bv.parent_view.length} bytes")
            file = Path(bv.file.filename).read_bytes()
            if bv.parent_view.length > 10 * 1024 ** 2:
                log_error(f"RevEng.AI | File size is too large. Please upload a file smaller than 10MB.")
                return False
                
            success, sha_256_hash = self.upload_file(bv.file.filename, revengai.UploadFileType.BINARY)
            if not success:
                log_error(f"RevEng.AI | Failed to upload binary {bv.file.filename}.")
                return False

            log_info(f"RevEng.AI | Binary {bv.file.filename} uploaded successfully. SHA-256 hash: {sha_256_hash}")

            if options["debug_info"]:
                success, debug_info_hash = self.upload_file(options["debug_info"], revengai.UploadFileType.DEBUG)
                if not success:
                    log_error(f"RevEng.AI | Failed to upload debug info {options['debug_info']}.")
                    return False

                log_info(f"RevEng.AI | Debug info {options['debug_info']} uploaded successfully. SHA-256 hash: {debug_info_hash}")
            
            symbols = {
                "base_address": bv.image_base, 
                "function_boundaries": []
            }

            for func in bv.functions:
                symbols["function_boundaries"].append({
                        "mangled_name": func.name,
                        "start_address": func.start,
                        "end_address": func.start + func.total_bytes,
                })
            log_info(f"RevEng.AI | Collected {len(symbols['function_boundaries'])} functions from Binary Ninja!")

            with revengai.ApiClient(configuration=self.config.api_config) as api_client:

                analyses_client = revengai.AnalysesCoreApi(api_client)

                tags = []

                for tag in options["tags"]:
                    tags.append(revengai.Tag(name=tag))

                analysis_create_request=revengai.AnalysisCreateRequest(
                    filename=basename(bv.file.filename),
                    sha_256_hash=sha_256_hash,
                    debug_hash=debug_info_hash if options["debug_info"] else None,
                    tags=tags,
                    analysis_scope=revengai.AnalysisScope.PRIVATE if options["is_private"] else revengai.AnalysisScope.PUBLIC,
                    symbols=symbols
                )
                
                analysis_result = analyses_client.create_analysis(
                    analysis_create_request=analysis_create_request
                )

                log_info(f"RevEng.AI | Analysis started successfully. Analysis ID: {analysis_result.data.analysis_id}, Binary ID: {analysis_result.data.binary_id}")

            PeriodicChecker().start_checking(bv, analysis_result.data.analysis_id, analysis_result.data.binary_id, self.config.set_current_info, self.config.api_config)

            return True, "Analysis started successfully."
            
        except Exception as e:
            log_error(f"RevEng.AI | Failed to upload binary: {str(e)}")
            return False, str(e)