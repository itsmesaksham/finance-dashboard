import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import glob
import os
import sys
from datetime import datetime, timedelta

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def safe_format_date(date_series, format_str="%d-%m-%Y"):
    """Safely format dates handling various input formats"""
    try:
        return pd.to_datetime(date_series, dayfirst=True, errors='coerce').dt.strftime(format_str)
    except:
        return date_series.astype(str)

from src.database.db import init_db, insert_transactions, fetch_all, get_sweep_balance_adjustments, add_sweep_balance_adjustment, get_inter_person_transfers, get_account_balances, get_transfer_patterns, get_all_transfer_transactions, purge_all_data, get_transaction_count, check_duplicate_transactions, update_categories_for_existing_transactions, get_category_summary, get_monthly_category_trends, update_sweep_balance, get_latest_sweep_balance, get_sweep_balance_history
from src.utils.parser import parse_csv, validate_data_integrity
from src.utils.indian_formatting import format_indian_currency, format_indian_number

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
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Load CSV Data", type="primary"):
            files = glob.glob("data/*.csv")
            if files:
                # Check current transaction count
                current_count = get_transaction_count()
                if current_count > 0:
                    st.warning(f"⚠️ Database already contains {current_count} transactions. Loading new data may create duplicates.")
                    if not st.session_state.get('proceed_with_load', False):
                        if st.button("Proceed Anyway", key="proceed_load"):
                            st.session_state['proceed_with_load'] = True
                            st.rerun()
                        st.stop()
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                loaded_count = 0
                skipped_count = 0
                
                for i, f in enumerate(files):
                    status_text.text(f"Processing {os.path.basename(f)}...")
                    records = parse_csv(f)
                    if records:
                        # Check for duplicates
                        duplicates = check_duplicate_transactions(records)
                        if duplicates > 0:
                            status_text.text(f"Skipping {duplicates} duplicate records in {os.path.basename(f)}...")
                            skipped_count += duplicates
                        
                        insert_transactions(records)
                        loaded_count += 1
                    progress_bar.progress((i + 1) / len(files))
                
                status_text.empty()
                progress_bar.empty()
                
                if skipped_count > 0:
                    st.success(f"✅ {loaded_count}/{len(files)} files processed! {skipped_count} duplicate records were skipped.")
                else:
                    st.success(f"✅ {loaded_count}/{len(files)} files loaded successfully!")
                
                # Reset the proceed flag
                st.session_state['proceed_with_load'] = False
            else:
                st.warning("No CSV files found in the data/ directory")
    
    with col2:
        if st.button("🗑️ Purge Data", type="secondary", help="Delete all transaction data"):
            if st.session_state.get('confirm_purge', False):
                deleted_count = purge_all_data()
                st.success(f"✅ Purged {deleted_count} records from database!")
                st.session_state['confirm_purge'] = False
                st.rerun()
            else:
                st.session_state['confirm_purge'] = True
                st.warning("⚠️ Click again to confirm data purge")
                st.rerun()
    
    # Auto-categorization
    st.subheader("🏷️ Auto-Categorization")
    if st.button("🔄 Update Categories", help="Auto-categorize all transactions"):
        with st.spinner("Categorizing transactions..."):
            updated_count = update_categories_for_existing_transactions()
            st.success(f"✅ Updated categories for {updated_count} transactions!")
    
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🔄 Transfers", "💼 Accounts", "📈 Categories", "📋 Data Quality"])

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
                    value=format_indian_currency(current_balance)
                )
        
        with col2:
            total_credit = filtered["credit"].sum()
            st.metric(
                label="📈 Total Credits",
                value=format_indian_currency(total_credit)
            )
        
        with col3:
            total_debit = filtered["debit"].sum()
            st.metric(
                label="📉 Total Debits",
                value=format_indian_currency(total_debit)
            )
        
        with col4:
            net_flow = total_credit - total_debit
            st.metric(
                label="🔄 Net Flow",
                value=format_indian_currency(net_flow),
                delta=format_indian_currency(net_flow)
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
            
            # Add formatted columns for hover tooltips
            daily_summary["balance_formatted"] = daily_summary["end_balance"].apply(format_indian_currency)
            daily_summary["credit_formatted"] = daily_summary["total_credit"].apply(format_indian_currency)
            daily_summary["debit_formatted"] = daily_summary["total_debit"].apply(format_indian_currency)
            
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
                                 '<b>Balance:</b> %{customdata[0]}<br>' +
                                 '<b>Transactions:</b> %{customdata[1]}<br>' +
                                 '<extra></extra>',
                    customdata=list(zip(daily_summary["balance_formatted"], daily_summary["transaction_count"]))
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
                                 '<b>Credits:</b> %{customdata}<br>' +
                                 '<extra></extra>',
                    customdata=daily_summary["credit_formatted"]
                ))
                
                fig.add_trace(go.Bar(
                    x=daily_summary["date"],
                    y=-daily_summary["total_debit"],
                    name='Debits',
                    marker_color='#DC143C',
                    hovertemplate='<b>Date:</b> %{x}<br>' +
                                 '<b>Debits:</b> %{customdata}<br>' +
                                 '<extra></extra>',
                    customdata=daily_summary["debit_formatted"]
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
                                 '<b>Balance:</b> %{customdata}<br>' +
                                 '<extra></extra>',
                    customdata=daily_summary["balance_formatted"]
                ))
                
                fig.update_layout(
                    title="Balance Area Chart",
                    xaxis_title="Date",
                    yaxis_title="Balance (₹)",
                    height=500
                )
            
            st.plotly_chart(fig, width='stretch')
            
            # Transaction details on week selection
            st.subheader("🔍 Weekly Transaction Details")
            
            # Week picker for detailed view
            selected_date = st.date_input(
                "Select a date to view weekly transactions (week containing this date):",
                value=daily_summary["date"].iloc[-1] if not daily_summary.empty else datetime.now().date(),
                key="main_date_picker"
            )
            
            # Calculate week start (Monday) and end (Sunday) for selected date
            selected_datetime = datetime.combine(selected_date, datetime.min.time())
            week_start = selected_datetime - timedelta(days=selected_datetime.weekday())  # Monday
            week_end = week_start + timedelta(days=6)  # Sunday
            
            st.write(f"**Week: {week_start.strftime('%d %b %Y')} to {week_end.strftime('%d %b %Y')}**")
            
            # Show transactions for selected week
            week_transactions = filtered[
                (filtered["date"].dt.date >= week_start.date()) & 
                (filtered["date"].dt.date <= week_end.date())
            ]
            
            if not week_transactions.empty:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Transactions in selected week** ({len(week_transactions)} transactions)")
                    
                    # Format the transactions for better display
                    display_df = week_transactions[["date", "owner", "bank", "description", "debit", "credit", "balance"]].copy()
                    display_df["date"] = display_df["date"].dt.strftime("%d %b %Y")
                    display_df["debit"] = display_df["debit"].apply(lambda x: format_indian_currency(x) if x > 0 else "")
                    display_df["credit"] = display_df["credit"].apply(lambda x: format_indian_currency(x) if x > 0 else "")
                    display_df["balance"] = display_df["balance"].apply(lambda x: format_indian_currency(x))
                    
                    st.dataframe(
                        display_df,
                        width='stretch',
                        hide_index=True
                    )
                
                with col2:
                    week_summary = week_transactions.agg({
                        "credit": "sum",
                        "debit": "sum"
                    })
                    
                    # Daily breakdown for the week
                    daily_breakdown = week_transactions.groupby(week_transactions["date"].dt.date).agg({
                        "credit": "sum",
                        "debit": "sum"
                    }).reset_index()
                    
                    st.metric("Weekly Credits", format_indian_currency(week_summary['credit']))
                    st.metric("Weekly Debits", format_indian_currency(week_summary['debit']))
                    st.metric("Net Weekly Change", format_indian_currency(week_summary['credit'] - week_summary['debit']))
                    
                    if len(daily_breakdown) > 1:
                        st.write("**Daily Summary:**")
                        for _, day in daily_breakdown.iterrows():
                            day_name = day['date'].strftime('%a %d')
                            net_change = day['credit'] - day['debit']
                            if net_change >= 0:
                                st.write(f"{day_name}: :green[{format_indian_currency(net_change)}]")
                            else:
                                st.write(f"{day_name}: :red[{format_indian_currency(net_change)}]")
            else:
                st.info(f"No transactions found for the week containing {selected_date}")

    # Tab 2: Inter-Bank Transfers
    with tab2:
        st.subheader("🔄 Inter-Bank Transfer Analysis")
        st.write("Analysis of transfers between different bank accounts - either same person's different banks or between different persons")
        
        # Get both transfer types
        transfers = get_inter_person_transfers()
        transfer_patterns = get_transfer_patterns()
        all_transfers = get_all_transfer_transactions()
        
        # Create sub-tabs for different views
        transfer_tab1, transfer_tab2 = st.tabs(["📊 Transfer Patterns", "🔄 Inter-Bank Transfers"])
        
        with transfer_tab1:
            st.subheader("📊 All Transfer Transactions")
            
            if all_transfers is not None and not all_transfers.empty:
                st.write(f"**Found {len(all_transfers)} transfer transactions**")
                
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_debits = all_transfers['debit'].sum()
                    st.metric("Total Outgoing", format_indian_currency(total_debits))
                
                with col2:
                    total_credits = all_transfers['credit'].sum()
                    st.metric("Total Incoming", format_indian_currency(total_credits))
                
                with col3:
                    net_transfer = total_credits - total_debits
                    st.metric("Net Transfer", format_indian_currency(net_transfer))
                
                with col4:
                    unique_methods = all_transfers['transfer_method'].nunique()
                    st.metric("Transfer Methods", unique_methods)
                
                # Transfer method breakdown
                st.subheader("Transfer Method Breakdown")
                method_summary = all_transfers.groupby('transfer_method').agg({
                    'debit': 'sum',
                    'credit': 'sum',
                    'date': 'count'
                }).reset_index()
                method_summary.columns = ['Transfer Method', 'Total Debits', 'Total Credits', 'Transaction Count']
                
                # Format for display
                method_display = method_summary.copy()
                method_display['Total Debits'] = method_display['Total Debits'].apply(format_indian_currency)
                method_display['Total Credits'] = method_display['Total Credits'].apply(format_indian_currency)
                method_display['Transaction Count'] = method_display['Transaction Count'].apply(format_indian_number)
                
                st.dataframe(method_display, width='stretch', hide_index=True)
                
                # Detailed transaction list
                st.subheader("Detailed Transfer Transactions")
                
                # Format transfers for display
                transfers_display = all_transfers.copy()
                transfers_display["debit"] = transfers_display["debit"].apply(lambda x: format_indian_currency(x) if x > 0 else "")
                transfers_display["credit"] = transfers_display["credit"].apply(lambda x: format_indian_currency(x) if x > 0 else "")
                transfers_display["balance"] = transfers_display["balance"].apply(lambda x: format_indian_currency(x))
                
                # Convert dates to datetime for proper sorting, then format for display
                transfers_display["date"] = pd.to_datetime(transfers_display["date"], format="%d-%m-%Y", errors='coerce')
                transfers_display = transfers_display.sort_values("date", ascending=False)
                transfers_display["date"] = transfers_display["date"].dt.strftime("%d-%m-%Y")
                
                # Filter by transfer method
                selected_methods = st.multiselect(
                    "Filter by Transfer Method:",
                    options=all_transfers['transfer_method'].unique(),
                    default=all_transfers['transfer_method'].unique()
                )
                
                if selected_methods:
                    filtered_transfers = transfers_display[transfers_display['transfer_method'].isin(selected_methods)]
                    st.dataframe(filtered_transfers, width='stretch', hide_index=True)
                else:
                    st.info("Select at least one transfer method to view transactions")
                    
            else:
                st.info("No transfer transactions found. Transfer detection looks for keywords like TRANSFER, UPI, IMPS, NEFT, RTGS in transaction descriptions.")
        
        with transfer_tab2:
            st.subheader("🔄 Inter-Bank Transfers")
            
            if transfers is not None and not transfers.empty:
                st.write(f"**Found {len(transfers)} inter-bank transfers**")
                
                # Show transfer type breakdown
                if 'transfer_type' in transfers.columns:
                    type_counts = transfers['transfer_type'].value_counts()
                    st.write("**Transfer Types:**")
                    for transfer_type, count in type_counts.items():
                        st.write(f"• {transfer_type}: {count} transfers")
                
                # Format transfers for display
                transfers_display = transfers.copy()
                transfers_display["amount"] = transfers_display["amount"].apply(lambda x: format_indian_currency(x))
                
                # Convert dates to datetime for proper sorting, then format for display
                transfers_display["date"] = pd.to_datetime(transfers_display["date"], format="%d-%m-%Y", errors='coerce')
                transfers_display = transfers_display.sort_values("date", ascending=False)
                transfers_display["date"] = transfers_display["date"].dt.strftime("%d-%m-%Y")
                
                st.dataframe(transfers_display, width='stretch', hide_index=True)
                
                # Transfer flow visualization for exact matches
                exact_matches = transfers[transfers.get('detection_type', '') == 'Exact Match'] if 'detection_type' in transfers.columns else transfers
                if len(exact_matches) > 0:
                    st.subheader("Transfer Flow Network")
                    
                    # Create a simple transfer summary
                    transfer_summary = exact_matches.groupby(['from_owner', 'to_owner'])['amount'].sum().reset_index()
                    
                    if len(transfer_summary) > 0:
                        fig = go.Figure(data=[go.Sankey(
                            node=dict(
                                pad=15,
                                thickness=20,
                                line=dict(color="black", width=0.5),
                                label=list(set(exact_matches['from_owner'].tolist() + exact_matches['to_owner'].tolist())),
                                color="blue"
                            ),
                            link=dict(
                                source=[list(set(exact_matches['from_owner'].tolist() + exact_matches['to_owner'].tolist())).index(x) 
                                       for x in exact_matches['from_owner']],
                                target=[list(set(exact_matches['from_owner'].tolist() + exact_matches['to_owner'].tolist())).index(x) 
                                       for x in exact_matches['to_owner']],
                                value=exact_matches['amount']
                            )
                        )])
                        
                        fig.update_layout(title_text="Money Flow Between Accounts", font_size=10)
                        st.plotly_chart(fig, width='stretch')
                    else:
                        st.info("No transfer flow data available for visualization")
            else:
                st.info("No inter-account transfers detected.")
                st.markdown("""
                **Note:** Inter-account transfer detection works best when:
                - Multiple family member accounts are loaded
                - Transactions have matching amounts and dates
                - Or when transaction descriptions contain transfer keywords
                """)

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
                balance_display["balance"] = balance_display["balance"].apply(lambda x: format_indian_currency(x))
                
                # Convert dates to datetime for proper sorting, then format for display
                balance_display["date"] = pd.to_datetime(balance_display["date"], format="%d-%m-%Y", errors='coerce')
                balance_display = balance_display.sort_values("date", ascending=False)
                balance_display["date"] = balance_display["date"].dt.strftime("%d-%m-%Y")
                
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
            account_display = account_summary.copy()
            for col in ["Total Credits", "Total Debits", "Latest Balance", "Net Flow"]:
                account_display[col] = account_summary[col].apply(lambda x: format_indian_currency(x))
            
            account_display["First Transaction"] = safe_format_date(account_summary["First Transaction"])
            account_display["Last Transaction"] = safe_format_date(account_summary["Last Transaction"])
            
            st.dataframe(account_display, width='stretch')    # Tab 4: Data Quality
    # Tab 4: Categories  
    with tab4:
        st.header("📈 Spending Categories Analysis")
        st.write("Auto-categorized transaction analysis based on description keywords")
        
        # Show filter info
        if selected_accounts:
            selected_account_names = ", ".join(selected_accounts)
            st.info(f"📊 **Filtered View**: Showing data for: {selected_account_names}")
        else:
            st.info("📊 **All Accounts**: No filters applied - showing all bank accounts")
        
        # Helper function to calculate category summary from filtered data
        def calculate_category_summary_from_df(df_filtered):
            if df_filtered.empty or 'category' not in df_filtered.columns:
                return None
            
            # Filter out rows where category is None or empty
            categorized_df = df_filtered[df_filtered['category'].notna() & (df_filtered['category'] != '')]
            
            if categorized_df.empty:
                return None
            
            summary = categorized_df.groupby('category').agg({
                'debit': ['sum', 'mean', 'count'],
                'credit': ['sum', 'mean'],
                'id': 'count'
            }).reset_index()
            
            # Flatten column names
            summary.columns = ['category', 'total_debits', 'avg_debit', 'debit_count', 'total_credits', 'avg_credit', 'transaction_count']
            
            # Calculate net amount
            summary['net_amount'] = summary['total_credits'] - summary['total_debits']
            
            # Fill NaN values
            summary = summary.fillna(0)
            
            # Sort by total debits descending
            summary = summary.sort_values('total_debits', ascending=False)
            
            return summary
        
        # Helper function to calculate monthly trends from filtered data
        def calculate_monthly_trends_from_df(df_filtered):
            if df_filtered.empty or 'category' not in df_filtered.columns:
                return None
            
            # Filter out rows where category is None or empty
            categorized_df = df_filtered[df_filtered['category'].notna() & (df_filtered['category'] != '')]
            
            if categorized_df.empty:
                return None
            
            # Create month column
            categorized_df = categorized_df.copy()
            categorized_df['month'] = categorized_df['date'].dt.to_period('M').astype(str)
            
            trends = categorized_df.groupby(['month', 'category']).agg({
                'debit': 'sum',
                'credit': 'sum'
            }).reset_index()
            
            trends.columns = ['month', 'category', 'total_debits', 'total_credits']
            trends = trends.fillna(0)
            
            return trends
        
        # Get category data from filtered dataframe
        category_summary = calculate_category_summary_from_df(filtered)
        monthly_trends = calculate_monthly_trends_from_df(filtered)
        
        if category_summary is not None and not category_summary.empty:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_categories = len(category_summary)
                st.metric("Total Categories", total_categories)
            
            with col2:
                total_debits = category_summary['total_debits'].sum()
                st.metric("Total Spending", format_indian_currency(total_debits))
            
            with col3:
                avg_per_category = category_summary['total_debits'].mean()
                st.metric("Avg per Category", format_indian_currency(avg_per_category))
            
            with col4:
                top_category = category_summary.iloc[0]['category'] if len(category_summary) > 0 else "N/A"
                st.metric("Top Spending Category", top_category)
            
            # Category breakdown chart
            st.subheader("💰 Spending by Category")
            
            # Create pie chart for spending distribution
            if len(category_summary) > 0:
                fig_pie = px.pie(
                    category_summary, 
                    values='total_debits', 
                    names='category',
                    title="Spending Distribution by Category",
                    hover_data=['transaction_count']
                )
                fig_pie.update_traces(
                    textposition='inside', 
                    textinfo='percent+label',
                    hovertemplate='<b>%{label}</b><br>Amount: ₹%{value:,.0f}<br>Transactions: %{customdata[0]}<extra></extra>'
                )
                st.plotly_chart(fig_pie, width='stretch')
            
            # Category details table
            st.subheader("📊 Detailed Category Breakdown")
            
            # Format the summary for display
            display_summary = category_summary.copy()
            display_summary['total_debits'] = display_summary['total_debits'].apply(format_indian_currency)
            display_summary['total_credits'] = display_summary['total_credits'].apply(format_indian_currency)
            display_summary['net_amount'] = display_summary['net_amount'].apply(format_indian_currency)
            display_summary['avg_debit'] = display_summary['avg_debit'].apply(lambda x: format_indian_currency(x) if pd.notna(x) else "₹0.00")
            display_summary['avg_credit'] = display_summary['avg_credit'].apply(lambda x: format_indian_currency(x) if pd.notna(x) else "₹0.00")
            
            st.dataframe(
                display_summary,
                column_config={
                    'category': 'Category',
                    'transaction_count': 'Transactions',
                    'total_debits': 'Total Spent',
                    'total_credits': 'Total Received',
                    'net_amount': 'Net Amount',
                    'avg_debit': 'Avg Spent',
                    'avg_credit': 'Avg Received'
                },
                width='stretch',
                hide_index=True
            )
            
            # Monthly trends
            if monthly_trends is not None and not monthly_trends.empty:
                st.subheader("📈 Monthly Category Trends")
                
                # Create a bar chart for monthly trends
                fig_trends = px.bar(
                    monthly_trends, 
                    x='month', 
                    y='total_debits',
                    color='category',
                    title="Monthly Spending by Category",
                    labels={'total_debits': 'Amount Spent (₹)', 'month': 'Month'}
                )
                fig_trends.update_layout(xaxis_title="Month", yaxis_title="Amount Spent (₹)")
                st.plotly_chart(fig_trends, width='stretch')
                
                # Monthly trends table
                with st.expander("View Monthly Trends Data"):
                    trends_display = monthly_trends.copy()
                    trends_display['total_debits'] = trends_display['total_debits'].apply(format_indian_currency)
                    trends_display['total_credits'] = trends_display['total_credits'].apply(format_indian_currency)
                    st.dataframe(trends_display, width='stretch', hide_index=True)
            
            # Individual category view
            st.subheader("🔍 View Expenses by Category")
            
            # Category selector
            available_categories = category_summary['category'].tolist() if not category_summary.empty else []
            if available_categories:
                selected_category = st.selectbox(
                    "Select a category to view detailed expenses:",
                    available_categories,
                    index=0
                )
                
                if selected_category:
                    # Get transactions for the selected category from filtered data
                    category_transactions = filtered[filtered['category'] == selected_category].copy()
                    
                    if not category_transactions.empty:
                        # Show category summary
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            total_spent = category_transactions['debit'].sum()
                            st.metric("Total Spent", format_indian_currency(total_spent))
                        with col2:
                            transaction_count = len(category_transactions)
                            st.metric("Transactions", transaction_count)
                        with col3:
                            avg_amount = category_transactions['debit'].mean()
                            st.metric("Average Amount", format_indian_currency(avg_amount))
                        
                        # Show transactions table
                        st.write(f"**All transactions in {selected_category} category:**")
                        
                        # Format the transactions for display
                        display_transactions = category_transactions[['date', 'description', 'debit', 'credit', 'balance', 'owner', 'bank']].copy()
                        display_transactions['date'] = display_transactions['date'].dt.strftime('%d-%m-%Y')
                        display_transactions['debit'] = display_transactions['debit'].apply(lambda x: format_indian_currency(x) if pd.notna(x) and x > 0 else "")
                        display_transactions['credit'] = display_transactions['credit'].apply(lambda x: format_indian_currency(x) if pd.notna(x) and x > 0 else "")
                        display_transactions['balance'] = display_transactions['balance'].apply(format_indian_currency)
                        
                        st.dataframe(
                            display_transactions,
                            column_config={
                                'date': 'Date',
                                'description': 'Description',
                                'debit': 'Debit',
                                'credit': 'Credit',
                                'balance': 'Balance',
                                'owner': 'Owner',
                                'bank': 'Bank'
                            },
                            hide_index=True,
                            width='stretch'
                        )
                        
                        # Monthly spending pattern for selected category
                        if len(category_transactions) > 1:
                            st.write(f"**Monthly spending pattern for {selected_category}:**")
                            monthly_spending = category_transactions.groupby(category_transactions['date'].dt.to_period('M'))['debit'].sum().reset_index()
                            monthly_spending['date'] = monthly_spending['date'].astype(str)
                            
                            fig_monthly = px.line(
                                monthly_spending,
                                x='date',
                                y='debit',
                                title=f"Monthly Spending Trend - {selected_category}",
                                labels={'debit': 'Amount Spent (₹)', 'date': 'Month'}
                            )
                            st.plotly_chart(fig_monthly, width='stretch')
                    else:
                        st.info(f"No transactions found for {selected_category} category.")
        
        else:
            st.info("No categorized transactions found. Click '🔄 Update Categories' in the sidebar to categorize your transactions.")
            
            # Show some sample categories
            st.subheader("📋 Available Categories")
            sample_categories = [
                "🍽️ Food & Dining", "🚗 Transportation", "🛒 Shopping", 
                "💡 Utilities & Bills", "🏥 Healthcare", "🎬 Entertainment",
                "📚 Education", "🏦 Banking & Finance", "💰 Cash Withdrawal",
                "🔄 Transfers", "💼 Salary & Income", "📦 Other"
            ]
            
            cols = st.columns(3)
            for i, category in enumerate(sample_categories):
                with cols[i % 3]:
                    st.write(f"• {category}")

    # Tab 5: Data Quality
    with tab5:
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
            st.metric("Total Transactions", format_indian_number(len(df)))
            st.metric("Date Range", f"{df['date'].min().strftime('%d-%m-%Y')} to {df['date'].max().strftime('%d-%m-%Y')}")
            st.metric("Unique Accounts", format_indian_number(len(df[['owner', 'bank']].drop_duplicates())))
        
        # Show sweep adjustments
        sweep_adjustments = get_sweep_balance_adjustments()
        if sweep_adjustments is not None and not sweep_adjustments.empty:
            st.write("**Active Sweep Balance Adjustments**")
            sweep_display = sweep_adjustments.copy()
            sweep_display["amount"] = sweep_display["amount"].apply(lambda x: format_indian_currency(x))
            st.dataframe(sweep_display, width='stretch', hide_index=True)
        
        # Show sweep balance history
        st.subheader("📊 Sweep Balance History")
        sweep_balance_history = get_sweep_balance_history("Saksham", "SBI")
        if sweep_balance_history is not None and not sweep_balance_history.empty:
            st.write("**SBI Sweep Account (MOD Balance) History**")
            history_display = sweep_balance_history.copy()
            history_display["mod_balance"] = history_display["mod_balance"].apply(lambda x: format_indian_currency(x))
            st.dataframe(history_display, width='stretch', hide_index=True)
        else:
            st.info("No sweep balance history found. Load SBI data to see MOD balance tracking.")
        
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
