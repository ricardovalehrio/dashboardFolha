import streamlit as st
import pandas as pd

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
    if pd.isna(valor):
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_data
def carregar_dados(caminho_excel: str):
    try:
        # Carregando as abas necessárias
        xls = pd.ExcelFile(caminho_excel)
        raw = pd.read_excel(xls, sheet_name="EMPRESA")
        
        # Parâmetros Globais (extraídos da planilha)
        taxa_ir = raw.loc[raw["Empresa XYZ"] == "Imposto de Renda Receita", "Unnamed: 5"].iloc[0]
        valor_hora_extra = raw.loc[raw["Empresa XYZ"] == "Valor da Hora Extra", "Unnamed: 5"].iloc[0]

        # Dados dos Funcionários (ajustando header)
        df = pd.read_excel(xls, sheet_name="EMPRESA", header=5)
        df.columns = df.iloc[0].str.strip() # Define nomes das colunas e limpa espaços
        df = df.iloc[1:].reset_index(drop=True)
        df = df.dropna(subset=["Nome"]) # Remove linhas sem nome

        # Conversão de tipos e limpeza
        numeric_cols = [
            "Salário Bruto", "INSS", "Gratificação", "INSS R$",
            "Imposto de Renda R$", "Gratificação R$", "Hora Extra (trab.)",
            "Hora Extra (Total.)", "Descontos", "Salário Líquido"
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Recálculo das colunas para garantir integridade
        df["Gratificação R$"] = df["Salário Bruto"] * df.get("Gratificação", 0)
        df["INSS R$"] = df["Salário Bruto"] * df.get("INSS", 0)
        df["Imposto de Renda R$"] = df["Salário Bruto"] * taxa_ir
        df["Hora Extra (Total.)"] = df["Hora Extra (trab.)"] * valor_hora_extra
        df["Descontos"] = df["INSS R$"] + df["Imposto de Renda R$"]
        df["Salário Líquido"] = (df["Salário Bruto"] + df["Gratificação R$"] + 
                                df["Hora Extra (Total.)"] - df["Descontos"])

        return df, taxa_ir, valor_hora_extra
    except Exception as e:
        st.error(f"⚠️ Erro ao carregar o arquivo '{caminho_excel}': {e}")
        return None, 0, 0

# ==============================================================================
# 3. EXECUÇÃO E INTERFACE
# ==============================================================================

# Nome do arquivo atualizado conforme solicitado
ARQUIVO = "extraFinal.xlsx"

df_base, taxa_ir_val, v_he_val = carregar_dados(ARQUIVO)

if df_base is not None:
    # --- BARRA LATERAL (FILTROS) ---
    with st.sidebar:
        st.title("📂 Filtros de Análise")
        
        niveis = sorted(df_base["Nível Funcional"].unique().astype(str))
        niveis_sel = st.multiselect("Nível Funcional", niveis, default=niveis)
        
        nomes = sorted(df_base["Nome"].unique().astype(str))
        nomes_sel = st.multiselect("Funcionários", nomes, default=nomes)
        
        st.divider()
        st.info("Dica: Use os filtros acima para ajustar os indicadores e gráficos simultaneamente.")

    # Aplicação dos Filtros
    df_f = df_base[
        (df_base["Nível Funcional"].astype(str).isin(niveis_sel)) & 
        (df_base["Nome"].astype(str).isin(nomes_sel))
    ]

    # --- ÁREA PRINCIPAL ---
    st.title("📊 Painel de Controle de Folha de Pagamento")
    
    # KPIs Rápidos
    if not df_f.empty:
        c1, c2, c3, c4 = st.columns(4)