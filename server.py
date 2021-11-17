import os
import asyncio
import logging
import base64
from email import message_from_bytes
from email.message import Message
from datetime import datetime

import aiosmtpd
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP as Server, syntax

MAIL_PATH = "mails"
BIND_IP = "0.0.0.0"
PORT = 8025
USERNAME = "smtp@demo.com"
PASSWORD = "demo"


def render_html(**kwargs):
    html = """\
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>email</title>
    </head>
    <body>
    <div><span>发件人: </span><span>{from_addr}</span></div>
    <div><span>收件人: </span><span>{to_addr}</span></div>
    <div><span>主题: </span><span>{subject}</span></div>
    <div>
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


class SMTPServerHandler:
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(self, server, session, envelope: aiosmtpd.smtp.Envelope):
        message: Message = message_from_bytes(envelope.content)
        message_info = await self.parse_message(message)
        if not os.path.exists(MAIL_PATH):
            os.makedirs(MAIL_PATH)
        with open(os.path.join(MAIL_PATH, f"mail_{datetime.now().strftime('%Y-%m-%d-%H_%M_%S_%f')[:-3]}.html"), "w") as f:
            f.write(render_html(**message_info))
        return "250 Message accepted for delivery"

    def try_to_decode(self, raw: str):
        if raw.startswith("=?"):
            tmp_list = raw.split("?")
            if len(tmp_list) > 2:
                raw = tmp_list[-2]
            charset = tmp_list[1]
            assert charset == "utf-8"
        else:
            charset = "utf-8"
        try:
            return base64.b64decode(raw).decode(charset)
        except Exception as e:
            logging.exception(e)
            return raw

    def get(self, message, item):
        return self.try_to_decode(message[item])

    async def parse_message(self, message: Message):
        subject = self.get(message, "Subject")
        from_addr = self.get(message, "From")
        to_addr = self.get(message, "To")
        payload = message.get_payload()
        if isinstance(payload, (list, tuple)):
            payload = payload[0].get_payload(decode=True).decode("utf-8")
        return {"subject": subject, "payload": payload, "from_addr": from_addr, "to_addr": to_addr}

    async def handle_EHLO(self, *args, **kwargs):
        return """\
250-mail
250-PIPELINING
250-AUTH PLAIN
250-AUTH=PLAIN
250-coremail
250 8BITMIME"""


class SMTPServer(Server):
    @syntax("AUTH PLAIN")
    async def smtp_AUTH(self, plain, *args, **kwargs):
        credential_base64 = plain.replace("PLAIN ", "")
        username, password = base64.b64decode(credential_base64).split(b"\x00")[1::]
        if username.decode("utf-8") != USERNAME:
            await self.push("535 Incorrect username")
            return
        if password.decode("utf-8") != PASSWORD:
            await self.push("535 Incorrect password")
            return
        await self.push("235 auth successfully")

    @syntax("EHLO hostname")
    async def smtp_EHLO(self, hostname):
        status = await self._call_handler_hook("EHLO", hostname)
        self.session.host_name = hostname
        await self.push(status)


class SMTPController(Controller):
    def factory(self):
        return SMTPServer(self.handler)


async def main():
    controller = SMTPController(SMTPServerHandler(), hostname=BIND_IP, port=PORT)
    controller.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
