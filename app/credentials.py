"""User-managed Azure credentials. No CLI/readback API, files, or fallback vault.

Windows Credential Manager protects data at rest for the current OS account.
It cannot isolate credentials from arbitrary programs running as that account.
"""
import ctypes
import json
import os
import re
import sys
from dataclasses import dataclass, field

TARGET = 'short-video/AzureSpeech/v1'
ERROR = '无法访问安全凭据存储；请检查当前 Windows 用户的凭据管理器'


class CredentialError(ValueError):
    pass


@dataclass(repr=False)
class Credential:
    key: str = field(repr=False)
    region: str

    def __repr__(self):
        return 'Credential(<redacted>)'


def validate(key, region):
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,256}', key):
        raise CredentialError('密钥格式无效；请输入资源密钥，不要输入连接字符串')
    if not isinstance(region, str) or not re.fullmatch(r'[a-z][a-z0-9-]{1,63}', region):
        raise CredentialError('区域格式无效，例如 eastus')
    return Credential(key, region)


class UnsupportedVault:
    available = False
    name = 'unavailable'

    def read(self):
        raise CredentialError('本系统尚未提供受支持的安全存储；不会保存为文件')

    def write(self, credential):
        self.read()

    def delete(self):
        self.read()


class WindowsVault:
    """Fixed generic credential, current user, local-machine persistence only."""
    available = True
    name = 'Windows Credential Manager'

    def __init__(self):
        from ctypes import wintypes as w

        class NativeCredential(ctypes.Structure):
            _fields_ = [('Flags', w.DWORD), ('Type', w.DWORD), ('TargetName', w.LPWSTR),
                        ('Comment', w.LPWSTR), ('LastWritten', w.FILETIME),
                        ('CredentialBlobSize', w.DWORD), ('CredentialBlob', ctypes.POINTER(w.BYTE)),
                        ('Persist', w.DWORD), ('AttributeCount', w.DWORD),
                        ('Attributes', ctypes.c_void_p), ('TargetAlias', w.LPWSTR), ('UserName', w.LPWSTR)]
        self.struct = NativeCredential
        pointer = ctypes.POINTER(NativeCredential)
        self.api = ctypes.WinDLL('advapi32', use_last_error=True)
        for name, args, result in [
            ('CredReadW', [w.LPCWSTR, w.DWORD, w.DWORD, ctypes.POINTER(pointer)], w.BOOL),
            ('CredWriteW', [pointer, w.DWORD], w.BOOL),
            ('CredDeleteW', [w.LPCWSTR, w.DWORD, w.DWORD], w.BOOL),
            ('CredFree', [ctypes.c_void_p], None),
        ]:
            fn = getattr(self.api, name)
            fn.argtypes, fn.restype = args, result

    def read(self):
        pointer = ctypes.POINTER(self.struct)()
        if not self.api.CredReadW(TARGET, 1, 0, ctypes.byref(pointer)):
            if ctypes.get_last_error() == 1168:  # ERROR_NOT_FOUND only
                return None
            raise CredentialError(ERROR)
        try:
            native = pointer.contents
            if not 0 < native.CredentialBlobSize <= 2048:
                raise CredentialError(ERROR)
            data = json.loads(ctypes.string_at(native.CredentialBlob, native.CredentialBlobSize).decode('utf-8'))
            if not isinstance(data, dict) or set(data) != {'key', 'region'}:
                raise CredentialError(ERROR)
            return validate(data['key'], data['region'])
        except Exception:
            raise CredentialError(ERROR) from None
        finally:
            # Best effort only: Python/OS copies cannot be guaranteed erased.
            if pointer.contents.CredentialBlob and pointer.contents.CredentialBlobSize <= 2048:
                ctypes.memset(pointer.contents.CredentialBlob, 0, pointer.contents.CredentialBlobSize)
            self.api.CredFree(pointer)

    def write(self, credential):
        raw = json.dumps({'key': credential.key, 'region': credential.region}).encode('utf-8')
        buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
        native = self.struct()
        native.Type, native.TargetName, native.Persist = 1, TARGET, 2
        native.CredentialBlobSize, native.CredentialBlob = len(raw), buffer
        native.UserName = 'short-video'
        try:
            if not self.api.CredWriteW(ctypes.byref(native), 0):
                raise CredentialError(ERROR)
        finally:
            ctypes.memset(buffer, 0, len(raw))

    def delete(self):
        if not self.api.CredDeleteW(TARGET, 1, 0) and ctypes.get_last_error() != 1168:
            raise CredentialError(ERROR)


def native_vault():
    if sys.platform != 'win32':
        return UnsupportedVault()
    try:
        return WindowsVault()
    except Exception:
        raise CredentialError(ERROR) from None


def environment_credential():
    key, region = os.environ.get('AZURE_SPEECH_KEY'), os.environ.get('AZURE_SPEECH_REGION')
    if key is None and region is None:
        return None
    if not key or not region:
        raise CredentialError('环境变量须同时配置 AZURE_SPEECH_KEY 和 AZURE_SPEECH_REGION；不会混用存储的凭据')
    return validate(key, region)


class CredentialSettings:
    def __init__(self, vault=None):
        self.vault = vault if vault is not None else native_vault()

    def status(self):
        # Deliberately construct an allowlist; never serialize Credential objects.
        saved = self.vault.read() if self.vault.available else None
        env = environment_credential()
        effective = env or saved
        return {'available': self.vault.available, 'backend': self.vault.name,
                'saved': saved is not None, 'configured': effective is not None,
                'region': effective.region if effective else '',
                'source': 'environment' if env else 'vault' if saved else 'none'}

    def save(self, data):
        if set(data) != {'key', 'region'}:
            raise CredentialError('凭据请求只能包含密钥和区域')
        if not self.vault.available:
            raise CredentialError('本系统尚未提供受支持的安全存储；不会保存为文件')
        credential = validate(data['key'], data['region'])
        # Validate environment first, so a malformed env cannot produce ambiguous success.
        environment_credential()
        self.vault.write(credential)
        return self.status()

    def delete(self):
        if not self.vault.available:
            raise CredentialError('本系统尚未提供受支持的安全存储；不会保存为文件')
        self.vault.delete()
        return self.status()


def resolve_credentials():
    """Called inside synthesis only. Never print or serialize its result."""
    env = environment_credential()
    if env:
        return env
    vault = native_vault()
    if not vault.available:
        raise CredentialError('Configure AZURE_SPEECH_KEY and AZURE_SPEECH_REGION locally; secure UI storage is available on Windows only')
    saved = vault.read()
    if saved is None:
        raise CredentialError('请先在本机工作台保存 Azure 凭据，或配置两个 Azure Speech 环境变量')
    return saved


def configured_region():
    # Cache metadata needs the effective region, never the key.
    env = environment_credential()
    if env:
        return env.region
    vault = native_vault()
    saved = vault.read() if vault.available else None
    return saved.region if saved else ''
