import streamlit as st
import pandas as pd
import sqlite3
import os
import datetime

st.set_page_config(page_title="Gestão de Bingo 2026", layout="wide", page_icon="🎱")

def check_password():
    """Valida o usuário e a senha verificando no st.secrets"""
    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Acesso Restrito")
    with st.form("login_form"):
        username_input = st.text_input("Usuário")
        pwd = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        
        if submitted:
            try:
                usernames_dict = st.secrets["credentials"]["usernames"]
                user = str(username_input).strip()
                digitada = str(pwd).strip()
                
                if user in usernames_dict and usernames_dict[user] == digitada:
                    st.session_state["password_correct"] = True
                    st.session_state["logged_user"] = user
                    st.rerun()
                else:
                    st.error("😕 Usuário ou senha incorretos.")
            except KeyError:
                st.error("Erro: secrets.toml não configurado na chave [credentials] usernames.")
                
    return False

if not check_password():
    st.stop()  # Impede a execução do restante do código se não estiver logado

DB_FILE = 'bingo_2026.db'

def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            event_id INTEGER,
            key TEXT,
            value REAL,
            PRIMARY KEY (event_id, key)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS event_vendors (
            event_id INTEGER,
            vendor_id INTEGER,
            troco_enviado REAL DEFAULT 0,
            troco_devolvido REAL DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            PRIMARY KEY (event_id, vendor_id)
        )
    ''')
    try:
        c.execute('ALTER TABLE event_vendors ADD COLUMN is_active BOOLEAN DEFAULT 1')
    except sqlite3.OperationalError:
        pass
    c.execute('''
        CREATE TABLE IF NOT EXISTS rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            round_type TEXT,
            name TEXT,
            valor_cartela REAL,
            UNIQUE(event_id, round_type, name)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendor_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_id INTEGER,
            vendor_id INTEGER,
            cartelas_recebidas INTEGER DEFAULT 0,
            cartelas_adicionais INTEGER DEFAULT 0,
            cartelas_devolvidas INTEGER DEFAULT 0,
            val_dinheiro REAL DEFAULT 0,
            val_pix REAL DEFAULT 0,
            val_santa_ficha REAL DEFAULT 0,
            val_debito REAL DEFAULT 0,
            UNIQUE(round_id, vendor_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS sangrias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            valor REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    try:
        c.execute("ALTER TABLE audit_logs ADD COLUMN username TEXT DEFAULT 'Sistema'")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def log_action(event_id, action):
    conn = get_conn()
    username = st.session_state.get("logged_user", "Sistema")
    try:
        conn.execute("INSERT INTO audit_logs (event_id, action, username) VALUES (?, ?, ?)", (event_id, action, username))
    except sqlite3.OperationalError:
        conn.execute("INSERT INTO audit_logs (event_id, action) VALUES (?, ?)", (event_id, action))
    conn.commit()
    conn.close()

if not os.path.exists(DB_FILE):
    init_db()
else:
    init_db()

# Funções de Auxílio DB
def get_setting(event_id, key, default=0.0):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE event_id = ? AND key = ?', (event_id, key))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(event_id, key, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO settings (event_id, key, value) 
        VALUES (?, ?, ?) 
        ON CONFLICT(event_id, key) DO UPDATE SET value=excluded.value
    ''', (event_id, key, value))
    conn.commit()
    conn.close()

def get_current_date_name():
    dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    hoje = datetime.datetime.now()
    dia_nome = dias_semana[hoje.weekday()]
    data_str = hoje.strftime("%d/%m")
    return f"{dia_nome} {data_str}"

@st.dialog("Cadastrar Novo Vendedor")
def add_vendor_modal():
    vname = st.text_input("Nome do Vendedor")
    if st.button("Salvar Vendedor", type="primary"):
        if vname:
            conn = get_conn()
            try:
                conn.execute("INSERT INTO vendors (name) VALUES (?)", (vname,))
                conn.commit()
                st.success(f"Vendedor {vname} cadastrado com sucesso!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Este vendedor já existe.")
            finally:
                conn.close()
        else:
            st.error("Informe o nome do vendedor.")

# Sidebar para Gestão de Eventos
st.sidebar.title("📅 Gestão de Eventos")

conn = get_conn()
df_events = pd.read_sql('SELECT * FROM events ORDER BY id DESC', conn)

with st.sidebar.expander("➕ Novo Evento", expanded=False):
    novo_nome = st.text_input("Nome do Evento", value=get_current_date_name())
    if st.button("Criar Evento", use_container_width=True, type="primary"):
        if novo_nome:
            try:
                conn.execute("INSERT INTO events (name) VALUES (?)", (novo_nome,))
                conn.commit()
                st.success(f"Evento criado!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Já existe um evento com este nome.")

if df_events.empty:
    st.sidebar.warning("Nenhum evento criado. Crie um evento para começar.")
    st.title("🎱 Sistema de Controle do Bingo 2026")
    st.info("⬅️ Crie um evento na barra lateral para iniciar.")
    st.stop()

# Seleção de Evento
event_options = df_events.apply(lambda x: f"[{x['id']}] {x['name']}", axis=1).tolist()
selected_event_str = st.sidebar.selectbox("Evento Ativo", event_options)
active_event_id = int(selected_event_str.split(']')[0][1:])
active_event_name = selected_event_str.split('] ')[1]

st.sidebar.success(f"Ativo: {active_event_name}")

st.sidebar.divider()
st.sidebar.subheader("👤 Vendedores")
if st.sidebar.button("➕ Novo Vendedor", use_container_width=True):
    add_vendor_modal()

st.sidebar.divider()
current_user = st.session_state.get("logged_user", "Usuário")
st.sidebar.markdown(f"**Bem-vindo, {current_user.capitalize()}!**")
if st.sidebar.button("🚪 Sair (Logout)", use_container_width=True):
    st.session_state["password_correct"] = False
    st.session_state["logged_user"] = None
    st.rerun()

conn.close()


@st.dialog("Criar Nova Rodada")
def add_round_modal(event_id):
    round_type = st.selectbox("Tipo de Rodada", ["Geral", "Extra", "Dinheiro"])
    name = st.text_input("Sequência / Nome (ex: A, B, 1, 2)")
    valor_cartela = st.number_input("Valor da Cartela (R$)", min_value=0.0, step=0.5, format="%.2f")
    
    if st.button("Salvar Rodada", type="primary"):
        if name:
            conn = get_conn()
            try:
                conn.execute("INSERT INTO rounds (event_id, round_type, name, valor_cartela) VALUES (?, ?, ?, ?)", (event_id, round_type, name, valor_cartela))
                conn.commit()
                log_action(event_id, f"Criou a rodada {round_type} - {name} com cartela a R$ {valor_cartela:.2f}")
                st.success(f"Rodada {round_type} - {name} criada com sucesso!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Esta rodada já existe neste evento.")
            finally:
                conn.close()
        else:
            st.error("Informe a sequência/nome da rodada.")

@st.dialog("Registro de Vendedor")
def open_vendor_modal(r_id, vid, vname, r_price, event_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM vendor_rounds WHERE round_id=? AND vendor_id=?', (r_id, vid))
    vr_row = c.fetchone()
    conn.close()
    
    vr_cr = vr_row[3] if vr_row else 0
    vr_ca = vr_row[4] if vr_row else 0
    vr_cd = vr_row[5] if vr_row else 0
    vr_vd = vr_row[6] if vr_row else 0.0
    vr_vp = vr_row[7] if vr_row else 0.0
    vr_vsf = vr_row[8] if vr_row else 0.0
    vr_vdeb = vr_row[9] if vr_row else 0.0

    st.markdown(f"### 👤 {vname}")
    
    with st.expander("Controle de Cartelas", expanded=True):
        cr = st.number_input("Recebidas", min_value=0, value=int(vr_cr), step=1, key=f"m_cr_{r_id}_{vid}")
        ca = st.number_input("Adicionais", min_value=0, value=int(vr_ca), step=1, key=f"m_ca_{r_id}_{vid}")
        cd = st.number_input("Devolvidas", min_value=0, value=int(vr_cd), step=1, key=f"m_cd_{r_id}_{vid}")
    
    cartelas_vendidas = cr + ca - cd
    valor_esperado = cartelas_vendidas * r_price
    
    with st.expander("Valores Devolvidos (R$)", expanded=True):
        vd = st.number_input("Dinheiro", min_value=0.0, value=float(vr_vd), step=5.0, format="%.2f", key=f"m_vd_{r_id}_{vid}")
        vp = st.number_input("Pix", min_value=0.0, value=float(vr_vp), step=5.0, format="%.2f", key=f"m_vp_{r_id}_{vid}")
        vsf = st.number_input("Santa Ficha", min_value=0.0, value=float(vr_vsf), step=5.0, format="%.2f", key=f"m_vsf_{r_id}_{vid}")
        vdeb = st.number_input("Débito", min_value=0.0, value=float(vr_vdeb), step=5.0, format="%.2f", key=f"m_vdeb_{r_id}_{vid}")
        
    valor_devolvido = vd + vp + vsf + vdeb
    diferenca = valor_esperado - valor_devolvido
    
    st.markdown(f"**Cartelas Vendidas:** {cartelas_vendidas}")
    st.markdown(f"**Valor Esperado:** R$ {valor_esperado:.2f}")
    st.markdown(f"**Valor Devolvido:** R$ {valor_devolvido:.2f}")
    
    if abs(diferenca) > 0.01:
        if diferenca > 0:
            st.error(f"Faltando: R$ {diferenca:.2f}")
        else:
            st.warning(f"Excedente: R$ {abs(diferenca):.2f}")
    else:
        st.success("Tudo certo! (Diferença: R$ 0.00)")
        
    if st.button("💾 Salvar Registro", key=f"m_btn_{r_id}_{vid}", use_container_width=True):
        conn_local = get_conn()
        conn_local.execute('''
            INSERT INTO vendor_rounds (round_id, vendor_id, cartelas_recebidas, cartelas_adicionais, cartelas_devolvidas, val_dinheiro, val_pix, val_santa_ficha, val_debito)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(round_id, vendor_id) DO UPDATE SET
                cartelas_recebidas=excluded.cartelas_recebidas,
                cartelas_adicionais=excluded.cartelas_adicionais,
                cartelas_devolvidas=excluded.cartelas_devolvidas,
                val_dinheiro=excluded.val_dinheiro,
                val_pix=excluded.val_pix,
                val_santa_ficha=excluded.val_santa_ficha,
                val_debito=excluded.val_debito
        ''', (r_id, vid, cr, ca, cd, vd, vp, vsf, vdeb))
        conn_local.commit()
        conn_local.close()
        log_action(event_id, f"Salvou registro do vendedor {vname} na rodada ID {r_id} (Cartelas vendidas: {cartelas_vendidas}, Devolvido: R$ {valor_devolvido:.2f})")
        st.toast(f"Registro de {vname} salvo!")
        st.rerun()

# Interface Principal
st.title(f"🎱 Sistema de Controle - {active_event_name}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚙️ Dados do Dia", "🎯 Rodadas e Vendedores", "💰 Sangria", "📊 Fechamento", "📋 Logs"])

with tab1:
    st.header("Dados Iniciais do Evento")
    
    colA, colB = st.columns([1, 2])
    with colA:
        current_caixa = get_setting(active_event_id, 'caixa_inicial', 0.0)
        caixa_inicial = st.number_input("Valor do Caixa Inicial (R$)", min_value=0.0, step=10.0, value=float(current_caixa), format="%.2f")
        if st.button("Salvar Caixa Inicial", type="primary"):
            set_setting(active_event_id, 'caixa_inicial', caixa_inicial)
            log_action(active_event_id, f"Definiu o caixa inicial como R$ {caixa_inicial:.2f}")
            st.success("Caixa inicial salvo para este evento!")
            
    with colB:
        st.subheader("Gestão de Vendedores no Evento")
        st.write("Marque os vendedores ativos neste evento e lance o Troco Enviado.")
        conn = get_conn()
        
        query = '''
            SELECT v.id, v.name, COALESCE(ev.is_active, 0) as is_active, COALESCE(ev.troco_enviado, 0.0) as troco_enviado
            FROM vendors v
            LEFT JOIN event_vendors ev ON v.id = ev.vendor_id AND ev.event_id = ?
        '''
        df_vendors = pd.read_sql(query, conn, params=(active_event_id,))
        df_vendors['is_active'] = df_vendors['is_active'].astype(bool)
        
        edited_vendors = st.data_editor(
            df_vendors,
            column_config={
                "id": None,
                "is_active": st.column_config.CheckboxColumn("Ativo no Evento?", default=False),
                "name": st.column_config.TextColumn("Nome do Vendedor", required=True),
                "troco_enviado": st.column_config.NumberColumn("Troco Enviado (R$)", min_value=0.0, format="R$ %.2f")
            },
            hide_index=True,
            key="vendors_init_editor",
            use_container_width=True
        )
        
        if st.button("Salvar Vendedores"):
            existing_ids = edited_vendors['id'].dropna().astype(int).tolist()
            if existing_ids:
                placeholders = ','.join('?' for _ in existing_ids)
                conn.execute(f"DELETE FROM vendors WHERE id NOT IN ({placeholders})", existing_ids)
            else:
                conn.execute("DELETE FROM vendors")

            for _, row in edited_vendors.iterrows():
                name = row['name'] if pd.notna(row['name']) else ""
                is_active = int(row['is_active']) if pd.notna(row['is_active']) else 1
                t_env = row['troco_enviado'] if pd.notna(row['troco_enviado']) else 0.0
                
                if pd.isna(row['id']) and name:
                    c = conn.execute("INSERT OR IGNORE INTO vendors (name) VALUES (?)", (name,))
                    vid = c.lastrowid
                    if vid is None:
                        c_find = conn.execute("SELECT id FROM vendors WHERE name=?", (name,))
                        vid = c_find.fetchone()[0]
                    
                    conn.execute("""
                        INSERT INTO event_vendors (event_id, vendor_id, is_active, troco_enviado) 
                        VALUES (?, ?, ?, ?) 
                        ON CONFLICT(event_id, vendor_id) DO UPDATE SET is_active=excluded.is_active, troco_enviado=excluded.troco_enviado
                    """, (active_event_id, vid, is_active, t_env))
                    
                elif not pd.isna(row['id']):
                    vid = int(row['id'])
                    conn.execute("UPDATE vendors SET name=? WHERE id=?", (name, vid))
                    conn.execute("""
                        INSERT INTO event_vendors (event_id, vendor_id, is_active, troco_enviado) 
                        VALUES (?, ?, ?, ?) 
                        ON CONFLICT(event_id, vendor_id) DO UPDATE SET is_active=excluded.is_active, troco_enviado=excluded.troco_enviado
                    """, (active_event_id, vid, is_active, t_env))
                    
            conn.commit()
            conn.close()
            log_action(active_event_id, "Atualizou a lista de vendedores ativos e os trocos enviados.")
            st.success("Vendedores e trocos atualizados com sucesso!")
            st.rerun()
        else:
            conn.close()

with tab2:
    st.header("Gestão de Rodadas")
    
    if st.button("➕ Criar Nova Rodada", type="primary"):
        add_round_modal(active_event_id)
        
    st.divider()
    
    conn = get_conn()
    df_rounds = pd.read_sql('SELECT * FROM rounds WHERE event_id=? ORDER BY id', conn, params=(active_event_id,))
    
    query_active_vendors = '''
        SELECT v.id, v.name 
        FROM vendors v
        JOIN event_vendors ev ON v.id = ev.vendor_id
        WHERE ev.event_id = ? AND ev.is_active = 1
        ORDER BY v.name
    '''
    df_vendors = pd.read_sql(query_active_vendors, conn, params=(active_event_id,))
    
    if not df_rounds.empty and not df_vendors.empty:
        round_options = df_rounds.apply(lambda x: f"[{int(x['id'])}] {x['round_type']} - {x['name']} (R$ {x['valor_cartela']:.2f})", axis=1).tolist()
        selected_round_str = st.selectbox("Selecione a Rodada Atual para Lançamentos", round_options)
        
        selected_round_id = int(selected_round_str.split(']')[0][1:])
        selected_round_row = df_rounds[df_rounds['id'] == selected_round_id].iloc[0]
        r_id = int(selected_round_row['id'])
        r_price = float(selected_round_row['valor_cartela'])
        
        st.subheader("Registro das Informações por Vendedor")
        st.write("Clique no **Nome do Vendedor** para abrir seu registro de cartelas e valores:")
        
        df_vr_all = pd.read_sql('SELECT vendor_id FROM vendor_rounds WHERE round_id=?', conn, params=(r_id,))
        registered_vids = df_vr_all['vendor_id'].tolist()
        
        col_h1, col_h2 = st.columns([3, 1])
        col_h1.markdown("**Nome do Vendedor**")
        col_h2.markdown("**Status na Rodada**")
        st.divider()
        
        for idx, vendor in df_vendors.iterrows():
            vid = int(vendor['id'])
            vname = vendor['name']
            status = "✅ Registrado" if vid in registered_vids else "⏳ Pendente"
            
            c1, c2 = st.columns([3, 1])
            with c1:
                if st.button(vname, key=f"btn_modal_{r_id}_{vid}", use_container_width=True, type="secondary"):
                    open_vendor_modal(r_id, vid, vname, r_price, active_event_id)
            with c2:
                st.markdown(f"<div style='margin-top: 5px;'>{status}</div>", unsafe_allow_html=True)

        st.divider()
        st.header("Resultado da Rodada")
        
        df_vr = pd.read_sql('SELECT * FROM vendor_rounds WHERE round_id=?', conn, params=(r_id,))
        if not df_vr.empty:
            df_vr['vendidas'] = df_vr['cartelas_recebidas'] + df_vr['cartelas_adicionais'] - df_vr['cartelas_devolvidas']
            total_vendidas = df_vr['vendidas'].sum()
            receita_total = total_vendidas * r_price
            t_dinheiro = df_vr['val_dinheiro'].sum()
            t_pix = df_vr['val_pix'].sum()
            t_sf = df_vr['val_santa_ficha'].sum()
            t_deb = df_vr['val_debito'].sum()
            t_devolvido = t_dinheiro + t_pix + t_sf + t_deb
            t_diff = receita_total - t_devolvido
            
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Cartelas Vendidas", int(total_vendidas))
            m2.metric("Receita (Esperada)", f"R$ {receita_total:.2f}")
            m3.metric("Total Dinheiro", f"R$ {t_dinheiro:.2f}")
            m4.metric("Total Pix", f"R$ {t_pix:.2f}")
            m5.metric("Total Santa Ficha", f"R$ {t_sf:.2f}")
            m6.metric("Total Débito", f"R$ {t_deb:.2f}")
            
            if abs(t_diff) > 0.01:
                st.error(f"Divergência Total na Rodada: R$ {t_diff:.2f} (Falta)" if t_diff > 0 else f"Divergência Total na Rodada: R$ {abs(t_diff):.2f} (Excesso)")
            else:
                st.success("Caixa da rodada bateu perfeitamente!")
        else:
            st.info("Nenhum registro salvo para esta rodada ainda.")

    elif df_vendors.empty:
        st.warning("Cadastre vendedores na aba 'Dados do Dia'.")
    elif df_rounds.empty:
        st.info("Crie uma rodada para começar.")
    
    conn.close()

with tab3:
    st.header("Sangria (Envio de Dinheiro ao Caixa Central)")
    st.write("Registre os valores em dinheiro que foram retirados do caixa para envio ao caixa central neste evento.")
    
    sangria_val = st.number_input("Valor da Sangria (R$)", min_value=0.0, step=10.0, format="%.2f")
    if st.button("Registrar Sangria", type="primary"):
        if sangria_val > 0:
            conn = get_conn()
            conn.execute("INSERT INTO sangrias (event_id, valor) VALUES (?, ?)", (active_event_id, sangria_val))
            conn.commit()
            conn.close()
            log_action(active_event_id, f"Registrou uma sangria de R$ {sangria_val:.2f}")
            st.success(f"Sangria de R$ {sangria_val:.2f} registrada com sucesso!")
        else:
            st.error("O valor deve ser maior que zero.")
            
    st.subheader("Histórico de Sangrias")
    conn = get_conn()
    df_sangrias = pd.read_sql('SELECT id, timestamp, valor FROM sangrias WHERE event_id=? ORDER BY timestamp DESC', conn, params=(active_event_id,))
    conn.close()
    
    if not df_sangrias.empty:
        df_sangrias['timestamp'] = pd.to_datetime(df_sangrias['timestamp']).dt.strftime('%d/%m/%Y %H:%M:%S')
        st.dataframe(
            df_sangrias,
            column_config={
                "id": None,
                "timestamp": "Data/Hora",
                "valor": st.column_config.NumberColumn("Valor Enviado", format="R$ %.2f")
            },
            hide_index=True,
            use_container_width=True
        )
        total_sangria = df_sangrias['valor'].sum()
        st.metric("Total de Sangrias Realizadas", f"R$ {total_sangria:.2f}")
    else:
        st.info("Nenhuma sangria registrada neste evento.")

with tab4:
    st.header("Fechamento do Evento")
    
    colA, colB = st.columns([1, 2])
    with colA:
        st.subheader("Dinheiro em Caixa")
        current_dinheiro = get_setting(active_event_id, 'dinheiro_fechamento', 0.0)
        dinheiro_fechamento = st.number_input("Valor em Dinheiro Existente (R$)", min_value=0.0, step=10.0, value=float(current_dinheiro), format="%.2f")
        if st.button("Salvar Valor em Caixa"):
            set_setting(active_event_id, 'dinheiro_fechamento', dinheiro_fechamento)
            log_action(active_event_id, f"Definiu o dinheiro final em caixa como R$ {dinheiro_fechamento:.2f}")
            st.success("Valor em caixa salvo para este evento!")
            st.rerun()
            
    with colB:
        st.subheader("Troco Devolvido pelos Vendedores")
        conn = get_conn()
        query_v_fechamento = '''
            SELECT v.id, v.name, COALESCE(ev.troco_enviado, 0.0) as troco_enviado, COALESCE(ev.troco_devolvido, 0.0) as troco_devolvido
            FROM vendors v
            LEFT JOIN event_vendors ev ON v.id = ev.vendor_id AND ev.event_id = ?
        '''
        df_v_fechamento = pd.read_sql(query_v_fechamento, conn, params=(active_event_id,))
        
        df_v_fechamento_ativo = df_v_fechamento[df_v_fechamento['troco_enviado'] > 0].copy()
        
        if not df_v_fechamento_ativo.empty:
            edited_v_fechamento = st.data_editor(
                df_v_fechamento_ativo,
                column_config={
                    "id": None,
                    "name": st.column_config.TextColumn("Vendedor", disabled=True),
                    "troco_enviado": st.column_config.NumberColumn("Troco Enviado (R$)", disabled=True, format="R$ %.2f"),
                    "troco_devolvido": st.column_config.NumberColumn("Troco Devolvido (R$)", min_value=0.0, format="R$ %.2f")
                },
                hide_index=True,
                use_container_width=True
            )
            if st.button("Atualizar Troco Devolvido"):
                for _, row in edited_v_fechamento.iterrows():
                    td = row['troco_devolvido'] if pd.notna(row['troco_devolvido']) else 0.0
                    vid = int(row['id'])
                    conn.execute("UPDATE event_vendors SET troco_devolvido=? WHERE event_id=? AND vendor_id=?", (td, active_event_id, vid))
                conn.commit()
                log_action(active_event_id, "Atualizou os valores de troco devolvido pelos vendedores no fechamento.")
                st.success("Troco devolvido atualizado!")
                st.rerun()
        else:
            st.info("Nenhum vendedor recebeu troco neste evento.")

    st.divider()
    
    df_rounds_f = pd.read_sql('SELECT * FROM rounds WHERE event_id=?', conn, params=(active_event_id,))
    
    if not df_rounds_f.empty:
        r_ids = df_rounds_f['id'].tolist()
        placeholders = ','.join('?' for _ in r_ids)
        df_vr_f = pd.read_sql(f'SELECT * FROM vendor_rounds WHERE round_id IN ({placeholders})', conn, params=r_ids)
    else:
        df_vr_f = pd.DataFrame()
        
    df_s_f = pd.read_sql('SELECT * FROM sangrias WHERE event_id=?', conn, params=(active_event_id,))
    
    caixa_inicial = get_setting(active_event_id, 'caixa_inicial', 0.0)
    dinheiro_caixa_final = get_setting(active_event_id, 'dinheiro_fechamento', 0.0)
    
    receita_total_teorica = 0.0
    total_cartelas_evento = 0
    
    if not df_rounds_f.empty and not df_vr_f.empty:
        for _, r in df_rounds_f.iterrows():
            r_id = r['id']
            r_price = float(r['valor_cartela'])
            df_vr_round = df_vr_f[df_vr_f['round_id'] == r_id]
            
            if not df_vr_round.empty:
                v = df_vr_round['cartelas_recebidas'] + df_vr_round['cartelas_adicionais'] - df_vr_round['cartelas_devolvidas']
                v_sum = v.sum()
                total_cartelas_evento += v_sum
                receita_total_teorica += v_sum * r_price

    total_sangrias = df_s_f['valor'].sum() if not df_s_f.empty else 0.0
    SD = total_sangrias + dinheiro_caixa_final
    
    TP = df_vr_f['val_pix'].sum() if not df_vr_f.empty else 0.0
    TS = df_vr_f['val_santa_ficha'].sum() if not df_vr_f.empty else 0.0
    TD = df_vr_f['val_debito'].sum() if not df_vr_f.empty else 0.0
    
    quebra = receita_total_teorica + caixa_inicial - SD - TP - TS - TD
    
    VC = SD + TP + TS + TD
    RL = VC - caixa_inicial
    
    conn.close()
    
    st.subheader("Resumo dos Indicadores Finais do Evento")
    
    rc1, rc2, rc3, rc4 = st.columns(4)
    rc1.metric("Receita Total Bruta (Teórica)", f"R$ {receita_total_teorica:.2f}")
    rc2.metric("Receita Líquida", f"R$ {RL:.2f}")
    
    if quebra != 0:
        if quebra > 0:
            rc3.metric("Quebra de Caixa", f"R$ {quebra:.2f} (Falta)", delta=f"-R$ {quebra:.2f}", delta_color="inverse")
        else:
            rc3.metric("Quebra de Caixa", f"R$ {abs(quebra):.2f} (Sobra)", delta=f"+R$ {abs(quebra):.2f}", delta_color="normal")
    else:
        rc3.metric("Quebra de Caixa", "R$ 0.00 (Perfeito)")
        
    rc4.metric("Total de Cartelas Vendidas", int(total_cartelas_evento))
    
    st.write("### Detalhamento por Forma de Pagamento")
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.metric("Total de Sangrias", f"R$ {total_sangrias:.2f}")
    mc2.metric("Dinheiro Final em Caixa", f"R$ {dinheiro_caixa_final:.2f}")
    mc3.metric("Total Pix", f"R$ {TP:.2f}")
    mc4.metric("Total Santa Ficha", f"R$ {TS:.2f}")
    mc5.metric("Total Débito", f"R$ {TD:.2f}")

    with st.expander("Ver Fórmulas de Fechamento"):
        st.markdown(f'''
        **Caixa Inicial (CI):** R$ {caixa_inicial:.2f}
        **Receita Total (RT):** R$ {receita_total_teorica:.2f}
        **Total de Sangria + Caixa Final (SD):** R$ {SD:.2f} (R$ {total_sangrias:.2f} + R$ {dinheiro_caixa_final:.2f})
        **Total PIX (TP):** R$ {TP:.2f}
        **Total Santa Ficha (TS):** R$ {TS:.2f}
        **Total Débito (TD):** R$ {TD:.2f}
        
        **Quebra = RT + CI - SD - TP - TS - TD**
        Quebra = {receita_total_teorica:.2f} + {caixa_inicial:.2f} - {SD:.2f} - {TP:.2f} - {TS:.2f} - {TD:.2f} = **R$ {quebra:.2f}**
        
        **Valor Consolidado (VC) = SD + TP + TS + TD**
        VC = {SD:.2f} + {TP:.2f} + {TS:.2f} + {TD:.2f} = **R$ {VC:.2f}**
        
        **Receita Líquida (RL) = VC - CI**
        RL = {VC:.2f} - {caixa_inicial:.2f} = **R$ {RL:.2f}**
        ''')

with tab5:
    st.header("Logs de Auditoria do Evento")
    st.write("Acompanhe o histórico de ações e edições importantes realizadas neste evento.")
    
    conn = get_conn()
    try:
        df_logs = pd.read_sql('SELECT timestamp, username, action FROM audit_logs WHERE event_id = ? ORDER BY timestamp DESC', conn, params=(active_event_id,))
    except Exception:
        df_logs = pd.read_sql('SELECT timestamp, action FROM audit_logs WHERE event_id = ? ORDER BY timestamp DESC', conn, params=(active_event_id,))
    conn.close()
    
    if not df_logs.empty:
        df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp']).dt.strftime('%d/%m/%Y %H:%M:%S')
        
        col_config = {
            "timestamp": "Data / Hora",
            "action": st.column_config.TextColumn("Descrição da Ação")
        }
        if 'username' in df_logs.columns:
            col_config["username"] = "Usuário"
            
        st.dataframe(
            df_logs,
            column_config=col_config,
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Nenhuma atividade registrada para este evento ainda.")

