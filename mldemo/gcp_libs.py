import html
import os
import re
import time
from typing import List

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import firestore

client = firestore.Client(project=os.environ['FIRESTORE_PROJECT_ID'])

# プロジェクトID / ロケーション / 検索エンジンの ID を指定する
gcp_settings = dict(
    project_id=os.environ['PROJECT_ID'],
    location=os.environ['VERTEX_AI_SEARCH_LOCATION'],
    engine_id=os.environ['VERTEX_AI_SEARCH_ENGINE_ID'],
)


def get_histories(count: int = 10) -> [str]:
    # クエリの履歴を取得する
    # isPickUp: true - 優先的に取得する
    # isUserQuery: true - ユーザのクエリ（直近 N 件）
    picked_ups = []
    user_queries = []

    query = client.collection("Queries").where(
        filter=firestore.FieldFilter("isPickUp", "==", True)
    ).limit(1000)
    for entry in query.stream():
        picked_ups.append(entry.to_dict())
        count -= 1

    query = client.collection("Queries").order_by(
        "updatedAt", direction=firestore.Query.DESCENDING
    ).limit(1000)
    for entry in query.stream():
        dict_ = entry.to_dict()
        if dict_.get('isPickUp'):
            continue
        user_queries.append(dict_)
        count -= 1
        if count == 0:
            break
    return picked_ups + user_queries


def add_or_update_entry(search_query: str):
    col = client.collection("Queries")
    query = col.where(
        filter=firestore.FieldFilter("query", "==", search_query)
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
    # TODO: base 64 して入れたほうが確実なので後でやる
    data = {
        'isUserQuery': True,
        'query': search_query,
        'createdAt': int(time.time()),
        'updatedAt': int(time.time()),
        'count': 0,
    }
    print(data)
    client.collection("Queries").document().set(data)


def clean_summary_text(summary_text: str) -> str:
    # [1], [1,2] のような参照リンクを削除する（ひとまず）
    # ex: あああ[1] いいい [5] ううう -> あああ いいい うううう
    return ''.join(re.split(r'\[[0-9, ]+\]', summary_text))


def clean_snippet_text(snippet_text: str) -> list:
    # snippet テキストをきれいにする
    # 1) &nbsp; -> 半角スペース
    # 2) <b>AAA</b> の部分を太字にするための処理
    # - <b>,</b>のいずれかで split するので、奇数配列目を太字にする処理を入れる
    # 太字がある場合、list の長さが 2 以上になるので、spans=[] で接続する
    tmp = html.unescape(snippet_text)
    tmp = tmp.replace("\xa0", " ")
    # m = re.findall(r'<b>.+?<\/b>', tmp)
    return re.split(r'<\/*b>', tmp)


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
        # summary_references=list(search_response.summary.summary_with_metadata.references),
        total_size=search_response.total_size,
        attribution_token=search_response.attribution_token,
        next_page_token=search_response.next_page_token,
    )

    # 検索結果
    # try:
    for r in search_response.results:
        struct_data = r.document.struct_data
        if not struct_data:
            title = r.document.derived_struct_data.get(
                'link', 'https://example.com').split('/')[-1].split('.')[0]
        else:
            title = struct_data.get('title')

        response['result'].append(
            dict(
                # タイトル
                # title=r.document.struct_data.get('title', 'No title'),
                title=title,
                # リンク先
                link=r.document.derived_struct_data.get('link', 'https://example.com'),
                # スニペット文字列
                snippet=r.document.derived_struct_data["snippets"][0]["snippet"],
                # スニペットを取得できたかどうか
                snippet_status=r.document.derived_struct_data["snippets"][0]["snippet_status"],
            )
        )

    # except Exception as e:
    #     # 何らかのエラーが起きたら何も返さない
    #     print(e)
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
            summary_result_count=3,
            include_citations=True,
            ignore_adversarial_query=True,
            ignore_non_summary_seeking_query=True,
            model_prompt_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
                # preamble=preamble,
                preamble="Given the dialogue between a user and a helpful assistant, along with relevant search results, craft a final response for the assistant in Japanese. The response should:\n\nUtilize all pertinent information from the search results.\nAvoid introducing any new information not found in the search results.\nQuote directly from the search results whenever possible, using the exact same wording.\nNot exceed 20 sentences in total length.\nBe formatted as a bulleted list, with each item beginning with a \"🌳 \" symbol.\nBe written in a casual, easy-to-understand style that aligns with Google's web-based Japanese language.\nEmphasize key points using bold text.\nInclude hyperlinks to company websites when company names are mentioned.",
            ),
            language_code="ja",
            # extractive_content_spec=
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
        page_size=5,
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
