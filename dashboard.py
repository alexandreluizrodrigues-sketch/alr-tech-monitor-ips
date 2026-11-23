from datetime import datetime, date, timedelta, time
import ipaddress
import re
import pandas as pd
import plotly.express as px
import streamlit as st
from storage import connect, setup

st.set_page_config(page_title='ALR TECH | Monitor de IPs', page_icon='📡', layout='wide')
setup()
st.markdown('''<style>
.block-container {padding-top: 1.5rem;}
h1 {letter-spacing:-.03em}
[data-testid="stMetric"] {background:rgba(128,128,128,.07);padding:16px;border-radius:12px}
</style>''', unsafe_allow_html=True)

st.title('📡 ALR TECH | Monitor de IPs')
st.caption('Disponibilidade e latência por ICMP (ping). Coleta em segundo plano; atualize a página para ver novos registros.')

with st.sidebar:
    st.header('Gerenciar IPs')
    with st.form('add_target', clear_on_submit=True):
        address = st.text_input('Endereço IP ou hostname', placeholder='192.168.0.1')
        label = st.text_input('Identificação', placeholder='Firewall / Servidor / Impressora')
        submitted = st.form_submit_button('Adicionar IP', use_container_width=True)
        if submitted:
            value = address.strip()
            valid = False
            try:
                ipaddress.ip_address(value)
                valid = True
            except ValueError:
                valid = bool(re.fullmatch(r'(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', value))
            if not valid:
                st.error('Informe um IP ou hostname válido.')
            else:
                try:
                    with connect() as db:
                        db.execute('INSERT INTO targets(address,label) VALUES (?,?)', (value, label.strip() or value))
                    st.success('IP adicionado.')
                except Exception as exc:
                    st.error(f'Não foi possível adicionar: {exc}')
    with connect() as db:
        all_targets = pd.read_sql_query('SELECT id, address, label, enabled FROM targets ORDER BY label', db)
    if not all_targets.empty:
        chosen = st.selectbox('IP para ativar/pausar/excluir', all_targets['id'].tolist(),
                              format_func=lambda x: next(f'{row.label} ({row.address})' for row in all_targets.itertuples() if row.id == x))
        row = all_targets.loc[all_targets.id == chosen].iloc[0]
        c1, c2 = st.columns(2)
        if c1.button('Pausar' if row.enabled else 'Ativar', use_container_width=True):
            with connect() as db:
                db.execute('UPDATE targets SET enabled = ? WHERE id = ?', (0 if row.enabled else 1, chosen))
            st.rerun()
        if c2.button('Excluir', use_container_width=True, help='Exclui IP e histórico'):
            with connect() as db:
                db.execute('DELETE FROM checks WHERE target_id = ?', (chosen,))
                db.execute('DELETE FROM targets WHERE id = ?', (chosen,))
            st.rerun()
    st.divider()
    if st.button('🔄 Atualizar dashboard', use_container_width=True):
        st.rerun()
    st.caption('O arquivo collector.py precisa permanecer em execução para coletar dados.')

if all_targets.empty:
    st.info('Cadastre seu primeiro IP na barra lateral. Inicie também o coletor pelo arquivo iniciar_windows.bat.')
    st.stop()

st.subheader('Filtros')
c1, c2, c3 = st.columns([2,2,2])
with c1:
    interval = st.segmented_control('Agrupar por intervalo', options=['1 min', '2 min', '5 min', '30 min'], default='5 min')
with c2:
    mode = st.radio('Período', ['Hoje', 'Ontem', 'Últimos 7 dias', 'Personalizado'], horizontal=True)
with c3:
    options = all_targets['id'].tolist()
    selected = st.multiselect('IPs', options, default=options,
                              format_func=lambda x: next(f'{row.label} ({row.address})' for row in all_targets.itertuples() if row.id == x))

now = datetime.now().astimezone()
if mode == 'Hoje':
    start_day = end_day = now.date()
elif mode == 'Ontem':
    start_day = end_day = now.date() - timedelta(days=1)
elif mode == 'Últimos 7 dias':
    start_day, end_day = now.date() - timedelta(days=6), now.date()
else:
    period = st.date_input('Selecione os dias (início e fim)', value=(now.date() - timedelta(days=6), now.date()), format='DD/MM/YYYY')
    if not isinstance(period, (tuple, list)) or len(period) != 2:
        st.info('Escolha as duas datas.')
        st.stop()
    start_day, end_day = period

if not selected:
    st.warning('Selecione ao menos um IP.')
    st.stop()
if start_day > end_day:
    st.error('A data inicial deve ser anterior à data final.')
    st.stop()

# Datas no mesmo fuso local da máquina coletora, conforme os timestamps armazenados.
start_stamp = datetime.combine(start_day, time.min, tzinfo=now.tzinfo).isoformat(timespec='seconds')
end_stamp = datetime.combine(end_day + timedelta(days=1), time.min, tzinfo=now.tzinfo).isoformat(timespec='seconds')
placeholders = ','.join('?' for _ in selected)
with connect() as db:
    df = pd.read_sql_query(f'''SELECT c.target_id, t.label, t.address, c.checked_at, c.online, c.latency_ms
        FROM checks c JOIN targets t ON c.target_id = t.id
        WHERE c.target_id IN ({placeholders}) AND c.checked_at >= ? AND c.checked_at < ?
        ORDER BY c.checked_at''', db, params=(*selected, start_stamp, end_stamp))

if df.empty:
    st.info('Ainda não existem verificações para os IPs e dias selecionados. Confirme que o coletor está aberto.')
    st.stop()

df['checked_at'] = pd.to_datetime(df['checked_at'], utc=True).dt.tz_convert(now.tzinfo)
df['equipamento'] = df['label'] + ' (' + df['address'] + ')'
up = df['online'].mean() * 100
online_count = df.sort_values('checked_at').groupby('target_id').tail(1)['online'].sum()
m1,m2,m3,m4 = st.columns(4)
m1.metric('IPs selecionados', len(selected))
m2.metric('Último status: online', f'{int(online_count)}/{df.target_id.nunique()}')
m3.metric('Disponibilidade nas amostras', f'{up:.1f}%')
m4.metric('Latência média (online)', f'{df.latency_ms.mean():.1f} ms' if df.latency_ms.notna().any() else '—')

freq = {'1 min':'1min','2 min':'2min','5 min':'5min','30 min':'30min'}[interval]
agg = (df.set_index('checked_at').groupby('equipamento').resample(freq)
       .agg(disponibilidade=('online','mean'), latencia=('latency_ms','mean'), amostras=('online','size'))
       .reset_index())
agg['disponibilidade'] *= 100

st.subheader('Disponibilidade por intervalo')
fig = px.line(agg, x='checked_at', y='disponibilidade', color='equipamento', markers=False,
              labels={'checked_at':'Data / hora','disponibilidade':'Disponibilidade (%)','equipamento':'IP'},
              range_y=[-3,103])
fig.update_layout(legend_title_text='', height=345, hovermode='x unified', margin=dict(l=10,r=10,t=10,b=10))
st.plotly_chart(fig, use_container_width=True)

st.subheader('Latência média por intervalo')
lat = agg.dropna(subset=['latencia'])
fig2 = px.line(lat, x='checked_at', y='latencia', color='equipamento',
               labels={'checked_at':'Data / hora','latencia':'Latência (ms)','equipamento':'IP'})
fig2.update_layout(legend_title_text='', height=345, hovermode='x unified', margin=dict(l=10,r=10,t=10,b=10))
st.plotly_chart(fig2, use_container_width=True)

st.subheader('Resumo por IP')
summary = (df.sort_values('checked_at').groupby(['target_id','equipamento'], as_index=False)
           .agg(verificacoes=('online','size'), disponibilidade=('online','mean'),
                latencia_media_ms=('latency_ms','mean'), ultima_verificacao=('checked_at','max'), ultimo_status=('online','last')))
summary['disponibilidade'] = (summary['disponibilidade'] * 100).round(2)
summary['latencia_media_ms'] = summary['latencia_media_ms'].round(2)
summary['ultimo_status'] = summary['ultimo_status'].map({1:'Online',0:'Offline'})
summary = summary.drop(columns=['target_id']).rename(columns={
    'equipamento':'Equipamento', 'verificacoes':'Amostras', 'disponibilidade':'Disponibilidade (%)',
    'latencia_media_ms':'Latência média (ms)', 'ultima_verificacao':'Última verificação', 'ultimo_status':'Status'})
st.dataframe(summary, use_container_width=True, hide_index=True)

csv = df[['checked_at','label','address','online','latency_ms']].to_csv(index=False).encode('utf-8-sig')
st.download_button('⬇️ Exportar verificações (CSV)', data=csv, file_name=f'monitor_ips_{start_day}_{end_day}.csv', mime='text/csv')
st.caption('Disponibilidade = percentual de pings respondidos. Isto não mede consumo de banda, portas, conexões nem tráfego entre IPs.')
