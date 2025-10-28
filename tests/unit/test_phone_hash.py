import hashlib
import importlib
import os

import pytest


MODULE_PATH = 'apps.security.phone_hash'


def reload_module(**env):
    saved_env = {key: os.environ.get(key) for key in env.keys()}
    try:
        os.environ.update(env)
        if 'PHONE_HASH_SALT' not in os.environ:
            os.environ['PHONE_HASH_SALT'] = 'unit-test-pepper'
        if 'PHONE_DEFAULT_COUNTRY_CODE' not in os.environ:
            os.environ['PHONE_DEFAULT_COUNTRY_CODE'] = '+49'
        module = importlib.import_module(MODULE_PATH)
        return importlib.reload(module)
    finally:
        for key, value in saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def sha256_hex(pepper: str, number: str) -> str:
    digest = hashlib.sha256()
    digest.update(pepper.encode('utf-8'))
    digest.update(number.encode('utf-8'))
    return digest.hexdigest()


def test_hash_phone_number_with_default_country_code():
    pepper = 'pepper-1234'
    module = reload_module(PHONE_HASH_SALT=pepper, PHONE_HASH_SALT_PREVIOUS='')

    phone_hash = module.hash_phone_number('030 1234567')

    assert phone_hash.normalized == '+49301234567'
    assert phone_hash.pepper_id == 'current'
    assert phone_hash.value == sha256_hex(pepper, '+49301234567')


def test_rehash_with_previous_pepper():
    current = 'pepper-current'
    previous = 'pepper-prev'
    module = reload_module(
        PHONE_HASH_SALT=current,
        PHONE_HASH_SALT_PREVIOUS=previous,
    )

    prev_hash = module.rehash_with_previous_pepper('+49 160 1112233')

    assert prev_hash is not None
    assert prev_hash.normalized == '+491601112233'
    assert prev_hash.pepper_id == 'previous'
    assert prev_hash.value == sha256_hex(previous, '+491601112233')


def test_mask_number_hides_middle_digits():
    module = reload_module(PHONE_HASH_SALT='pepper', PHONE_HASH_SALT_PREVIOUS='')

    masked = module.mask_number('+4915112345678')
    assert masked.startswith('+4915')
    assert masked.endswith('5678')
    assert '1234' not in masked


def test_missing_pepper_raises_config_error():
    module = reload_module(PHONE_HASH_SALT='CHANGE_ME', PHONE_HASH_SALT_PREVIOUS='')

    with pytest.raises(module.PhoneHashConfigError):
        module.hash_phone_number('+491234567890')

