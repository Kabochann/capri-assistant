# Capri Assistant

Assistente virtual **local** para Windows, feito por fã: conversa por **voz e texto em português do Brasil**, com uma janela flutuante e o avatar que você escolher. Tudo roda no seu PC, sem API paga.

| Parte   | Tecnologia                                  | Onde roda                      |
|---------|---------------------------------------------|--------------------------------|
| Cérebro | [Ollama](https://ollama.com) + `qwen2.5:7b-instruct` | Placa de vídeo (cabe numa RTX 4060) |
| Ouvido  | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | GPU ou CPU (automático)        |
| Voz     | edge-tts (natural, precisa de internet) ou voz do Windows (offline) | -                              |
| Janela  | tkinter + Pillow                            | -                              |

> Projeto de fã sem fins lucrativos, sem relação com CD Projekt Red, Studio Trigger ou Netflix.
> O repositório **não inclui o avatar**: você coloca a imagem que quiser em `assets/`.

## Instalação (Windows)

1. Instale o **Python 3.11 ou 3.12** ([python.org](https://www.python.org/downloads/)), marcando *Add Python to PATH*.
2. Instale o **Ollama** ([ollama.com/download](https://ollama.com/download)) e deixe-o aberto.
3. Baixe este repositório e dê dois cliques em **`setup_windows.bat`**. Ele cria o ambiente, instala as dependências e baixa o modelo (~5 GB, só na primeira vez).
4. Dê dois cliques em **`run.bat`**.

## Como usar

- **Texto:** digite na caixinha e aperte Enter.
- **Voz:** clique em 🎤, fale, e pare de falar. Ela detecta o silêncio sozinha.
- **∞ (modo contínuo):** ela escuta o tempo todo e responde quando você falar (pausa enquanto ela fala). Também dá para ligar em `config.toml` com `modo_escuta = "continuo"`.
- **■** interrompe a fala dela. **✕** fecha. Arraste a janela pelo avatar.
- Modo terminal, sem janela: `run.bat --texto`.

Comandos que mexem no PC (só a lista abaixo, nada além):

- "que horas são", "que dia é hoje"
- "pesquisa sobre ..." (abre o Google no navegador)
- "abre o bloco de notas / calculadora / spotify..." (programas listados em `[acoes.apps]` no `config.toml`)

## Seu avatar

Coloque PNGs com fundo transparente em `assets/` (`idle.png`, `listening.png`, `thinking.png`, `speaking.png`, `speaking2.png`). Veja [`assets/README.md`](assets/README.md). Sem imagens, aparece um orbe colorido genérico.

## Configuração

Tudo está no [`config.toml`](config.toml), com comentários. Os ajustes mais úteis:

- `llm.modelo`: troque por outro modelo do Ollama (rode `ollama pull <nome>` antes). Numa placa de 8 GB, escolha modelos de até ~8B parâmetros.
- `stt.modelo`: `small` é um bom equilíbrio; `medium` entende melhor, mas é mais pesado.
- `tts.motor`: `edge` (voz natural, online) ou `offline`. `tts.voz_edge` aceita outras vozes, como `pt-BR-AntonioNeural`.
- `audio.limiar_voz`: se ela não te ouve, diminua; se capta ruído, aumente.
- `persona.py`: o texto que define a personalidade dela.

## Problemas comuns

- **"Não consegui falar com o Ollama"**: abra o Ollama e confira se o modelo foi baixado (`ollama list`).
- **Reconhecimento de voz lento**: instale as bibliotecas CUDA (`pip install -r requirements-gpu.txt` dentro do `.venv`) para usar a placa de vídeo. Sem elas, funciona na CPU.
- **Ela não te ouve**: confira o microfone padrão do Windows ou defina `audio.dispositivo_entrada` no `config.toml`.
- **Sem internet**: ela troca sozinha para a voz offline do Windows.

## Desenvolvimento

```bash
pip install pytest
pytest
```

Estrutura: `capri/brain.py` (conversa), `stt.py` (ouvido), `tts.py` (voz), `audio_in.py` (microfone), `actions.py` (comandos), `assistant.py` (orquestra), `gui.py` (janela).
