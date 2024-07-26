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
    # 'preamble': "Given the dialogue between a user and a helpful assistant, along with relevant search results, craft a final response for the assistant in Japanese. The response should:\n\nUtilize all pertinent information from the search results.\nAvoid introducing any new information not found in the search results.\nQuote directly from the search results whenever possible, using the exact same wording.\nNot exceed 20 sentences in total length.\nBe formatted as a bulleted list, with each item beginning with a \"🌳 \" symbol and end with \\n sequence.\nBe written in a casual, easy-to-understand style that aligns with Google's web-based Japanese language.\nEmphasize key points using【】.\nInclude hyperlinks to company websites when company names are mentioned.\nMust put \\n character at the end of every sentences."
    'preamble': "ユーザーと親切なアシスタント間の対話、および関連する検索結果を踏まえて、アシスタントの最終的な回答をNotebookLM風の日本語で作成してください。回答は以下の条件を満たす必要があります。\n検索結果から関連性の高い情報を最大3件活用し、**「ソースによると、〇〇〇について、下記企業の事例が挙げられます。」**という形で回答を始める。\n検索結果にない新しい情報は一切導入しない。\n可能な限り検索結果から直接引用し、全く同じ表現を使用する。引用部分は「」（鉤括弧）で囲み、文末に出典を明記する。\n各項目は箇条書き形式で記述する。各項目の先頭に「-」記号を付けてください。\nGoogleのウェブベースの日本語に沿った、カジュアルでわかりやすい文体を使用する。\n重要なポイントは太字で強調する。\n企業名が言及された場合は、企業ウェブサイトへのハイパーリンクを含める。\n専門用語については、可能な限り一般的な言葉で言い換えるか、括弧内に簡潔な説明を加える。\n可能な限り、具体的な使用例や事例、数値データを含めて説明する。\n検索結果に含まれる情報の日付に注意し、最新の情報を優先して使用する。古い情報を使用する場合は、その旨を明記する（例：2023年7月時点の情報では...）。\n検索結果に複数の観点が含まれる場合は、それらを公平に扱い、バランスの取れた回答を心がける。\n回答の最後に、「質問の意図とずれている場合は、遠慮なく別の表現で質問してくださいね。」という一文を追加してください。\n個人情報や機密情報が含まれている可能性がある場合は、それらを慎重に扱い、必要に応じて一般化または匿名化する。\n出力にHTMLタグを含めない。\n各文末に改行コード(\\n)を挿入します。"
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
    client.collection("Queries").document().set(data)


def clean_summary_text(summary_text: str) -> str:
    """太字や行頭のドットのマークアップを解釈する"""
    output = []
    try:
        # 。と-の間のスペースを除去する
        tmp = re.sub(r'。\s+?\-', '。-', summary_text)
        # <br> タグを除去する
        tmp = tmp.replace('<br>', '')
        # (,,,,) を除去する
        tmp = re.sub(r'\(,+\)', '', tmp)
        # 。と- が並んでいたら改行コードを挿入する
        lines = tmp.replace('。-', '。\n-').split('\n')
        for s in lines:
            se = s.strip()
            if s.startswith("- "):
                se = '・' + se[2:]
            ss = se.split('**')
            for i, _ in enumerate(ss):
                if i % 2 == 1:
                    output.append('[BOLD]{}'.format(_))
                else:
                    output.append(_)
            output.append('\n')
    except Exception as e:
        print('ERROR:{}'.format(str(e)))
    return output


def clean_snippet_text(snippet_text: str) -> list:
    """snippet テキストをきれいにする
    1) &nbsp; -> 半角スペース(削除)
    2) <b>AAA</b> の部分を太字にするための処理
    - <b>,</b>のいずれかで split するので、奇数配列目を太字にする処理を入れる
    太字がある場合、list の長さが 2 以上になるので、spans=[] で接続する
    """
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
                version="gemini-1.5-flash-001/answer_gen/v1",
            ),
            use_semantic_chunks=True,
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
    # print(response)
    return response
