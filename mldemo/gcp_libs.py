from typing import List

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine

# プロジェクトID / ロケーション / 検索エンジンの ID を指定する
gcp_settings = dict(
    project_id="automldemo4hisol",
    location="global", # Values: "global", "us", "eu"
    engine_id="1_1716775403001",
)


# memo
# r.results[0].document.derived_struct_data["title"]: タイトル
# r.results[0].document.derived_struct_data["link"]: ドキュメントのリンク
# r.results[0].document.derived_struct_data["snippets"][0]["snippet"]: スニペット（検索結果に出てくる文字列）
# r.results[0].document.derived_struct_data["snippets"][0]["snippet_status"]: スニペットを取得できたかどうか
# r.summary.summary_text: 要約のテキスト
# r.summary.summary_with_metadata.summary: 要約のテキスト（メタデータ込）
# r.summary.summary_with_metadata.references (要約の引用元, インデックスは0開始だけど要約のリンクは1開始なので注意)
# r.summary.summary_with_metadata.references[0].title
# r.summary.summary_with_metadata.references[0].document

def parse_result(
    search_response: List[discoveryengine.SearchResponse]
) -> dict:
    response = {
        'meta': {},
        'result': []
    }
    # サマリー、メタ情報
    response['meta'] = dict(
        summary=search_response.summary.summary_text,
        total_size=search_response.total_size,
        attribution_token=search_response.attribution_token,
        next_page_token=search_response.next_page_token,
    )

    # 検索結果
    for r in search_response.results:
        response['result'].append(
            dict(
                # タイトル（PDF名)
                title=r.document.derived_struct_data['title'],
                # リンク先
                link=r.document.derived_struct_data['link'],
                # スニペット文字列
                snippet=r.document.derived_struct_data["snippets"][0]["snippet"],
                # スニペットを取得できたかどうか
                snippet_status=r.document.derived_struct_data["snippets"][0]["snippet_status"],
            )
        )
    return response


def exec_search(
    search_query: str,
) -> List[discoveryengine.SearchResponse]:
    # needed valuables
    project_id = gcp_settings['project_id']
    location = gcp_settings['location']
    engine_id = gcp_settings['engine_id']

    #  For more information, refer to:
    # https://cloud.google.com/generative-ai-app-builder/docs/locations#specify_a_multi-region_for_your_data_store
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    # Create a client
    client = discoveryengine.SearchServiceClient(client_options=client_options)

    # The full resource name of the search app serving config
    serving_config = f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/servingConfigs/default_config"

    # Optional: Configuration options for search
    # Refer to the `ContentSearchSpec` reference for all supported fields:
    # https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchRequest.ContentSearchSpec
    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        # For information about snippets, refer to:
        # https://cloud.google.com/generative-ai-app-builder/docs/snippets
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True
        ),
        # For information about search summaries, refer to:
        # https://cloud.google.com/generative-ai-app-builder/docs/get-search-summaries
        summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
            # サマリーで利用する結果の数
            summary_result_count=5,
            include_citations=True,
            ignore_adversarial_query=True,
            ignore_non_summary_seeking_query=True,
            model_prompt_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
                # preamble="please show the answer format in an ordered list"
                # preamble="Simple English"
                preamble="YOUR_CUSTOM_PROMPT"
                # preamble="詳細に説明して"
                # preamble="小学生でもわかりやすいように説明して"
            ),
            model_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                version="stable",
            ),
        ),
    )

    # Refer to the `SearchRequest` reference for all supported fields:
    # https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchRequest
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=search_query,
        page_size=10,
        content_search_spec=content_search_spec,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
        ),
    )

    response = client.search(request)
    # print(response)

    return response