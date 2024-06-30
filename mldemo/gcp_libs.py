from typing import List
import re
import html
import os

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine


# プロジェクトID / ロケーション / 検索エンジンの ID を指定する
gcp_settings = dict(
    # project_id="automldemo4hisol",
    project_id=os.environ['PROJECT_ID'],
    location=os.environ['VERTEX_AI_SEARCH_LOCATION'],
    # location="global", # Values: "global", "us", "eu"
    engine_id=os.environ['VERTEX_AI_SEARCH_ENGINE_ID'],
    # engine_id="1_1716775403001",
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
    try:
        for r in search_response.results:
            title = r.document.struct_data['title']
            # title が存在しない場合、ファイル名を利用する
            if not title:
                title = r.document.derived_struct_data.get('link', 'https://example.com').split('/')[-1].split('.')[0]

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

    except Exception as e:
        # 何らかのエラーが起きたら何も返さない
        print(e)
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

    preamble = '''
Given the dialogue between a user and a helpful assistant, along with relevant search results, craft a final response for the assistant in Japanese. The response should:

Utilize all pertinent information from the search results.
Avoid introducing any new information not found in the search results.
Quote directly from the search results whenever possible, using the exact same wording.
Not exceed 20 sentences in total length.
Be formatted as a bulleted list, with each item beginning with a "🌳  " symbol and followed by a line break.
Be written in a casual, easy-to-understand style that aligns with Google's web-based Japanese language.
Emphasize key points using bold text.
Include hyperlinks to company websites when company names are mentioned.
'''[1:-1]

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
                preamble=preamble,
                # preamble="Simple English"
                # preamble="YOUR_CUSTOM_PROMPT"
                # preamble="詳細に説明して"
                # preamble="Please answer in English"
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
        # 検索結果の件数（ページング大変なので多めにしておくのが吉？）
        page_size=20,
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