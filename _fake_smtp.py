import asyncio
import base64
from email import message_from_bytes
from email.message import Message

import aiosmtpd
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP as Server, syntax


class SMTPServerHandler:
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(self, server, session, envelope: aiosmtpd.smtp.Envelope):
        message: Message = message_from_bytes(envelope.content)
        message_data: dict = await self.parse_message(message)
        self.operate_data(data=message_data)
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
        except Exception:
            return raw

    def get(self, message, item):
        return self.try_to_decode(message[item])

    async def handle_EHLO(self, *args, **kwargs):
        return """\
250-mail
250-PIPELINING
250-AUTH PLAIN
250-AUTH=PLAIN
250-coremail
250 8BITMIME"""

    def operate_data(self, data):
        """
        store data
        """
        raise NotImplementedError

    async def parse_message(self, message: Message):
        """
        解析 message
        """
        raise NotImplementedError


class SMTPServer(Server):
    @syntax("AUTH PLAIN")
    @asyncio.coroutine
    def smtp_AUTH(self, plain, *args, **kwargs):
        credential_base64 = plain.replace("PLAIN ", "")
        username, password = base64.b64decode(credential_base64).split(b"\x00")[1::]
        if username.decode("utf-8") != self.USERNAME:
            yield from self.push("535 Incorrect username")
            return
        if password.decode("utf-8") != self.PASSWORD:
            yield from self.push("535 Incorrect password")
            return
        yield from self.push("235 auth successfully")

    @syntax("EHLO hostname")
    async def smtp_EHLO(self, hostname):
        status = await self._call_handler_hook("EHLO", hostname)
        self.session.host_name = hostname
        await self.push(status)


class SMTPController(Controller):
    def factory(self):
        return SMTPServer(self.handler)


async def main(*, host, port, user_name, password, handler):
    SMTPServer.USERNAME = user_name
    SMTPServer.PASSWORD = password
    controller = SMTPController(handler(), hostname=host, port=port)
    controller.start()
