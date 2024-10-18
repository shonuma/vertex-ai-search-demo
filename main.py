import os

import flet as ft

from libs.gcp_libs import (add_or_update_entry, clean_snippet_text,
                           clean_summary_text, exec_search_by_curl,
                           generate_text, get_histories,
                           get_histories_by_count, get_recommendations,
                           parse_result_by_curl)

google_color = {
    'primary_blue': '#4285F4',
    'primary_red': '#EA4335',
    'primary_yellow': '#FBBC04',
    'primary_green': '#34A853',
    'tertiary_blue': '#D2E3FC',
    'tertiary_green': '#CEEAD6',
    'primary_white': '#ffffff',
}

global_design_settings = {
    'result_horizontal_margin': 64,
    'result_vertical_margin': 5,
}


def main(page: ft.Page):
    def remove_all():
        for _ in range(0, len(page.controls)):
            page.controls.pop()

    def render_main():
        # History
        histories = get_histories()
        histories_container = []
        for i, history in enumerate(histories):
            q = history['query']
            display_q = q
            # 15 文字以上の場合は、表示を ... にする
            if len(display_q) > 15:
                display_q = display_q[0:15] + '...'
            histories_container.append(
                ft.Container(
                    content=ft.Text(
                        display_q,
                        color=google_color['primary_white'],
                        text_align=ft.TextAlign.CENTER
                    ),
                    margin=4,
                    padding=4,
                    alignment=ft.alignment.center,
                    bgcolor=google_color['primary_blue'],
                    width=148,
                    height=48,
                    border_radius=32,
                    ink=True,
                    # 元のクエリを保持
                    data=q,
                    on_click=click_history,
                )
            )
            if i == 5:
                break
        # 3行ずつに揃える
        histories_area = [
            ft.Row(
                histories_container[0:3],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Row(
                histories_container[3:6],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ]

        # メインコンポーネントの描画
        page.controls.append(
            ft.Column(
                controls=[header_field],
            )
        )
        page.controls.append(
            ft.Row(
                [eyecatch_image],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )
        page.controls.append(histories_area[0])
        page.controls.append(histories_area[1])
        page.controls.append(
            ft.Row(
                [text_field],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )
        page.controls.append(
            ft.Row(
                [button_field],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )

    def open_faq(e):
        # faq url
        page.launch_url("https://www.google.com")

    def open_dialog(e):
        def on_dissmiss_dialog(e):
            page.close(dlg)

        def setup_barchart_modal():
            # 棒グラフの作成
            hs_ = get_histories_by_count()
            bar_groups = []
            labels = []
            max_ = 0
            for i, h_ in enumerate(hs_):
                bar_groups.append(
                    ft.BarChartGroup(
                        x=i+1,
                        bar_rods=[
                            ft.BarChartRod(
                                from_y=0,
                                to_y=h_['count'],
                                width=24,
                                color='#' + str(hex(255 - (i * 16 + 1)))[2:] + '4285FF',
                                tooltip='{} : {}'.format(h_['query'], h_['count']),
                                border_radius=0,
                            )
                        ]
                    )
                )
                labels.append(
                    ft.ChartAxisLabel(
                        value=i+1,
                        label=ft.Container(
                            ft.Text(
                                h_['query'][0:15] + "...",
                                size=10,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            padding=1,
                            width=48,
                        )
                    )
                )
                if i == 0:
                    max_ = h_['count']
                if i == 9:
                    break
            chart = ft.Container(
                ft.BarChart(
                    bar_groups=bar_groups,
                    border=ft.border.all(1, ft.colors.GREY_400),
                    left_axis=ft.ChartAxis(
                        title=ft.Text("検索件数"),
                        labels_size=48,
                        title_size=24,
                    ),
                    bottom_axis=ft.ChartAxis(
                        title=ft.Text("よく検索されているワード"),
                        labels=labels,
                        labels_size=64,
                        title_size=24,
                    ),
                    horizontal_grid_lines=ft.ChartGridLines(
                        color=ft.colors.GREY_300,
                        width=1,
                        dash_pattern=[3, 3]
                    ),
                    tooltip_bgcolor=ft.colors.with_opacity(0.8, ft.colors.GREY_300),
                    max_y=int(max_/10) * 10 + 10,
                    interactive=True,
                    expand=True,
                ),
                width=640,
            )
            return ft.AlertDialog(
                content=chart,
                on_dismiss=lambda e: on_dissmiss_dialog(e),
            )
        dlg = setup_barchart_modal()
        page.open(dlg)

    def open_url(e):
        page.launch_url(e.control.data)

    def text_field_on_submit(e):
        add_clicked(e)

    def click_history(e):
        if text_field.disabled:
            return
        history_query = e.control.data
        text_field.value = history_query
        page.update()
        add_clicked(e)

    def add_clicked(e):
        # クエリが空の場合は空振りさせる
        if not text_field.value:
            return
        text_field.disabled = True
        button_field.disabled = True
        remove_all()
        render_main()
        page.update()
        page.controls.append(
            ft.Row(
                [
                    ft.Image(
                        src="/Gemini_icon_full-color-rgb@2x.png",
                        width=16,
                        height=16,
                        fit=ft.ImageFit.CONTAIN,
                    ),
                    ft.Container(
                        ft.Text(
                            "生成しています...",
                            size=12,
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )
        # Loading の gif を表示
        loading_image = ft.Image(
            src="/GEMINI_Regular_Skeleton_Loader.gif",
            # 720 x 400
            width=540,
            height=300,
            fit=ft.ImageFit.CONTAIN,
            border_radius=2,
        )
        page.controls.append(
            ft.Row(
                [loading_image],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )
        page.update()
        # 検索実行
        search_query = text_field.value
        search_response = exec_search_by_curl(search_query=search_query)
        pd_result = {}
        try:
            pd_result = parse_result_by_curl(search_response)
        except Exception as e:
            pd_result = {}
            print(e)

        # 最終的にコントロールに追加するリスト
        stacked_controls = []
        if not pd_result:
            print("Error occured.")
            stacked_controls.append(
                ft.Row(
                    [
                        ft.Text("結果が取得できませんでした。他の検索ワードでお試しください。")
                    ]
                )
            )
        else:
            prompt = '''
ユーザーと親切なアシスタント間の対話、および関連する検索結果を踏まえて、アシスタントの最終的な回答をNotebookLM風の日本語で作成してください。
検索結果のタイトルとURLは、===== で囲まれたプロンプト末尾にあります。
回答は以下の条件を満たす必要があります。
1. 検索結果から関連性の高い情報を最大3件活用し、**「ソースによると、〇〇〇について、下記企業の事例が挙げられます。」**という形で回答を始める。
2. 企業それぞれ必ず1文で結果を回答する。
3. 検索結果にない新しい情報は一切導入しない。
4. 可能な限り検索結果から直接引用し、全く同じ表現を使用する。引用部分は「」（鉤括弧）で囲み、文末に出典を明記する。
5. 各項目は箇条書き形式で記述する。
6. 文頭に「-」記号を付けてください。
7. Googleのウェブベースの日本語に沿った、カジュアルでわかりやすい文体を使用する。
8. 企業名は太字で強調表示する。
9. 専門用語については、可能な限り一般的な言葉で言い換えるか、括弧内に簡潔な説明を加える。
10. 可能な限り、具体的な使用例や事例、数値データを含めて説明する。
11. 検索結果に含まれる情報の日付に注意し、最新の情報を優先して使用する。古い情報を使用する場合は、その旨を明記する（例：2023年7月時点の情報では...）。
12. 検索結果に複数の観点が含まれる場合は、それらを公平に扱い、バランスの取れた回答を心がける。
13. 個人情報や機密情報が含まれている可能性がある場合は、それらを慎重に扱い、必要に応じて一般化または匿名化する。
14. 出力にHTMLタグを含めない。
15. 各文末で改行してください。
16. 検索結果が1件以上存在する場合、要約結果から推薦される次の検索単語候補を 3 つ生成し、以下のフォーマットで追記してください。
{"recommendations": ["検索ワード1", "検索ワード2" , "検索ワード3"]}
17. 検索結果が1件以上存在する場合、回答の最後に、「質問の意図とずれている場合は、遠慮なく別の表現で質問してくださいね。」という一文を追加します。
18. 検索結果が0件の場合は「該当する結果を取得できませんでした、別の表現で質問してみてください」と回答してください。

=====

'''[1:-1]
            # 検索結果
            for j, entry in enumerate(pd_result['result']):
                snippet = entry['snippet']
                # これだと長すぎなので Trim が必要
                # snippet = entry['extractive_segment']
                if entry['snippet_status'] != "SUCCESS":
                    snippet = 'このページの概要は提供されていません。'
                txts = []
                try:
                    txts = clean_snippet_text(snippet)
                except Exception as e:
                    print('ERROR:{}'.format(e))
                # パースに失敗したら結果に表示しない
                if not txts:
                    continue
                spans = []

                spans.append(
                    ft.TextSpan(
                        entry['title'] + "\n",
                        ft.TextStyle(
                            weight=ft.FontWeight.BOLD,
                            color=google_color['primary_blue'],
                        ),
                    )
                )

                for i in range(len(txts)):
                    if i % 2 == 0:
                        spans.append(
                            ft.TextSpan(txts[i])
                        )
                    else:
                        spans.append(
                            ft.TextSpan(
                                txts[i],
                                ft.TextStyle(weight=ft.FontWeight.BOLD),
                            )
                        )
                if j < 3:
                    prompt += '''
                {}, {}
'''.format(
        entry['title'],
        entry['link'],
    )
                icon = ft.icons.PICTURE_AS_PDF
                color = 'red'
                if entry.get('source') == 'GOOGLE_DRIVE':
                    icon = ft.icons.ADD_TO_DRIVE
                    color = 'blue'
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    leading=ft.Icon(icon, color=color),
                                    # 検索結果のタイトルと説明文のフォントサイズ
                                    # title=ft.Text(entry['title'], size=24),
                                    title=ft.Text(entry['customer'], size=24),
                                    subtitle=ft.Text(spans=spans, size=16)
                                ),
                                ft.Row(
                                    [
                                        ft.ElevatedButton(
                                            content=ft.Row(
                                                [
                                                    ft.Icon(
                                                        name=ft.icons.OPEN_IN_NEW,
                                                        color=google_color['primary_white']
                                                    ),
                                                    ft.Text("開く"),
                                                ]
                                            ),
                                            data=entry['link'],
                                            on_click=open_url,
                                            color=google_color['primary_white'],
                                            bgcolor=google_color['primary_blue']
                                        )
                                    ],
                                    alignment=ft.MainAxisAlignment.END
                                )
                            ]
                        ),
                        width=800,
                        padding=10,
                    ),
                    margin=ft.margin.symmetric(
                        vertical=global_design_settings['result_vertical_margin'],
                        horizontal=global_design_settings['result_horizontal_margin'],
                    ),
                )
                stacked_controls.append(
                    ft.ResponsiveRow(
                        [card],
                        alignment=ft.MainAxisAlignment.CENTER
                    )
                )
            prompt += '\n====='
            summary = generate_text(prompt)
            # stacked controls に要約を足す
            spans = []
            recommendations = []
            try:
                txts = clean_summary_text(summary)
                recommendation_buttons = []
                for r in get_recommendations(summary):
                    recommendation_buttons.append(
                        ft.Container(
                            content=ft.Text(
                                r,
                                color=google_color['primary_white'],
                                text_align=ft.TextAlign.CENTER
                            ),
                            margin=16,
                            padding=4,
                            alignment=ft.alignment.center,
                            bgcolor=google_color['primary_blue'],
                            width=296,
                            height=48,
                            border_radius=32,
                            ink=True,
                            # 元のクエリを保持
                            data=r,
                            on_click=click_history,
                        )
                        # ft.TextButton(
                        #     r,
                        #     data=r,
                        #     on_click=click_history,
                        # )
                    )

                for i in range(len(txts)):
                    txt = txts[i]
                    if txt.startswith('[BOLD]'):
                        txt = txt.split('[BOLD]')[1:][0]
                        spans.append(
                            ft.TextSpan(
                                txt,
                                ft.TextStyle(weight=ft.FontWeight.BOLD),
                            )
                        )
                    else:
                        spans.append(ft.TextSpan(txt))
                summary_card = ft.Card(
                    content=ft.Container(
                        bgcolor=google_color['tertiary_blue'],
                        content=ft.Column(
                            [
                                ft.Text(
                                    size=20,
                                    spans=spans,
                                ),
                                ft.Row(
                                    recommendation_buttons,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                )
                            ]
                        ),
                        width=800,
                        border_radius=5,
                        padding=10,
                    ),
                    margin=ft.margin.symmetric(
                        vertical=global_design_settings['result_vertical_margin'],
                        horizontal=global_design_settings['result_horizontal_margin'],
                    ),
                )
                stacked_controls = [
                    ft.ResponsiveRow(
                        [summary_card],
                        alignment=ft.MainAxisAlignment.CENTER
                    )
                ] + stacked_controls
            except Exception as e:
                print('ERROR{}'.format(str(e)))
            add_or_update_entry(search_query)

        # 再描画
        remove_all()
        render_main()
        for _ in stacked_controls:
            page.controls.append(_)

        text_field.disabled = False
        button_field.disabled = False
        # 表示
        page.update()
        # print(prompt)

    # Theme
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = google_color['primary_white']
    page.title = "事例の森"
    # Font
    page.fonts = {
       "GoogleNotoSansJp": "https://fonts.googleapis.com/css2?family=Noto+Sans+JP&display=swap",
    }
    page.theme = ft.Theme(
        font_family="GoogleNotoSansJp"
    )
    page.scroll = "always"

    # Header
    header_field = ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    ft.Text(
                        spans=[
                            ft.TextSpan(
                                "FAQ",
                                ft.TextStyle(
                                    decoration=ft.TextDecoration.UNDERLINE,
                                    decoration_color=google_color['primary_blue'],
                                ),
                                on_click=open_faq,
                            ),
                        ],
                        color=google_color['primary_blue'],
                        size=16,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=64,
                ),
                ft.Container(
                    ft.Text(
                        spans=[
                            ft.TextSpan(
                                "よく検索されているワードをみる",
                                ft.TextStyle(
                                    decoration=ft.TextDecoration.UNDERLINE,
                                    decoration_color=google_color['primary_blue'],
                                ),
                                on_click=lambda e: open_dialog(e),
                            ),
                        ],
                        color=google_color['primary_blue'],
                        size=16,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=256,
                ),
            ],
            alignment=ft.MainAxisAlignment.END,
        ),
    )
    # Text Field
    text_field = ft.TextField(
        hint_text="検索ワードを入力してください",
        prefix_icon=ft.icons.SEARCH,
        helper_text="関連する事例の一覧が表示されます。",
        border_radius=20,
        bgcolor=ft.colors.GREY_50,
        on_submit=text_field_on_submit,
        width=480,
    )
    # Button
    button_field = ft.ElevatedButton(
        content=ft.Container(
            ft.Text(
                "検索",
            ),
        ),
        height=40,
        width=240,
        color=google_color['primary_white'],
        bgcolor=google_color['primary_blue'],
        on_click=add_clicked,
    )
    # Eyecatch images
    eyecatch_image = ft.Image(
        src="/blue-logo4.png",
        # src="/case_study_forest_eyecatch_02.png",
        width=480,
        height=240,
        fit=ft.ImageFit.CONTAIN,
    )
    eyecache_developed_on_gcp = ft.Image(
        src="/developed_on_google_cloud.png",
        height=94,
        fit=ft.ImageFit.CONTAIN,
    )
    # 上部のメニューバー
    appbar = ft.AppBar(
        leading=ft.Icon(ft.icons.FOREST, color=ft.colors.GREEN_ACCENT_700),
        leading_width=24,
        title=ft.Text("事例の森"),
        center_title=False,
        bgcolor=ft.colors.SURFACE_VARIANT,
        actions=[
            ft.IconButton(
                ft.icons.QUESTION_MARK,
                bgcolor=ft.colors.BLUE_50,
                on_click=open_faq
            ),
        ]
    )
    # page.appbar = appbar
    render_main()
    page.update()


app = ft.app(
    target=main,
    assets_dir="assets",
    view=ft.AppView.WEB_BROWSER,
)
