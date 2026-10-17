-- schema do banco (PostgreSQL / Aiven)
-- Tema 05: Acesso a Microcredito e Inclusao Financeira Regional
--
-- Escolhemos um esquema estrela (poucas tabelas de dimensao + tabelas fato)
-- porque e simples de consultar no dashboard depois (filtro por ano, UF,
-- modalidade) e o volume de dados ja ta agregado, entao nao precisa de um
-- modelo totalmente normalizado.

DROP TABLE IF EXISTS fato_credito_regional CASCADE;
DROP TABLE IF EXISTS fato_microcredito_nacional CASCADE;
DROP TABLE IF EXISTS dim_modalidade CASCADE;
DROP TABLE IF EXISTS dim_uf CASCADE;

CREATE TABLE dim_uf (
    uf_id      SERIAL PRIMARY KEY,
    sigla_uf   VARCHAR(2) NOT NULL UNIQUE,
    nome_uf    VARCHAR(40) NOT NULL,
    regiao     VARCHAR(20) NOT NULL
);

CREATE TABLE dim_modalidade (
    modalidade_id   SERIAL PRIMARY KEY,
    nome_modalidade VARCHAR(150) NOT NULL,
    segmento        VARCHAR(2) NOT NULL, -- PF ou PJ (coluna "cliente" do SCR.data)
    UNIQUE (nome_modalidade, segmento)
);

-- series nacionais de microcredito, vem da API SGS (series 20618 e 20712)
CREATE TABLE fato_microcredito_nacional (
    id              SERIAL PRIMARY KEY,
    serie_id        INTEGER NOT NULL,
    descricao_serie VARCHAR(200) NOT NULL,
    data_referencia DATE NOT NULL,
    valor           DECIMAL(15,2) NOT NULL,
    UNIQUE (serie_id, data_referencia)
);

-- dados regionais, vem do SCR.data (Brasil todo (27 UFs), submodalidade
-- Microcredito, a partir de 2021 - ver etl/filtrar_scr.py)
-- obs: o arquivo do bcb nao traz "quantidade de clientes", so numero de
-- operacoes, por isso essa coluna nao existe aqui (diferente do que a gente
-- tinha imaginado na etapa 1 antes de ver os dados de verdade)
CREATE TABLE fato_credito_regional (
    id                      SERIAL PRIMARY KEY,
    uf_id                   INTEGER NOT NULL REFERENCES dim_uf (uf_id),
    modalidade_id           INTEGER NOT NULL REFERENCES dim_modalidade (modalidade_id),
    data_referencia         DATE NOT NULL,
    valor_carteira_ativa    DECIMAL(15,2),
    taxa_inadimplencia      DECIMAL(6,4),
    quantidade_operacoes    INTEGER,
    UNIQUE (uf_id, modalidade_id, data_referencia)
);

CREATE INDEX idx_credito_regional_data ON fato_credito_regional (data_referencia);
CREATE INDEX idx_credito_regional_uf ON fato_credito_regional (uf_id);
CREATE INDEX idx_microcredito_nacional_data ON fato_microcredito_nacional (data_referencia);
