"""
Resumen de clientes -> clientes_resumen.csv + clientes_cohortes.csv

No llama a ninguna API: lee los CSV de ventas que ya están en el repo (vivo + histórico)
y arma, por canal y cliente (seudonimizado), la primera/última compra, pedidos, gasto y
marcas compradas. Con eso el dashboard calcula nuevos vs recurrentes, recompra, valor
del cliente, cohortes y cruce entre marcas.

Ojo: "nuevo" = primera compra desde que hay datos en el repo (ene-2026 Shopify, sep-2026 MeLi).
"""
import os
import pandas as pd

FUENTES = {
    "Tienda Online": ["ventas_historico.csv", "ventas_hot_sale.csv"],
    "MercadoLibre": ["ventas_meli_historico.csv", "ventas_meli.csv"],
}
COLS = ["id_pedido", "fecha", "marca", "total_pedido", "es_reverso", "cliente"]


def pedidos_canal(canal, archivos):
    partes = []
    for a in archivos:
        if os.path.exists(a):
            d = pd.read_csv(a, usecols=lambda c: c in COLS, low_memory=False)
            if "cliente" in d.columns:
                partes.append(d)
    if not partes:
        return pd.DataFrame()
    d = pd.concat(partes, ignore_index=True)
    d = d[d["cliente"].notna() & (d["cliente"].astype(str).str.len() > 0)]
    d = d[pd.to_numeric(d["es_reverso"], errors="coerce").fillna(0) == 0]
    d["fecha"] = pd.to_datetime(d["fecha"], errors="coerce", format="mixed", utc=True).dt.tz_convert("America/Argentina/Buenos_Aires")
    d = d.dropna(subset=["fecha"])
    p = d.groupby(["marca", "id_pedido"]).agg(fecha=("fecha", "first"), total=("total_pedido", "first"),
                                              cliente=("cliente", "first")).reset_index()
    p["canal"] = canal
    return p


def main():
    peds = [pedidos_canal(c, a) for c, a in FUENTES.items()]
    peds = [p for p in peds if not p.empty]
    if not peds:
        print("😴 Todavía no hay columna 'cliente' en las ventas (correr el backfill).")
        return
    P = pd.concat(peds, ignore_index=True)

    res = P.groupby(["canal", "cliente"]).agg(
        primera_compra=("fecha", "min"), ultima_compra=("fecha", "max"),
        pedidos=("id_pedido", "count"), gasto=("total", "sum"),
        marcas=("marca", lambda s: "|".join(sorted(set(map(str, s)))))).reset_index()
    res["n_marcas"] = res["marcas"].str.count(r"\|") + 1
    res["primera_compra"] = res["primera_compra"].dt.strftime("%Y-%m-%d")
    res["ultima_compra"] = res["ultima_compra"].dt.strftime("%Y-%m-%d")
    res["gasto"] = res["gasto"].round(0)
    res.to_csv("clientes_resumen.csv", index=False)

    # Cohortes mensuales: de los que compraron por primera vez en el mes X, cuántos volvieron en X+n
    P["mes"] = P["fecha"].dt.tz_localize(None).dt.to_period("M")
    prim = P.groupby(["canal", "cliente"])["mes"].min().rename("cohorte")
    P = P.join(prim, on=["canal", "cliente"])
    P["mes_n"] = (P["mes"] - P["cohorte"]).apply(lambda x: x.n)
    coh = P.groupby(["canal", "cohorte", "mes_n"])["cliente"].nunique().rename("clientes").reset_index()
    coh["cohorte"] = coh["cohorte"].astype(str)
    coh.to_csv("clientes_cohortes.csv", index=False)
    print(f"✅ clientes_resumen.csv: {len(res):,} clientes | clientes_cohortes.csv: {len(coh):,} filas")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"🚨 Error clientes: {e}")
