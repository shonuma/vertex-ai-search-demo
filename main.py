import os

import flet as ft

from libs.gcp_libs import (add_or_update_entry, clean_snippet_text,
                           clean_summary_text, exec_search, get_histories,
                           parse_result)

google_color = {
    'primary_blue': '#4285F4',
    'primary_red': '#EA4335',
    'primary_yellow': '#FBBC04',
    'primary_green': '#34A853',
    'tertiary_blue': '#D2E3FC',
    'tertiary_green': '#CEEAD6',
    'primary_white': '#ffffff'
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
            histories_container.append(
                ft.Container(
                    content=ft.Text(q, text_align=ft.TextAlign.CENTER),
                    margin=5,
                    padding=5,
                    alignment=ft.alignment.center,
                    # bgcolor=ft.colors.GREEN_50,
                    bgcolor='#81C995',
                    width=128,
                    height=64,
                    border_radius=5,
                    ink=True,
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
        # page.controls.append(
        #     ft.Row(
        #         [eyecache_developed_on_gcp],
        #         alignment=ft.MainAxisAlignment.CENTER,
        #     )
        # )
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
        page.launch_url("https://storage.cloud.google.com/forest_of_usecase/customer_case/「事例の森」FAQ資料.pdf")

    def open_url(e):
        gs_url = e.control.data
        url = 'https://storage.cloud.google.com/{}'.format(gs_url.split('//')[1])
        page.launch_url(url)

    def text_field_on_submit(e):
        add_clicked(e)

    def click_history(e):
        if text_field.disabled:
            return
        history_query = e.control.content.value
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
            # 1. これが一番それっぽく見える
            # color=ft.colors.RED_50,
            # color=ft.colors.GREY_50,
            # color_blend_mode=ft.BlendMode.COLOR_DODGE,
            # 2. これもあり
            # color=ft.colors.GREY_200,
            # color_blend_mode=ft.BlendMode.LUMINOSITY,
            # color=ft.colors.GREEN_50,
            # color_blend_mode=ft.BlendMode.LUMINOSITY,
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
        search_response = exec_search(search_query=search_query)
        pd_result = {}
        try:
            pd_result = parse_result(search_response)
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
            # 要約
            spans = []
            try:
                txts = clean_summary_text(
                    pd_result['meta']['summary']
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
                        content=ft.Text(
                            size=20,
                            spans=spans,
                        ),
                #         content=ft.Text(
                #             pd_result['meta']['summary'],
                #             size=20,
                #             # selectable=True,
                #             # extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                #             # on_tap_link=lambda e: page.launch_url(e.data),
                #         ),
                        width=800,
                        border_radius=5,
                        padding=10
                    )
                )
                stacked_controls.append(
                    ft.ResponsiveRow(
                        [summary_card],
                        alignment=ft.MainAxisAlignment.CENTER
                    )
                )
            except Exception as e:
                print('ERROR{}'.format(str(e)))

            # 検索結果
            for entry in pd_result['result']:
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

                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    leading=ft.Icon(ft.icons.PICTURE_AS_PDF, color="red"),
                                    # 検索結果のタイトルと説明文のフォントサイズ
                                    title=ft.Text(entry['title'], size=24),
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
                )
                stacked_controls.append(
                    ft.ResponsiveRow(
                        [card],
                        alignment=ft.MainAxisAlignment.CENTER
                    )
                )
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
                            )
                        ],
                        color=google_color['primary_blue'],
                        size=16,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=64,
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
        src="/case_study_forest_eyecatch_02.png",
        width=280,
        height=280,
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
    # export_asgi_app=False if os.environ.get('run_local') else True,
)