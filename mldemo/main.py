import flet as ft

from gcp_libs import exec_search, parse_result, clean_summary_text, clean_snippet_text

card_count = 0

def main(page: ft.Page):
    def open_url(e):
        gs_url = e.control.data
        url = 'https://storage.cloud.google.com/{}'.format(gs_url.split('//')[1])
        # page.launch_url("https://www.google.com")
        page.launch_url(url)

    def add_clicked(e):
        global card_count
        text_field.disabled = True
        button_field.disabled = True
        page.update()
        for _ in range(0, card_count):
            page.controls.pop()
        page.update()
        card_count = 1

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
                padding=20
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
                                        icon=ft.icons.SEARCH,
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
            card_count += 1

        page.scroll = "always"

        text_field.disabled = False
        button_field.disabled = False
        page.update()

    text_field = ft.TextField(hint_text="Input query", width=300)
    button_field = ft.ElevatedButton("Search", on_click=add_clicked)
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.icons.FOREST, color=ft.colors.GREEN_ACCENT_700),
        leading_width=32,
        title=ft.Text("事例の森"),
        center_title=False,
        bgcolor=ft.colors.SURFACE_VARIANT,
    )
    page.add(
        ft.Row(
            [
                text_field,
                button_field
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )
    )

ft.app(target=main, view=ft.AppView.WEB_BROWSER)