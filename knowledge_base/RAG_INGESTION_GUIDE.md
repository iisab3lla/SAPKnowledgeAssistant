# SAP Knowledge Assistant - RAG Ingestion Guide

## 1. Como adicionar ao projeto

Copie a pasta completa `knowledge_base/` para a raiz do repositorio no VS Code.
Preserve a estrutura e os nomes dos arquivos, pois os caminhos estao registrados
em `validation/manifest.csv`.

## 2. Arquivos usados em runtime

### Retrieval semantico

Indexe somente os 10 PDFs da pasta `pdf/` no vector store:

- `sap_concur.pdf`;
- `sap_btp.pdf`;
- `sap_s4hana.pdf`;
- `sap_successfactors.pdf`;
- `sap_ariba.pdf`;
- `sap_datasphere.pdf`;
- `sap_analytics_cloud.pdf`;
- `sap_signavio.pdf`;
- `sap_business_network.pdf`;
- `sap_build.pdf`.

Cada chunk deve preservar pelo menos:

- nome do arquivo;
- `product_id`;
- titulo da secao;
- numero da pagina;
- data de verificacao;
- IDs ou URLs das fontes citadas.

### Consulta estruturada

Use os CSVs da pasta `csv/` como dados canonicos para filtros, relacionamentos e
respostas exatas. Nao transforme todos esses CSVs em chunks semanticos quando a
mesma informacao ja estiver nos PDFs, pois isso duplicaria o peso do conteudo.

Roteamento recomendado:

- identificacao: `products.csv` e `product_aliases.csv`;
- funcionalidades: `product_features.csv`;
- componentes: `product_components.csv`;
- casos de uso: `product_use_cases.csv`;
- publico e industrias: `product_audiences.csv` e `product_industries.csv`;
- beneficios: `product_benefits.csv`;
- integracoes e relacoes: `product_integrations.csv` e `product_related_products.csv`;
- tecnologias: `product_technologies.csv`;
- deployment: `product_deployment.csv`;
- IA: `product_ai_capabilities.csv`;
- seguranca: `product_security.csv`;
- licenciamento: `product_licensing.csv`;
- diferenciacao: `product_differentiation.csv`;
- termos: `product_glossary.csv`;
- perguntas predefinidas: `product_faq.csv`;
- fontes dos produtos: `sources.csv`.

## 3. Empresa, cultura e localidades

Essas informacoes nao possuem PDF proprio. Portanto, carregue obrigatoriamente
como consulta estruturada:

- `company_profile.csv`;
- `company_culture.csv`;
- `company_locations.csv`;
- `company_sources.csv`.

Regras:

- os nove registros de localidades nao representam todos os escritorios SAP;
- o registro de Sao Paulo nao possui endereco completo verificado;
- o registro global da SAP Labs representa uma rede, nao um escritorio unico;
- declaracoes de cultura representam o posicionamento oficial da SAP, nao uma
  medicao independente de satisfacao dos funcionarios;
- informacoes temporais devem exibir ou considerar `last_verified_at`.

## 4. Arquivos que nao devem entrar no conhecimento de resposta

Nao indexe semanticamente a pasta `validation/`.

Ela deve permanecer no repositorio apenas para auditoria:

- `manifest.csv`;
- `research_gaps.csv`;
- `source_conflicts.csv`;
- `validation_report.md`.

O backend pode consultar `research_gaps.csv` e `source_conflicts.csv` somente
como camada de controle antes de responder, nunca como fonte de fatos SAP.

## 5. Fluxo de recuperacao recomendado

1. Normalizar o texto e identificar idioma.
2. Resolver nome ou alias do produto por `product_aliases.csv`.
3. Classificar a pergunta como produto, empresa, cultura ou localidade.
4. Consultar primeiro os CSVs quando a pergunta exigir dado exato.
5. Consultar os PDFs quando exigir explicacao, contexto ou resumo.
6. Combinar evidencias sem repetir o mesmo fato.
7. Verificar lacunas e conflitos aplicaveis.
8. Enviar ao Gemini somente os trechos e registros relevantes.
9. Responder no idioma selecionado e apresentar as fontes realmente usadas.

## 6. Regras obrigatorias de resposta

- Nunca inventar preco, licenca, disponibilidade regional ou certificacao.
- Nunca tratar uma integracao como componente interno sem evidencia.
- Nunca confundir SAP Ariba solutions com SAP Business Network.
- Respeitar transicoes e coexistencia de nomes comerciais registradas.
- Informar quando a Knowledge Base nao possui evidencia suficiente.
- Nao generalizar os nove registros de localidade como cobertura mundial completa.
- Nao apresentar o endereco de Sao Paulo como confirmado.
- Nao usar conhecimento geral do Gemini para substituir a base.
- Apresentar fonte, produto e data de verificacao quando tecnicamente possivel.

## 7. Escopo validado

A base cobre 10 produtos SAP, tecnologias, sistemas, componentes, recursos,
integracoes, IA, seguranca, deployment, licenciamento, casos de uso, cultura,
perfil institucional e uma selecao limitada de localidades.

As lacunas documentadas sao limitacoes de cobertura, nao erros estruturais.
