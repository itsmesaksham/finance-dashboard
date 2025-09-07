import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import glob
import os
from datetime import datetime, timedelta

def safe_format_date(date_series, format_str="%d-%m-%Y"):
    """Safely format dates handling various input formats"""
    try:
        return pd.to_datetime(date_series, dayfirst=True, errors='coerce').dt.strftime(format_str)
    except:
        return date_series.astype(str)

from db import init_db, insert_transactions, fetch_all, get_sweep_balance_adjustments, add_sweep_balance_adjustment, get_inter_person_transfers, get_account_balances
from parser import parse_csv, validate_data_integrity

# Initialize DB
init_db()

# Page configuration
st.set_page_config(
    page_title="Family Finance Dashboard", 
    page_icon="💰", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("💰 Family Finance Dashboard")
st.markdown("*Your comprehensive personal finance management solution*")
st.markdown("---")

# Sidebar for controls
with st.sidebar:
    st.header("📊 Dashboard Controls")
    
    # Data loading section
    st.subheader("📥 Data Management")
    if st.button("🔄 Load CSV Data", type="primary"):
        files = glob.glob("data/*.csv")
        if files:
            progress_bar = st.progress(0)
            status_text = st.empty()
            loaded_count = 0
            
            for i, f in enumerate(files):
                status_text.text(f"Processing {os.path.basename(f)}...")
                records = parse_csv(f)
                if records:
                    insert_transactions(records)
                    loaded_count += 1
                progress_bar.progress((i + 1) / len(files))
            
            status_text.empty()
            progress_bar.empty()
            st.success(f"✅ {loaded_count}/{len(files)} files loaded successfully!")
        else:
            st.warning("No CSV files found in the data/ directory")
    
    # Sweep balance adjustments
    st.subheader("⚖️ Sweep Balance Adjustments")
    with st.expander("Add Adjustment"):
        adj_date = st.date_input("Date")
        adj_owner = st.text_input("Owner")
        adj_amount = st.number_input("Amount", value=0.0, help="Positive for additions, negative for deductions")
        adj_description = st.text_input("Description", value="Sweep balance adjustment")
        if st.button("Add Adjustment"):
            add_sweep_balance_adjustment(adj_date, adj_owner, adj_amount, adj_description)
            st.success("Adjustment added!")
            st.experimental_rerun()

# Create tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🔄 Transfers", "💼 Accounts", "📋 Data Quality"])

# Fetch all transactions
df = fetch_all()

if df is not None and not df.empty:
    # Convert date column with better error handling
    try:
        df["date"] = pd.to_datetime(df["date"], format='%d-%m-%Y', dayfirst=True, errors='coerce')
    except:
        try:
            df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors='coerce')
        except:
            st.error("Error parsing dates. Please check your CSV file format.")
            st.stop()
    
    df = df.dropna(subset=['date'])  # Remove rows with invalid dates
    
    # Apply sweep balance adjustments
    sweep_adjustments = get_sweep_balance_adjustments()
    if sweep_adjustments is not None and not sweep_adjustments.empty:
        for _, adj in sweep_adjustments.iterrows():
            mask = (df['date'].dt.date >= pd.to_datetime(adj['date']).date()) & (df['owner'] == adj['owner'])
            df.loc[mask, 'balance'] += adj['amount']
    
    # Sidebar filters (common for all tabs)
    with st.sidebar:
        st.subheader("🔍 Filters")
        
        # Account selection with checkboxes
        st.write("**Select Bank Accounts:**")
        account_combinations = df[["owner", "bank"]].drop_duplicates()
        account_options = [f"{row['owner']} - {row['bank']}" for _, row in account_combinations.iterrows()]
        
        selected_accounts = []
        for account in account_options:
            if st.checkbox(account, value=True, key=f"account_{account}"):
                selected_accounts.append(account)
        
        # Date range filter
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()
        
        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
    
    # Filter data based on selections
    if selected_accounts:
        selected_owners = [acc.split(" - ")[0] for acc in selected_accounts]
        selected_banks = [acc.split(" - ")[1] for acc in selected_accounts]
        
        account_filter = pd.Series(False, index=df.index)
        for owner, bank in zip(selected_owners, selected_banks):
            account_filter |= (df["owner"] == owner) & (df["bank"] == bank)
        
        filtered = df[account_filter]
    else:
        filtered = df.copy()
    
    # Apply date filter
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered = filtered[
            (filtered["date"].dt.date >= start_date) & 
            (filtered["date"].dt.date <= end_date)
        ]

    # Tab 1: Main Dashboard
    with tab1:
        # Key metrics
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        
        with col1:
            if not filtered.empty:
                current_balance = filtered.groupby(['owner', 'bank'])['balance'].last().sum()
                st.metric(
                    label="💰 Total Balance",
                    value=f"₹{current_balance:,.2f}"
                )
        
        with col2:
            total_credit = filtered["credit"].sum()
            st.metric(
                label="📈 Total Credits",
                value=f"₹{total_credit:,.2f}"
            )
        
        with col3:
            total_debit = filtered["debit"].sum()
            st.metric(
                label="📉 Total Debits",
                value=f"₹{total_debit:,.2f}"
            )
        
        with col4:
            net_flow = total_credit - total_debit
            st.metric(
                label="🔄 Net Flow",
                value=f"₹{net_flow:,.2f}",
                delta=f"₹{net_flow:,.2f}"
            )
        
        st.markdown("---")
        
        # Chart type selector
        chart_col1, chart_col2 = st.columns([3, 1])
        
        with chart_col2:
            chart_type = st.selectbox(
                "Chart Type",
                ["Line Chart", "Bar Chart", "Area Chart"],
                key="main_chart_type"
            )
        
        with chart_col1:
            st.subheader("📊 Interactive Financial Trends")
        
        if not filtered.empty:
            # Prepare daily summary data
            daily_summary = filtered.groupby(filtered["date"].dt.date).agg({
                "credit": "sum",
                "debit": "sum",
                "balance": "last",
                "description": "count"
            }).reset_index()
            daily_summary.columns = ["date", "total_credit", "total_debit", "end_balance", "transaction_count"]
            daily_summary["net_change"] = daily_summary["total_credit"] - daily_summary["total_debit"]
            
            # Create interactive chart based on selection
            if chart_type == "Line Chart":
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=daily_summary["date"],
                    y=daily_summary["end_balance"],
                    mode='lines+markers',
                    name='Balance',
                    line=dict(color='#1f77b4', width=3),
                    marker=dict(size=6),
                    hovertemplate='<b>Date:</b> %{x}<br>' +
                                 '<b>Balance:</b> ₹%{y:,.2f}<br>' +
                                 '<b>Transactions:</b> %{customdata}<br>' +
                                 '<extra></extra>',
                    customdata=daily_summary["transaction_count"]
                ))
                
                fig.update_layout(
                    title="Daily Balance Trend",
                    xaxis_title="Date",
                    yaxis_title="Balance (₹)",
                    hovermode='x unified',
                    height=500
                )
                
            elif chart_type == "Bar Chart":
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=daily_summary["date"],
                    y=daily_summary["total_credit"],
                    name='Credits',
                    marker_color='#2E8B57',
                    hovertemplate='<b>Date:</b> %{x}<br>' +
                                 '<b>Credits:</b> ₹%{y:,.2f}<br>' +
                                 '<extra></extra>'
                ))
                
                fig.add_trace(go.Bar(
                    x=daily_summary["date"],
                    y=-daily_summary["total_debit"],
                    name='Debits',
                    marker_color='#DC143C',
                    hovertemplate='<b>Date:</b> %{x}<br>' +
                                 '<b>Debits:</b> ₹%{y:,.2f}<br>' +
                                 '<extra></extra>'
                ))
                
                fig.update_layout(
                    title="Daily Credits vs Debits",
                    xaxis_title="Date",
                    yaxis_title="Amount (₹)",
                    barmode='relative',
                    height=500
                )
                
            else:  # Area Chart
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=daily_summary["date"],
                    y=daily_summary["end_balance"],
                    mode='lines',
                    name='Balance',
                    fill='tonexty',
                    line=dict(color='#1f77b4'),
                    hovertemplate='<b>Date:</b> %{x}<br>' +
                                 '<b>Balance:</b> ₹%{y:,.2f}<br>' +
                                 '<extra></extra>'
                ))
                
                fig.update_layout(
                    title="Balance Area Chart",
                    xaxis_title="Date",
                    yaxis_title="Balance (₹)",
                    height=500
                )
            
            st.plotly_chart(fig, width='stretch')
            
            # Transaction details on date selection
            st.subheader("🔍 Daily Transaction Details")
            
            # Date picker for detailed view
            selected_date = st.date_input(
                "Select a date to view detailed transactions:",
                value=daily_summary["date"].iloc[-1] if not daily_summary.empty else datetime.now().date(),
                key="main_date_picker"
            )
            
            # Show transactions for selected date
            day_transactions = filtered[filtered["date"].dt.date == selected_date]
            
            if not day_transactions.empty:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Transactions on {selected_date}** ({len(day_transactions)} transactions)")
                    
                    # Format the transactions for better display
                    display_df = day_transactions[["date", "owner", "bank", "description", "debit", "credit", "balance"]].copy()
                    display_df["date"] = display_df["date"].dt.strftime("%H:%M")
                    display_df["debit"] = display_df["debit"].apply(lambda x: f"₹{x:,.2f}" if x > 0 else "")
                    display_df["credit"] = display_df["credit"].apply(lambda x: f"₹{x:,.2f}" if x > 0 else "")
                    display_df["balance"] = display_df["balance"].apply(lambda x: f"₹{x:,.2f}")
                    
                    st.dataframe(
                        display_df,
                        width='stretch',
                        hide_index=True
                    )
                
                with col2:
                    day_summary = day_transactions.agg({
                        "credit": "sum",
                        "debit": "sum"
                    })
                    
                    st.metric("Credits", f"₹{day_summary['credit']:,.2f}")
                    st.metric("Debits", f"₹{day_summary['debit']:,.2f}")
                    st.metric("Net Change", f"₹{day_summary['credit'] - day_summary['debit']:,.2f}")
            else:
                st.info(f"No transactions found for {selected_date}")

    # Tab 2: Inter-person Transfers
    with tab2:
        st.subheader("🔄 Inter-Person Transfer Analysis")
        
        transfers = get_inter_person_transfers()
        
        if transfers is not None and not transfers.empty:
            st.write(f"**Found {len(transfers)} potential inter-person transfers**")
            
            # Format transfers for display
            transfers_display = transfers.copy()
            transfers_display["amount"] = transfers_display["amount"].apply(lambda x: f"₹{x:,.2f}")
            transfers_display["date"] = safe_format_date(transfers_display["date"])
            
            st.dataframe(transfers_display, width='stretch', hide_index=True)
            
            # Transfer flow visualization
            if len(transfers) > 0:
                st.subheader("Transfer Flow Network")
                
                # Create a simple transfer summary
                transfer_summary = transfers.groupby(['from_owner', 'to_owner'])['amount'].sum().reset_index()
                
                fig = go.Figure(data=[go.Sankey(
                    node=dict(
                        pad=15,
                        thickness=20,
                        line=dict(color="black", width=0.5),
                        label=list(set(transfers['from_owner'].tolist() + transfers['to_owner'].tolist())),
                        color="blue"
                    ),
                    link=dict(
                        source=[list(set(transfers['from_owner'].tolist() + transfers['to_owner'].tolist())).index(x) 
                               for x in transfers['from_owner']],
                        target=[list(set(transfers['from_owner'].tolist() + transfers['to_owner'].tolist())).index(x) 
                               for x in transfers['to_owner']],
                        value=transfers['amount']
                    )
                )])
                
                fig.update_layout(title_text="Money Flow Between Family Members", font_size=10)
                st.plotly_chart(fig, width='stretch')
        else:
            st.info("No inter-person transfers detected. This feature looks for matching debit/credit amounts on the same date between different accounts.")

    # Tab 3: Account Summary
    with tab3:
        st.subheader("💼 Account-wise Analysis")
        
        # Current account balances
        account_balances = get_account_balances()
        
        if account_balances is not None and not account_balances.empty:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.write("**Current Account Balances**")
                balance_display = account_balances.copy()
                balance_display["balance"] = balance_display["balance"].apply(lambda x: f"₹{x:,.2f}")
                balance_display["date"] = safe_format_date(balance_display["date"])
                st.dataframe(balance_display, width='stretch', hide_index=True)
            
            with col2:
                # Account balance pie chart
                fig = px.pie(
                    account_balances, 
                    values='balance', 
                    names=[f"{row['owner']} - {row['bank']}" for _, row in account_balances.iterrows()],
                    title="Balance Distribution"
                )
                st.plotly_chart(fig, width='stretch')
        
        # Account-wise transaction summary
        if not filtered.empty:
            st.write("**Transaction Summary by Account**")
            account_summary = filtered.groupby(["owner", "bank"]).agg({
                "credit": "sum",
                "debit": "sum",
                "balance": "last",
                "date": ["min", "max"],
                "description": "count"
            }).round(2)
            
            # Flatten column names
            account_summary.columns = ["Total Credits", "Total Debits", "Latest Balance", "First Transaction", "Last Transaction", "Transaction Count"]
            account_summary["Net Flow"] = account_summary["Total Credits"] - account_summary["Total Debits"]
            
            # Format for display
            for col in ["Total Credits", "Total Debits", "Latest Balance", "Net Flow"]:
                account_summary[col] = account_summary[col].apply(lambda x: f"₹{x:,.2f}")
            
            account_summary["First Transaction"] = safe_format_date(account_summary["First Transaction"])
            account_summary["Last Transaction"] = safe_format_date(account_summary["Last Transaction"])
            
                        st.dataframe(account_summary, width='stretch')

    # Tab 4: Data Quality
    with tab4:
        st.subheader("📋 Data Quality & Integrity")
        
        # Data validation
        issues = validate_data_integrity(df)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.write("**Data Quality Report**")
            for issue in issues:
                if "good" in issue.lower():
                    st.success(f"✅ {issue}")
                else:
                    st.warning(f"⚠️ {issue}")
        
        with col2:
            st.write("**Database Statistics**")
            st.metric("Total Transactions", len(df))
            st.metric("Date Range", f"{df['date'].min().strftime('%d-%m-%Y')} to {df['date'].max().strftime('%d-%m-%Y')}")
            st.metric("Unique Accounts", len(df[['owner', 'bank']].drop_duplicates()))
        
        # Show sweep adjustments
        sweep_adjustments = get_sweep_balance_adjustments()
        if sweep_adjustments is not None and not sweep_adjustments.empty:
            st.write("**Active Sweep Balance Adjustments**")
            sweep_display = sweep_adjustments.copy()
            sweep_display["amount"] = sweep_display["amount"].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(sweep_display, width='stretch', hide_index=True)
        
        # Raw data view
        with st.expander("View Raw Transaction Data"):
            st.dataframe(df, width='stretch')

else:
    st.info("🚀 Welcome to your Finance Dashboard! Please load CSV files to get started.")
    st.markdown("""
    ### Getting Started:
    1. Place your bank statement CSV files in the `data/` folder
    2. Use the naming convention: `Owner_Bank.csv` (e.g., `Saksham_SBI.csv`)
    3. Click the '🔄 Load CSV Data' button in the sidebar
    4. Explore your financial data across different tabs!
    
    ### Supported Features:
    - 📊 Interactive charts with hover details
    - 🔄 Inter-person transfer detection
    - ⚖️ Sweep balance adjustments
    - 💼 Account-wise analysis
    - 📋 Data quality validation
    """)
