from binaryninja import log_info, BinaryView
from revengai import AnalysesCoreApi, Configuration, FunctionMapping
from revengai import BaseResponseBasic, AnalysesCoreApi, ApiClient
from binaryninja import BinaryView, log_error, log_info, Symbol, SymbolType, Function

class AnalysisSyncService:

    sdk_config: Configuration

    def __init__(self, config):
        self.config = config
        self.sdk_config = config.api_config

    def _get_current_base_address(self, bv) -> int:
        return bv.start

    def _rebase_program(self, bv, base_address_delta: int) -> None:
        bv.rebase(bv.start + base_address_delta)

    def _fetch_basic_and_rebase(self, bv: BinaryView, analysis_id: int) -> BaseResponseBasic:
        """
        Fetches basic analysis information and rebases the program if necessary.
        """
        with ApiClient(self.sdk_config) as api_client:
            analyses_client = AnalysesCoreApi(api_client)
            analysis_details: BaseResponseBasic = analyses_client.get_analysis_basic_info(
                analysis_id=analysis_id
            )

            local_base_address: int = self._get_current_base_address(bv)

            if analysis_details.data and analysis_details.data.base_address is not None:
                remote_base_address: int = analysis_details.data.base_address

            if local_base_address != remote_base_address:
                    base_address_delta: int = remote_base_address - local_base_address
                    self._rebase_program(bv, base_address_delta)

    def _fetch_function_map(self, analysis_id: int) -> FunctionMapping:
        """
        Fetches the function map for the given analysis ID.
        """
        with ApiClient(self.sdk_config) as api_client:
            analyses_client = AnalysesCoreApi(api_client)

            function_map = analyses_client.get_analysis_function_map(
                analysis_id=analysis_id
            )
            func_map = function_map.data.function_maps
            return func_map

    def _match_functions(
        self,
        func_map: FunctionMapping,
        bv: BinaryView,
    ) -> None:
        function_map = func_map.function_map
        inverse_function_map = func_map.inverse_function_map

        log_info(
            f"RevEng.AI | Retrieved {len(function_map)} function mappings from analysis"
        )

        # Compute which IDA functions match the revengai analysis functions
        matched_functions = []
        unmatched_local_functions = []
        unmatched_remote_functions = []

        # Track local functions matched
        local_function_vaddrs_matched = set()

        for func in bv.functions:
            start_ea = func.start
            if str(start_ea) in inverse_function_map:
                new_name: str | None = func_map.name_map.get(str(start_ea), None)
                if new_name is None:
                    continue

                # Rename local function
                new_symbol = Symbol(SymbolType.FunctionSymbol, start_ea, new_name)
                bv.define_user_symbol(new_symbol)
                
                matched_functions.append(
                    (int(inverse_function_map[str(start_ea)]), start_ea)
                )
                local_function_vaddrs_matched.add(start_ea)
            else:
                unmatched_local_functions.append(start_ea)

        unmatched_portal_map = {}
        # Track remote functions not matched
        for func_id_str, func_vaddr in function_map.items():
            if int(func_vaddr) not in local_function_vaddrs_matched:
                unmatched_remote_functions.append((int(func_vaddr), int(func_id_str)))
                unmatched_portal_map[int(func_vaddr)] = int(func_id_str)

        log_info(f"RevEng.AI | Matched {len(matched_functions)} functions")
        log_info(
            f"RevEng.AI | {len(unmatched_local_functions)} local functions not matched"
        )
        log_info(
            f"RevEng.AI | {len(unmatched_remote_functions)} remote functions not matched"
        )

    def sync_analysis_data(
        self, analysis_id: int, bv: BinaryView
    ) -> None:
        """
        Syncs the analysis data until completion or failure.
        """
        response = self._fetch_function_map(analysis_id=analysis_id)

        function_mapping: FunctionMapping = response

        self._match_functions(func_map=function_mapping, bv=bv)

        self._fetch_basic_and_rebase(bv=bv, analysis_id=analysis_id)
