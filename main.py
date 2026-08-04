import streamlit as st
import pandas as pd
import re
import urllib.parse
import os
from datetime import datetime

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Missão NY | Gestão", page_icon="🕊️", layout="centered")
st.title("🕊️ Missão LusoBrasileira NY")

# Nomes dos arquivos (certifique-se de que o nome da planilha na raiz do GitHub seja exatamente este)
DB_FILE = 'banco_de_dados_missao.csv'
MISSIONARIOS_FILE = 'missionarios.csv'
TEMPLATE_FILE = 'mensagem_padrao.txt'
EXCEL_INICIAL = 'FORMULARIO MISSAO NY (Responses).xlsx'

# Mensagem Padrão Atualizada
MENSAGEM_INICIAL = """¡Hola [NOME]! Fue un gusto conocerte en la feria de salud.
Te invitamos a "Noches de Esperanza", nuestro programa hispano hoy en la Iglesia Adventista Luso-Brasileña

🎁 ¡Sortearemos 2 Airfryers entre quienes asistan todas las noches!
📍 Iglesia Adventista Luso-Brasileña: 96-11 34th Ave, Corona, NY 11368.
⏰ Hoy a las 7:45 PM. ¡Te esperamos con tu familia!"""

# Missionárias Padrão
MISSIONARIOS_INICIAIS = ['Célia', 'Brícia', 'Bruna', 'Benere', 'Marly']


# 2. FUNÇÕES DE SUPORTE
def format_us_number(phone_str):
    if pd.isna(phone_str) or not str(phone_str).strip():
        return None, "Sem número"
    digits = re.sub(r'\D', '', str(phone_str))
    if len(digits) == 10:
        return f"1{digits}", "Válido"
    elif len(digits) == 11 and digits.startswith('1'):
        return digits, "Válido"
    else:
        return None, "Mal formatado"


def get_whatsapp_link(phone, name, template_msg):
    if pd.isna(phone) or not phone:
        return None

    phone_str = str(phone).replace('.0', '')
    msg = template_msg.replace("[NOME]", str(name))

    encoded_msg = urllib.parse.quote(msg.encode('utf-8'))
    return f"https://api.whatsapp.com/send?phone={phone_str}&text={encoded_msg}"


def redistribuir_contatos(df_dados, lista_missionarios):
    if df_dados.empty or not lista_missionarios:
        return df_dados

    for i, idx in enumerate(df_dados.index):
        df_dados.at[idx, 'Missionario_Designado'] = lista_missionarios[i % len(lista_missionarios)]
    return df_dados


# 4. INICIALIZAÇÃO DO SISTEMA E IMPORTAÇÃO
if 'admin_logged' not in st.session_state:
    st.session_state['admin_logged'] = False

if not os.path.exists(MISSIONARIOS_FILE):
    pd.DataFrame({'Nome': MISSIONARIOS_INICIAIS}).to_csv(MISSIONARIOS_FILE, index=False)

if not os.path.exists(TEMPLATE_FILE):
    with open(TEMPLATE_FILE, 'w', encoding='utf-8') as f:
        f.write(MENSAGEM_INICIAL)

if not os.path.exists(DB_FILE):
    df_base = pd.DataFrame(columns=[
        'Timestamp', 'Nome', 'Telefone_Original', 'Telefone_Validado',
        'Status_Telefone', 'Link_WhatsApp', 'Missionario_Designado',
        'Contato_Realizado', 'Data_Ultimo_Contato'
    ])

    if os.path.exists(EXCEL_INICIAL):
        try:
            df_novo = pd.read_excel(EXCEL_INICIAL)
            col_nome = [c for c in df_novo.columns if 'nome' in c.lower() or 'name' in c.lower()][0]
            col_tel = [c for c in df_novo.columns if 'telefone' in c.lower() or 'phone' in c.lower() or 'telefono' in c.lower()][0]

            novas_linhas = []
            for index, row in df_novo.iterrows():
                phone, status = format_us_number(row[col_tel])
                nova_linha = {
                    'Timestamp': row.get('Timestamp', datetime.now()),
                    'Nome': row[col_nome],
                    'Telefone_Original': row[col_tel],
                    'Telefone_Validado': phone,
                    'Status_Telefone': status,
                    'Link_WhatsApp': get_whatsapp_link(phone, row[col_nome], MENSAGEM_INICIAL),
                    'Missionario_Designado': "Pendente",
                    'Contato_Realizado': False,
                    'Data_Ultimo_Contato': None
                }
                novas_linhas.append(nova_linha)

            df_db = pd.concat([df_base, pd.DataFrame(novas_linhas)], ignore_index=True)
            df_db = redistribuir_contatos(df_db, MISSIONARIOS_INICIAIS)
            df_db.to_csv(DB_FILE, index=False)
        except Exception as e:
            st.error(f"Erro ao importar {EXCEL_INICIAL}: {e}")
            df_base.to_csv(DB_FILE, index=False)
    else:
        df_base.to_csv(DB_FILE, index=False)

# Carrega os dados atualizados
df_missionarios = pd.read_csv(MISSIONARIOS_FILE)
df_db = pd.read_csv(DB_FILE)

# Garante que as colunas aceitem texto
df_db['Data_Ultimo_Contato'] = df_db['Data_Ultimo_Contato'].astype(object)
df_db['Telefone_Validado'] = df_db['Telefone_Validado'].astype(object)

with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
    template_msg = f.read()

# 5. INTERFACE COM ABAS
tab1, tab2 = st.tabs(["📋 Contatos", "⚙️ Administração"])

# ==========================================
# ABA 1: LISTAGEM DE CONTATOS
# ==========================================
with tab1:
    st.header("Lista de Interessados")

    if not df_db.empty:
        c1, c2 = st.columns(2)
        with c1:
            com_filtro_status = st.selectbox("Filtro de Status:", ["Pendentes", "Contactados", "Todos"])
        with c2:
            opcoes_missionarios = ["Todos"] + sorted(df_db['Missionario_Designado'].dropna().unique().tolist())
            filtro_missionario = st.selectbox("Filtrar por Missionário:", opcoes_missionarios)

        df_exibicao = df_db.copy()

        if com_filtro_status == "Pendentes":
            df_exibicao = df_exibicao[df_exibicao['Contato_Realizado'] == False]
        elif com_filtro_status == "Contactados":
            df_exibicao = df_exibicao[df_exibicao['Contato_Realizado'] == True]

        if filtro_missionario != "Todos":
            df_exibicao = df_exibicao[df_exibicao['Missionario_Designado'] == filtro_missionario]

        st.divider()
        st.write(f"**Total de contatos encontrados:** {len(df_exibicao)}")

        if not df_exibicao.empty:
            hc1, hc2, hc3, hc4 = st.columns([3, 2, 2, 3])
            hc1.markdown("**Nome e Telefone**")
            hc2.markdown("**Designado(a)**")
            hc3.markdown("**Status**")
            hc4.markdown("**Ação**")
            st.divider()

            for idx, row in df_exibicao.iterrows():
                cc1, cc2, cc3, cc4 = st.columns([3, 2, 2, 3])

                with cc1:
                    st.write(f"**{row['Nome']}**")
                    if pd.notna(row['Telefone_Validado']):
                        telefone_limpo = str(row['Telefone_Validado']).replace('.0', '')
                        telefone_exibicao = f"+{telefone_limpo}"
                    else:
                        telefone_exibicao = "S/ Número"
                    st.caption(f"📞 {telefone_exibicao}")

                with cc2:
                    st.write(f"{row['Missionario_Designado']}")

                with cc3:
                    if row['Contato_Realizado']:
                        st.success("✅ Ok")
                    else:
                        st.warning("⏳ Pendente")

                with cc4:
                    if not row['Contato_Realizado']:
                        if row['Status_Telefone'] == 'Válido':
                            link_whatsapp = get_whatsapp_link(row['Telefone_Validado'], row['Nome'], template_msg)
                            
                            # Botão em HTML puro para evitar bloqueador de pop-up
                            st.markdown(f"""
                                <a href="{link_whatsapp}" target="_blank" style="
                                    display: inline-block;
                                    text-align: center;
                                    background-color: #25D366;
                                    color: white;
                                    padding: 0.4rem 1rem;
                                    border-radius: 0.5rem;
                                    text-decoration: none;
                                    font-weight: 600;
                                    width: 100%;
                                    box-sizing: border-box;
                                    margin-bottom: 5px;
                                ">💬 Enviar</a>
                            """, unsafe_allow_html=True)

                            # Checkbox para marcar o envio após abrir a conversa
                            marcado = st.checkbox("Marcar enviado", key=f"chk_{idx}", value=row['Contato_Realizado'])
                            if marcado:
                                df_db.at[idx, 'Contato_Realizado'] = True
                                df_db.at[idx, 'Data_Ultimo_Contato'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                                df_db.to_csv(DB_FILE, index=False)
                                st.rerun()
                        else:
                            st.button("Inválido", key=f"btn_err_{idx}", disabled=True, use_container_width=True)
                    else:
                        if st.button("🔄 Desfazer", key=f"btn_undo_{idx}", use_container_width=True):
                            df_db.at[idx, 'Contato_Realizado'] = False
                            df_db.at[idx, 'Data_Ultimo_Contato'] = None
                            df_db.to_csv(DB_FILE, index=False)
                            st.rerun()
                st.divider()
        else:
            st.info("Nenhum contato encontrado com os filtros atuais.")
    else:
        st.warning(f"O banco de dados está vazio. Certifique-se de que o arquivo '{EXCEL_INICIAL}' está na raiz do repositório.")

# ==========================================
# ABA 2: ADMINISTRAÇÃO (Protegida por Senha)
# ==========================================
with tab2:
    if not st.session_state['admin_logged']:
        st.header("🔒 Acesso Restrito")
        st.write("Área exclusiva para gestão do sistema.")
        senha = st.text_input("Digite a senha de administrador:", type="password")
        if st.button("Acessar", type="primary", use_container_width=True):
            if senha == "missão":
                st.session_state['admin_logged'] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
    else:
        st.header("⚙️ Painel de Gestão")
        if st.button("Sair do Modo Admin", use_container_width=True):
            st.session_state['admin_logged'] = False
            st.rerun()

        st.divider()

        st.subheader("📥 Receber Novos Formulários")
        uploaded_file = st.file_uploader("Envie a planilha do Forms (.xlsx)", type=["xlsx"])

        if uploaded_file is not None:
            if st.button("Processar Arquivo", type="primary", use_container_width=True):
                try:
                    df_novo = pd.read_excel(uploaded_file)

                    col_nome = [c for c in df_novo.columns if 'nome' in c.lower() or 'name' in c.lower()][0]
                    col_tel = [c for c in df_novo.columns if 'telefone' in c.lower() or 'phone' in c.lower() or 'telefono' in c.lower()][0]

                    df_novo.rename(columns={col_nome: 'Nome', col_tel: 'Telefone_Original'}, inplace=True)

                    if not df_db.empty:
                        novos = df_novo[~df_novo['Timestamp'].astype(str).isin(df_db['Timestamp'].astype(str))].copy()
                    else:
                        novos = df_novo.copy()

                    if not novos.empty:
                        missionarios_ativos = df_missionarios['Nome'].tolist()
                        novas_linhas = []

                        for index, row in novos.iterrows():
                            phone, status = format_us_number(row['Telefone_Original'])
                            nova_linha = row.to_dict()
                            nova_linha.update({
                                'Telefone_Validado': phone,
                                'Status_Telefone': status,
                                'Link_WhatsApp': get_whatsapp_link(phone, row['Nome'], template_msg),
                                'Missionario_Designado': "Pendente",
                                'Contato_Realizado': False,
                                'Data_Ultimo_Contato': None
                            })
                            novas_linhas.append(nova_linha)

                        df_db = pd.concat([df_db, pd.DataFrame(novas_linhas)], ignore_index=True)
                        df_db = redistribuir_contatos(df_db, missionarios_ativos)
                        df_db.to_csv(DB_FILE, index=False)
                        st.success(f"{len(novas_linhas)} novos contatos inseridos e lista redistribuída com sucesso!")
                    else:
                        st.info("Nenhum cadastro novo encontrado nesta planilha.")
                except Exception as e:
                    st.error(f"Erro ao processar o arquivo: {e}")

        st.divider()

        st.subheader("👥 Equipe & Distribuição")
        st.write("Edite a lista. Adicionar ou remover alguém afetará a distribuição de todos os contatos.")
        edited_missionarios = st.data_editor(
            df_missionarios, num_rows="dynamic", use_container_width=True, hide_index=True
        )

        if st.button("💾 Salvar Equipe e Redistribuir Contatos", type="primary", use_container_width=True):
            edited_missionarios.to_csv(MISSIONARIOS_FILE, index=False)
            lista_atualizada = edited_missionarios['Nome'].dropna().tolist()
            df_db = redistribuir_contatos(df_db, lista_atualizada)
            df_db.to_csv(DB_FILE, index=False)
            st.success("Equipe salva e contatos redistribuídos com sucesso!")
            st.rerun()

        st.divider()

        st.subheader("✉️ Mensagem Padrão")
        novo_template = st.text_area(
            "Use [NOME] onde o nome da pessoa deve aparecer:",
            template_msg,
            height=250
        )
        if st.button("💾 Salvar Nova Mensagem", use_container_width=True):
            with open(TEMPLATE_FILE, 'w', encoding='utf-8') as f:
                f.write(novo_template)
            st.success("Mensagem atualizada!")
            st.rerun()

        st.divider()

        with st.expander("⚠️ Zona de Perigo (Limpar Dados)"):
            st.error("Esta ação apagará todo o histórico e os contatos. A equipe e a mensagem serão mantidas.")
            confirmacao = st.text_input('Digite "APAGAR" para confirmar:')
            if st.button("🗑️ Limpar Todos os Dados"):
                if confirmacao == "APAGAR":
                    pd.DataFrame(columns=df_db.columns).to_csv(DB_FILE, index=False)
                    st.success("Banco de dados resetado com sucesso!")
                    st.rerun()
                else:
                    st.warning("Confirmação incorreta. Ação cancelada.")
