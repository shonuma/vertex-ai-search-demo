import flet as ft

from gcp_libs import exec_search, parse_result, clean_summary_text, clean_snippet_text


def main(page: ft.Page):
    def add_main():
        page.add(
            ft.Row(
                [eyecatch_image],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )
        page.add(
            ft.Row(
                [
                    text_field,
                    ft.Column(
                        controls=[button_field],
                        alignment=ft.VerticalAlignment.END,
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )
    def open_url(e):
        gs_url = e.control.data
        url = 'https://storage.cloud.google.com/{}'.format(gs_url.split('//')[1])
        page.launch_url(url)

    def add_clicked(e):
        # クエリが空の場合は空振りさせる
        if not text_field.value:
            return
        text_field.disabled = True
        button_field.disabled = True
        page.update()
        for _ in range(0, len(page.controls)):
            page.controls.pop()
        add_main()
        page.update()
        loading_image = ft.Image(
            src=f"/gemini_loading.gif",
            width=720,
            height=400,
            fit=ft.ImageFit.CONTAIN,
        )
        page.controls.append(
            ft.Row(
                [loading_image],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )
        page.update()
        page.controls.pop()

        search_response = exec_search(search_query=text_field.value)
        pd_result = parse_result(search_response)
        print(pd_result)
        # 要約
        spans = []
        txts = clean_snippet_text(
            clean_summary_text(pd_result['meta']['summary'])
        )
        for i in range(len(txts)):
            if i % 2 == 0:
                spans.append(ft.TextSpan(txts[i]))
            else:
                ft.TextSpan(
                    txts[i],
                    ft.TextStyle(weight=ft.FontWeight.BOLD),
                )

        summary_card = ft.Card(
            color=ft.colors.INDIGO_500,
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.EDIT_DOCUMENT, color="blue"),
                            title=ft.Text("要約"),
                            subtitle=ft.Text(spans=spans)
                        )
                    ]
                ),
                width=800,
                padding=15
            )
        )
        page.controls.append(
            ft.Row(
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
                                title=ft.Text(entry['title']),
                                subtitle=ft.Text(spans=spans)
                            ),
                            ft.Row(
                                [
                                    ft.ElevatedButton(
                                        text="開く",
                                        icon=ft.icons.OPEN_IN_NEW,
                                        data=entry['link'],
                                        on_click=open_url,
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
            page.controls.append(
                ft.Row(
                    [card],
                    alignment=ft.MainAxisAlignment.CENTER
                )
            )

        page.scroll = "always"

        text_field.disabled = False
        button_field.disabled = False
        page.update()

    text_field = ft.TextField(
        hint_text="検索ワードを入力してください",
        prefix_icon=ft.icons.SEARCH,
        helper_text="関連する事例の一覧が表示されます。",
        border_radius=30,
        width=576,
    )
    button_field = ft.ElevatedButton(
        "検索",
        on_click=add_clicked,
        height=32,
    )
    eyecatch_image = ft.Image(
        src=f"/eyecatch.png",
        width=384,
        height=384,
        fit=ft.ImageFit.CONTAIN,
    )
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.icons.FOREST, color=ft.colors.GREEN_ACCENT_700),
        leading_width=32,
        title=ft.Text("事例の森"),
        center_title=False,
        bgcolor=ft.colors.SURFACE_VARIANT,
    )
    add_main()

ft.app(
    target=main,
    assets_dir="assets",
    # view=ft.AppView.WEB_BROWSER
)