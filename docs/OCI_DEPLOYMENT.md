# Preparação para deploy no OCI

Este documento é apenas um checklist de preparação. Nenhum recurso OCI, infraestrutura, banco de dados, Docker ou serviço pago é criado por este projeto nesta fase.

## Antes de solicitar um deploy

- Definir, fora do repositório, o ambiente de execução aprovado para o backend FastAPI e o frontend Vite compilado.
- Escolher uma estratégia de exposição do backend e do frontend compatível com as políticas da organização.
- Definir onde os arquivos da `knowledge_base/` serão disponibilizados, preservando os PDFs, CSVs e arquivos de validação originais.
- Confirmar os limites de CPU, memória, armazenamento e tráfego necessários para o volume esperado.
- Definir monitoramento, logs e procedimento de rollback antes da publicação.

## Secrets e configuração

- Não fazer upload de `backend/.env` para o OCI.
- Armazenar `GEMINI_API_KEY` em um mecanismo de secrets aprovado pela organização e injetá-la somente no processo do backend.
- Configurar `GEMINI_MODEL` no ambiente do backend, usando `gemini-3.5-flash-lite` quando esse modelo estiver aprovado e disponível.
- Não colocar secrets em imagens, artefatos do frontend, logs ou parâmetros públicos.

## Validações antes da promoção

1. Executar a suíte completa de testes do backend.
2. Executar `npm.cmd run build` dentro de `frontend/`.
3. Verificar `GET /health` no ambiente de destino.
4. Testar `POST /api/chat` com uma pergunta pertencente à Knowledge Base e verificar as fontes.
5. Confirmar que a busca local ocorre antes do Gemini e que perguntas sem contexto não fazem chamada externa.
6. Confirmar que uma pergunta com contexto faz no máximo uma chamada ao Gemini.
7. Verificar que nenhum secret está rastreado pelo Git ou presente no bundle do frontend.

O deploy não deve alterar o comportamento local-first, enviar a Knowledge Base inteira ao Gemini ou introduzir embeddings, vector store, banco, filas ou serviços externos sem uma decisão arquitetural específica.
