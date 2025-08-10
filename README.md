# Envio de Mensagens via API — App GUI (v2.5)

Aplicativo desktop (Tkinter) para envio automatizado de mensagens por API, com suporte a texto e mídia, processamento multithread, delays aleatórios, pausa/retomada/cancelamento, logs em tempo real e planilha de resultados.

Licença: CC BY-NC-ND 4.0. Consulte o arquivo LICENSE.

## Visão geral

O app lê uma planilha Excel com a coluna "Telefone Celular", carrega uma mensagem de um arquivo .txt, opcionalmente anexa uma imagem (jpg/jpeg/png) e envia para cada contato usando uma API HTTP autenticada por token. O resultado de cada envio é salvo em um novo arquivo Excel com status e detalhes por linha.

Principais recursos:
- Interface gráfica simples (Tkinter) para selecionar arquivos e operar.
- Envio de mensagem de texto ou de mídia (upload do arquivo + mensagem de texto).
- Multithread (5 workers) com delays aleatórios entre envios.
- Botões Pausar/Continuar e Cancelar; barra de progresso e log em tempo real.
- Normalização automática dos números para o padrão brasileiro (55 + 10/11 dígitos).
- Geração de planilha de resultados: `<nome_da_planilha>_RESULTADOS.xlsx` com colunas `status_envio` e `detalhes_envio`.

## Requisitos

- Windows com Python 3.13+ (funciona também em versões 3.10+)
- Dependências Python: pandas, openpyxl, requests, python-dotenv, tkinter (padrão no Python para Windows)

Instalação rápida (PowerShell):

```
py -3.13 -m venv venv
./venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
```

## Configuração

Crie/preencha um arquivo `config.env` (ou use o botão da interface para selecionar) com:

```
API_URL=https://sua.api/de/envio
API_TOKEN=seu_token_aqui
```

Planilha de entrada (ex.: `clientes.xlsx`):
- Deve conter a coluna `Telefone Celular` (valores numéricos ou texto). Outros campos serão preservados.

Mensagem:
- Arquivo `.txt` em UTF-8 com o corpo da mensagem.

Imagem (opcional):
- Arquivo `.jpg`, `.jpeg` ou `.png` para anexar aos envios.

## Como usar

1) Execute o aplicativo:

```
python .\main.py
```

2) Na interface:
- Clique em "Selecionar Config.env" e aponte para o seu `config.env`.
- Em "Arquivos de Entrada": selecione a planilha, a mensagem (.txt) e, opcionalmente, a imagem.
- Em "Configuração de Delay": ajuste os valores mínimo e máximo (segundos) entre envios.
- Clique em "Iniciar Envio". Use "Pausar/Continuar" e "Cancelar" conforme necessário.

3) Saída:
- Ao final, será gerado o arquivo `<planilha>_RESULTADOS.xlsx` com as colunas adicionadas `status_envio` e `detalhes_envio`.

## Detalhes técnicos

- API: envio de texto via JSON; envio de mídia via multipart (campo `medias`), seguido de envio de texto.
- Autenticação: header `Authorization: Bearer <API_TOKEN>`.
- Padrão de número: normalização para `55` + 10/11 dígitos (remove símbolos/DDD duplicado).
- Concorrência: 5 threads; delays aleatórios entre `mín` e `máx` (segundos).
- Logs: exibidos em tempo real na GUI; formatação `HH:MM:SS - LEVEL - mensagem`.
- Erros: são capturados e registrados; cada linha recebe o status (`Enviado`, `Erro`, etc.) e detalhes da falha (ex.: timeout, arquivo ausente, número inválido).

## Executável (opcional)

Se desejar empacotar como EXE (PyInstaller instalado):

```
py -3.13 -m pip install pyinstaller
py -3.13 -m PyInstaller --noconsole --onefile --name EnvioMensagens .\main.py
```

O binário será gerado em `dist/EnvioMensagens.exe`.

## Atualizações recentes (v2.5 — 2025-08-10)

- Refatoração com classe `APIClient` para isolar chamadas HTTP.
- Suporte a envio de mídia (upload do arquivo + mensagem de texto).
- GUI aprimorada: botões Pausar/Continuar/Cancelar e botão "Sobre".
- Barra de progresso e log não bloqueante via `QueueHandler`.
- Normalização mais robusta dos números brasileiros.
- Paralelismo com 5 threads e delays configuráveis entre envios.
- Geração do arquivo de resultados com `status_envio` e `detalhes_envio`.
- Leitura de variáveis `API_URL` e `API_TOKEN` do `config.env` (via `python-dotenv`).

## Solução de problemas (FAQ)

- "API_URL ou API_TOKEN não encontrados": verifique o `config.env` e se foi selecionado na GUI.
- "Coluna 'Telefone Celular' não existe": confirme o nome da coluna e o tipo (texto/número) no Excel.
- "Permissão negada ao salvar resultados": feche a planilha no Excel antes de iniciar o envio.
- "ImportError: tkinter": reinstale o Python com suporte a Tcl/Tk (Windows installer padrão).
- Timeouts/erros de rede: valide conectividade e se o endpoint aceita os campos usados.

## Licença

Este projeto está licenciado sob a [Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International](LICENSE).

