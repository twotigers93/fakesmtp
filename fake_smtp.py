import base64
import time

from _fake_smtp import SMTPServerHandler, main as _main


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


MAIL_PATH = "mails"


class MySMTPServerHandler(SMTPServerHandler):
    globals_data_list = []

    async def parse_message(self, message):
        subject = self.get(message, "Subject")
        from_addr = self.get(message, "From")
        to_addr = self.get(message, "To")
        payload = message.get_payload()
        if isinstance(payload, (list, tuple)):
            payload = payload[0].get_payload(decode=True).decode("utf-8")
        try:
            payload = base64.b64decode(payload).decode()
        except Exception as e:
            pass
        return {"subject": subject, "payload": payload, "from_addr": from_addr, "to_addr": to_addr, "time": str(int(time.time()))}

    def operate_data(self, data):
        self.globals_data_list.append(data)


def run_server(loop, handler, *, host, port, user_name, password):
    loop.create_task(_main(host=host, port=port, user_name=user_name, password=password, handler=handler))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
