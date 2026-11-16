/*
limpar.sql

Esse arquivo APAGA as cinco tabelas e todos os dados que tem nelas.
So uso quando quero zerar o banco de proposito, e quem roda ele e o
carregar.py com a flag --limpar (que pede pra eu confirmar antes).
*/

DROP TABLE IF EXISTS perfil_ocupados_uf CASCADE;
DROP TABLE IF EXISTS fato_credito_regional CASCADE;
DROP TABLE IF EXISTS fato_microcredito_nacional CASCADE;
DROP TABLE IF EXISTS dim_modalidade CASCADE;
DROP TABLE IF EXISTS dim_uf CASCADE;
