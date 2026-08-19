# SAP Knowledge Base - VS Code Ready

Status: `validated_with_gaps`  
Knowledge Base version: `1.1.0`  
Prepared for integration: `2026-08-19`

Este pacote esta pronto para ser colocado no repositorio do SAP Knowledge
Assistant. Ele contem:

- 10 PDFs pesquisaveis para retrieval semantico;
- 19 CSVs canonicos de produtos;
- 4 CSVs institucionais sobre empresa, cultura, localidades e fontes;
- 197 fontes oficiais registradas;
- manifesto, lacunas, conflitos e relatorio de validacao;
- guia de ingestao para impedir duplicacao e uso incorreto dos dados.

Antes de implementar o RAG, leia `RAG_INGESTION_GUIDE.md`.

Nao carregue `validation/` como conhecimento de resposta. Mantenha essa pasta
somente para auditoria e controle de qualidade.
