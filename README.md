# README
以下の環境変数を定義する必要があります。

- PROJECT_ID: Google Cloud プロジェクトのID
- VERTEX_AI_SEARCH_LOCATION: 検索エンジンのロケーション（global / us / eu）
- VERTEX_AI_SEARCH_ENGINE_ID: 検索エンジンのID

run_local.sh でローカルでサーバーを実行できますが、その際は .env ファイルに環境変数を定義しておくと読みこまれます。
