import flet as ft

from gcp_libs import exec_search

def main(page: ft.Page):
    def add_clicked(e):
        search_response = exec_search(search_query=new_task.value)
        pd_result = parse_result(search_response)

        containers = []
        for entry in pd_result['result']:
            html_ = """
<h3><a href="{link}">{title}</a></h3>
<p>{snippet}</p>
"""[1:-1].format(
    link=entry['link'],
    title=entry['title'],
    snippet=entry['snippet'],
)
            containers.append(
                ft.Text(html_)
            )

        t = ft.Row(controls=containers)
        ft.add(t)

        # t = ft.Text(value=str(result))
        # page.add(ft.Checkbox(label=new_task.value + "x"))
        # new_task.value = ""
        # new_task.focus()
        # new_task.update()
        # page.controls.append(t)
        # page.update()

    new_task = ft.TextField(hint_text="Input query", width=300)
    page.add(ft.Row([new_task, ft.ElevatedButton("Search", on_click=add_clicked)]))

ft.app(target=main)