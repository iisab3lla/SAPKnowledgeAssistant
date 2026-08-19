# Relatório de validação - Base de conhecimento SAP

## 1. Produto pesquisado

- Produtos: SAP Concur solutions, SAP Business Technology Platform, SAP S/4HANA, SAP SuccessFactors HCM, SAP Ariba solutions, SAP Datasphere, SAP Analytics Cloud, SAP Signavio Process Transformation Suite, SAP Business Network e SAP Build
- product_ids: `sap_concur`, `sap_btp`, `sap_s4hana`, `sap_successfactors`, `sap_ariba`, `sap_datasphere`, `sap_analytics_cloud`, `sap_signavio`, `sap_business_network`, `sap_build`
- Data de acesso e verificação: 2026-08-19
- Versão do esquema: 1.0
- Versão da base: 1.1.0

## 2. Arquivos criados ou atualizados

- 10 PDFs individuais pesquisáveis (134 páginas no total)
- 19 CSVs canônicos e 4 CSVs institucionais complementares
- `manifest.csv`, `research_gaps.csv`, `source_conflicts.csv` e este relatório

## 3. Quantidade de registros por CSV

- `products.csv`: 10
- `product_aliases.csv`: 35
- `product_features.csv`: 125
- `product_components.csv`: 104
- `product_use_cases.csv`: 95
- `product_audiences.csv`: 85
- `product_industries.csv`: 50
- `product_benefits.csv`: 93
- `product_integrations.csv`: 79
- `product_technologies.csv`: 96
- `product_deployment.csv`: 39
- `product_ai_capabilities.csv`: 80
- `product_security.csv`: 66
- `product_licensing.csv`: 36
- `product_related_products.csv`: 75
- `product_differentiation.csv`: 49
- `product_glossary.csv`: 111
- `product_faq.csv`: 139
- `sources.csv`: 185
- `company_profile.csv`: 1
- `company_culture.csv`: 7
- `company_locations.csv`: 9
- `company_sources.csv`: 12

## 4. Fontes

- Fontes oficiais verificadas: 185 de produtos + 12 institucionais
- Domínios utilizados: sap.com, help.sap.com, learning.sap.com, pages.community.sap.com, concur.com, news.sap.com e architecture.learning.sap.com
- O domínio concur.com foi tratado como domínio oficial SAP Concur porque é vinculado diretamente pela página SAP do produto.

## 5. Cobertura por seção

- Cobertas: identificação, visão geral, funcionalidades, componentes, casos de uso, públicos, indústrias, benefícios, integrações, tecnologias, deployment, IA, segurança, licenciamento, produtos relacionados, diferenciação, glossário e FAQ.
- FAQ: 139 perguntas em níveis básico, intermediário e específico.
- Camada institucional complementar: `company_profile.csv`, `company_culture.csv`, `company_locations.csv` e `company_sources.csv`, com presença global, cultura declarada e diretório de localidades da SAP.

## 6. Campos obrigatórios ausentes

- Nenhum campo estrutural obrigatório ausente.
- Células vazias foram mantidas somente quando a informação não era pública ou não se aplicava.

## 7. Lacunas

- Total registrado: 52
- Principais: preços não públicos, catálogos e matrizes regionais dinâmicos, escopos detalhados de compliance, disponibilidade de IA e transições de nomenclatura comercial.

## 8. Conflitos

- Total registrado: 9
- Os registros foram resolvidos por contexto, incluindo a evolução de Ariba Network para SAP Business Network sem confundir a rede com o portfólio SAP Ariba.

## 9. Duplicidades removidas

- Nenhuma duplicidade exata ou semântica permaneceu após normalização.

## 10. Validações executadas

- UTF-8, delimitador, RFC 4180, cabeçalhos e ordem de colunas
- IDs únicos, product_ids e referências de fontes
- Datas ISO, booleanos e placeholders proibidos
- Proteção contra CSV injection
- Domínios oficiais permitidos e URLs HTTPS
- Contagens e hashes SHA-256 do manifesto
- Presença das 23 seções do PDF e correspondência do product_id
- Parse dos 19 CSVs canônicos e verificação estrutural dos 4 CSVs institucionais
- Renderização dos PDFs e inspeção visual de cortes, sobreposições, legibilidade e páginas vazias

## 11. Erros encontrados e corrigidos

- Erros estruturais pendentes: 0
- Alertas não bloqueantes: 0
- Nenhum erro estrutural pendente.

## 12. Limitações

- Alguns documentos detalhados de segurança e compliance exigem solicitação, acesso de cliente ou NDA.
- Preços e condições podem variar por mercado, serviço, região, consumo e compromisso contratual.
- O catálogo de integrações é dinâmico; foram incluídas apenas relações comprovadas pelas fontes verificadas.

## 13. Status final

**validated_with_gaps**

A estrutura está validada e pronta para processamento posterior pelo RAG. O status inclui lacunas documentadas, sem uso de informações inventadas.
