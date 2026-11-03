"""Envio de mensagens de WhatsApp via Twilio ou Meta Cloud API."""
import os
import requests


class WhatsAppError(RuntimeError):
    pass


def send_whatsapp_message(text: str) -> None:
    provider = os.getenv("WHATSAPP_PROVIDER", "twilio").lower()
    try:
        if provider == "twilio":
            _send_via_twilio(text)
        elif provider == "meta":
            _send_via_meta(text)
        else:
            raise WhatsAppError(f"WHATSAPP_PROVIDER desconhecido: {provider!r}")
    except KeyError as exc:
        raise WhatsAppError(
            f"Variável de ambiente ausente para o provedor {provider!r}: {exc}"
        ) from exc


def _send_via_twilio(text: str) -> None:
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_WHATSAPP_FROM"]
    to_number = os.environ["WHATSAPP_TO"]

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    resp = requests.post(
        url,
        auth=(account_sid, auth_token),
        data={"From": from_number, "To": to_number, "Body": text},
        timeout=15,
    )
    if resp.status_code >= 300:
        raise WhatsAppError(f"Twilio retornou {resp.status_code}: {resp.text}")


def _send_via_meta(text: str) -> None:
    phone_number_id = os.environ["META_PHONE_NUMBER_ID"]
    access_token = os.environ["META_ACCESS_TOKEN"]
    to_number = os.environ["META_TO_NUMBER"]
    template_name = os.getenv("META_TEMPLATE_NAME")
    template_lang = os.getenv("META_TEMPLATE_LANG", "pt_BR")

    url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}"}

    if template_name:
        # Necessário para mensagens iniciadas pelo negócio fora da janela de
        # 24h de atendimento. O template precisa aceitar 1 parâmetro de texto.
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": template_lang},
                "components": [
                    {"type": "body", "parameters": [{"type": "text", "text": text}]}
                ],
            },
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": text},
        }

    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    if resp.status_code >= 300:
        raise WhatsAppError(f"Meta Cloud API retornou {resp.status_code}: {resp.text}")
