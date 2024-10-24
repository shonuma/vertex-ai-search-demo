import html
import json
import os
import re
import time
from base64 import b64encode
from typing import List

import requests
import vertexai
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import firestore
from vertexai.generative_models import GenerationConfig, GenerativeModel

from libs.gcp_token import get_token

client = firestore.Client(project=os.environ['FIRESTORE_PROJECT_ID'])
vertexai.init(project=os.environ['FIRESTORE_PROJECT_ID'], location='us-west1')


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
    'retreive_count': 30,
    'display_count': 20,
}


def get_histories_by_count(count: int = 100) -> []:
    """検索回数が多い順番に履歴を返す"""
    query = client.collection("Queries").order_by(
        "count", direction=firestore.Query.DESCENDING
    ).limit(global_search_settings['query_store_limit'])

    result = []
    for entry in query.stream():
        result.append(entry.to_dict())
        count -= 1
        if count == 0:
            break
    return result


def get_histories(count: int = 10) -> []:
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
    now_ = int(time.time())
    data = {
        'isUserQuery': True,
        'query': search_query,
        'base64dQuery': b64encode(search_query.encode()).decode(),
        'createdAt': now_,
        'updatedAt': now_,
        'count': 0,
    }
    client.collection("Queries").document().set(data)


def get_recommendations(summary_text: str) -> [str]:
    """Gemini からのおすすめワードを解釈する"""
    output = []
    try:
        lines = summary_text.split('\n')
        tmp = {}
        for i, s in enumerate(lines):
            if s.startswith('{"recommendations":'):
                tmp = json.loads(str(s))
                break
            else:
                continue
        output = tmp.get('recommendations') or []
    except Exception as e:
        print('ERROR in recommendations: {}'.format(e))
    return output


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
            # { から始まる行は除外する
            if s.startswith('{"recommendations":'):
                output.append('\n')
                continue
            # 何も無い行は除外する
            if s == '':
                continue
            ss = se.split('**')
            for i, _ in enumerate(ss):
                if i % 2 == 1:
                    output.append('[BOLD]{}'.format(_))
                else:
                    output.append(_)
            output.append('\n')
        # 最後のエントリの改行や空行を削除する
        while True:
            if output[-1] in ('\n', ''):
                output.pop(-1)
            else:
                break
        # print(output)
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


def exec_search_by_curl(
    search_query: str,
) -> dict:
    # needed valuables
    project_id = global_gcp_settings['project_id']
    location = global_gcp_settings['location']
    engine_id = global_gcp_settings['engine_id']

    # retreive token
    token = get_token()

    url = "https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{locations}/collections/default_collection/engines/{engine_id}/servingConfigs/default_search:search".format(
        project_id=project_id,
        locations=location,
        engine_id=engine_id,
    )

    headers = {
        "Authorization": "Bearer {token}".format(token=token),
        "Content-Type": "application/json"
    }
    data = {
        "query": search_query,
        "pageSize": global_search_settings['retreive_count'],
        "spellCorrectionSpec": {"mode": "AUTO"},
        "contentSearchSpec": {
            "snippetSpec": {"returnSnippet": True},
            "extractiveContentSpec": {"maxExtractiveAnswerCount": 1}
        }
    }

    response = requests.post(url, headers=headers, json=data)
    print(response.text)
    return json.loads(response.text)


def parse_result_by_curl(
    search_response: dict,
    display_count=global_search_settings['display_count'],
):
    response = {
        'meta': {},
        'result': []
    }

    # サマリー、メタ情報
    response['meta'] = dict(
        total_size=search_response.get('total_size', 0),
        attribution_token=search_response.get('attribution_token', ''),
        next_page_token=search_response.get('next_page_token', '')
    )

    # 検索結果
    i = 0
    for r in search_response['results']:
        if i == display_count:
            break
        source = ''
        struct_data = r['document'].get('structData')
        derived_struct_data = r['document']['derivedStructData']
        title, customer, link = ('', '', '')

        if not struct_data:
            # ドライブのデータ
            title = "Google Drive のデータ"
            customer = r['document']['derivedStructData']['title']
            link = r['document']['derivedStructData']['link']
            source = 'GOOGLE_DRIVE'
        else:
            # BigQuery からのデータ
            title = struct_data.get('title')
            customer = struct_data.get('customer_company_name_in_japanese')
            if not customer:
                customer = struct_data.get('customer_name')
            gs_url = derived_struct_data.get('link')
            link = 'https://storage.cloud.google.com/{}'.format(gs_url.split('//')[1])
            source = 'CLOUD_STORAGE'

        # global_black_list に登録された PDF の場合は検索から除外する
        if title in global_black_list:
            continue
        
        extractive_answers = ""
        if derived_struct_data.get('extractive_answers'):
            extractive_answers = derived_struct_data["extractive_answers"][0]["content"]

        snippet = ""
        snippet_status = False
        if derived_struct_data.get('snippets'):
            snippet = derived_struct_data["snippets"][0]["snippet"]
            snippet_status = derived_struct_data["snippets"][0]["snippet_status"]

        response['result'].append(
            dict(
                # タイトル
                title=title,
                # リンク先
                link=link or 'https://www.google.com/',
                # 顧客名
                customer=customer,
                # 抽出
                extractive_segment=extractive_answers,
                # スニペット文字列
                snippet=snippet,
                # スニペットを取得できたかどうか
                snippet_status=snippet_status,
                # source
                source=source,
            )
        )
        i += 1

    return response


def generate_text(prompt: str) -> str:
    """プロンプトに与えた内容を生成 AI モデルで処理する"""
    # Load the model
    multimodal_model = GenerativeModel("gemini-1.5-pro-002")
    # config
    config = GenerationConfig(
        temperature=0,
        top_p=1,
        top_k=32,
        max_output_tokens=2048,
    )
    # Query the model
    response = multimodal_model.generate_content(
        [
            # Add an example query
            prompt
        ],
        generation_config=config
    )
    print(prompt)
    # print(response)
    print(response.text)
    return response.text


def prompt_base():
    """利用するプロンプト"""
    return '''ユーザーと親切なアシスタント間の対話、および関連する検索結果を踏まえて、アシスタントの最終的な回答をNotebookLM風の日本語で作成してください。
検索結果を基に、以下の条件を満たす回答を生成してください。
回答は以下の条件を満たす必要があります。
1. 検索結果から関連性の高い情報を最大3件活用し、**「検索結果によると、〇〇〇について、下記企業の事例が挙げられます。」**という形で回答を始め、〇〇〇には、検索クエリを参考にした適切な単語を挿入する。
2. 企業それぞれ必ず1文で結果を回答する。
3. 検索結果にない新しい情報は一切導入しない。
4. 可能な限り検索結果から直接引用し、全く同じ表現を使用する。引用部分は「」（鉤括弧）で囲み、文末に出典（検索結果の URL を含めない）を明記する。出典部は（）（丸括弧）で囲みます。
5. 各項目は箇条書き形式で記述する。
6. 文頭に「-」記号を付ける。
7. Googleのウェブベースの日本語に沿った、カジュアルでわかりやすい文体を使用する。
8. 企業名は太字で強調表示する。
9. 専門用語については、可能な限り一般的な言葉で言い換えるか、括弧内に簡潔な説明を加える。
10. 可能な限り、具体的な使用例や事例、数値データを含めて説明する。
11. 検索結果に含まれる情報の日付に注意し、最新の情報を優先して使用する。古い情報を使用する場合は、その旨を明記する（例：2023年7月時点の情報では...）。
12. 検索結果に複数の観点が含まれる場合は、それらを公平に扱い、バランスの取れた回答を心がける。
13. 個人情報や機密情報が含まれている可能性がある場合は、それらを慎重に扱い、必要に応じて一般化または匿名化する。
14. 出力にHTMLタグを含めない。
15. 各文末で改行すること。
16. 検索結果が1件以上存在する場合、要約結果から推薦される次の検索単語候補を 3 つ生成し、以下のフォーマットで追記する。
{"recommendations": ["検索ワード1", "検索ワード2" , "検索ワード3"]}
17. 検索結果が1件以上存在する場合、回答の最後に、「質問の意図とずれている場合は、遠慮なく別の表現で質問してくださいね。」という一文を追加する。
18. 検索結果が0件の場合は「該当する結果を取得できませんでした、別の表現で質問してみてください」と回答する。
19. 検索結果に含まれる法人名については正しいものを利用する。
20. 検索結果に含まれる法人名が明確でない場合は省略を行い検索結果の概要を説明したうえで、「詳細は検索結果を確認してください」で回答を終えること。
21. 要約結果から Google Drive のURL (https://drive. で始まるURL)、及び Google Cloud Storage のURL (https://storage.) で始まる URL を削除する。
22. 検索結果に事例が含まれない場合はファイルのタイトル（拡張子を除外）を太字表記し、内容から短い要約を作成し、「詳細は検索結果を確認してください」で回答を終えること。

なお、検索結果のタイトルとURLは、===== で囲まれたプロンプト末尾にある。

=====

'''[1:-1]