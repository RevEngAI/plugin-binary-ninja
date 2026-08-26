import inspect
from importlib.metadata import version

import pytest
import revengai
from revengai.models.analysis_function_entry import AnalysisFunctionEntry
from revengai.models.analysis_function_mapping import AnalysisFunctionMapping
from revengai.models.basic import Basic
from revengai.models.binary_search_result import BinarySearchResult
from revengai.models.comments_data import CommentsData
from revengai.models.create_ai_decomp_output_body import CreateAIDecompOutputBody
from revengai.models.decompilation_data import DecompilationData
from revengai.models.function_mapping import FunctionMapping
from revengai.models.function_match import FunctionMatch
from revengai.models.inline_comment import InlineComment
from revengai.models.matched_function import MatchedFunction
from revengai.models.rename_input_body import RenameInputBody
from revengai.models.status_output import StatusOutput
from revengai.models.summary_data import SummaryData
from revengai.models.task_status import TaskStatus
from revengai.models.workflow_progress import WorkflowProgress

PINNED = (4, 4, 0)

API_METHODS = {
    "ConfigApi": ["get_config"],
    "SearchApi": ["search_binaries"],
    "CollectionsApi": ["v3_list_collections"],
    "AnalysesCoreApi": [
        "upload_file",
        "create_analysis",
        "get_analysis_status",
        "get_analysis_basic_info",
        "get_analysis_function_map",
        "start_analysis_function_matching",
        "get_analysis_function_matching_status",
        "get_analysis_function_matches",
    ],
    "ModelsApi": ["get_models"],
    "FunctionsCoreApi": [
        "list_analysis_functions",
        "start_functions_matching",
        "get_functions_matching_status",
        "get_functions_matches",
    ],
    "FunctionsRenamingHistoryApi": ["rename_function"],
    "DataTypesApi": ["v3_list_function_signatures"],
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


def test_v3_list_collections_accepts_plugin_kwargs():
    assert {
        "search_term",
        "filters",
        "limit",
        "offset",
    } <= _params(revengai.CollectionsApi.v3_list_collections)


def test_collection_list_item_has_plugin_fields():
    from revengai.models.collection_list_item_body import CollectionListItemBody

    assert {
        "collection_id",
        "collection_name",
        "collection_owner",
        "collection_scope",
        "updated_at",
    } <= set(CollectionListItemBody.model_fields)


def test_upload_file_accepts_plugin_kwargs():
    assert {"upload_file_type", "file", "force_overwrite"} <= _params(
        revengai.AnalysesCoreApi.upload_file
    )


def test_create_analysis_accepts_request_kwarg():
    assert "analysis_create_request" in _params(
        revengai.AnalysesCoreApi.create_analysis
    )


def test_analysis_id_methods_accept_analysis_id():
    for method in (
        "get_analysis_status",
        "get_analysis_basic_info",
        "get_analysis_function_map",
    ):
        assert "analysis_id" in _params(getattr(revengai.AnalysesCoreApi, method))


def test_list_analysis_functions_accepts_analysis_id():
    assert "analysis_id" in _params(revengai.FunctionsCoreApi.list_analysis_functions)


def test_list_analysis_functions_output_has_no_envelope():
    assert {"functions"} <= set(revengai.ListAnalysisFunctionsOutputBody.model_fields)


def test_start_functions_matching_accepts_request_kwargs():
    params = _params(revengai.FunctionsCoreApi.start_functions_matching)
    assert "start_matching_for_functions_input_body" in params


def test_functions_matching_status_and_results_accept_function_ids():
    for method in ("get_functions_matching_status", "get_functions_matches"):
        assert "function_ids" in _params(getattr(revengai.FunctionsCoreApi, method))


def test_start_analysis_function_matching_accepts_request_kwargs():
    params = _params(revengai.AnalysesCoreApi.start_analysis_function_matching)
    assert {"analysis_id", "start_matching_for_analysis_input_body"} <= params


def test_analysis_matching_status_and_results_accept_analysis_id():
    for method in (
        "get_analysis_function_matching_status",
        "get_analysis_function_matches",
    ):
        assert "analysis_id" in _params(getattr(revengai.AnalysesCoreApi, method))


def test_rename_function_accepts_kwargs():
    params = _params(revengai.FunctionsRenamingHistoryApi.rename_function)
    assert {"function_id", "rename_input_body"} <= params


def test_ai_decompilation_methods_accept_function_id():
    for method in (
        "get_ai_decompilation_status",
        "create_ai_decompilation",
        "get_ai_decompilation",
        "get_ai_decompilation_summary",
        "get_ai_decompilation_inline_comments",
    ):
        assert "function_id" in _params(
            getattr(revengai.FunctionsAIDecompilationApi, method)
        )


def test_analysis_create_request_has_plugin_fields():
    assert {
        "filename",
        "sha_256_hash",
        "debug_hash",
        "tags",
        "analysis_scope",
        "symbols",
    } <= set(revengai.AnalysisCreateRequest.model_fields)


def test_match_filters_has_plugin_fields():
    assert {"collection_ids", "binary_ids", "debug_types"} <= set(
        revengai.MatchFilters.model_fields
    )


def test_rename_input_body_has_plugin_fields():
    assert {"new_name", "new_mangled_name"} <= set(RenameInputBody.model_fields)


def test_tag_has_name_field():
    assert "name" in revengai.Tag.model_fields


def test_analysis_scope_has_plugin_members():
    assert {"PRIVATE", "PUBLIC"} <= set(revengai.AnalysisScope.__members__)


def test_upload_file_type_has_plugin_members():
    assert {"BINARY", "DEBUG"} <= set(revengai.UploadFileType.__members__)


def test_task_status_covers_plugin_state_machine():
    assert {"UNINITIALISED", "COMPLETED", "FAILED"} <= set(TaskStatus.__members__)


def test_status_input_covers_analysis_state_machine():
    assert {"UPLOADED", "QUEUED", "PROCESSING", "COMPLETE", "ERROR"} <= set(
        revengai.StatusInput.__members__
    )


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
        AnalysisFunctionEntry.model_fields
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


def test_start_matching_input_bodies_have_per_function_count_field():
    for model in (
        revengai.StartMatchingForAnalysisInputBody,
        revengai.StartMatchingForFunctionsInputBody,
    ):
        assert "results_per_function" in model.model_fields
        assert "result_per_function" not in model.model_fields


def test_start_matching_for_functions_input_has_function_ids_field():
    assert "function_ids" in revengai.StartMatchingForFunctionsInputBody.model_fields


def test_get_matches_output_has_status_and_matches():
    assert {"status", "matches"} <= set(revengai.GetMatchesOutputBody.model_fields)


def test_get_matches_status_output_has_progress_fields():
    assert {"status", "step", "step_index", "steps_total", "messages"} <= set(
        revengai.GetMatchesStatusOutputBody.model_fields
    )


def test_match_functions_request_shape_is_honored():
    filters = revengai.MatchFilters.from_dict(
        {"collection_ids": [1], "binary_ids": [2]}
    )
    request = revengai.StartMatchingForAnalysisInputBody.from_dict(
        {
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
    filters = revengai.MatchFilters.from_dict(
        {"collection_ids": [1], "binary_ids": [2]}
    )
    request = revengai.StartMatchingForFunctionsInputBody.from_dict(
        {
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


def test_v3_list_function_signatures_accepts_plugin_kwargs():
    assert {"function_ids", "include_data_types"} <= _params(
        revengai.DataTypesApi.v3_list_function_signatures
    )


def test_batch_function_signature_entry_has_plugin_fields():
    from revengai.models.batch_function_signature_entry import (
        BatchFunctionSignatureEntry,
    )

    assert {
        "function_id",
        "function_name",
        "has_signature",
        "calling_convention",
        "parameters",
        "return_data_type_id",
        "source_function_id",
        "source_type",
    } <= set(BatchFunctionSignatureEntry.model_fields)


def test_list_function_signatures_output_has_items_and_data_types_catalogue():
    from revengai.models.list_function_signatures_output_body import (
        ListFunctionSignaturesOutputBody,
    )

    assert {"items", "data_types"} <= set(ListFunctionSignaturesOutputBody.model_fields)


def test_analysis_data_types_group_has_analysis_id_and_items():
    from revengai.models.analysis_data_types_group import AnalysisDataTypesGroup

    assert {"analysis_id", "items"} <= set(AnalysisDataTypesGroup.model_fields)
