import streamlit as st
import pandas as pd
from datetime import date, timedelta # NOVO: Para calcular a data de hoje e os 15 dias

# Mantém a tela inteira sem rolagem geral
st.set_page_config(layout="wide", page_title="Painel Oracon", page_icon="Oracon_Logo.png")

# Usamos colunas para deixar a imagem perfeitamente alinhada ao lado do texto
col_logo, col_titulo = st.columns([2, 15]) # O [1, 15] controla a proporção de espaço

with col_logo:
    # Ajuste o 'width' (largura) para deixar a logo maior ou menor
    st.image("Oracon_Logo.png", width=150) 

with col_titulo:
    # O st.title sem o emoji
    st.title("Painel de Compras Oracon")

st.markdown("Visão de suprimentos para engenheiros com atualização diária.")

# O seu código de carregamento de dados continua a partir daqui

@st.cache_data (ttl=900)
def load_data():
    df = pd.read_excel("Relatorio_Painel de Compras.xlsx")
    if 'Data da solicitação' in df.columns:
        df['Data da solicitação'] = pd.to_datetime(df['Data da solicitação'], dayfirst=True, errors='coerce')
    return df

try:
    df = load_data()
except FileNotFoundError:
    st.error("Arquivo 'Relatorio_Painel de Compras.xlsx' não encontrado. Verifique se ele está na mesma pasta.")
    st.stop()

# --- 1. FILTROS NA BARRA LATERAL ---
st.sidebar.header("🔍 Filtros do Painel")

obras_disponiveis = df['Obra'].dropna().unique().tolist()
obras_selecionadas = st.sidebar.multiselect(
    "Filtrar por Obra:",
    options=obras_disponiveis,
    default=[] # NOVO: Inicia sem nenhuma obra selecionada
)

solicitacoes_disponiveis = df['Nº da Solicitação'].dropna().unique().astype(str).tolist()
solicitacoes_disponiveis.sort()
solicitacoes_selecionadas = st.sidebar.multiselect(
    "Nº da Solicitação:",
    options=solicitacoes_disponiveis,
    default=[] 
)

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Período da Solicitação")

# NOVO: Cálculo automático das datas padrão (Hoje e 15 dias atrás)
hoje = date.today()
quinze_dias_atras = hoje - timedelta(days=15)

col_dt1, col_dt2 = st.sidebar.columns(2)
with col_dt1:
    data_inicio = st.date_input("Data Inicial", value=quinze_dias_atras, format="DD/MM/YYYY")
with col_dt2:
    data_fim = st.date_input("Data Final", value=hoje, format="DD/MM/YYYY")

# APLICAR FILTROS (Com inteligência para filtros vazios)
# 1. Primeiro filtra o período de datas (que sempre tem um valor)
df_filtrado = df[
    (df['Data da solicitação'].dt.date >= data_inicio) & 
    (df['Data da solicitação'].dt.date <= data_fim)
]

# 2. Se houver obras selecionadas, filtra por elas. Se não, mostra todas.
if obras_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['Obra'].isin(obras_selecionadas)]

# 3. Se houver solicitações selecionadas, filtra por elas.
if solicitacoes_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['Nº da Solicitação'].astype(str).isin(solicitacoes_selecionadas)]

# --- LÓGICA DE FILTRAGEM (Para as colunas) ---
mask_sem_pedido = df_filtrado['N° do Pedido'].isna()
insumos_aut = df_filtrado[mask_sem_pedido & (df_filtrado['Situação autorização do item'] == 'Autorizado')]
insumos_nao_aut = df_filtrado[mask_sem_pedido & (df_filtrado['Situação autorização do item'] != 'Autorizado')]

mask_com_pedido = df_filtrado['N° do Pedido'].notna() & (df_filtrado['Situação do pedido'] != 'Totalmente entregue')
pedidos_aut = df_filtrado[mask_com_pedido & (df_filtrado['Situação autorização do pedido'] == 'Autorizado')]
pedidos_nao_aut = df_filtrado[mask_com_pedido & (df_filtrado['Situação autorização do pedido'] != 'Autorizado')]

entregas = df_filtrado[df_filtrado['N° do Pedido'].notna() & (df_filtrado['Situação do pedido'] == 'Totalmente entregue')]

# --- FUNÇÃO DE SEGURANÇA PARA CONVERTER NÚMEROS DO EXCEL ---
def converter_numero(valor):
    if pd.isna(valor) or valor == '' or valor == '-':
        return 0.0
    if isinstance(valor, str):
        valor = valor.replace('.', '').replace(',', '.')
    try:
        return float(valor)
    except ValueError:
        return 0.0

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
            # Usando a função de segurança 'converter_numero'
            qtd_sol = converter_numero(row.get('Quantidade solicitada', 0))
            un = row.get('Unidade de movimento', '')
            st.text(f"Qtd: {qtd_sol:,.2f} {un}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            st.text(f"Nº Solicitação: {row.get('Nº da Solicitação', '-')}")
            
            status = row.get('Situação da solicitação', 'Pendente')
            cor = "blue" if status == "Parcialmente atendida" else "orange"
            st.markdown(f":{cor}[**{status}**]")
            
            with st.expander("Ver Detalhes"):
                data_sol = row.get('Data da solicitação')
                data_sol_str = data_sol.strftime('%d/%m/%Y') if pd.notna(data_sol) else '-'
                st.write(f"**Data da solicitação:** {data_sol_str}")
            
        elif tipo == "pedido":
            # Usando a função de segurança 'converter_numero'
            qtd_pendente = converter_numero(row.get('Saldo', 0))
            un = row.get('Unidade de movimento', '')
            st.text(f"Qtd pendente: {qtd_pendente:,.2f} {un}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            
            st.text(f"Pedido: {row.get('N° do Pedido', '-')}")
            
            status = row.get('Situação do pedido', 'Pendente')
            st.markdown(f":orange[**{status}**]")
            
            with st.expander("Ver Detalhes"):
                st.write(f"**Nº da Solicitação:** {row.get('Nº da Solicitação', '-')}")
                st.write(f"**Fornecedor:** {row.get('Fornecedor', '-')}")
                data_sol = row.get('Data da solicitação')
                data_sol_str = data_sol.strftime('%d/%m/%Y') if pd.notna(data_sol) else '-'
                st.write(f"**Data da solicitação:** {data_sol_str}")
            
        elif tipo == "entrega":
            st.text(f"Pedido: {row.get('N° do Pedido', '-')}")
            
            # Usando a função de segurança 'converter_numero'
            qtd_ent = converter_numero(row.get('Quantidade entregue', 0))
            un = row.get('Unidade de movimento', '')
            st.text(f"Qtd entregue: {qtd_ent:,.2f} {un}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            
            st.markdown(f":green[**Totalmente entregue**]")
            
            with st.expander("Ver Detalhes"):
                st.write(f"**Nº da Solicitação:** {row.get('Nº da Solicitação', '-')}")
                st.write(f"**Fornecedor:** {row.get('Fornecedor', '-')}")
                data_sol = row.get('Data da solicitação')
                data_sol_str = data_sol.strftime('%d/%m/%Y') if pd.notna(data_sol) else '-'
                st.write(f"**Data da solicitação:** {data_sol_str}")

# --- CONSTRUÇÃO DO KANBAN ---

head1, head2, head3, head4, head5 = st.columns(5)
with head1: st.subheader("🟠 Insumos Não Autorizados")
with head2: st.subheader("🔵 Insumos Autorizados")
with head3: st.subheader("🟠 Pedidos Não Autorizados")
with head4: st.subheader("🔵 Pedidos Autorizados")
with head5: st.subheader("🟢 Entregas")

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
