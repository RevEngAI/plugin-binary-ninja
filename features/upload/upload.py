from binaryninja import BinaryView, log_info, log_error, log_debug, SymbolType, BinaryViewType
from reait.api import RE_models, RE_upload, RE_analysis_lookup, RE_analyse
import json

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

            upload = RE_upload(bv.file.filename).json()   

            if not upload.get("success", False):
                log_error(f"RevEng.AI | Failed to upload binary {bv.file.filename}.")
                return False

            log_info(f"RevEng.AI | Binary {bv.file.filename} uploaded successfully.")

            sha_256_hash = upload["sha_256_hash"]
            log_info(f"RevEng.AI | SHA-256 hash: {sha_256_hash}")
            
            # Convert symbols to a list of dictionaries with hex strings
            symbols = []
            log_info(f"RevEng.AI | Image Base: {bv.image_base:x}")
            for key, value in bv.symbols.items():
                if value[0].type == SymbolType.FunctionSymbol:
                    func = bv.get_function_at(value[0].address)
                    symbols.append({
                        "name": func.name,
                        "start": func.start,
                        "end": func.start + func.total_bytes,
                    })
                    log_info(f"RevEng.AI | Name: {key} | Start: {func.start:x} | End: {func.start + func.total_bytes:x} | Size: {func.total_bytes}")

            # Log all analysis parameters
            log_info("RevEng.AI | Analysis parameters:")
            log_info(f"RevEng.AI | - File path: {bv.file.filename}")
            log_info(f"RevEng.AI | - Binary scope: {'PRIVATE' if options['is_private'] else 'PUBLIC'}")
            log_info(f"RevEng.AI | - Debug info path: {options.get('debug_info', None)}")
            log_info(f"RevEng.AI | - Model name: {options['model']}")
            log_info(f"RevEng.AI | - Tags: {options.get('tags', [])}")
            log_info(f"RevEng.AI | - Number of symbols: {len(symbols)}")
                
            analysis = RE_analyse(
                fpath=bv.file.filename,
                binary_scope= "PRIVATE" if options["is_private"] else "PUBLIC",
                model_name=options["model"],
                tags=options["tags"],
                symbols=symbols
            ).json()

            log_info(f"RevEng.AI | Analysis response: {analysis}")

            binary_id = analysis["binary_id"]
            analysis_info = RE_analysis_lookup(str(binary_id)).json()
                
            log_info(f"RevEng.AI | Analysis info: {analysis_info}")
            
            self.config.set_binary_id(binary_id)
            self.config.set_analysis_id(analysis_info["analysis_id"])
                
            return True
            
        except Exception as e:
            log_error(f"RevEng.AI | Failed to upload binary: {str(e)}")
            return False 