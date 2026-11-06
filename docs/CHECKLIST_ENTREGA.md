# Checklist da entrega — Fase 3

Tema 05 — Acesso a Microcrédito e Inclusão Financeira Regional.
Relaciona cada item exigido ao arquivo ou resultado que comprova a entrega.

Legenda: ✅ pronto · 🟡 parcial · ⬜ não feito

Atualizado em **05/11/2026**. Os itens de infraestrutura e carga dependem das partes do
Roberto, do Vinicius e do Guilherme; esta coluna é atualizada por último, quando cada um
fechar a sua branch.

---

## Itens do enunciado

| # | Item | Status | Onde está | O que ainda falta |
|---|---|---|---|---|
| **AI03.1** | Base tratada | 🟡 | `data/processed/fato_credito_regional.csv` (7.080 linhas) e `data/processed/fato_microcredito_nacional.csv` (136 linhas); amostras antes/depois em `data/amostra/` | — manifesto e hashes agora em `data/manifesto-fontes.csv` ✅; falta preencher os hashes dos ZIPs do SCR |
| **AI03.2** | Processo de tratamento documentado | ✅ | `etl/extrair_sgs.py`, `etl/filtrar_scr.py`, `etl/tratar.py`; decisões em `docs/DECISOES_TECNICAS.md`; campos em `docs/DICIONARIO_DADOS.md` | testes automatizados de tratamento (Guilherme) |
| **AI03.3** | Banco de dados em nuvem | 🟡 | `sql/schema.sql`, `etl/carregar.py`, `etl/verificar_banco.py` | consulta atual ao serviço da Aiven e evidência datada em `docs/evidencias/banco-fase2.txt`, sem credenciais (Vinicius) |
| **AI04.4** | Infraestrutura como código (Terraform) | ⬜ | — | `terraform/main.tf`, `variables.tf`, `terraform.tfvars.example`, `outputs.tf`, `terraform/README.md` e evidência em `docs/evidencias/terraform.md` (Roberto) |
| **AI04.5** | Segurança e credenciais | 🟡 | `.gitignore` já ignora `.env`; `AIVEN_PG_URL` é lida de variável de ambiente | `.env.example`, regras de ignore para `.terraform/`, `*.tfstate`, `*.tfvars`, e o `docs/SEGURANCA.md` (Guilherme) |
| **AI04.6** | Repositório organizado | ✅ | `etl/`, `sql/`, `data/`, `docs/`, `README.md`, `requirements.txt` | incorporar a documentação revisada e a pasta `terraform/` quando existir |
| **AI04.7** | README | 🟡 | `README.md` atualizado com fontes, estrutura, execução, modelo e limitações | comandos de Terraform realmente testados e links para as evidências |
| **ODS** | Vínculo com ODS 5 e/ou 18 | ✅ | `docs/ODS_ANALISE.md` (resultados, método e ressalva); `analise/ods_cruzamento.py`; `data/ibge_ocupacao_uf_2022.csv`; evidências `docs/evidencias/ods_cruzamento_uf.csv` e `ods_cruzamento.png`; decisão D-16 | repetir a ressalva de falácia ecológica no relatório e no dashboard |

---

## Conferências já feitas sobre os arquivos locais (05/11/2026)

| Verificação | Resultado |
|---|---|
| Linhas do fato regional | 7.080 (+ cabeçalho) |
| Linhas do fato nacional | 136 (+ cabeçalho), 68 por série |
| UFs distintas | 27 |
| Datas-base regionais | 67, de 31/01/2021 a 31/07/2026 |
| Datas nacionais | 68, de 01/01/2021 a 01/08/2026 |
| Combinações modalidade × segmento | 4 |
| Duplicatas na chave de negócio | 0 |
| Campos vazios nos CSVs finais | 0 |
| Taxas de inadimplência fora de [0, 1] | 0 |
| `quantidade_operacoes` negativa | **1.084 linhas (15,3%)**, mínimo −32 — lacuna declarada, ver D-07 |
| Total esperado no banco | 7.247 linhas (27 + 4 + 7.080 + 136) |
| SHA-256 dos CSVs finais | registrados em `data/manifesto-fontes.csv` |
| Cruzamento ODS: UFs com par completo | 27 de 27 |
| Nordeste na carteira nacional de 2022 | 62,1% |

---

## Documentos desta parte

| Arquivo | Conteúdo |
|---|---|
| `data/manifesto-fontes.csv` | fonte, URL oficial, arquivo, período, tamanho, SHA-256 e data conhecida de cada insumo |
| `docs/DICIONARIO_DADOS.md` | campos, tipos, chaves, origem, unidade e nulos de cada camada; o que a base **não** tem |
| `docs/DECISOES_TECNICAS.md` | 16 decisões registradas, semântica dos campos, limites e o encaminhamento das ODS |
| `docs/ODS_ANALISE.md` | cruzamento territorial com o IBGE: método, resultados, leitura e limitações |
| `analise/ods_cruzamento.py` | script que reproduz o cruzamento, a tabela e o gráfico |
| `data/ibge_ocupacao_uf_2022.csv` | base do IBGE por UF (tabela SIDRA 10261) |
| `docs/CHECKLIST_ENTREGA.md` | este arquivo |

---

## Antes de enviar

- [ ] Alguém do grupo que não escreveu a documentação seguiu o README do zero e anotou o
      que faltou.
- [ ] As evidências em `docs/evidencias/` estão datadas e **sem** URL completa, usuário,
      senha ou token.
- [ ] `git check-ignore` confirma que arquivos privados estão fora e que os exemplos
      (`.env.example`, `terraform.tfvars.example`) e o `.terraform.lock.hcl` estão dentro.
- [ ] Os números citados na apresentação batem com os desta página.
- [ ] A limitação das ODS aparece no relatório **e** no dashboard, com as palavras da
      ressalva de D-16.
- [ ] O prazo da fase 3 foi confirmado no Classroom.
