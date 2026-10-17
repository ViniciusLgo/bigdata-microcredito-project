# verificar_banco.py
# Mostra o que de fato ficou guardado no postgres da Aiven: as tabelas, os
# campos com o tipo de cada um, as chaves estrangeiras e a quantidade de
# linhas. Serve de prova pro entregavel 3 (estrutura + quantidade de dados).
#
# uso:
#   export AIVEN_PG_URL="postgres://usuario:senha@host:porta/defaultdb?sslmode=require"
#   python etl/verificar_banco.py

import os
import sys
import psycopg2


def main():
    url = os.environ.get("AIVEN_PG_URL")
    if not url:
        print("faltou definir a variavel AIVEN_PG_URL")
        sys.exit(1)

    conn = psycopg2.connect(url)
    cur = conn.cursor()

    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name"
    )
    tabelas = [linha[0] for linha in cur.fetchall()]

    print("== tabelas, campos e tipos ==")
    for tabela in tabelas:
        print(f"\n{tabela}")
        cur.execute(
            "SELECT column_name, data_type, character_maximum_length, "
            "numeric_precision, numeric_scale, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s "
            "ORDER BY ordinal_position",
            (tabela,),
        )
        for nome, tipo, tam, prec, esc, nulo in cur.fetchall():
            if tam:
                tipo = f"{tipo}({tam})"
            elif tipo == "numeric" and prec:
                tipo = f"numeric({prec},{esc})"
            print(f"  {nome:24} {tipo:18} {'NULL' if nulo == 'YES' else 'NOT NULL'}")

    print("\n== relacionamentos (chaves estrangeiras) ==")
    cur.execute(
        "SELECT tc.table_name, kcu.column_name, ccu.table_name, ccu.column_name "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name "
        "JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name "
        "WHERE tc.constraint_type = 'FOREIGN KEY' ORDER BY 1, 2"
    )
    for tabela, coluna, ref_tabela, ref_coluna in cur.fetchall():
        print(f"  {tabela}.{coluna} -> {ref_tabela}.{ref_coluna}")

    print("\n== quantidade de linhas ==")
    total = 0
    for tabela in tabelas:
        cur.execute(f"SELECT count(*) FROM {tabela}")
        n = cur.fetchone()[0]
        total += n
        print(f"  {tabela:30} {n}")
    print(f"  {'total':30} {total}")

    cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
    print(f"\ntamanho do banco: {cur.fetchone()[0]} (limite do plano gratis: 1 GB)")

    cur.execute(
        "SELECT d.segmento, count(*), min(f.data_referencia), max(f.data_referencia) "
        "FROM fato_credito_regional f JOIN dim_modalidade d USING (modalidade_id) "
        "GROUP BY d.segmento ORDER BY 1"
    )
    print("\n== fato_credito_regional por segmento ==")
    for segmento, n, ini, fim in cur.fetchall():
        print(f"  {segmento}: {n} linhas, de {ini} ate {fim}")

    conn.close()


if __name__ == "__main__":
    main()
