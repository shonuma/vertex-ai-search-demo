import html
import os
import re
import time
from base64 import b64encode
from typing import List

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import firestore

client = firestore.Client(project=os.environ['FIRESTORE_PROJECT_ID'])

# プロジェクトID / ロケーション / 検索エンジンの ID を指定する
global_gcp_settings = dict(
    project_id=os.environ['PROJECT_ID'],
    location=os.environ['VERTEX_AI_SEARCH_LOCATION'],
    engine_id=os.environ['VERTEX_AI_SEARCH_ENGINE_ID'],
)

# 検索結果に表示しない PDF のタイトル
global_black_list = [
    '「事例の森」FAQ資料',
]

# vertex_ai_search の settings
global_search_settings = {
    'query_store_limit': 1000,
    'retreive_count': 10,
    'display_count': 5,
    'summary_result_count': 3,
    'preamble': "Given the dialogue between a user and a helpful assistant, along with relevant search results, craft a final response for the assistant in Japanese. The response should:\n\nUtilize all pertinent information from the search results.\nAvoid introducing any new information not found in the search results.\nQuote directly from the search results whenever possible, using the exact same wording.\nNot exceed 20 sentences in total length.\nBe formatted as a bulleted list, with each item beginning with a \"🌳 \" symbol and end with \\n sequence.\nBe written in a casual, easy-to-understand style that aligns with Google's web-based Japanese language.\nEmphasize key points using【】.\nInclude hyperlinks to company websites when company names are mentioned.\nMust put \\n character at the end of every sentences."
}


def get_histories(count: int = 10) -> [str]:
    # クエリの履歴を取得する
    # isPickUp: true - 優先的に取得する
    # isUserQuery: true - ユーザのクエリ（直近 N 件）
    picked_ups = []
    user_queries = []

    query = client.collection("Queries").where(
        filter=firestore.FieldFilter("isPickUp", "==", True)
    ).limit(global_search_settings['query_store_limit'])
    for entry in query.stream():
        picked_ups.append(entry.to_dict())
        count -= 1

    query = client.collection("Queries").order_by(
        "updatedAt", direction=firestore.Query.DESCENDING
    ).limit(global_search_settings['query_store_limit'])

    for entry in query.stream():
        dict_ = entry.to_dict()
        if dict_.get('isPickUp'):
            continue
        # 同じクエリが 2 件表示されないようにする
        if dict_.get('query') in [_['query'] for _ in picked_ups]:
            continue
        user_queries.append(dict_)
        count -= 1
        if count == 0:
            break
    return picked_ups + user_queries


def add_or_update_entry(search_query: str):
    col = client.collection("Queries")
    b64_encoded_query = b64encode(search_query.encode()).decode()
    query = col.where(
        filter=firestore.FieldFilter("base64dQuery", "==", b64_encoded_query)
    )
    id = None
    for entry in query.stream():
        id = entry.id
    # すでにあるクエリなら更新する
    if id:
        # エントリが存在していれば、1 回検索されたということ
        dict_ = col.document(id).get().to_dict()
        count = dict_.get('count', 1)
        count += 1
        col.document(id).update(
            dict(
                count=count,
                updatedAt=int(time.time()),
            )
        )
        return
    # クエリをストレージに格納する
    data = {
        'isUserQuery': True,
        'query': search_query,
        'base64dQuery': b64encode(search_query.encode()).decode(),
        'createdAt': int(time.time()),
        'updatedAt': int(time.time()),
        'count': 0,
    }
    print(data)
    client.collection("Queries").document().set(data)


def clean_summary_text(summary_text: str) -> str:
    return summary_text


def clean_snippet_text(snippet_text: str) -> list:
    # snippet テキストをきれいにする
    # 1) &nbsp; -> 半角スペース(削除)
    # 2) <b>AAA</b> の部分を太字にするための処理
    # - <b>,</b>のいずれかで split するので、奇数配列目を太字にする処理を入れる
    # 太字がある場合、list の長さが 2 以上になるので、spans=[] で接続する
    tmp = html.unescape(snippet_text)
    tmp = tmp.replace("\xa0", "")
    # m = re.findall(r'<b>.+?<\/b>', tmp)
    return re.split(r'<\/*b>', tmp)


def parse_result(
    search_response: List[discoveryengine.SearchResponse],
    display_count=global_search_settings['display_count'],
) -> dict:
    response = {
        'meta': {},
        'result': []
    }
    # サマリー、メタ情報
    response['meta'] = dict(
        summary=search_response.summary.summary_text,
        # summary_references=list(search_response.summary.summary_with_metadata.references),
        total_size=search_response.total_size,
        attribution_token=search_response.attribution_token,
        next_page_token=search_response.next_page_token,
    )

    # 検索結果
    i = 0
    for r in search_response.results:
        if i == display_count:
            break
        struct_data = r.document.struct_data
        if not struct_data:
            title = r.document.derived_struct_data.get(
                'link', 'https://example.com').split('/')[-1].split('.')[0]
        else:
            title = struct_data.get('title')
        # global_black_list に登録された PDF の場合は検索から除外する
        if title in global_black_list:
            continue

        response['result'].append(
            dict(
                # タイトル
                # title=r.document.struct_data.get('title', 'No title'),
                title=title,
                # リンク先
                link=r.document.derived_struct_data.get('link', 'https://example.com'),
                # 抽出
                extractive_segment=r.document.derived_struct_data["extractive_segments"][0]["content"],
                # スニペット文字列
                snippet=r.document.derived_struct_data["snippets"][0]["snippet"],
                # スニペットを取得できたかどうか
                snippet_status=r.document.derived_struct_data["snippets"][0]["snippet_status"],
            )
        )
        i += 1

    return response


def exec_search(
    search_query: str,
) -> List[discoveryengine.SearchResponse]:
    # needed valuables
    project_id = global_gcp_settings['project_id']
    location = global_gcp_settings['location']
    engine_id = global_gcp_settings['engine_id']

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
        extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
            max_extractive_segment_count=1,
            max_extractive_answer_count=1,
        ),
        # For information about search summaries, refer to:
        # https://cloud.google.com/generative-ai-app-builder/docs/get-search-summaries
        summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
            # サマリーで利用する結果の数
            summary_result_count=global_search_settings['summary_result_count'],
            include_citations=True,
            ignore_adversarial_query=True,
            ignore_non_summary_seeking_query=True,
            model_prompt_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
                # preamble="Given the dialogue between a user and a helpful assistant, along with relevant search results, craft a final response for the assistant in Japanese. The response should:\n\nUtilize all pertinent information from the search results.\nAvoid introducing any new information not found in the search results.\nQuote directly from the search results whenever possible, using the exact same wording.\nNot exceed 20 sentences in total length.\nBe formatted as a bulleted list, with each item beginning with a \"🌳 \" symbol.\nBe written in a casual, easy-to-understand style that aligns with Google's web-based Japanese language.\nEmphasize key points using bold text.\nInclude hyperlinks to company websites when company names are mentioned.",
                preamble=global_search_settings['preamble'],
            ),
            language_code="ja",
            model_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                # version="stable",
                version="preview",
            ),
        ),
    )

    # Refer to the `SearchRequest` reference for all supported fields:
    # https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchRequest
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=search_query,
        # 検索結果の件数
        page_size=global_search_settings['retreive_count'],
        content_search_spec=content_search_spec,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
        ),
    )

    response = client.search(request)
    print(response)
    return response
