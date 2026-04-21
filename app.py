import streamlit as st
import pandas as pd
import os

# ==============================================================================
# 1. CONFIGURAÇÕES DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Dashboard Folha de Pagamento",
    page_icon="💰",
    layout="wide",
)

# Estilização básica para métricas
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.6rem; color: #1E88E5; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES AUXILIARES E PROCESSAMENTO
# ==============================================================================

def formata_moeda(valor: float) -> str:
    """Formata valores numéricos para o padrão de moeda brasileiro."""
    if pd.isna(valor) or valor == 0:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_data
def carregar_dados(caminho_excel: str):
    try:
        xls = pd.ExcelFile(caminho_excel)
        raw = pd.read_excel(xls, sheet_name="EMPRESA")
        
        # Parâmetros Globais
        taxa_ir = raw.loc[raw["Empresa XYZ"] == "Imposto de Renda Receita", "Unnamed: 5"].iloc[0]
        valor_hora_extra = raw.loc[raw["Empresa XYZ"] == "Valor da Hora Extra", "Unnamed: 5"].iloc[0]

        # Dados dos Funcionários
        df = pd.read_excel(xls, sheet_name="EMPRESA", header=5)
        df.columns = df.iloc[0].str.strip()
        df = df.iloc[1:].reset_index(drop=True)
        df = df.dropna(subset=["Nome"])

        numeric_cols = [
            "Salário Bruto", "INSS", "Gratificação", "INSS R$",
            "Imposto de Renda R$", "Gratificação R$", "Hora Extra (trab.)",
            "Hora Extra (Total.)", "Descontos", "Salário Líquido"
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Recálculo das colunas
        df["Gratificação R$"] = df["Salário Bruto"] * df.get("Gratificação", 0)
        df["INSS R$"] = df["Salário Bruto"] * df.get("INSS", 0)
        df["Imposto de Renda R$"] = df["Salário Bruto"] * taxa_ir
        df["Hora Extra (Total.)"] = df["Hora Extra (trab.)"] * valor_hora_extra
        df["Descontos"] = df["INSS R$"] + df["Imposto de Renda R$"]
        df["Salário Líquido"] = (df["Salário Bruto"] + df["Gratificação R$"] + 
                                df["Hora Extra (Total.)"] - df["Descontos"])

        return df, taxa_ir, valor_hora_extra
    except Exception as e:
        st.error(f"⚠️ Erro interno ao processar o Excel: {e}")
        return None, 0, 0

# ==============================================================================
# 3. LÓGICA DE CAMINHO DO ARQUIVO (BLINDAGEM)
# ==============================================================================

# Define o caminho absoluto para evitar erro de diretório no servidor (Linux)
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
NOME_ARQUIVO = "extraFinal.xlsx"
CAMINHO_COMPLETO = os.path.join(diretorio_atual, NOME_ARQUIVO)

# Verificação de existência do arquivo antes de carregar
if not os.path.exists(CAMINHO_COMPLETO):
    st.error(f"❌ Arquivo '{NOME_ARQUIVO}' não encontrado no servidor.")
    st.info(f"Arquivos detectados na pasta: {os.listdir(diretorio_atual)}")
    st.stop()

df_base, taxa_ir_val, v_he_val = carregar_dados(CAMINHO_COMPLETO)

# ==============================================================================
# 4. INTERFACE DO DASHBOARD
# ==============================================================================

if df_base is not None:
    with st.sidebar:
        st.title("📂 Filtros")
        niveis = sorted(df_base["Nível Funcional"].unique().astype(str))
        niveis_sel = st.multiselect("Nível Funcional", niveis, default=niveis)
        
        nomes = sorted(df_base["Nome"].unique().astype(str))
        nomes_sel = st.multiselect("Funcionários", nomes, default=nomes)

    df_f = df_base[
        (df_base["Nível Funcional"].astype(str).isin(niveis_sel)) & 
        (df_base["Nome"].astype(str).isin(nomes_sel))
    ]

    st.title("📊 Painel de Folha de Pagamento")
    
    if not df_f.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Funcionários", len(df_f))
        c2.metric("Média Líquida", formata_moeda(df_f["Salário Líquido"].mean()))
        c3.metric("Total Descontos", formata_moeda(df_f["Descontos"].sum()))
        c4.metric("Total H.E.", formata_moeda(df_f["Hora Extra (Total.)"].sum()))

        st.divider()

        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.subheader("Bruto vs Líquido")
            st.bar_chart(df_f.set_index("Nome")[["Salário Bruto", "Salário Líquido"]])

        with col_graf2:
            st.subheader("Descontos Acumulados")
            st.area_chart(df_f.sort_values("Salário Bruto").set_index("Salário Bruto")["Descontos"].cumsum())

        st.subheader("📄 Relatório")
        st.dataframe(df_f.sort_values("Salário Líquido", ascending=False), use_container_width=True)
    else:
        st.warning("Selecione filtros para exibir os dados.")