"""Utility-Funktionen für DSGVO-konforme Verarbeitung von Telefonnummern.

Die Nummern werden in ein kanonisches E.164-Format gebracht und anschließend
mit einem rotationsfähigen Pepper gehasht (SHA-256). Der Pepper wird aktuell
über Environment-Variablen bereitgestellt und kann später aus Vault/SOPS
bezogen werden.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from typing import Optional

DEFAULT_COUNTRY_CODE = os.getenv('PHONE_DEFAULT_COUNTRY_CODE', '+49')
CURRENT_PEPPER = os.getenv('PHONE_HASH_SALT', 'CHANGE_ME')
PREVIOUS_PEPPER = os.getenv('PHONE_HASH_SALT_PREVIOUS')


class PhoneHashConfigError(RuntimeError):
    """Raised when the hash configuration is invalid."""


def normalize_e164(number: str, default_country_code: Optional[str] = None) -> str:
    """Normalisiert eine Telefonnummer in ein E.164-ähnliches Format.

    * Entfernt alle Nicht-Ziffern außer dem führenden `+`.
    * Wandelt `00`-Präfixe in `+` um.
    * Fügt optional einen Default-Ländercode an, falls kein Präfix vorhanden ist.
    """

    if not number:
        raise ValueError('number must not be empty')

    number = number.strip()
    default_country_code = default_country_code or DEFAULT_COUNTRY_CODE

    # Alles außer + und Ziffern entfernen
    cleaned = re.sub(r'[^0-9+]', '', number)

    if cleaned.startswith('00'):
        cleaned = '+' + cleaned[2:]
    elif cleaned.startswith('+'):
        pass
    elif cleaned.startswith('0') and default_country_code:
        cleaned = default_country_code + cleaned.lstrip('0')
    elif default_country_code:
        cleaned = default_country_code + cleaned
    else:
        cleaned = '+' + cleaned

    if not cleaned.startswith('+'):
        cleaned = '+' + cleaned

    return cleaned


def _hash(value: str, pepper: str) -> str:
    if not pepper or pepper == 'CHANGE_ME':
        raise PhoneHashConfigError('PHONE_HASH_SALT must be configured and rotated via Vault/SOPS')
    digest = hashlib.sha256()
    digest.update(pepper.encode('utf-8'))
    digest.update(value.encode('utf-8'))
    return digest.hexdigest()


@dataclass(frozen=True)
class PhoneHash:
    value: str
    normalized: str
    pepper_id: str


def hash_phone_number(number: str, *, pepper: Optional[str] = None, pepper_id: str = 'current') -> PhoneHash:
    """Hash eine Telefonnummer mit SHA-256 und Pepper.

    Gibt ein ``PhoneHash``-Objekt zurück, damit Aufrufer zusätzliche Metadaten
    (z. B. Pepper-ID) für Audits speichern können.
    """

    normalized = normalize_e164(number)
    selected_pepper = (pepper if pepper is not None else CURRENT_PEPPER)
    hashed = _hash(normalized, selected_pepper)
    return PhoneHash(value=hashed, normalized=normalized, pepper_id=pepper_id)


def rehash_with_previous_pepper(number: str) -> Optional[PhoneHash]:
    """Falls ein vorheriger Pepper existiert, liefere den Hash dafür."""

    if not PREVIOUS_PEPPER:
        return None
    normalized = normalize_e164(number)
    hashed = _hash(normalized, PREVIOUS_PEPPER)
    return PhoneHash(value=hashed, normalized=normalized, pepper_id='previous')


def mask_number(number: str) -> str:
    """Erzeugt eine maskierte Darstellung (z. B. +49 **** 1234) für Logs."""

    normalized = normalize_e164(number)
    if len(normalized) <= 6:
        return normalized
    return f"{normalized[:4]}****{normalized[-4:]}"

