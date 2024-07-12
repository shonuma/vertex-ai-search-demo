import flet as ft

from gcp_libs import (add_or_update_entry, clean_snippet_text,
                      clean_summary_text, exec_search, get_histories,
                      parse_result)


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
                    margin=10,
                    padding=10,
                    alignment=ft.alignment.center,
                    bgcolor=ft.colors.GREEN_50,
                    width=128,
                    height=96,
                    border_radius=5,
                    ink=True,
                    on_click=click_history,
                )
            )
            if i == 2:
                break
        histories_area = ft.Row(
            histories_container,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        # メインコンポーネントの描画
        page.controls.append(
            ft.Row(
                [eyecatch_image],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )
        page.controls.append(
            ft.Row(
                [eyecache_developed_on_gcp],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )
        page.controls.append(histories_area)
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
        # Loading の gif を表示
        loading_image = ft.Image(
            src="/gemini_loading.gif",
            width=720,
            height=400,
            # 1. これが一番それっぽく見える
            # color=ft.colors.RED_50,
            # color_blend_mode=ft.BlendMode.COLOR_DODGE,
            # 2. これもあり
            # color=ft.colors.GREY_200,
            # color_blend_mode=ft.BlendMode.LUMINOSITY,
            color=ft.colors.GREEN_50,
            color_blend_mode=ft.BlendMode.LUMINOSITY,
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
        pd_result = parse_result(search_response)
        print(pd_result)
        # 最終的にコントロールに追加するリスト
        stacked_controls = []

        # 要約
        spans = []

        txts = clean_snippet_text(
            clean_summary_text(pd_result['meta']['summary'])
        )
        for i in range(len(txts)):
            if i % 2 == 0:
                spans.append(ft.TextSpan(txts[i]))
            else:
                spans.append(
                    ft.TextSpan(
                        txts[i],
                        ft.TextStyle(weight=ft.FontWeight.BOLD),
                    )
                )

        summary_card = ft.Card(
            content=ft.Container(
                bgcolor=ft.colors.BLUE_50,
                content=ft.Text(
                    pd_result['meta']['summary'],
                    size=20,
                    # selectable=True,
                    # extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                    # on_tap_link=lambda e: page.launch_url(e.data),
                ),
                width=800,
                border_radius=5,
                padding=15
            )
        )
        stacked_controls.append(
            ft.ResponsiveRow(
                [summary_card],
                alignment=ft.MainAxisAlignment.CENTER
            )
        )

        # 検索結果
        for entry in pd_result['result']:
            snippet = entry['snippet']
            if entry['snippet_status'] != "SUCCESS":
                snippet = 'このページの概要は提供されていません。'
            txts = clean_snippet_text(snippet)
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
                                        text="開く",
                                        icon=ft.icons.OPEN_IN_NEW,
                                        data=entry['link'],
                                        on_click=open_url
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
    page.title = "事例の森"
    # Font
    page.fonts = {
       "NotoSansJpMedium": "/fonts/NotoSansJP-Medium.ttf",
       "NotoSansJpRegular": "/fonts/NotoSansJP-Regular.ttf",
       "NotoSansJpSemiBold": "/fonts/NotoSansJP-SemiBold.ttf",
       "NotoSansVariableFont": "/fonts/NotoSansJP-VariableFont_wght.ttf",
       "GoogleNotoSansJp": "https://fonts.googleapis.com/css2?family=Noto+Sans+JP&display=swap",
    }
    page.theme = ft.Theme(
        font_family="GoogleNotoSansJp"
    )
    page.scroll = "always"

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
        "検索",
        on_click=add_clicked,
        height=40,
        width=240,
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
        width=400,
        height=73.5,
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


ft.app(
    target=main,
    assets_dir="assets",
    view=ft.AppView.WEB_BROWSER
)
