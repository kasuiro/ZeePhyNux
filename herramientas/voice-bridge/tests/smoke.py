#!/usr/bin/env python3
"""Offline smoke tests for voice-bridge. No network, no microphone, no vault."""
import copy
import io
import json
import pathlib
import sys
import tempfile
import unittest
import wave
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import mcp  # noqa: E402
import voicectl  # noqa: E402


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class VoiceBridgeSmoke(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.rules = voicectl.load_rules()
        self.rules["paths"]["state"] = self.tmp.name
        self.rules["deliver"]["backend"] = "none"
        self.wav = pathlib.Path(self.tmp.name) / "sample.wav"
        with wave.open(str(self.wav), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(16000)
            out.writeframes(b"\x00\x00" * 16000)

    def test_rules_defaults(self):
        self.assertEqual(self.rules["stt"]["provider"], "cloudflare")
        self.assertEqual(self.rules["stt"]["providers"]["cloudflare"]["model"],
                         "@cf/openai/whisper")
        self.assertEqual(self.rules["stt"]["language"], "es")
        self.assertEqual(self.rules["deliver"]["backend"], "none")

    def test_no_key_by_default(self):
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "groq"
        missing = pathlib.Path(self.tmp.name) / "no-key"
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(voicectl, "DEFAULT_KEY_FILE", missing):
            self.assertFalse(voicectl.key_ready())
            with self.assertRaises(RuntimeError):
                voicectl.transcribe_file(self.wav, rules)

    def test_key_from_default_file(self):
        key_file = pathlib.Path(self.tmp.name) / "key"
        key_file.write_text("gsk_test_only\n", encoding="utf-8")
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(voicectl, "DEFAULT_KEY_FILE", key_file):
            self.assertTrue(voicectl.key_ready())
            self.assertEqual(voicectl.api_key(), "gsk_test_only")

    def test_wav_duration(self):
        self.assertEqual(voicectl.wav_seconds(self.wav), 1.0)

    def test_groq_request_and_response(self):
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "groq"
        payload = json.dumps({"text": "  hola mundo  "}).encode()
        with mock.patch.dict("os.environ", {"GROQ_API_KEY": "unit-test-key"}):
            with mock.patch("urllib.request.urlopen",
                            return_value=FakeResponse(payload)) as request:
                result = voicectl.transcribe_file(self.wav, rules, hint="zeep")
        self.assertEqual(result["text"], "hola mundo")
        self.assertEqual(result["seconds"], 1.0)
        args = request.call_args.args[0]
        self.assertEqual(args.get_header("Authorization"), "Bearer unit-test-key")
        body = args.data.decode("utf-8", "ignore")
        self.assertIn("whisper-large-v3-turbo", body)
        self.assertIn("zeep", body)

    def test_cloudflare_request_and_response(self):
        payload = json.dumps({"success": True,
                              "result": {"text": "  hola nube  "}}).encode()
        env = {"CLOUDFLARE_API_TOKEN": "cf-token", "CF_ACCOUNT_ID": "acct"}
        with mock.patch.dict("os.environ", env):
            with mock.patch("urllib.request.urlopen",
                            return_value=FakeResponse(payload)) as request:
                result = voicectl.transcribe_file(self.wav, self.rules)
        self.assertEqual(result["text"], "hola nube")
        self.assertEqual(result["model"], "@cf/openai/whisper")
        args = request.call_args.args[0]
        self.assertEqual(
            args.full_url,
            "https://api.cloudflare.com/client/v4/accounts/acct/ai/run/@cf/openai/whisper")
        self.assertEqual(args.get_header("Authorization"), "Bearer cf-token")
        self.assertEqual(args.data, self.wav.read_bytes())

    def test_cloudflare_credentials_from_files(self):
        token = pathlib.Path(self.tmp.name) / "cf_token"
        account = pathlib.Path(self.tmp.name) / "cf_account"
        token.write_text("cf-file-token\n", encoding="utf-8")
        account.write_text("acct-file\n", encoding="utf-8")
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(voicectl, "DEFAULT_CF_TOKEN_FILE", token), \
                mock.patch.object(voicectl, "DEFAULT_CF_ACCOUNT_FILE", account):
            self.assertEqual(voicectl.cloudflare_credentials(),
                             ("cf-file-token", "acct-file"))

    def test_cloudflare_missing_credentials(self):
        missing = pathlib.Path(self.tmp.name) / "missing"
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(voicectl, "DEFAULT_CF_TOKEN_FILE", missing), \
                mock.patch.object(voicectl, "DEFAULT_CF_ACCOUNT_FILE", missing):
            with self.assertRaises(RuntimeError):
                voicectl.transcribe_file(self.wav, self.rules)

    def test_last_roundtrip(self):
        state = voicectl.state_dir(self.rules)
        (state / "last.txt").write_text("texto anterior")
        self.assertEqual(voicectl.last(self.rules), "texto anterior")

    def test_status(self):
        info = voicectl.status(self.rules)
        self.assertFalse(info["recording"])
        self.assertEqual(info["provider"], "cloudflare")
        self.assertEqual(info["language"], "es")
        self.assertIn("state", info)

    def test_deliver_none(self):
        self.assertEqual(voicectl.deliver("hola", self.rules), "none")

    def test_deliver_clipboard_fallback(self):
        rules = dict(self.rules)
        rules["deliver"] = {"backend": "clipboard", "suffix": "\r"}
        with mock.patch("subprocess.run") as run:
            self.assertEqual(voicectl.deliver("hola", rules), "clipboard")
        self.assertEqual(run.call_args.kwargs["input"], b"hola")

    def test_pty_discovery_is_safe(self):
        self.assertIsInstance(voicectl._kitty_master(), (str, type(None)))

    def test_mcp_initialize_and_list(self):
        init = mcp.respond({"id": 1, "method": "initialize"})
        self.assertEqual(init["result"]["serverInfo"]["name"], "voice-bridge")
        tools = mcp.respond({"id": 2, "method": "tools/list"})
        names = [tool["name"] for tool in tools["result"]["tools"]]
        self.assertEqual(names, ["listen", "transcribe", "last", "languages"])

    def test_mcp_last_and_languages(self):
        (voicectl.state_dir(self.rules) / "last.txt").write_text("hola")
        with mock.patch.object(voicectl, "last", return_value="hola"):
            result = mcp.respond({"id": 3, "method": "tools/call",
                                  "params": {"name": "last", "arguments": {}}})
        self.assertEqual(json.loads(result["result"]["content"][0]["text"])["text"], "hola")
        result = mcp.respond({"id": 4, "method": "tools/call",
                              "params": {"name": "languages", "arguments": {}}})
        self.assertIn("es", json.loads(result["result"]["content"][0]["text"])["languages"])

    def test_mcp_listen_error_shape(self):
        with mock.patch.object(voicectl, "listen",
                               return_value={"text": "", "seconds": 1}):
            result = mcp.respond({"id": 5, "method": "tools/call",
                                  "params": {"name": "listen", "arguments": {}}})
        self.assertTrue(result["result"]["isError"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
