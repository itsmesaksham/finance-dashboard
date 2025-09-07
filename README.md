# 💰 Family Finance Dashboard

A comprehensive personal finance management solution built with Streamlit to manage all your family's financial data with interactive visualizations and intelligent analysis.

## 🌟 Features

### � Indian Number System Support
- **Proper comma placement** following Indian standards (lakhs, crores)
- **Currency formatting** with ₹ symbol and Indian comma conventions
- **Consistent formatting** across all charts, tables, and metrics
- **Hover tooltips** display amounts in Indian format

### �📊 Interactive Dashboard
- **Real-time visualizations** with multiple chart types (Line, Bar, Area charts)
- **Hover details** showing transaction information for each day
- **Daily balance trends** with smooth transitions
- **Credits vs Debits** comparison charts

### 🏦 Multi-Account Management
- Support for **multiple family members** and **multiple banks**
- **Checkbox filters** to select specific bank accounts
- **Account-wise summaries** and balance distributions
- **Date range filtering** for focused analysis

### 🔄 Inter-Person Transfer Detection
- **Automatic detection** of money transfers between family members
- **Transfer flow visualization** using Sankey diagrams
- **Matching algorithm** based on amounts and dates

### ⚖️ Sweep Balance Adjustments
- **Easy adjustments** for sweep account balances
- **Historical tracking** of all adjustments
- **Automatic application** to future calculations

### 📋 Data Quality & Integrity
- **Validation checks** for data consistency
- **Duplicate detection** and anomaly highlighting
- **Statistics overview** of your financial data
- **Raw data inspection** capabilities

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone or download** this repository
2. **Install dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Prepare your data**:
   - Place your bank statement CSV files in the `data/` folder
   - Use the naming convention: `Owner_Bank.csv` (e.g., `Saksham_SBI.csv`, `Priya_HDFC.csv`)

4. **Run the application**:
   ```bash
   streamlit run app.py
   ```

5. **Open your browser** and navigate to the URL shown in the terminal (usually `http://localhost:8501`)

## 📁 File Structure

```
finance-dashboard/
├── app.py              # Main Streamlit application
├── db.py              # Database operations and management
├── parser.py          # CSV parsing and data processing
├── requirements.txt   # Python dependencies
├── finance.db        # SQLite database (created automatically)
└── data/             # Directory for CSV files
    └── *.csv         # Your bank statement files
```

## 💡 Usage Guide

### 1. Loading Data
- Click **"🔄 Load CSV Data"** in the sidebar
- The app will automatically process all CSV files in the `data/` folder
- Progress bar shows loading status

### 2. Exploring Your Data
- Use the **Dashboard tab** for main overview and trends
- Check **Transfers tab** for inter-family money movements
- View **Accounts tab** for detailed account summaries
- Monitor **Data Quality tab** for validation and integrity

### 3. Filtering and Analysis
- **Select specific accounts** using checkboxes in the sidebar
- **Choose date ranges** for focused analysis
- **Switch chart types** for different perspectives
- **Click on specific dates** to see detailed transactions

### 4. Sweep Balance Adjustments
- Open the **"Sweep Balance Adjustments"** section in sidebar
- Add adjustments for accounts with sweep facilities
- Adjustments are automatically applied to all future calculations

## 🏗️ Supported Bank Formats

The parser automatically detects and handles various CSV formats from different banks:

### Column Mapping
- **Dates**: "date", "txn date", "transaction date", "value date"
- **Descriptions**: "description", "narration", "remarks", "particulars"
- **Debits**: "debit", "withdrawal amt.", "withdrawal amount"
- **Credits**: "credit", "deposit amt.", "deposit amount"
- **Balance**: "balance", "balance amt.", "available balance"

### Features
- **Automatic encoding detection** (UTF-8, Latin1, CP1252)
- **Indian number format support** (commas, quotes, currency symbols)
- **Multiple date format parsing**
- **Transfer transaction detection**
- **Data cleaning and standardization**

## 🔧 Customization

### Adding New Banks
1. Update the column mapping in `parser.py`
2. Add new column name variations to the `col_map` dictionary
3. Test with sample data

### Extending Features
- **Custom metrics**: Add new calculations in `app.py`
- **Additional charts**: Use Plotly or Altair for new visualizations
- **Export functionality**: Add CSV/PDF export options
- **Budgeting features**: Implement spending categories and limits

## 🇮🇳 Indian Number System Examples

The application uses the Indian number system for all currency and number displays:

| Amount | International Format | Indian Format |
|--------|---------------------|---------------|
| ₹1,500 | ₹1,500 | ₹1,500 |
| ₹15,000 | ₹15,000 | ₹15,000 |
| ₹150,000 | ₹150,000 | ₹1,50,000 |
| ₹1,500,000 | ₹1,500,000 | ₹15,00,000 |
| ₹15,000,000 | ₹15,000,000 | ₹1,50,00,000 |

**Benefits:**
- Natural reading for Indian users
- Familiar lakhs and crores representation
- Consistent across all dashboard elements

## 🐛 Troubleshooting

### Common Issues

1. **"No data found"**
   - Check CSV files are in the `data/` folder
   - Verify filename format: `Owner_Bank.csv`
   - Ensure CSV files have proper headers

2. **Date parsing errors**
   - Check date format in your CSV files
   - Add new date formats to `parse_date()` function in `parser.py`

3. **Column not recognized**
   - Add column name variations to `col_map` in `parser.py`
   - Check for extra spaces or special characters in headers

4. **Missing transactions**
   - Verify CSV encoding (try different encodings)
   - Check for empty rows or formatting issues

## 📝 Data Privacy

- All data is stored **locally** in SQLite database
- **No external connections** or data sharing
- **Complete control** over your financial information
- **Secure processing** within your environment

## 🤝 Contributing

Feel free to contribute to this project by:
- **Reporting bugs** and issues
- **Suggesting new features**
- **Submitting pull requests**
- **Improving documentation**

## 📄 License

This project is open-source and available under the MIT License.

---

**Happy Finance Tracking! 💰📊**
