"""Préparation et envoi d'e-mails de candidature (SMTP). L'envoi exige toujours une confirmation explicite."""

from __future__ import annotations

import mimetypes
import os
import re
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from dotenv import load_dotenv

from .config import ConfigError

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
MAX_SENDS_PER_SESSION = 10


class MailError(RuntimeError):
    """Adresse invalide ou échec d'envoi."""


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    user: str
    password: str
    sender: str

    @classmethod
    def from_env(cls) -> "SmtpSettings":
        load_dotenv()
        host, user, pwd = (os.getenv(k, "").strip() for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))
        if not (host and user and pwd) or pwd.endswith("..."):
            raise ConfigError(
                "Envoi d'e-mail non configuré : renseignez SMTP_HOST, SMTP_USER et SMTP_PASSWORD dans .env "
                "(pour Gmail : smtp.gmail.com et un « mot de passe d'application »)."
            )
        port = int(os.getenv("SMTP_PORT", "587") or 587)
        return cls(host, port, user, pwd, os.getenv("SMTP_FROM", "").strip() or user)


def validate_address(address: str) -> str:
    address = (address or "").strip()
    if not EMAIL_RE.match(address):
        raise MailError(f"Adresse e-mail invalide : « {address} ».")
    return address


def _one_line(text: str) -> str:
    return re.sub(r"[\r\n]+", " ", text).strip()  # empêche l'injection d'en-têtes


def build_message(
    to: str,
    subject: str,
    body: str,
    attachments: list[tuple[str, bytes]] | None = None,
    sender: str | None = None,
) -> EmailMessage:
    msg = EmailMessage()
    if sender:
        msg["From"] = _one_line(sender)
    msg["To"] = validate_address(to)
    msg["Subject"] = _one_line(subject) or "Candidature"
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.set_content(body)
    for filename, data in attachments or []:
        mime, _ = mimetypes.guess_type(filename)
        maintype, subtype = (mime or "application/octet-stream").split("/", 1)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)
    return msg


def to_eml(msg: EmailMessage) -> bytes:
    return msg.as_bytes()


def send(settings: SmtpSettings, msg: EmailMessage) -> None:
    """Envoie le message. À n'appeler qu'après confirmation de l'utilisateur."""
    if "From" not in msg:
        msg["From"] = settings.sender
    try:
        if settings.port == 465:
            with smtplib.SMTP_SSL(settings.host, settings.port, context=ssl.create_default_context(), timeout=30) as s:
                s.login(settings.user, settings.password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(settings.host, settings.port, timeout=30) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(settings.user, settings.password)
                s.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        raise MailError("Identifiants SMTP refusés (Gmail : utilisez un mot de passe d'application).") from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise MailError(f"Échec de l'envoi : {exc}") from exc
