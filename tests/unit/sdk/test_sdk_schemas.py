import inspect
from importlib.metadata import version

import pytest
import revengai
from revengai.models.analysis_function_mapping import AnalysisFunctionMapping
from revengai.models.app_api_rest_v2_functions_types_function import (
    AppApiRestV2FunctionsTypesFunction,
)
from revengai.models.auto_unstrip_response import AutoUnstripResponse
from revengai.models.basic import Basic
from revengai.models.binary_search_result import BinarySearchResult
from revengai.models.comments_data import CommentsData
from revengai.models.create_ai_decomp_output_body import CreateAIDecompOutputBody
from revengai.models.decompilation_data import DecompilationData
from revengai.models.function_mapping import FunctionMapping
from revengai.models.function_match import FunctionMatch
from revengai.models.inline_comment import InlineComment
from revengai.models.matched_function import MatchedFunction
from revengai.models.matched_function_suggestion import MatchedFunctionSuggestion
from revengai.models.status_output import StatusOutput
from revengai.models.summary_data import SummaryData
from revengai.models.task_status import TaskStatus
from revengai.models.workflow_progress import WorkflowProgress

PINNED = (3, 96, 3)

API_METHODS = {
    "ConfigApi": ["get_config"],
    "SearchApi": ["search_binaries", "search_collections"],
    "AnalysesCoreApi": [
        "upload_file",
        "create_analysis",
        "get_analysis_status",
        "get_analysis_basic_info",
        "get_analysis_function_map",
    ],
    "ModelsApi": ["get_models"],
    "AnalysesResultsMetadataApi": ["get_functions_list"],
    "FunctionsCoreApi": ["analysis_function_matching", "auto_unstrip"],
    "FunctionsRenamingHistoryApi": ["rename_function_id"],
    "FunctionsDataTypesApi": [
        "generate_function_data_types_for_functions",
        "list_function_data_types_for_functions",
    ],
    "FunctionsAIDecompilationApi": [
        "get_ai_decompilation_status",
        "create_ai_decompilation",
        "get_ai_decompilation",
        "get_ai_decompilation_summary",
        "get_ai_decompilation_inline_comments",
        "regenerate_ai_decompilation_summary",
        "regenerate_ai_decompilation_inline_comments",
    ],
}


def _version_tuple(value):
    return tuple(int(part) for part in value.split(".")[:3])


def _params(func):
    return set(inspect.signature(func).parameters)


def test_installed_revengai_is_at_least_pinned():
    assert _version_tuple(version("revengai")) >= PINNED


@pytest.mark.parametrize("api_name", list(API_METHODS))
def test_api_class_exists(api_name):
    assert getattr(revengai, api_name, None) is not None


@pytest.mark.parametrize(
    "api_name,method",
    [(api, method) for api, methods in API_METHODS.items() for method in methods],
)
def test_api_method_exists(api_name, method):
    api = getattr(revengai, api_name)
    assert callable(getattr(api, method, None)), f"{api_name}.{method}"


def test_search_binaries_accepts_plugin_kwargs():
    assert {
        "partial_sha256",
        "user_files_only",
        "partial_name",
        "tags",
        "model_name",
        "page",
        "page_size",
    } <= _params(revengai.SearchApi.search_binaries)


def test_search_collections_accepts_plugin_kwargs():
    assert {
        "partial_collection_name",
        "partial_binary_name",
        "partial_binary_sha256",
        "tags",
        "model_name",
        "page",
        "page_size",
    } <= _params(revengai.SearchApi.search_collections)


def test_upload_file_accepts_plugin_kwargs():
    assert {"upload_file_type", "file", "force_overwrite"} <= _params(
        revengai.AnalysesCoreApi.upload_file
    )


def test_create_analysis_accepts_request_kwarg():
    assert "analysis_create_request" in _params(revengai.AnalysesCoreApi.create_analysis)


def test_analysis_id_methods_accept_analysis_id():
    for method in ("get_analysis_status", "get_analysis_basic_info", "get_analysis_function_map"):
        assert "analysis_id" in _params(getattr(revengai.AnalysesCoreApi, method))


def test_function_matching_accepts_request_kwargs():
    params = _params(revengai.FunctionsCoreApi.analysis_function_matching)
    assert {"analysis_id", "analysis_function_matching_request"} <= params


def test_auto_unstrip_accepts_request_kwargs():
    params = _params(revengai.FunctionsCoreApi.auto_unstrip)
    assert {"analysis_id", "auto_unstrip_request"} <= params


def test_rename_function_id_accepts_kwargs():
    params = _params(revengai.FunctionsRenamingHistoryApi.rename_function_id)
    assert {"function_id", "function_rename"} <= params


def test_ai_decompilation_methods_accept_function_id():
    for method in (
        "get_ai_decompilation_status",
        "create_ai_decompilation",
        "get_ai_decompilation",
        "get_ai_decompilation_summary",
        "get_ai_decompilation_inline_comments",
    ):
        assert "function_id" in _params(getattr(revengai.FunctionsAIDecompilationApi, method))


def test_analysis_create_request_has_plugin_fields():
    assert {
        "filename",
        "sha_256_hash",
        "debug_hash",
        "tags",
        "analysis_scope",
        "symbols",
    } <= set(revengai.AnalysisCreateRequest.model_fields)


def test_function_matching_filters_has_plugin_fields():
    assert {"collection_ids", "binary_ids"} <= set(
        revengai.FunctionMatchingFilters.model_fields
    )


def test_function_rename_has_plugin_fields():
    assert {"new_name", "new_mangled_name"} <= set(revengai.FunctionRename.model_fields)


def test_tag_has_name_field():
    assert "name" in revengai.Tag.model_fields


def test_analysis_scope_has_plugin_members():
    assert {"PRIVATE", "PUBLIC"} <= set(revengai.AnalysisScope.__members__)


def test_upload_file_type_has_plugin_members():
    assert {"BINARY", "DEBUG"} <= set(revengai.UploadFileType.__members__)


def test_task_status_covers_plugin_state_machine():
    assert {"UNINITIALISED", "COMPLETED", "FAILED"} <= set(TaskStatus.__members__)


def test_binary_search_result_has_plugin_fields():
    assert {
        "binary_id",
        "analysis_id",
        "binary_name",
        "sha_256_hash",
        "model_id",
        "model_name",
        "owned_by",
        "created_at",
    } <= set(BinarySearchResult.model_fields)


def test_status_output_exposes_analysis_status():
    assert "analysis_status" in StatusOutput.model_fields


def test_basic_exposes_base_address_and_model_id():
    assert {"base_address", "model_id"} <= set(Basic.model_fields)


def test_analysis_function_mapping_exposes_function_maps():
    assert "function_maps" in AnalysisFunctionMapping.model_fields


def test_function_mapping_has_plugin_fields():
    assert {"function_map", "inverse_function_map", "name_map"} <= set(
        FunctionMapping.model_fields
    )


def test_analysis_functions_item_has_plugin_fields():
    assert {"function_id", "function_vaddr", "function_name"} <= set(
        AppApiRestV2FunctionsTypesFunction.model_fields
    )


def test_function_match_has_plugin_fields():
    assert {"function_id", "matched_functions"} <= set(FunctionMatch.model_fields)


def test_matched_function_has_plugin_fields():
    assert {
        "function_id",
        "function_vaddr",
        "function_name",
        "mangled_name",
        "sha_256_hash",
        "binary_name",
        "similarity",
        "confidence",
    } <= set(MatchedFunction.model_fields)


def test_matched_function_suggestion_has_plugin_fields():
    assert {
        "function_id",
        "function_vaddr",
        "suggested_demangled_name",
        "suggested_name",
    } <= set(MatchedFunctionSuggestion.model_fields)


def test_auto_unstrip_response_has_status_and_matches():
    fields = set(AutoUnstripResponse.model_fields)
    assert {"status", "matches", "error_message"} <= fields


def test_workflow_progress_exposes_status():
    assert "status" in WorkflowProgress.model_fields


def test_create_ai_decomp_output_body_exposes_status():
    assert "status" in CreateAIDecompOutputBody.model_fields


def test_decompilation_data_has_plugin_fields():
    assert {"status", "decompilation"} <= set(DecompilationData.model_fields)


def test_summary_data_has_plugin_fields():
    assert {"task_status", "ai_summary"} <= set(SummaryData.model_fields)


def test_comments_data_has_plugin_fields():
    assert {"task_status", "inline_comments"} <= set(CommentsData.model_fields)


def test_inline_comment_has_plugin_fields():
    assert {"line", "comment"} <= set(InlineComment.model_fields)


def test_matching_request_per_function_count_field_name():
    assert "results_per_function" in revengai.AnalysisFunctionMatchingRequest.model_fields
    assert "result_per_function" not in revengai.AnalysisFunctionMatchingRequest.model_fields


def test_matching_request_from_dict_honors_results_per_function():
    request = revengai.AnalysisFunctionMatchingRequest.from_dict(
        {
            "min_similarity": 0,
            "filters": {"collection_ids": [], "binary_ids": []},
            "results_per_function": 7,
        }
    )
    assert request.to_dict().get("results_per_function") == 7


def test_function_matching_request_has_function_ids_field():
    assert "function_ids" in revengai.FunctionMatchingRequest.model_fields


def test_match_functions_request_shape_is_honored():
    filters = revengai.FunctionMatchingFilters.from_dict(
        {"collection_ids": [1], "binary_ids": [2]}
    )
    request = revengai.AnalysisFunctionMatchingRequest.from_dict(
        {
            "function_ids": [1, 2, 3],
            "min_similarity": 0,
            "filters": filters,
            "results_per_function": 1,
        }
    )
    payload = request.to_dict()
    assert payload["results_per_function"] == 1
    assert payload["filters"]["collection_ids"] == [1]
    assert payload["filters"]["binary_ids"] == [2]


def test_match_current_function_request_shape_is_honored():
    filters = revengai.FunctionMatchingFilters.from_dict(
        {"collection_ids": [1], "binary_ids": [2]}
    )
    request = revengai.FunctionMatchingRequest.from_dict(
        {
            "model_id": 7,
            "function_ids": [42],
            "filters": filters,
            "results_per_function": 20,
            "min_similarity": 90,
        }
    )
    payload = request.to_dict()
    assert payload["results_per_function"] == 20
    assert payload["function_ids"] == [42]
    assert payload["filters"]["collection_ids"] == [1]
    assert payload["filters"]["binary_ids"] == [2]
