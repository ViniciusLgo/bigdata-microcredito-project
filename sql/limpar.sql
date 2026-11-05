/*
limpar.sql

Esse arquivo APAGA as quatro tabelas e todos os dados que tem nelas.
So uso quando quero zerar o banco de proposito, e quem roda ele e o
carregar.py com a flag --limpar (que pede pra eu confirmar antes).
A ordem importa: primeiro as fatos, depois as dimensoes que elas usam.
*/

DROP TABLE IF EXISTS fato_credito_regional CASCADE;
DROP TABLE IF EXISTS fato_microcredito_nacional CASCADE;
DROP TABLE IF EXISTS dim_modalidade CASCADE;
DROP TABLE IF EXISTS dim_uf CASCADE;
