# Telegram Scraper

Este projeto é uma ferramenta para automação e extração de dados do Telegram.

## � Instalação

Clone o repositório para sua máquina local:

```bash
git clone https://github.com/My8Of/TelegramAdder.git
cd TelegramAdder
```

## �📂 Estrutura do Projeto

- **app/**: Contém o código fonte principal da aplicação.
  - **main.py**: Ponto de entrada da aplicação.
  - **src/**: Código fonte dos módulos principais.
  - **utils/**: Funções utilitárias e auxiliares.
  - **templates/**: Arquivos de template (se aplicável).
  - **temp/**: Diretório para arquivos temporários.
  - **cache/**: Diretório de cache da aplicação.
- **Dockerfile**: Arquivo de configuração para construção da imagem Docker.
- **pyproject.toml / uv.lock**: Gerenciamento de dependências do projeto.
- **.env.example**: Modelo das variáveis de ambiente necessárias.

## ⚙️ Configuração do Ambiente (.env)

Para executar o projeto, você precisa configurar as variáveis de ambiente. Renomeie o arquivo `.env.example` para `.env` e preencha as seguintes informações:

- **TELEGRAM_API_ID**: Seu ID de API do Telegram.
- **TELEGRAM_API_HASH**: Seu Hash de API do Telegram.
  > 🔗 **Obtenha o API_ID e API_HASH aqui:** [https://my.telegram.org/auth](https://my.telegram.org/auth)
- **TELEGRAM_PHONE_NUMBER**: Seu número de telefone conectado à conta do Telegram (formato internacional, ex: +5511999999999).
- **TELEGRAM_GROUP_ID**: ID do grupo de origem (se aplicável).
- **TELEGRAM_TARGET_GROUP_ID**: ID do grupo de destino (se aplicável).

## 🐳 Como Rodar com Docker

Se você não tem o Docker instalado, faça o download e instalação através do site oficial:
[Instalar Docker](https://docs.docker.com/get-docker/)

### 1. Buildar a Imagem

No diretório raiz do projeto, execute o seguinte comando para criar a imagem Docker:

```bash
docker build -t telegram-scraper .
```

### 2. Rodar o Container

Após o build, execute o container. É importante passar o arquivo `.env` para que o container tenha acesso às credenciais:

```bash
docker run --env-file .env -v $(pwd)/app:/app/app telegram-scraper
```

> **Nota:** O argumento `-v $(pwd)/app:/app/app` é opcional, mas recomendado para desenvolvimento, pois mapeia a pasta local `app` para dentro do container, permitindo alterações sem necessidade de rebuildar para cada mudança de código (dependendo de como o Dockerfile está configurado). Se preferir rodar apenas a versão buildada, pode omitir essa parte.
