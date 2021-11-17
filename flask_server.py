import time
import asyncio
import threading

from flask import Flask, jsonify, make_response

from fake_smtp import run_server, MySMTPServerHandler


def format_html(data):
    tr_list = []
    for index, item in enumerate(data):
        tr_list.append(f"""
<tr>
    <th>{item['to_addr']}</th>
    <th>{item['from_addr']}</th>
    <th>{item['subject']}</th>
    <th>{time.strftime("%Y-%m-%d_%H:%M:%S",time.localtime(int(item['time'])))}</th>
    <th><a href="wiew/{index}">预览</a></th>
    <th><a href="download/{index}">下载</a></th>

</tr>
""")

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>emails</title>
</head>
<body>


<table border="1">
    <tr>
        <th>收件人</th>
        <th>发件人</th>
        <th>主题</th>
        <th>时间</th>
        <th>预览</th>
        <th>下载</th>
    </tr>
    {''.join(tr_list)}
</table>
</body>
</html>
"""
    return html


app = Flask(__name__, static_folder="mails")


@app.route('/')
def index_page():
    return format_html(MySMTPServerHandler.globals_data_list)


@app.route('/json')
def json_data():
    return jsonify(MySMTPServerHandler.globals_data_list)


def render_html(**kwargs):
    html = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>email</title>
</head>
<body>
<div><span>发件人: </span><span id='from'>{from_addr}</span></div>
<div><span>收件人: </span><span id='to'>{to_addr}</span></div>
<div><span>主题: </span><span id='subject'>{subject}</span></div>
<div id='payload'>
    {payload}
</div>
</body>
</html>
    """
    for k in kwargs.keys():
        if k == "payload":
            continue
        kwargs[k] = kwargs[k].replace("<", "&lt;").replace(">", "&gt;")
    return html.format(**kwargs)


@app.route('/wiew/<int:index>')
def view_data(index):
    return render_html(**MySMTPServerHandler.globals_data_list[index])


@app.route('/download/<int:index>')
def download_data(index):
    response = make_response(render_html(**MySMTPServerHandler.globals_data_list[index]))
    response.headers["Content-Disposition"] = "attachment; filename={}".format("email.html")
    return response


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default=8025)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--username", default="smtp@demo.com")
    parser.add_argument("--password", default="demo")
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    t_smtp = threading.Thread(target=run_server,
                              kwargs={"loop": loop, "handler": MySMTPServerHandler, "host": args.host, "port": args.port, "user_name": args.username, "password": args.password})
    t_smtp.setDaemon(True)
    t_smtp.start()
    app.run(port=5000)
