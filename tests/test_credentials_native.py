"""Mocked WinCred API only: exercises ctypes paths without opening any OS vault.

These tests verify control flow and memory cleanup, not the real Windows ABI,
OS encryption, or interoperability. Native Windows validation remains required.
"""
import ctypes
from ctypes import wintypes
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app.credentials import Credential, CredentialError, TARGET, WindowsVault

FAKE_KEY = 'FAKE-NATIVE-SECRET-123456789'


class NativeVaultContractTests(unittest.TestCase):
    def setUp(self):
        self.api = SimpleNamespace(**{name: Mock() for name in
                                    ('CredReadW', 'CredWriteW', 'CredDeleteW', 'CredFree')})
        with patch.object(ctypes, 'WinDLL', return_value=self.api, create=True) as loader:
            self.vault = WindowsVault()
        loader.assert_called_once_with('advapi32', use_last_error=True)

    def supply_blob(self, raw, size=None):
        # Keep both buffers alive through the fake CredFree callback.
        self.buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
        self.native = self.vault.struct()
        self.native.CredentialBlobSize = len(raw) if size is None else size
        self.native.CredentialBlob = self.buffer
        def read(target, kind, flags, out):
            self.assertEqual((target, kind, flags), (TARGET, 1, 0))
            ctypes.cast(out, ctypes.POINTER(ctypes.POINTER(self.vault.struct)))[0] = ctypes.pointer(self.native)
            return True
        self.api.CredReadW.side_effect = read

    def test_signatures_and_structure_contract(self):
        pointer = ctypes.POINTER(self.vault.struct)
        self.assertEqual(self.api.CredReadW.argtypes,
                         [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(pointer)])
        self.assertEqual(self.api.CredWriteW.argtypes, [pointer, wintypes.DWORD])
        self.assertEqual(self.api.CredDeleteW.argtypes,
                         [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD])
        self.assertEqual(self.api.CredFree.argtypes, [ctypes.c_void_p])
        self.assertIsNone(self.api.CredFree.restype)
        self.assertEqual([name for name, _ in self.vault.struct._fields_],
                         ['Flags', 'Type', 'TargetName', 'Comment', 'LastWritten',
                          'CredentialBlobSize', 'CredentialBlob', 'Persist',
                          'AttributeCount', 'Attributes', 'TargetAlias', 'UserName'])

    def test_read_success_zeroes_blob_and_frees_once(self):
        self.supply_blob(json.dumps({'key': FAKE_KEY, 'region': 'eastus'}).encode())
        value = self.vault.read()
        self.assertEqual((value.key, value.region), (FAKE_KEY, 'eastus'))
        self.assertNotIn(FAKE_KEY, repr(value))
        self.assertEqual(bytes(self.buffer), b'\0' * len(self.buffer))
        self.api.CredFree.assert_called_once()
        freed = self.api.CredFree.call_args.args[0]
        self.assertEqual(ctypes.addressof(freed.contents), ctypes.addressof(self.native))

    def test_corrupt_and_oversized_read_free_without_echo(self):
        for raw, size in [(FAKE_KEY.encode(), None), (b'{}', 2049),
                          (json.dumps({'key': FAKE_KEY, 'region': 'eastus', 'extra': 'bad'}).encode(), None)]:
            with self.subTest(size=size, length=len(raw)):
                self.api.CredFree.reset_mock()
                self.supply_blob(raw, size)
                with self.assertRaises(CredentialError) as result:
                    self.vault.read()
                self.assertNotIn(FAKE_KEY, str(result.exception))
                self.api.CredFree.assert_called_once()
                if size is None:
                    self.assertEqual(bytes(self.buffer), b'\0' * len(self.buffer))
                else:
                    # A corrupt oversized length must not be used for a memory overwrite.
                    self.assertEqual(bytes(self.buffer), raw)

    def test_write_flags_atomic_blob_and_cleanup_on_success_or_failure(self):
        for succeeds in (True, False):
            with self.subTest(succeeds=succeeds):
                captured = {}
                def write(pointer, flags):
                    native = pointer._obj  # Retain ctypes buffer owner after the API returns.
                    captured['native'] = native
                    captured['data'] = json.loads(ctypes.string_at(native.CredentialBlob, native.CredentialBlobSize))
                    self.assertEqual(flags, 0)
                    self.assertEqual((native.Flags, native.Type, native.Persist), (0, 1, 2))
                    self.assertEqual(native.TargetName, TARGET)
                    self.assertEqual(native.UserName, 'short-video')
                    self.assertIsNone(native.Comment)
                    self.assertEqual(native.AttributeCount, 0)
                    self.assertLessEqual(native.CredentialBlobSize, 2560)
                    return succeeds
                self.api.CredWriteW.side_effect = write
                if succeeds:
                    self.vault.write(Credential(FAKE_KEY, 'eastus'))
                else:
                    with self.assertRaises(CredentialError) as result:
                        self.vault.write(Credential(FAKE_KEY, 'eastus'))
                    self.assertNotIn(FAKE_KEY, str(result.exception))
                self.assertEqual(captured['data'], {'key': FAKE_KEY, 'region': 'eastus'})
                native = captured['native']
                self.assertEqual(ctypes.string_at(native.CredentialBlob, native.CredentialBlobSize),
                                 b'\0' * native.CredentialBlobSize)
                self.api.CredFree.assert_not_called()  # Caller-owned write buffer is not WinCred allocated.

    def test_not_found_distinguished_from_denied_and_delete_idempotent(self):
        self.api.CredReadW.return_value = False
        self.api.CredDeleteW.return_value = False
        with patch.object(ctypes, 'get_last_error', return_value=1168, create=True):
            self.assertIsNone(self.vault.read())
            self.vault.delete()
        with patch.object(ctypes, 'get_last_error', return_value=5, create=True):
            with self.assertRaises(CredentialError):
                self.vault.read()
            with self.assertRaises(CredentialError):
                self.vault.delete()
        self.api.CredFree.assert_not_called()
        self.api.CredDeleteW.assert_called_with(TARGET, 1, 0)


if __name__ == '__main__':
    unittest.main()
