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
from vertexai.generative_models import GenerativeModel

from libs.gcp_token import get_token, retreive_token

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
    retreive_token()
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
    multimodal_model = GenerativeModel("gemini-1.5-flash-001")
    # Query the model
    response = multimodal_model.generate_content(
        [
            # Add an example query
            prompt
        ]
    )
    print(response)
    return response.text