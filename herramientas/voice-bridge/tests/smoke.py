#!/usr/bin/env python3
"""Offline smoke tests for voice-bridge. No network, no microphone, no vault."""
import copy
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import urllib.error
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
        self.assertEqual(self.rules["stt"]["provider"], "whisper")
        whisper = self.rules["stt"]["providers"]["whisper"]
        self.assertEqual(whisper["model"], "base")
        self.assertEqual(whisper["compute_type"], "int8")
        self.assertEqual(whisper["cpu_threads"], 4)
        vosk = self.rules["stt"]["providers"]["vosk"]
        self.assertEqual(vosk["model"], "vosk-model-small-es-0.42")
        self.assertEqual(vosk["network"], "none")
        self.assertEqual(self.rules["stt"]["providers"]["cloudflare"]["model"],
                         "@cf/openai/whisper")
        self.assertEqual(self.rules["tts"]["provider"], "piper")
        piper = self.rules["tts"]["providers"]["piper"]
        self.assertEqual(piper["voice_es"], "es_ES-davefx-medium")
        self.assertEqual(piper["voice_en"], "en_US-lessac-medium")
        self.assertEqual(self.rules["stt"]["language"], "auto")
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

    def test_wav_duration_falls_back_to_size(self):
        fake = pathlib.Path(self.tmp.name) / "unfinalised.wav"
        fake.write_bytes(b"RIFF" + b"\x00" * 40 + b"\x00" * 32000)
        self.assertEqual(voicectl.wav_seconds(fake), 1.0)

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
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "cloudflare"
        payload = json.dumps({"success": True,
                              "result": {"text": "  hola nube  "}}).encode()
        env = {"CLOUDFLARE_API_TOKEN": "cf-token", "CF_ACCOUNT_ID": "acct"}
        with mock.patch.dict("os.environ", env):
            with mock.patch("urllib.request.urlopen",
                            return_value=FakeResponse(payload)) as request:
                result = voicectl.transcribe_file(self.wav, rules)
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
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "cloudflare"
        missing = pathlib.Path(self.tmp.name) / "missing"
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(voicectl, "DEFAULT_CF_TOKEN_FILE", missing), \
                mock.patch.object(voicectl, "DEFAULT_CF_ACCOUNT_FILE", missing):
            with self.assertRaises(RuntimeError):
                voicectl.transcribe_file(self.wav, rules)

    def test_last_roundtrip(self):
        state = voicectl.state_dir(self.rules)
        (state / "last.txt").write_text("texto anterior")
        self.assertEqual(voicectl.last(self.rules), "texto anterior")

    def test_status(self):
        info = voicectl.status(self.rules)
        self.assertFalse(info["recording"])
        self.assertEqual(info["provider"], "whisper")
        self.assertTrue(info["credential_ready"])
        self.assertEqual(info["language"], "auto")
        self.assertEqual(info["tts_provider"], "piper")
        self.assertEqual(info["tts_model"], "es_ES-davefx-medium")
        self.assertIn("state", info)

    def _piper_rules(self):
        rules = copy.deepcopy(self.rules)
        rules["tts"]["provider"] = "piper"
        cfg = rules["tts"]["providers"]["piper"]
        python = pathlib.Path(self.tmp.name) / "piper-python"
        python.write_text("")
        data = pathlib.Path(self.tmp.name) / "models"
        data.mkdir(exist_ok=True)
        for name in ("es_ES-davefx-medium", "en_US-lessac-medium"):
            (data / f"{name}.onnx").write_bytes(b"model")
            (data / f"{name}.onnx.json").write_text("{}")
        cfg["python"] = str(python)
        cfg["data_dir"] = str(data)
        return rules, python, data

    @staticmethod
    def _piper_success(cmd, **_kwargs):
        output = pathlib.Path(cmd[cmd.index("-f") + 1])
        output.write_bytes(b"RIFFfake-wav")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def test_piper_one_shot_contract(self):
        rules, python, data = self._piper_rules()
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch("voicectl.subprocess.run",
                           side_effect=self._piper_success) as run:
            result = voicectl.speak("hola mundo", rules, play=False)
        args = run.call_args.args[0]
        self.assertEqual(args[0], str(python))
        self.assertEqual(args[1:3], ["-m", "piper"])
        self.assertEqual(args[args.index("--data-dir") + 1], str(data))
        self.assertEqual(args[args.index("-m", 3) + 1], "es_ES-davefx-medium")
        self.assertEqual(args[-1], "hola mundo")
        self.assertEqual(result["provider"], "piper")
        self.assertEqual(result["speaker"], "es_ES-davefx-medium")
        self.assertEqual(result["bytes"], len(b"RIFFfake-wav"))
        self.assertTrue(result["path"].endswith("reply.wav"))
        self.assertFalse(result["played"])

    def test_piper_english_voice(self):
        rules, _, _ = self._piper_rules()
        with mock.patch("voicectl.subprocess.run",
                        side_effect=self._piper_success) as run:
            result = voicectl.speak("Hello", rules, language="en", play=False)
        args = run.call_args.args[0]
        self.assertEqual(args[args.index("-m", 3) + 1], "en_US-lessac-medium")
        self.assertEqual(result["language"], "en")

    def test_piper_missing_venv(self):
        rules, python, _ = self._piper_rules()
        python.unlink()
        with self.assertRaises(RuntimeError) as caught:
            voicectl.speak("hola", rules, play=False)
        self.assertIn("venv is missing", str(caught.exception))

    def test_piper_failure_reports_last_stderr_line(self):
        rules, _, _ = self._piper_rules()
        proc = subprocess.CompletedProcess(args=[], returncode=1,
                                           stdout="", stderr="oops\nfinal")
        with mock.patch("voicectl.subprocess.run", return_value=proc):
            with self.assertRaises(RuntimeError) as caught:
                voicectl.speak("hola", rules, play=False)
        self.assertIn("final", str(caught.exception))

    def test_unknown_tts_provider(self):
        rules, _, _ = self._piper_rules()
        rules["tts"]["provider"] = "espeak"
        with self.assertRaises(RuntimeError) as caught:
            voicectl.speak("hola", rules, play=False)
        self.assertIn("Unknown TTS provider", str(caught.exception))

    def test_speak_request_and_response(self):
        rules = copy.deepcopy(self.rules)
        rules["tts"]["provider"] = "cloudflare"
        env = {"CLOUDFLARE_API_TOKEN": "cf-token", "CF_ACCOUNT_ID": "acct"}
        with mock.patch.dict("os.environ", env), \
                mock.patch("urllib.request.urlopen",
                           return_value=FakeResponse(b"ID3fake-mp3")) as request, \
                mock.patch("subprocess.run") as play:
            result = voicectl.speak("hola mundo", rules, play=True)
        self.assertEqual(result["model"], "@cf/deepgram/aura-2-es")
        self.assertEqual(result["bytes"], len(b"ID3fake-mp3"))
        self.assertTrue(result["played"])
        self.assertTrue(pathlib.Path(result["path"]).is_file())
        args = request.call_args.args[0]
        self.assertIn("@cf/deepgram/aura-2-es", args.full_url)
        body = json.loads(args.data)
        self.assertEqual(body["text"], "hola mundo")
        self.assertEqual(body["encoding"], "mp3")
        self.assertEqual(play.call_args.args[0][0], "pw-play")

    def test_speak_without_playback(self):
        rules = copy.deepcopy(self.rules)
        rules["tts"]["provider"] = "cloudflare"
        env = {"CLOUDFLARE_API_TOKEN": "cf-token", "CF_ACCOUNT_ID": "acct"}
        with mock.patch.dict("os.environ", env), \
                mock.patch("urllib.request.urlopen",
                           return_value=FakeResponse(b"ID3fake")), \
                mock.patch("subprocess.run") as play:
            result = voicectl.speak("hola", rules, language="en", play=False)
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["model"], "@cf/deepgram/aura-2-en")
        self.assertFalse(result["played"])
        play.assert_not_called()

    def test_voice_preferences(self):
        rules = copy.deepcopy(self.rules)
        rules["tts"]["provider"] = "cloudflare"
        rules["voice"] = {"speaker_es": "nova", "rate": 1.0}
        env = {"CLOUDFLARE_API_TOKEN": "cf-token", "CF_ACCOUNT_ID": "acct"}
        with mock.patch.dict("os.environ", env), \
                mock.patch("urllib.request.urlopen",
                           return_value=FakeResponse(b"ID3fake")) as request, \
                mock.patch("subprocess.run"):
            result = voicectl.speak("hola", rules, play=False)
        body = json.loads(request.call_args.args[0].data)
        self.assertEqual(body["speaker"], "nova")
        self.assertEqual(result["speaker"], "nova")
        self.assertEqual(result["rate"], 1.0)

    def test_detect_language_bilingual(self):
        self.assertEqual(voicectl.detect_language("Hola, ¿cómo estás?"), "es")
        self.assertEqual(voicectl.detect_language("Hello, how are you?"), "en")
        self.assertEqual(voicectl.detect_language("...", default="en"), "en")

    def test_english_uses_english_voice(self):
        rules = copy.deepcopy(self.rules)
        rules["tts"]["provider"] = "cloudflare"
        env = {"CLOUDFLARE_API_TOKEN": "cf-token", "CF_ACCOUNT_ID": "acct"}
        with mock.patch.dict("os.environ", env), \
                mock.patch("urllib.request.urlopen",
                           return_value=FakeResponse(b"ID3fake")) as request, \
                mock.patch("subprocess.run"):
            result = voicectl.speak(
                "Hello, please send the message", rules, language="en",
                play=False)
        body = json.loads(request.call_args.args[0].data)
        self.assertEqual(result["model"], "@cf/deepgram/aura-2-en")
        self.assertEqual(body["speaker"], "asteria")
        self.assertEqual(result["speaker"], "asteria")

    def test_voice_rate_uses_ffmpeg(self):
        rules = copy.deepcopy(self.rules)
        rules["tts"]["provider"] = "cloudflare"
        rules["voice"] = {"speaker": "aquila", "rate": 1.2}
        env = {"CLOUDFLARE_API_TOKEN": "cf-token", "CF_ACCOUNT_ID": "acct"}
        def fake_ffmpeg(args, **_kwargs):
            pathlib.Path(args[-1]).write_bytes(b"ID3adjusted")

        with mock.patch.dict("os.environ", env), \
                mock.patch("urllib.request.urlopen",
                           return_value=FakeResponse(b"ID3fake")), \
                mock.patch("subprocess.run", side_effect=fake_ffmpeg) as run:
            result = voicectl.speak("hola", rules, play=False)
        self.assertEqual(result["rate"], 1.2)
        self.assertIn("atempo=1.2", run.call_args.args[0])

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
        self.assertEqual(names, ["listen", "transcribe", "last", "languages", "speak"])

    def test_mcp_last_and_languages(self):
        (voicectl.state_dir(self.rules) / "last.txt").write_text("hola")
        with mock.patch.object(voicectl, "last", return_value="hola"):
            result = mcp.respond({"id": 3, "method": "tools/call",
                                  "params": {"name": "last", "arguments": {}}})
        self.assertEqual(json.loads(result["result"]["content"][0]["text"])["text"], "hola")
        result = mcp.respond({"id": 4, "method": "tools/call",
                              "params": {"name": "languages", "arguments": {}}})
        self.assertIn("es", json.loads(result["result"]["content"][0]["text"])["languages"])

    def test_mcp_speak(self):
        reply = {"text": "hola", "model": "@cf/deepgram/aura-2-es", "played": False}
        with mock.patch.object(voicectl, "speak", return_value=reply) as speak:
            result = mcp.respond({"id": 6, "method": "tools/call",
                                  "params": {"name": "speak",
                                             "arguments": {"text": "hola", "play": False}}})
        payload = json.loads(result["result"]["content"][0]["text"])
        self.assertEqual(payload["model"], "@cf/deepgram/aura-2-es")
        self.assertFalse(speak.call_args.kwargs["play"])

    def test_mcp_listen_error_shape(self):
        with mock.patch.object(voicectl, "listen",
                               return_value={"text": "", "seconds": 1}):
            result = mcp.respond({"id": 5, "method": "tools/call",
                                  "params": {"name": "listen", "arguments": {}}})
        self.assertTrue(result["result"]["isError"])

    @staticmethod
    def _rate_limit():
        return urllib.error.HTTPError(
            "https://api.cloudflare.com", 429, "Too Many Requests",
            {"Retry-After": "0"}, None)

    def test_429_retries_then_succeeds(self):
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "cloudflare"
        payload = json.dumps({"success": True,
                              "result": {"text": "  hola nube  "}}).encode()
        env = {"CLOUDFLARE_API_TOKEN": "cf-token", "CF_ACCOUNT_ID": "acct"}
        with mock.patch.dict("os.environ", env):
            with mock.patch("voicectl.time.sleep"):
                with mock.patch("urllib.request.urlopen",
                                side_effect=[self._rate_limit(),
                                             FakeResponse(payload)]) as request:
                    result = voicectl.transcribe_file(self.wav, rules)
        self.assertEqual(result["text"], "hola nube")
        self.assertEqual(request.call_count, 2)

    def test_429_exhausts_retries(self):
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "cloudflare"
        rules["api"]["retry_attempts"] = 1
        env = {"CLOUDFLARE_API_TOKEN": "cf-token", "CF_ACCOUNT_ID": "acct"}
        with mock.patch.dict("os.environ", env):
            with mock.patch("voicectl.time.sleep"):
                with mock.patch("urllib.request.urlopen",
                                side_effect=[self._rate_limit(), self._rate_limit()]) as request:
                    with self.assertRaises(RuntimeError) as caught:
                        voicectl.transcribe_file(self.wav, rules)
        self.assertIn("HTTP 429", str(caught.exception))
        self.assertEqual(request.call_count, 2)

    def test_bad_request_is_not_retried(self):
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "cloudflare"
        error = urllib.error.HTTPError("https://api.cloudflare.com", 400,
                                       "Bad Request", {}, None)
        env = {"CLOUDFLARE_API_TOKEN": "cf-token", "CF_ACCOUNT_ID": "acct"}
        with mock.patch.dict("os.environ", env):
            with mock.patch("voicectl.time.sleep"):
                with mock.patch("urllib.request.urlopen", side_effect=error) as request:
                    with self.assertRaises(RuntimeError) as caught:
                        voicectl.transcribe_file(self.wav, rules)
        self.assertIn("HTTP 400", str(caught.exception))
        self.assertEqual(request.call_count, 1)

    def _whisper_rules(self):
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "whisper"
        python = pathlib.Path(self.tmp.name) / "venv-python"
        python.write_text("")
        rules["stt"]["providers"]["whisper"]["python"] = str(python)
        return rules, python

    def _whisper_proc(self, payload="hola desde whisper", language="es",
                      code=0, stderr=""):
        return subprocess.CompletedProcess(
            args=[], returncode=code,
            stdout=json.dumps({"text": payload, "language": language,
                               "model": "base"}) if code == 0 else "",
            stderr=stderr)

    def test_whisper_one_shot_contract(self):
        rules, python = self._whisper_rules()
        with mock.patch("voicectl.subprocess.run",
                        return_value=self._whisper_proc()) as run:
            result = voicectl.transcribe_file(self.wav, rules)
        args, kwargs = run.call_args
        self.assertEqual(args[0][0], str(python))
        self.assertEqual(args[0][-1], str(self.wav.resolve()))
        self.assertEqual(kwargs["env"]["WHISPER_MODEL"], "base")
        self.assertEqual(kwargs["env"]["WHISPER_COMPUTE_TYPE"], "int8")
        self.assertEqual(kwargs["env"]["WHISPER_LANGUAGE"], "auto")
        self.assertEqual(result["text"], "hola desde whisper")
        self.assertEqual(result["language"], "es")
        self.assertEqual(result["model"], "base")

    def test_whisper_forced_language(self):
        rules, _ = self._whisper_rules()
        with mock.patch("voicectl.subprocess.run",
                        return_value=self._whisper_proc("hello", "en")) as run:
            result = voicectl.transcribe_file(self.wav, rules, language="en")
        self.assertEqual(run.call_args.kwargs["env"]["WHISPER_LANGUAGE"], "en")
        self.assertEqual(result["language"], "en")

    def test_whisper_invalid_json(self):
        rules, _ = self._whisper_rules()
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="not-json")
        with mock.patch("voicectl.subprocess.run", return_value=proc):
            with self.assertRaises(RuntimeError) as caught:
                voicectl.transcribe_file(self.wav, rules)
        self.assertIn("invalid JSON", str(caught.exception))

    def test_whisper_missing_venv(self):
        rules, python = self._whisper_rules()
        python.unlink()
        with self.assertRaises(RuntimeError) as caught:
            voicectl.transcribe_file(self.wav, rules)
        self.assertIn("venv is missing", str(caught.exception))

    def test_whisper_failure_reports_last_stderr_line(self):
        rules, _ = self._whisper_rules()
        with mock.patch("voicectl.subprocess.run",
                        return_value=self._whisper_proc(code=1, stderr="oops\nfinal")):
            with self.assertRaises(RuntimeError) as caught:
                voicectl.transcribe_file(self.wav, rules)
        self.assertIn("final", str(caught.exception))

    def test_whisper_timeout(self):
        rules, _ = self._whisper_rules()
        with mock.patch("voicectl.subprocess.run",
                        side_effect=subprocess.TimeoutExpired(["x"], 120)):
            with self.assertRaises(RuntimeError) as caught:
                voicectl.transcribe_file(self.wav, rules)
        self.assertIn("timed out", str(caught.exception))

    def test_whisper_needs_no_credentials(self):
        rules, _ = self._whisper_rules()
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertTrue(voicectl.credential_ready(rules))

    def _vosk_proc(self, payload="hola desde vosk", code=0, stderr=""):
        return subprocess.CompletedProcess(
            args=[], returncode=code,
            stdout=json.dumps({"text": payload, "engine": "vosk"}) if code == 0 else "",
            stderr=stderr)

    def test_vosk_one_shot_contract(self):
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "vosk"
        with mock.patch("voicectl.shutil.which", return_value="/usr/bin/docker"), \
                mock.patch("voicectl.subprocess.run",
                           return_value=self._vosk_proc()) as run:
            result = voicectl.transcribe_file(self.wav, rules)
        args = run.call_args.args[0]
        self.assertEqual(args[0:2], ["docker", "run"])
        self.assertEqual(args[2], "--rm")
        self.assertEqual(args[3:5], ["--network", "none"])
        self.assertTrue(any(a.endswith(":/in.wav:ro") for a in args))
        self.assertEqual(args[-1], "voice-bridge-vosk-es:0.42")
        self.assertEqual(result["text"], "hola desde vosk")
        self.assertEqual(result["language"], "es")
        self.assertEqual(result["model"], "vosk-model-small-es-0.42")
        self.assertEqual(result["seconds"], 1.0)

    def test_vosk_english_explicit(self):
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "vosk"
        with mock.patch("voicectl.shutil.which", return_value="/usr/bin/docker"), \
                mock.patch("voicectl.subprocess.run",
                           return_value=self._vosk_proc("hello, this is ready")) as run:
            result = voicectl.transcribe_file(self.wav, rules, language="en")
        self.assertEqual(run.call_args.args[0][-1], "voice-bridge-vosk-en:0.15")
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["model"], "vosk-model-small-en-us-0.15")

    def test_vosk_auto_detects_language(self):
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "vosk"
        with mock.patch("voicectl.shutil.which", return_value="/usr/bin/docker"), \
                mock.patch("voicectl.subprocess.run",
                           return_value=self._vosk_proc("hello, this is ready")):
            result = voicectl.transcribe_file(self.wav, rules)
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["model"], "vosk-model-small-en-us-0.15")
        # Auto uses the Spanish image to capture, then reports the detected language.
        self.assertEqual(result["text"], "hello, this is ready")

    def test_vosk_needs_no_credentials(self):
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "vosk"
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertTrue(voicectl.credential_ready(rules))
            self.assertTrue(voicectl.status(rules)["credential_ready"])

    def test_vosk_missing_docker(self):
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "vosk"
        with mock.patch("voicectl.shutil.which", return_value=None):
            with self.assertRaises(RuntimeError) as caught:
                voicectl.transcribe_file(self.wav, rules)
        self.assertIn("Docker is required", str(caught.exception))

    def test_vosk_container_failure_reports_stderr(self):
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "vosk"
        with mock.patch("voicectl.shutil.which", return_value="/usr/bin/docker"), \
                mock.patch("voicectl.subprocess.run",
                           return_value=self._vosk_proc(code=1, stderr="model not found")):
            with self.assertRaises(RuntimeError) as caught:
                voicectl.transcribe_file(self.wav, rules)
        self.assertIn("model not found", str(caught.exception))

    def test_vosk_invalid_json(self):
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "vosk"
        bad = subprocess.CompletedProcess(args=[], returncode=0, stdout="not-json", stderr="")
        with mock.patch("voicectl.shutil.which", return_value="/usr/bin/docker"), \
                mock.patch("voicectl.subprocess.run", return_value=bad):
            with self.assertRaises(RuntimeError) as caught:
                voicectl.transcribe_file(self.wav, rules)
        self.assertIn("invalid JSON", str(caught.exception))

    def test_vosk_timeout(self):
        rules = copy.deepcopy(self.rules)
        rules["stt"]["provider"] = "vosk"
        with mock.patch("voicectl.shutil.which", return_value="/usr/bin/docker"), \
                mock.patch("voicectl.subprocess.run",
                           side_effect=subprocess.TimeoutExpired(cmd="docker", timeout=60)):
            with self.assertRaises(RuntimeError) as caught:
                voicectl.transcribe_file(self.wav, rules)
        self.assertIn("timed out", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
