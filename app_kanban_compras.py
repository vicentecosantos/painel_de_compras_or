import streamlit as st
import pandas as pd
from datetime import date, timedelta

# Mantém a tela inteira sem rolagem geral
st.set_page_config(layout="wide", page_title="Painel Oracon", page_icon="Oracon_Logo.png")

# Usamos colunas para deixar a imagem perfeitamente alinhada ao lado do texto
col_logo, col_titulo = st.columns([2, 15])
with col_logo:
    st.image("Oracon_Logo.png", width=140)
with col_titulo:
    st.title("Painel de Compras Oracon")
    st.markdown("Visão de suprimentos para engenheiros com atualização diária.")

@st.cache_data(ttl=900)
def load_data():
    df = pd.read_excel("Relatorio_Painel de Compras.xlsx")
    
    # Lista de todas as colunas de datas que precisam ser convertidas
    colunas_datas = [
        'Data da solicitação', 
        'Data autorização da solicitação', 
        'Data do pedido', 
        'Data autorização do pedido'
    ]
    
    for col in colunas_datas:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
            
    return df

try:
    df = load_data()
except FileNotFoundError:
    st.error("Arquivo 'Relatorio_Painel de Compras.xlsx' não encontrado. Verifique se ele está na mesma pasta.")
    st.stop()

# --- 1. FILTROS NA BARRA LATERAL ---
# CORREÇÃO: Aspas recolocadas para evitar o SyntaxError
st.sidebar.header("🔍 Filtros do Painel")
st.sidebar.subheader("📅 Período da Solicitação")

hoje = date.today()
# Filtro de 5 dias atrás (D-5)
cinco_dias_atras = hoje - timedelta(days=5)

col_dt1, col_dt2 = st.sidebar.columns(2)
with col_dt1:
    data_inicio = st.date_input("Data Inicial", value=cinco_dias_atras, format="DD/MM/YYYY")
with col_dt2:
    data_fim = st.date_input("Data Final", value=hoje, format="DD/MM/YYYY")

st.sidebar.markdown("---")

# Filtra a base primária por data
df_base = df[
    (df['Data da solicitação'].dt.date >= data_inicio) & 
    (df['Data da solicitação'].dt.date <= data_fim)
]

obras_disponiveis = df_base['Obra'].dropna().unique().tolist()
obras_selecionadas = st.sidebar.multiselect(
    "Filtrar por Obra:",
    options=obras_disponiveis,
    default=[]
)

if obras_selecionadas:
    df_base = df_base[df_base['Obra'].isin(obras_selecionadas)]

# --- FILTROS BIDIRECIONAIS (Solicitação <-> Pedido) ---
pedidos_ja_selecionados = st.session_state.get('key_pedidos', [])
if pedidos_ja_selecionados:
    df_sol_options = df_base[df_base['N° do Pedido'].astype(str).isin(pedidos_ja_selecionados)]
else:
    df_sol_options = df_base

solicitacoes_disponiveis = df_sol_options['Nº da Solicitação'].dropna().unique().astype(str).tolist()
solicitacoes_disponiveis.sort()
solicitacoes_selecionadas = st.sidebar.multiselect(
    "Nº da Solicitação:",
    options=solicitacoes_disponiveis,
    key='key_solicitacoes'
)

if solicitacoes_selecionadas:
    df_ped_options = df_base[df_base['Nº da Solicitação'].astype(str).isin(solicitacoes_selecionadas)]
else:
    df_ped_options = df_base

pedidos_disponiveis = df_ped_options['N° do Pedido'].dropna().unique().astype(str).tolist()
pedidos_disponiveis.sort()
pedidos_selecionados = st.sidebar.multiselect(
    "Nº do Pedido:",
    options=pedidos_disponiveis,
    key='key_pedidos'
)

# Filtro final aplicado aos dados após opções bidirecionais
df_filtrado = df_base.copy()
if solicitacoes_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['Nº da Solicitação'].astype(str).isin(solicitacoes_selecionadas)]
if pedidos_selecionados:
    df_filtrado = df_filtrado[df_filtrado['N° do Pedido'].astype(str).isin(pedidos_selecionados)]

# --- NOVOS FILTROS CASCATA (Insumo -> Fornecedor) ---
# 1. Filtro de Insumo
insumos_disponiveis = df_filtrado['Descrição do insumo'].dropna().unique().astype(str).tolist()
insumos_disponiveis.sort()
insumos_selecionados = st.sidebar.multiselect(
    "Filtrar por Insumo:",
    options=insumos_disponiveis,
    default=[]
)

if insumos_selecionados:
    df_filtrado = df_filtrado[df_filtrado['Descrição do insumo'].astype(str).isin(insumos_selecionados)]

# 2. Filtro de Fornecedor
fornecedores_disponiveis = df_filtrado['Fornecedor'].dropna().unique().astype(str).tolist()
fornecedores_disponiveis.sort()
fornecedores_selecionados = st.sidebar.multiselect(
    "Filtrar por Fornecedor:",
    options=fornecedores_disponiveis,
    default=[]
)

if fornecedores_selecionados:
    df_filtrado = df_filtrado[df_filtrado['Fornecedor'].astype(str).isin(fornecedores_selecionados)]


# --- LÓGICA DE FILTRAGEM (Para as colunas) ---
mask_sem_pedido = df_filtrado['N° do Pedido'].isna()
insumos_aut = df_filtrado[mask_sem_pedido & (df_filtrado['Situação autorização do item'] == 'Autorizado')]
insumos_nao_aut = df_filtrado[mask_sem_pedido & (df_filtrado['Situação autorização do item'] != 'Autorizado')]

mask_com_pedido = df_filtrado['N° do Pedido'].notna() & (df_filtrado['Situação do pedido'] != 'Totalmente entregue')
pedidos_aut = df_filtrado[mask_com_pedido & (df_filtrado['Situação autorização do pedido'] == 'Autorizado')]
pedidos_nao_aut = df_filtrado[mask_com_pedido & (df_filtrado['Situação autorização do pedido'] != 'Autorizado')]

entregas = df_filtrado[df_filtrado['N° do Pedido'].notna() & (df_filtrado['Situação do pedido'] == 'Totalmente entregue')]


# --- FUNÇÕES DE APOIO ---
def converter_numero(valor):
    if pd.isna(valor) or valor == '' or valor == '-':
        return 0.0
    if isinstance(valor, str):
        valor = valor.replace('.', '').replace(',', '.')
    try:
        return float(valor)
    except ValueError:
        return 0.0

def formatar_data(data):
    if pd.notna(data) and hasattr(data, 'strftime'):
        return data.strftime('%d/%m/%Y')
    return '-'

# --- FUNÇÃO PARA DESENHAR OS CARTÕES ---
def render_card(row, coluna):
    with st.container(border=True):
        st.markdown(f"**{row.get('Descrição do insumo', 'Sem descrição')}**")

        detalhe = row.get('Detalhe', '-')
        if pd.isna(detalhe):
            detalhe = '-'
        st.caption(f"Detalhe: {detalhe}")
        st.caption(f"Obra: {row.get('Obra', '-')}")

        if "insumo" in coluna:
            qtd_sol = converter_numero(row.get('Quantidade solicitada', 0))
            un = row.get('Unidade de movimento', '')
            st.text(f"Qtd: {qtd_sol:,.2f} {un}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            st.text(f"Nº Solicitação: {row.get('Nº da Solicitação', '-')}")

            status = row.get('Situação da solicitação', 'Pendente')
            cor = "blue" if status == "Parcialmente atendida" else "orange"
            st.markdown(f":{cor}[ {status} ]")

            with st.expander("Ver Detalhes"):
                st.write(f"Data da solicitação: {formatar_data(row.get('Data da solicitação'))}")
                if 'Data autorização da solicitação' in row and pd.notna(row['Data autorização da solicitação']) and coluna != "insumo_nao_aut":
                    st.write(f"Data Aut. Solicit.: {formatar_data(row['Data autorização da solicitação'])}")

        elif "pedido" in coluna:
            qtd_pendente = converter_numero(row.get('Saldo', 0))
            un = row.get('Unidade de movimento', '')
            st.text(f"Qtd pendente: {qtd_pendente:,.2f} {un}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            st.text(f"Pedido: {row.get('N° do Pedido', '-')}")

            status = row.get('Situação do pedido', 'Pendente')
            st.markdown(f":orange[ {status} ]")

            with st.expander("Ver Detalhes"):
                st.write(f"Nº da Solicitação: {row.get('Nº da Solicitação', '-')}")
                st.write(f"Fornecedor: {row.get('Fornecedor', '-')}")
                st.write(f"Data da solicitação: {formatar_data(row.get('Data da solicitação'))}")
                st.write(f"Data do pedido: {formatar_data(row.get('Data do pedido'))}")
                if coluna == "pedido_aut":
                    st.write(f"Data Aut. Pedido: {formatar_data(row.get('Data autorização do pedido'))}")

        elif "entrega" in coluna:
            st.text(f"Pedido: {row.get('N° do Pedido', '-')}")
            qtd_ent = converter_numero(row.get('Quantidade entregue', 0))
            un = row.get('Unidade de movimento', '')
            st.text(f"Qtd entregue: {qtd_ent:,.2f} {un}".replace(',', 'X').replace('.', ',').replace('X', '.'))

            st.markdown(":green[ Totalmente entregue ]")

            with st.expander("Ver Detalhes"):
                st.write(f"Nº da Solicitação: {row.get('Nº da Solicitação', '-')}")
                st.write(f"Fornecedor: {row.get('Fornecedor', '-')}")
                st.write(f"Data da solicitação: {formatar_data(row.get('Data da solicitação'))}")

# --- CONSTRUÇÃO DO KANBAN ---
head1, head2, head3, head4, head5 = st.columns(5)
with head1:
    st.subheader("🟠 Insumos Não Autorizados")
with head2:
    st.subheader("🔵 Insumos Autorizados")
with head3:
    st.subheader("🟠 Pedidos Não Autorizados")
with head4:
    st.subheader("🔵 Pedidos Autorizados")
with head5:
    st.subheader("🟢 Entregas")

ALTURA_COLUNA = 650
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    with st.container(height=ALTURA_COLUNA, border=False):
        for _, row in insumos_nao_aut.iterrows():
            render_card(row, "insumo_nao_aut")

with col2:
    with st.container(height=ALTURA_COLUNA, border=False):
        for _, row in insumos_aut.iterrows():
            render_card(row, "insumo_aut")

with col3:
    with st.container(height=ALTURA_COLUNA, border=False):
        for _, row in pedidos_nao_aut.iterrows():
            render_card(row, "pedido_nao_aut")

with col4:
    with st.container(height=ALTURA_COLUNA, border=False):
        for _, row in pedidos_aut.iterrows():
            render_card(row, "pedido_aut")

with col5:
    with st.container(height=ALTURA_COLUNA, border=False):
        for _, row in entregas.iterrows():
            render_card(row, "entrega")