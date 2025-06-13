from binaryninja import BinaryView, log_info, log_error, log_debug, SymbolType, BinaryViewType
from reait.api import RE_models, RE_upload, RE_analysis_lookup, RE_analyse
from revengai_bn.utils import PeriodicChecker

class BinaryUploader:
    def __init__(self, config):
        self.config = config

    
    def get_models(self, bv: BinaryView):
        try:
            guess_model_platform = ""
            if bv.view_type == "PE":
                guess_model_platform = "windows"
            elif bv.view_type == "ELF":
                guess_model_platform = "linux"
            elif bv.view_type == "MACHO":
                guess_model_platform = "macos"

            guess_model_arch = ""
            if bv.arch.name == "x86":
                guess_model_arch = "x86-32"
            elif bv.arch.name == "x86_64":
                guess_model_arch = "x86"
            else:
                guess_model_arch = bv.arch.name
            
            log_info(f"RevEng.AI | Architecture: {bv.arch.name} | File type: {bv.view_type}")
            models = RE_models().json()
            models = list([model["model_name"] for model in models["models"]])

            guess_model =  f"{guess_model_arch}-{guess_model_platform}"
            log_info(f"RevEng.AI | Guess model: {guess_model}")
            for i, model in enumerate(models):
                if guess_model in model:
                    log_info(f"RevEng.AI | Found model: {model}")
                    models.insert(0, models.pop(i))
                    break
            log_info(f"RevEng.AI | Models: {models}")
            return models
        except Exception as e:
            log_error(f"RevEng.AI | Failed to get models: {str(e)}")
            return []
                

    def upload_binary(self, bv: BinaryView, options: dict):
        try:

            log_info(f"RevEng.AI | Uploading binary {bv.file.filename}.")
            log_info(f"RevEng.AI | File size: {bv.parent_view.length} bytes")
            if bv.parent_view.length > 10 * 1024 ** 2:
                log_error(f"RevEng.AI | File size is too large. Please upload a file smaller than 10MB.")
                return False

            upload = RE_upload(bv.file.filename).json()   

            if not upload.get("success", False):
                log_error(f"RevEng.AI | Failed to upload binary {bv.file.filename}.")
                return False

            log_info(f"RevEng.AI | Binary {bv.file.filename} uploaded successfully.")

            sha_256_hash = upload["sha_256_hash"]
            log_info(f"RevEng.AI | SHA-256 hash: {sha_256_hash}")

            symbols = {
                "base_addr": bv.image_base, 
                "functions": []
            }

            for func in bv.functions:
                symbols["functions"].append({
                        "name": func.name,
                        "start_addr": func.start,
                        "end_addr": func.start + func.total_bytes,
                })
            
            analysis = RE_analyse(
                fpath=bv.file.filename,
                binary_scope= "PRIVATE" if options["is_private"] else "PUBLIC",
                model_name=options["model"],
                tags=options["tags"],
                debug_fpath=options["debug_info"],
                symbols=symbols,
                skip_scraping=True,
                skip_sbom=True,
                skip_capabilities=True,
                advanced_analysis=False
            ).json()

            log_info(f"RevEng.AI | Analysis response: {analysis}")

            analysis_info = RE_analysis_lookup(str(analysis["binary_id"])).json()
                
            log_info(f"RevEng.AI | Binary ID: {analysis['binary_id']}")
            log_info(f"RevEng.AI | Analysis ID: {analysis_info['analysis_id']}")
            
            # TODO: Set binary and analysis id in config in form of id in array in settings

            PeriodicChecker().start_checking(bv, analysis["binary_id"])

            return True
            
        except Exception as e:
            log_error(f"RevEng.AI | Failed to upload binary: {str(e)}")
            return False 