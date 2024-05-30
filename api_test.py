from flask import Flask
from flask import request

from typing import List

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine

from mldemo.gcp_libs import exec_search, parse_result

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/search")
def search():
    search_query = request.args.get("q") or ""
    result = "Specify query please."
    if search_query:
        result = exec_search(
            search_query=search_query
        )
    response = """
<h2>Search Query: {search_query}</h2>

<p>Result</p>
{result}
"""[1:-1].format(search_query=search_query, result=result)
    return response



if __name__ == "__main__":
    import sys
    import json
    query = sys.argv[1] or "データ"
    search_response = exec_search(
        search_query=query
    )
    parsed_result = parse_result(search_response)
    print(
        json.dumps(parsed_result, ensure_ascii=False)
    )