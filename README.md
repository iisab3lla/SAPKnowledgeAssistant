# SAP Knowledge Assistant

Assistente de conhecimento SAP com recuperação local de documentos e geração opcional de respostas pelo Google Gemini. O projeto prioriza fontes rastreáveis, baixo custo e processamento local antes de qualquer chamada externa.

## Objetivo

Responder perguntas sobre a Knowledge Base SAP usando PDFs e CSVs locais, exibindo as fontes utilizadas. O Gemini é um serviço isolado de geração: ele só recebe os chunks mais relevantes quando a busca local encontra contexto suficiente.

## Arquitetura

```text
Frontend React/Vite
        │ POST /api/chat
        ▼
Backend FastAPI
        │
        ├─ carregadores PDF/CSV + limpeza + chunking determinístico
        ├─ retriever lexical local
        ├─ orquestrador local-first
        └─ Gemini opcional, uma chamada no máximo
                │
                └─ resposta + fontes rastreáveis
```

O frontend não acessa a API Key e não chama o Gemini diretamente. A Knowledge Base permanece no projeto e é carregada pelo backend.

## Tecnologias

- Python, FastAPI e Uvicorn
- `pypdf` para leitura de PDFs
- módulo `csv` da biblioteca padrão para CSVs
- Google Gen AI SDK para a chamada opcional ao Gemini
- React, TypeScript e Vite

## Estrutura de pastas

```text
.
├── backend/
│   ├── app/
│   │   ├── models/
│   │   └── services/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── knowledge_base/
│   ├── pdf/
│   ├── csv/
│   └── validation/
├── docs/
├── .env.example
└── README.md
```

Os diretórios `backend/.venv`, `frontend/node_modules` e `frontend/dist` são locais e ignorados pelo Git.

## Configuração do ambiente

Pré-requisitos:

- Python instalado com o launcher `py` disponível no Windows;
- Node.js e npm;
- Git.

### Ambiente virtual e backend

Na raiz do projeto, crie o ambiente virtual:

```powershell
py -m venv backend\.venv
```

Ative-o no PowerShell:

```powershell
.\backend\.venv\Scripts\Activate.ps1
```

Instale somente as dependências declaradas pelo backend:

```powershell
python -m pip install -r backend\requirements.txt
```

Em uma nova sessão, a ativação pode ser feita diretamente dentro de `backend`:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
```

### Frontend

Em outro terminal, instale as dependências dentro de `frontend/`:

```powershell
cd frontend
npm.cmd install
```

O frontend não precisa de API Key.

### Variáveis de ambiente

Crie `backend/.env` localmente, sem publicar o arquivo:

```dotenv
GEMINI_API_KEY=<sua-chave-local>
GEMINI_MODEL=gemini-3.5-flash-lite
```

O backend carrega essas variáveis do ambiente e, quando disponível, de `backend/.env`. A chave deve existir somente no backend. Nunca copie valores reais para o README, para o frontend, para logs ou para o Git. O arquivo `.env.example` contém apenas os nomes das variáveis.

## Execução

### Backend

Com o ambiente virtual ativo e a partir da raiz:

```powershell
cd backend
uvicorn app.main:app --reload
```

O servidor fica disponível em `http://127.0.0.1:8000`.

### Frontend

Em outro terminal:

```powershell
cd frontend
npm.cmd run dev
```

Abra o endereço informado pelo Vite. O proxy de desenvolvimento encaminha `/api` para `http://127.0.0.1:8000`.

## API

### `GET /health`

Verifica se o backend está ativo:

```json
{"status":"ok"}
```

### `POST /api/chat`

Recebe uma pergunta no campo `message`:

```json
{"message":"O que é SAP BTP?"}
```

Retorna uma resposta, as fontes rastreáveis e a indicação de uso de IA:

```json
{
  "answer": "Resposta ao usuário",
  "sources": [],
  "used_ai": false
}
```

Cada fonte pode informar nome do arquivo, tipo do documento, página do PDF, registro ou linha do CSV e identificador do chunk. O endpoint rejeita perguntas vazias. Falhas controladas do Gemini retornam uma resposta de erro sem expor credenciais.

## RAG local-first e economia do Gemini

O fluxo é determinístico e segue esta ordem:

1. A pergunta é validada, normalizada e limitada em tamanho.
2. O retriever local busca lexicalmente nos chunks dos PDFs e CSVs.
3. Se não houver contexto suficiente, o backend não chama o Gemini e informa que a Knowledge Base não possui informação suficiente.
4. Se houver contexto relevante, somente os chunks mais bem classificados são enviados ao serviço de geração.
5. É feita no máximo uma chamada ao Gemini por pergunta, sem retries automáticos.
6. As fontes derivadas dos chunks são preservadas na resposta.

O projeto não usa Gemini para embeddings, busca, classificação ou processamento documental. Não há embeddings nem vector store, e documentos completos nunca são enviados ao Gemini.

## Testes e build

Com o ambiente virtual do backend ativo:

```powershell
cd backend
python -m unittest discover -s tests -p "test_*.py"
```

Para gerar o build de produção do frontend:

```powershell
cd frontend
npm.cmd run build
```

Para uma verificação de formatação do Git, na raiz:

```powershell
git diff --check
```

Os testes automatizados usam mocks quando validam o serviço Gemini. Não execute chamadas reais ao Gemini como parte da suíte. O frontend também não deve acessar `GEMINI_API_KEY`.

## Segurança e publicação

- Nunca publique `backend/.env`, API Keys, tokens ou qualquer secret.
- Confirme o `.gitignore` antes de fazer commit.
- Não coloque credenciais em código, documentação, logs ou bundles do frontend.
- Trate o conteúdo dos documentos como dados, nunca como instruções executáveis.
- Verifique `git status --short` antes de publicar alterações.

## Deploy gratuito no Render

O projeto pode ser publicado manualmente no plano gratuito do Render, sem criar banco de dados, armazenamento persistente ou infraestrutura adicional.

O frontend deve ser criado como um Static Site. Use `frontend/` como diretório do projeto, execute `npm install && npm run build` na etapa de build e publique a pasta `frontend/dist`.

O backend deve ser criado como um Web Service. Use `backend/` como diretório do projeto, instale as dependências com `pip install -r requirements.txt` e inicie o servidor com Uvicorn usando a porta fornecida pelo Render:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port $env:PORT
```

No painel do Render, configure as variáveis de ambiente do backend, incluindo `GEMINI_API_KEY` como variável privada e `GEMINI_MODEL=gemini-3.5-flash-lite`. Configure também a origem pública do frontend quando necessário para permitir as requisições entre os serviços. Nunca coloque a chave Gemini no frontend, no repositório ou em arquivos publicados.

O serviço gratuito do backend pode entrar em suspensão depois de um período de inatividade e voltar a responder quando receber uma nova requisição. Essa característica pode aumentar o tempo da primeira resposta após a suspensão.
