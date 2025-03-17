# Automação de Envio de Mensagens

Este script automatiza o processamento de dados de clientes a partir de um arquivo Excel (`clientes.xlsx`). Ele lê os dados, realiza operações de processamento e gera relatórios conforme necessário.

## Funcionalidades

- **carregar_dados**: Carrega os dados do arquivo Excel em um DataFrame.
- **processar_dados**: Realiza operações de processamento nos dados carregados.
- **gerar_relatorio**: Gera um relatório com base nos dados processados.
- **envio_mensagens_multithread**: Adiciona suporte para envio de mensagens em múltiplas threads.
- **interface_grafica**: Adiciona uma interface gráfica para seleção de arquivos e envio de mensagens.

## Como Usar

1. Coloque o arquivo `clientes.xlsx` no mesmo diretório do script.
2. Configure o arquivo `config.env` com as variáveis de ambiente necessárias, incluindo a API.
3. Execute o script para processar os dados e gerar os relatórios.
4. Utilize a interface gráfica para seleção de arquivos e envio de mensagens.
5. Um executável também está disponível para facilitar a execução sem a necessidade de um ambiente Python configurado.

## Requisitos

- Python 3.x
- Bibliotecas: pandas, openpyxl, tkinter

## Licença
Este projeto está licenciado sob a [Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International](LICENSE).  
Você pode compartilhá-lo, mas **não pode**:
- Usar para fins comerciais.
- Modificar ou criar obras derivadas.