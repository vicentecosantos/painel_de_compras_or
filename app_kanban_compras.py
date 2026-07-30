import streamlit as st
import pandas as pd

# Mantém a tela inteira sem rolagem geral
st.set_page_config(layout="wide", page_title="Kanban de Compras", page_icon="🏗️")

st.title("🏗️ Painel de Compras Kanban")
st.markdown("Visão atualizável para engenheiros e suprimentos.")

@st.cache_data
def load_data():
    # NOME DO ARQUIVO ATUALIZADO AQUI:
    df = pd.read_excel("Relatorio_Painel de Compras.xlsx")
    if 'Data da solicitação' in df.columns:
        df['Data da solicitação'] = pd.to_datetime(df['Data da solicitação'], dayfirst=True, errors='coerce')
    return df

try:
    df = load_data()
except FileNotFoundError:
    # MENSAGEM DE ERRO ATUALIZADA:
    st.error("Arquivo 'Relatorio_Painel de Compras.xlsx' não encontrado. Verifique se ele está na mesma pasta.")
    st.stop()

# --- 1. FILTROS NA BARRA LATERAL ---
st.sidebar.header("🔍 Filtros do Painel")

obras_disponiveis = df['Obra'].dropna().unique().tolist()
obras_selecionadas = st.sidebar.multiselect(
    "Filtrar por Obra:",
    options=obras_disponiveis,
    default=obras_disponiveis
)

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Período da Solicitação")

min_date_val = df['Data da solicitação'].min()
max_date_val = df['Data da solicitação'].max()

if pd.isna(min_date_val): min_date_val = pd.to_datetime('today')
if pd.isna(max_date_val): max_date_val = pd.to_datetime('today')

col_dt1, col_dt2 = st.sidebar.columns(2)
with col_dt1:
    data_inicio = st.date_input("Data Inicial", value=min_date_val.date(), format="DD/MM/YYYY")
with col_dt2:
    data_fim = st.date_input("Data Final", value=max_date_val.date(), format="DD/MM/YYYY")

df_filtrado = df[
    (df['Obra'].isin(obras_selecionadas)) & 
    (df['Data da solicitação'].dt.date >= data_inicio) & 
    (df['Data da solicitação'].dt.date <= data_fim)
]

# --- LÓGICA DE FILTRAGEM ---
mask_sem_pedido = df_filtrado['N° do Pedido'].isna()
insumos_aut = df_filtrado[mask_sem_pedido & (df_filtrado['Situação autorização do item'] == 'Autorizado')]
insumos_nao_aut = df_filtrado[mask_sem_pedido & (df_filtrado['Situação autorização do item'] != 'Autorizado')]

mask_com_pedido = df_filtrado['N° do Pedido'].notna() & (df_filtrado['Situação do pedido'] != 'Totalmente entregue')
pedidos_aut = df_filtrado[mask_com_pedido & (df_filtrado['Situação autorização do pedido'] == 'Autorizado')]
pedidos_nao_aut = df_filtrado[mask_com_pedido & (df_filtrado['Situação autorização do pedido'] != 'Autorizado')]

entregas = df_filtrado[df_filtrado['N° do Pedido'].notna() & (df_filtrado['Situação do pedido'] == 'Totalmente entregue')]

# --- FUNÇÃO PARA DESENHAR OS CARTÕES ---
def render_card(row, tipo):
    with st.container(border=True):
        st.markdown(f"**{row.get('Descrição do insumo', 'Sem descrição')}**")
        
        detalhe = row.get('Detalhe', '-')
        if pd.isna(detalhe): 
            detalhe = '-'
        st.caption(f"Detalhe: {detalhe}")
        st.caption(f"Obra: {row.get('Obra', '-')}")
        
        if tipo == "insumo":
            st.text(f"Qtd: {row.get('Quantidade solicitada', 0)} {row.get('Unidade de movimento', '')}")
            status = row.get('Situação da solicitação', 'Pendente')
            cor = "blue" if status == "Parcialmente atendida" else "orange"
            st.markdown(f":{cor}[**{status}**]")
            
        elif tipo == "pedido":
            st.text(f"Fornecedor: {row.get('Fornecedor', '-')}")
            st.text(f"Pedido: {row.get('N° do Pedido', '-')}")
            status = row.get('Situação do pedido', 'Pendente')
            st.markdown(f":orange[**{status}**]")
            
        elif tipo == "entrega":
            st.text(f"Fornecedor: {row.get('Fornecedor', '-')}")
            st.text(f"Pedido: {row.get('N° do Pedido', '-')}")
            st.text(f"Qtd entregue: {row.get('Quantidade entregue', 0)}")
            st.markdown(f":green[**Totalmente entregue**]")
            
        with st.expander("Ver Detalhes"):
            st.write(f"**Nº da Solicitação:** {row.get('Nº da Solicitação', '-')}")
            data_sol = row.get('Data da solicitação')
            data_sol_str = data_sol.strftime('%d/%m/%Y') if pd.notna(data_sol) else '-'
            st.write(f"**Data da solicitação:** {data_sol_str}")

# --- CONSTRUÇÃO DO KANBAN ---

# 1. Primeiro criamos uma linha apenas para os TÍTULOS (Fixos)
head1, head2, head3, head4, head5 = st.columns(5)
with head1: st.subheader("🟠 Insumos Não Autorizados")
with head2: st.subheader("🔵 Insumos Autorizados")
with head3: st.subheader("🟠 Pedidos Não Autorizados")
with head4: st.subheader("🔵 Pedidos Autorizados")
with head5: st.subheader("🟢 Entregas")

# 2. Depois criamos uma linha para os CARTÕES (Com barra de rolagem individual)
ALTURA_COLUNA = 650 
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    with st.container(height=ALTURA_COLUNA, border=False):
        for _, row in insumos_nao_aut.iterrows(): render_card(row, "insumo")

with col2:
    with st.container(height=ALTURA_COLUNA, border=False):
        for _, row in insumos_aut.iterrows(): render_card(row, "insumo")

with col3:
    with st.container(height=ALTURA_COLUNA, border=False):
        for _, row in pedidos_nao_aut.iterrows(): render_card(row, "pedido")

with col4:
    with st.container(height=ALTURA_COLUNA, border=False):
        for _, row in pedidos_aut.iterrows(): render_card(row, "pedido")

with col5:
    with st.container(height=ALTURA_COLUNA, border=False):
        for _, row in entregas.iterrows(): render_card(row, "entrega")