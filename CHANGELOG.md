# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e este projeto usa versionamento semântico simples (ex.: 2.5).

## [2.5] - 2025-08-10

### Adicionado
- Classe `APIClient` para encapsular chamadas HTTP à API (texto e mídia) com autenticação via `Bearer`.
- Suporte a envio de mídia (multipart/form-data) utilizando o campo `medias`, seguido por envio de texto.
- Interface gráfica (Tkinter) aprimorada com botões: `Iniciar`, `Pausar/Continuar`, `Cancelar` e `Sobre`.
- Barra de progresso e log em tempo real na GUI via `QueueHandler` e `queue` (não bloqueante).
- Normalização automática de números brasileiros para o padrão `55` + 10/11 dígitos.
- Geração automática da planilha de resultados `<planilha>_RESULTADOS.xlsx` com as colunas `status_envio` e `detalhes_envio`.
- Leitura de `API_URL` e `API_TOKEN` a partir de `config.env` usando `python-dotenv`.

### Alterado
- Fluxo de envio agora é multithread (5 workers) com delays aleatórios configuráveis entre os envios.
- Organização da interface com frames para Configuração, Arquivos, Delay, Ações, Progresso e Log; uso do tema `clam` quando disponível.

### Corrigido
- Inclusão do botão "Sobre" e pequenos ajustes de layout.
- Tratamento mais robusto para números iniciados com `55` e com comprimento superior a 11 dígitos (remoção de prefixo duplicado).
- Melhoria no controle de `cancel_event` e `pause_event` para evitar travamentos.

### Documentação
- README reescrito com visão geral, requisitos, guia de uso e FAQ.
- `DOCUMENTACAO.md` adicionado com arquitetura, contratos, fluxo e pontos de extensão.
- `requirements.txt` adicionado com dependências principais (pandas, openpyxl, requests, python-dotenv).

### Segurança
- Recomendação de não versionar `config.env` e evitar expor o token em logs.

---

Entradas anteriores não estavam padronizadas neste formato.

[2.5]: https://github.com/eugustavonsc/Bot-de-msg-que-funciona-via-API/releases/tag/2.5
