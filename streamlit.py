import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================
# 1. PAGE SETUP
# ==========================================
st.set_page_config(
    page_title="Logistics Control Tower", 
    page_icon="🚁", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for clean look
st.markdown("""
<style>
    /* 1. Main Container Padding */
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    
    /* 2. Headers */
    h3 {border-bottom: 2px solid #f0f2f6; padding-bottom: 10px;}
    
    /* 3. Metric Cards Styling */
    div.stMetric {
        background-color: #f8f9fa; 
        padding: 10px; 
        border-radius: 5px; 
        border-left: 5px solid #FF4B4B;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }

    /* 4. FORCE TEXT COLOR TO BLACK (Fixes the White-on-White issue) */
    div.stMetric > div { color: black !important; }
    [data-testid="stMetricValue"] { color: #1f1f1f !important; }
    [data-testid="stMetricLabel"] { color: #555555 !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADING ENGINE (Robust)
# ==========================================
@st.cache_data
def load_data():
    # 1. Try Local Path (Your specific path)
    local_path_excel = r"C:\Users\ESHWAR -NIT\Downloads\Task sheet - control tower.xlsx"
    local_path_csv = r"C:\Users\ESHWAR -NIT\Downloads\Task sheet - control tower - Raw data.csv"
    
    df = None
    
    # Try loading from local paths automatically
    try:
        df = pd.read_excel(local_path_excel)
    except:
        try:
            df = pd.read_csv(local_path_csv)
        except:
            pass # If both fail, we wait for upload

    # 2. If local fail, ask for Upload
    if df is None:
        uploaded_file = st.file_uploader("📂 Upload Data (CSV or Excel)", type=["csv", "xlsx"])
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
            except Exception as e:
                st.error(f"Error loading file: {e}")
                return pd.DataFrame()
        else:
            return pd.DataFrame()

    # 3. Data Cleaning & Type Conversion
    date_cols = ['Order Created At', 'Shipment picked up At', 'Out For Delivery At', 'Delivered At']
    
    # Ensure columns exist before converting
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    if 'Order Created At' in df.columns:
        df['Date'] = df['Order Created At'].dt.date
    
    return df

df = load_data()

# Show landing screen if no data
if df.empty:
    st.info("👋 Welcome! Please upload your 'Task sheet' file to start the Control Tower.")
    st.stop()

# ==========================================
# 3. LOGIC & METRICS
# ==========================================
current_time = pd.Timestamp('2026-01-08 09:00:00')

# Define Failure Flags
df['is_pickup_fail'] = (df['Current Shipment Status'] == 'PICKUP_PENDING') & \
                       ((current_time - df['Order Created At']).dt.total_seconds() / 3600 > 24)

active_status = ['IN_TRANSIT', 'PICKED_UP']
df['is_transit_fail'] = (df['Current Shipment Status'].isin(active_status)) & \
                        ((current_time - df['Shipment picked up At']).dt.total_seconds() / 3600 > df['Promised SLA (Hours)'])

df['is_delivery_fail'] = (df['Current Shipment Status'] == 'FAILED_DELIVERY')

# Risk Flag for Financials
df['is_risk'] = df['is_pickup_fail'] | df['is_transit_fail'] | df['is_delivery_fail']

# ==========================================
# 4. DASHBOARD HEADER
# ==========================================
c1, c2 = st.columns([3, 1])
with c1:
    st.title("🚁 Logistics Control Tower")
    st.markdown(f"**Status:** 🔴 Critical Alerts | **As of:** {current_time.strftime('%d %b %Y, %H:%M AM')}")
with c2:
    st.markdown("") 

# KPI Row
total_orders = len(df)
k1, k2, k3, k4 = st.columns(4)
k1.metric("📦 Total Shipments", f"{total_orders:,}")
k2.metric("🚫 Pickup Fails", f"{df['is_pickup_fail'].sum():,}", delta="First Mile Breach", delta_color="inverse")
k3.metric("🐢 Transit Fails", f"{df['is_transit_fail'].sum():,}", delta="SLA Breach", delta_color="inverse")
k4.metric("❌ Delivery Fails", f"{df['is_delivery_fail'].sum():,}", delta="Last Mile Failed", delta_color="inverse")
st.markdown("---")

# ==========================================
# 5. MAIN TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📦 Pickup Failures", 
    "🐢 Transit Failures", 
    "❌ Delivery Failures", 
    "💰 Financial Risk"
])

def plot_failure_view(df_full, fail_col, color_theme, title_prefix):
    """Helper to generate standard view for each failure type"""
    
    # 1. Prepare Data
    city_stats = df_full.groupby('City').agg(
        Total=('AWB', 'count'),
        Failures=(fail_col, 'sum')
    ).reset_index()
    
    city_stats['Fail_Rate'] = (city_stats['Failures'] / city_stats['Total'] * 100).round(1)
    city_stats = city_stats[city_stats['Failures'] > 0].sort_values('Failures', ascending=False)
    
    if city_stats.empty:
        st.success(f"✅ No {title_prefix} Failures detected!")
        return

    c_left, c_right = st.columns(2)
    
    # Bar Chart: Volume
    with c_left:
        st.subheader(f"⚠️ {title_prefix} Volume (Count)")
        fig_vol = px.bar(city_stats, x='City', y='Failures', text='Failures', 
                         color='Failures', color_continuous_scale=color_theme,
                         title="Absolute Number of Failures")
        st.plotly_chart(fig_vol, use_container_width=True)
        
    # Bar Chart: Percentage
    with c_right:
        st.subheader(f"📉 {title_prefix} Efficiency (%)")
        city_stats_pct = city_stats.sort_values('Fail_Rate', ascending=False)
        fig_pct = px.bar(city_stats_pct, x='City', y='Fail_Rate', text='Fail_Rate', 
                         color='Fail_Rate', color_continuous_scale=color_theme,
                         title="Failure Rate % (The True Bottleneck)")
        fig_pct.update_traces(texttemplate='%{text}%')
        st.plotly_chart(fig_pct, use_container_width=True)

    # Treemap: Drilldown
    st.subheader(f"🚚 Carrier Performance Matrix ({title_prefix})")
    df_fail_only = df_full[df_full[fail_col]]
    tree_data = df_fail_only.groupby(['City', 'Courier Partner']).size().reset_index(name='Count')
    
    fig_tree = px.treemap(tree_data, path=['City', 'Courier Partner'], values='Count',
                          color='Count', color_continuous_scale=color_theme,
                          title=f"Who is failing in which City?")
    st.plotly_chart(fig_tree, use_container_width=True)

# --- Render Tabs ---
with tab1: plot_failure_view(df, 'is_pickup_fail', 'Reds', "Pickup")
with tab2: plot_failure_view(df, 'is_transit_fail', 'Oranges', "Transit")
with tab3: plot_failure_view(df, 'is_delivery_fail', 'RdPu', "Delivery")

# --- Tab 4: Financials ---
with tab4:
    st.subheader("💰 Value at Risk Analysis")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("**💸 Revenue Stuck in Failed Shipments**")
        # Sum order value for all failing shipments
        risk_df = df[df['is_risk']].groupby('City')['Order Value (INR)'].sum().reset_index()
        risk_df = risk_df.sort_values('Order Value (INR)', ascending=False)
        
        fig_pie = px.pie(risk_df, values='Order Value (INR)', names='City', 
                         title="Total Value (INR) of Stuck Orders by City", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_b:
        st.markdown("**💳 COD vs Prepaid Failure Rates**")
        pay_stats = df.groupby('Payment Type').agg(
            Total=('AWB', 'count'),
            Failures=('is_risk', 'sum')
        ).reset_index()
        pay_stats['Rate'] = (pay_stats['Failures'] / pay_stats['Total'] * 100).round(1)
        
        fig_pay = px.bar(pay_stats, x='Payment Type', y='Rate', color='Payment Type', text='Rate',
                         title="Failure % by Payment Mode", color_discrete_map={'COD': '#EF553B', 'Prepaid': '#636EFA'})
        fig_pay.update_traces(texttemplate='%{text}%')
        st.plotly_chart(fig_pay, use_container_width=True)

    # Trend Line
    st.markdown("---")
    st.subheader("📈 Daily Failure Trend")
    daily_trend = df.groupby('Date').agg(
        Pickup_Fails=('is_pickup_fail', 'sum'),
        Transit_Fails=('is_transit_fail', 'sum'),
        Delivery_Fails=('is_delivery_fail', 'sum')
    ).reset_index()
    
    fig_trend = px.line(daily_trend, x='Date', y=['Pickup_Fails', 'Transit_Fails', 'Delivery_Fails'],
                        markers=True, title="Are we improving over time?")
    st.plotly_chart(fig_trend, use_container_width=True)
