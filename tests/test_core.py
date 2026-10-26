import json
import queue
import time

import numpy as np

from capri.actions import Actions
from capri.assistant import Assistant
from capri.audio_in import UtteranceDetector, feed_all
from capri.brain import Brain, clean_for_speech, split_sentences
from capri.config import DEFAULTS, load_config


def cfg():
    c = load_config()
    c["acoes"]["apps"] = {"bloco de notas": "notepad", "navegador": "https://example.com"}
    return c


# -- config ------------------------------------------------------------------
def test_config_loads_and_merges(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('[llm]\nmodelo = "outro"\n', encoding="utf-8")
    c = load_config(p)
    assert c["llm"]["modelo"] == "outro"
    assert c["llm"]["num_ctx"] == DEFAULTS["llm"]["num_ctx"]


def test_repo_config_is_valid():
    c = load_config()
    assert c["tts"]["voz_edge"].startswith("pt-BR")
    assert c["stt"]["idioma"] == "pt"


# -- frases ------------------------------------------------------------------
def test_split_sentences():
    done, rest = split_sentences("Oi! Tudo bem? Estou aqui")
    assert done == ["Oi!", "Tudo bem?"]
    assert rest == "Estou aqui"


def test_split_sentences_no_boundary():
    assert split_sentences("sem fim") == ([], "sem fim")


def test_clean_for_speech():
    assert clean_for_speech("**Olá** `mundo` 😀 [link](http://x.com)") == "Olá mundo link"


# -- ações -------------------------------------------------------------------
def test_actions_time_and_date():
    a = Actions(cfg())
    assert "Agora são" in a.handle("Que horas são?").reply
    assert "Hoje é" in a.handle("que dia é hoje").reply


def test_actions_unknown_app_and_passthrough():
    a = Actions(cfg())
    r = a.handle("abre o photoshop")
    assert r.handled and "config.toml" in r.reply
    assert not a.handle("me conta uma piada").handled


def test_actions_search_opens_browser(monkeypatch):
    opened = []
    monkeypatch.setattr("capri.actions.webbrowser.open", lambda u: opened.append(u))
    r = Actions(cfg()).handle("Pesquisa sobre música brasileira")
    assert r.handled and "m%C3%BAsica+brasileira" in opened[0]
    assert "música brasileira" in r.reply


def test_actions_disabled():
    c = cfg()
    c["acoes"]["habilitado"] = False
    assert not Actions(c).handle("que horas são").handled


# -- VAD ---------------------------------------------------------------------
def test_detector_finds_utterance():
    sr = 16000
    det = UtteranceDetector(sr, threshold=0.01, silence_s=0.3, max_s=5)
    quiet = np.zeros(int(sr * 0.05), dtype=np.float32)
    loud = np.full(int(sr * 0.05), 0.2, dtype=np.float32)
    blocks = [quiet] * 5 + [loud] * 10 + [quiet] * 10
    audio = feed_all(det, blocks)
    assert audio is not None
    assert 0.5 <= len(audio) / sr <= 1.0


def test_detector_ignores_pure_silence():
    det = UtteranceDetector(16000, 0.01, 0.3, 5)
    assert feed_all(det, [np.zeros(800, dtype=np.float32)] * 50) is None


def test_detector_respects_max_length():
    det = UtteranceDetector(16000, 0.01, 10.0, 0.5)
    loud = np.full(800, 0.2, dtype=np.float32)
    assert feed_all(det, [loud] * 100) is not None


# -- cérebro (Ollama simulado) -----------------------------------------------
class FakeResp:
    def __init__(self, pieces):
        self.pieces = pieces

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        pass

    def iter_lines(self):
        for p in self.pieces:
            yield json.dumps({"message": {"content": p}, "done": False}).encode()
        yield json.dumps({"message": {"content": ""}, "done": True}).encode()


def test_brain_streams_sentences_and_keeps_history(monkeypatch):
    monkeypatch.setattr(
        "capri.brain.requests.post",
        lambda *a, **k: FakeResp(["Oi, ", "tudo bem? ", "Eu sou a ", "Capri!"]),
    )
    b = Brain(cfg())
    assert list(b.stream_sentences("oi")) == ["Oi, tudo bem?", "Eu sou a Capri!"]
    assert [m["role"] for m in b.history] == ["user", "assistant"]


def test_brain_history_trim_starts_with_user():
    c = cfg()
    c["llm"]["historico_max"] = 4
    b = Brain(c)
    for i in range(6):
        b.history.append({"role": "user", "content": str(i)})
        b.history.append({"role": "assistant", "content": str(i)})
    b._trim()
    assert b.history[0]["role"] == "user" and len(b.history) <= 4


# -- orquestração com peças falsas -------------------------------------------
class FakeTTS:
    def __init__(self):
        self.said = []

    def speak(self, t):
        self.said.append(t)

    def stop(self):
        pass


class FakeBrain:
    def stream_sentences(self, text):
        yield "Resposta um."
        yield "Resposta dois."

    def check(self):
        pass


def drain(bot):
    out = []
    while True:
        try:
            out.append(bot.events.get_nowait())
        except queue.Empty:
            return out


def test_assistant_turn_speaks_and_emits():
    tts = FakeTTS()
    bot = Assistant(cfg(), tts=tts, brain=FakeBrain())
    bot._run_turn("fala algo")
    ev = drain(bot)
    kinds = [k for k, _ in ev]
    assert "user" in kinds and "assistant" in kinds
    assert tts.said == ["Resposta um.", "Resposta dois."]
    assert ("assistant", "Resposta um. Resposta dois.") in ev
    assert ev[-1] == ("status", "idle")


def test_assistant_action_skips_llm():
    tts = FakeTTS()
    bot = Assistant(cfg(), tts=tts, brain=object())  # brain falso quebraria se fosse usado
    bot._run_turn("que horas são")
    assert tts.said and "Agora são" in tts.said[0]


def test_assistant_reports_busy():
    bot = Assistant(cfg(), tts=FakeTTS(), brain=FakeBrain())
    bot._turn.acquire()
    bot._run_turn("oi")
    assert any(k == "error" for k, _ in drain(bot))
    bot._turn.release()


def test_assistant_text_only_mode():
    c = cfg()
    c["assistente"]["falar_respostas"] = False
    tts = FakeTTS()
    bot = Assistant(c, tts=tts, brain=FakeBrain())
    bot._run_turn("oi")
    assert tts.said == []


def test_assistant_submit_text_runs_in_thread():
    bot = Assistant(cfg(), tts=FakeTTS(), brain=FakeBrain())
    bot.submit_text("oi")
    for _ in range(50):
        if any(k == "assistant" for k, _ in list(bot.events.queue)):
            break
        time.sleep(0.05)
    assert any(k == "assistant" for k, _ in list(bot.events.queue))
