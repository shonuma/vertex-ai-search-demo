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
        page.launch_url("https://ff21c8942e4d5a83cd0ccc8f7d597c57b2367f7fc9d81d479a8b6a6-apidata.googleusercontent.com/download/storage/v1/b/forest_of_usecase/o/customer_case%2F%E3%80%8C%E4%BA%8B%E4%BE%8B%E3%81%AE%E6%A3%AE%E3%80%8DFAQ%E8%B3%87%E6%96%99.pdf?jk=AYBlUPDVL82oXX9aIDL3EyG9AV-h8xvuxS-lTy3Wyk5ZQUOrPKGI6lgS8gQ-_9TYMRf3pdje19TqCrMyWLMaBbfCOr0EWfDoZ3Ce7SBhzf6IXpxnczbWzubpMkSi3-L1a0a2pYS9GTyYjBKcicd18GGLlTcL5vKcbDIRgchFxUKZYlY9I7mFWoAi4U6waWg4GUkR5X-i1tqyMBBQcP6mWxbPccrMsn1ArFiXQklPHjxj3DnxqsEt2OQ03k5cIxg1_ZaGwivG6pdQ_pYym2qjPp7IsQWtUK0iXON1ZET9rV2VOFmV2ygWRrc8muosKOBaPrQg0fe6vs-wL7TG5dRwzxqNJqTuaLBJm_nUlsstWcR96c8fpTIy-cevBQc7wzHfVOWoAMfWGZxEzZEgoyes2nVhb3HVtCo8S47ef4LJ4dIY6hYHp1LMge5Mb2hcl6_tlPJbWGkISlZJJSvcbaOOIA4V2CBL4ppC8N6wXZPNqRmiI8Jf4AyaBZuHyfsWAnGQGMaZcPXLxucMxHbVyQUyeN1H_fl-dEkTEUf6uUKBDpVwRgLSInwpmTdyaatK7CwbNGEXyTvi8VkW29fZXHHgxI77OXGMechshtwxj4kSyUTcwQlq4bBcu7ia9kWKgE1aJhvb-AbXiCOW1mQbsAHtt-9OWRHNo3V822lrc0q8fRhs3knZfuFotqgOjBRpug6lXxnZ77ywKBr7lksjOFhDFrlPHzhah8VKlvduS6DIOknOJ3JMlk-eC6slCO_WjGCFtd8XAedqHJKUMV7EJ8OlaPxzLFmCLDW6VH1RAzTd0F5eG_qVDmFLzZbeTTjBFF5tEMg-2oteEtBZUUE6aOx8lzeCfZnjFRVGgZfczadZtcTQijDM2ZawOV8393XNmt8tCXJ3MowIF6yrCfBqklWL_2bi4-5hXJeOMGV_P4G1zye0GTcHmhpNqLtNjb0JVckWm2d8TKNKUx3drxJsyDLMq5pDOS8vjvHo4DBJNRuBlMF5m9FvY3nLmchI_3Lm4ODYa0zc00KGK2FoJywdkLSPIgj_Ta_6J2P-6Me_H0ZYjlt_XIvoplKM_CjgKTMV_vMhB7499FQEbw6yBMQQ3XdFC0-X3lE7SwWM3K3p68arlomlzAmSrwfMzwihcnc6dkj5FfRKhVMQZDXt4os1lsB3R6C51vHW9ZHRtwuZCQm32Y885KsQc2BCTfGItl9qRUTISchlZkn_OBib-dMskmn03anPK5JV6iwqwRAihU0&isca=1")

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
            fit=ft.ImageFit.CONTAIN,
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
                content=ft.Markdown(
                    pd_result['meta']['summary'],
                    selectable=True,
                    extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                    on_tap_link=lambda e: page.launch_url(e.data),
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
                                title=ft.Text(entry['title']),
                                subtitle=ft.Text(spans=spans)
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
    # Font
    page.fonts = {
       "NotoSansJp": "/fonts/NotoSansJP-SemiBold.ttf"
    }
    page.theme = ft.Theme(font_family="NotoSansJp")
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
        height=64,
    )
    # 上部のメニューバー
    page.appbar = ft.AppBar(
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
    render_main()
    page.update()


ft.app(
    target=main,
    assets_dir="assets",
    # view=ft.AppView.WEB_BROWSER
)
