
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import urllib3
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from models import Session, Funcionario, init_db
from datetime import datetime

BASE_URL = "https://transparencia.al.al.leg.br"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
session_http = requests.Session()
session_http.headers.update(HEADERS)


def get_links_mes(ano, mes):
    codigo_folha = f"{ano}{mes:02d}%7CEM"
    url = f"{BASE_URL}/?arg=&folha={codigo_folha}"
    print(f"Baixando lista mestra: {mes}/{ano}...")
    try:
        response = session_http.get(url, timeout=20)
        if "Nenhum resultado" in response.text:
            print(f"\tSem dados para {mes}/{ano}.")
            return []
        soup = BeautifulSoup(response.content, "html.parser")
        funcionarios = []
        for link in soup.find_all("a", href=True):
            if "detalhar.php" in link["href"] and len(link.text.strip()) > 3:
                full_url = (
                    link["href"]
                    if link["href"].startswith("http")
                    else f'{BASE_URL}/{link["href"]}'
                )
                funcionarios.append({"nome": link.text.strip(), "url": full_url})
        return funcionarios
    except Exception as e:
        print(f"\tErro de conexão na lista: {e}")
        return []


def processar_funcionario_individual(func_info):
    try:
        response = session_http.get(func_info["url"], timeout=15)
        if response.status_code != 200:
            return None
        html_io = StringIO(response.text)
        dfs = pd.read_html(html_io, match="Rendimento", decimal=",", thousands=".")
        if dfs:
            df = dfs[0]
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(-1)
            df = df.loc[:, ~df.columns.duplicated()]
            def limpar_valor(coluna):
                if coluna not in df.columns:
                    return 0.0
                val = df[coluna].iloc[0]
                if isinstance(val, (int, float)):
                    return float(val)
                val_str = str(val).strip()
                val_str = val_str.replace("R$", "").strip()
                val_str = val_str.replace(".", "")
                val_str = val_str.replace(",", ".")
                return float(val_str) if val_str else 0.0
            return {
                "nome": func_info["nome"],
                "cargo": (
                    str(df["Cargo"].iloc[0]).upper()
                    if "Cargo" in df.columns
                    else "DESCONHECIDO"
                ),
                "rendimento_liquido": limpar_valor("Rendimento Líquido"),
                "total_creditos": limpar_valor("Total de Créditos"),
                "total_debitos": limpar_valor("Total de Débitos"),
                "url_origem": func_info["url"],
            }
    except Exception:
        pass
    return None


def ingestor_turbo(ano_inicio, ano_fim):
    db_session = Session()
    total_global = 0
    for ano in range(ano_fim, ano_inicio - 1, -1):
        for mes in range(12, 0, -1):
            if ano == 2025 and mes > 11:
                continue
            lista_raw = get_links_mes(ano, mes)
            if not lista_raw:
                continue
            urls_existentes = (
                db_session.query(Funcionario.url_origem)
                .filter_by(mes_referencia=mes, ano_referencia=ano)
                .all()
            )
            urls_set = {u[0] for u in urls_existentes}
            lista_para_baixar = [f for f in lista_raw if f["url"] not in urls_set]
            total_mes = len(lista_raw)
            a_baixar = len(lista_para_baixar)
            if a_baixar == 0:
                print(
                    f"\tMês {mes}/{ano} já está completo no banco ({total_mes} registros)."
                )
                continue
            print(
                f"Turbinando {mes}/{ano}: Baixando {a_baixar} novos (de {total_mes})..."
            )
            resultados_para_salvar = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_func = {
                    executor.submit(processar_funcionario_individual, f): f
                    for f in lista_para_baixar
                }
                completos = 0
                for future in as_completed(future_to_func):
                    dados = future.result()
                    completos += 1
                    print(
                        f"\tProcessando: {completos}/{a_baixar} ({(completos/a_baixar):.1%})",
                        end="\r",
                    )
                    if dados:
                        resultados_para_salvar.append(dados)
            print(f"\n\tSalvando {len(resultados_para_salvar)} registros no banco...")
            for d in resultados_para_salvar:
                try:
                    novo = Funcionario(
                        nome=d["nome"],
                        cargo=d["cargo"],
                        rendimento_liquido=d["rendimento_liquido"],
                        total_creditos=d["total_creditos"],
                        total_debitos=d["total_debitos"],
                        mes_referencia=mes,
                        ano_referencia=ano,
                        url_origem=d["url_origem"],
                    )
                    db_session.add(novo)
                except Exception as e:
                    print(f"\tErro ao salvar registro: {e}")
            try:
                db_session.commit()
                total_global += len(resultados_para_salvar)
                print(f"\tMês {mes}/{ano} finalizado com sucesso!")
            except Exception as e:
                db_session.rollback()
                print(f"\tErro ao salvar lote: {e}")
    db_session.close()
    print(f"\nFim Turbo. Total salvo: {total_global}")


if __name__ == "__main__":
    init_db()
    ano_atual = datetime.now().year
    if os.getenv("CARGA_HISTORICA") == "true":
        print(f"--- MODO CARGA HISTÓRICA ATIVADO: 2020 até {ano_atual} ---")
        ingestor_turbo(2020, ano_atual)
    else:
        print(f"--- MODO MANUTENÇÃO MENSAL: Verificando apenas {ano_atual} ---")
        ingestor_turbo(ano_atual, ano_atual)
