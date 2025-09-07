# 💰 Family Finance Dashboard

A comprehensive Streamlit-based personal finance management dashboard with Indian number formatting and advanced transaction analysis.

## 🌟 Features

- **📊 Interactive Dashboard**: Multi-chart visualization (Line, Bar, Area) with hover details
- **🔄 Inter-Bank Transfer Analysis**: Detect transfers between different banks and accounts
- **📅 Weekly Transaction Details**: Comprehensive weekly transaction breakdown
- **💱 Indian Number Formatting**: Native support for Indian numbering system (lakhs, crores)
- **⚖️ Sweep Balance Adjustments**: Manual balance corrections and adjustments
- **📈 Real-time Analytics**: Account balances, net flows, and transaction insights
- **🔍 Advanced Filtering**: Filter by accounts, date ranges, and transaction types
- **🗄️ Data Management**: Load CSV data with duplicate detection and purge functionality

## 📁 Project Structure

```
finance-dashboard/
├── src/                          # Source code
│   ├── database/                 # Database operations
│   │   ├── __init__.py
│   │   └── db.py                 # SQLite database functions
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── parser.py             # CSV parsing utilities
│       └── indian_formatting.py # Indian number formatting
├── scripts/                      # Utility scripts
│   ├── setup.sh                 # Environment setup script
│   ├── start.sh                 # Application startup script
│   ├── demo.py                  # Demo script
│   ├── demo_indian_formatting.py
│   └── validate_data.py         # Data validation
├── tests/                       # Test files
│   ├── __init__.py
│   └── test_formatting.py      # Unit tests
├── docs/                        # Documentation
│   └── ENHANCEMENT_SUMMARY.md   # Feature enhancement log
├── data/                        # Data files
│   ├── README.md               # Data directory documentation
│   └── sample/                 # Sample data (git-tracked)
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Git (optional, for version control)

### Setup

1. **Clone or download the repository**
   ```bash
   git clone <repository-url>
   cd finance-dashboard
   ```

2. **Run the setup script**
   ```bash
   ./scripts/setup.sh
   ```

3. **Start the application**
   ```bash
   ./scripts/start.sh
   ```

   Or manually:
   ```bash
   source venv/bin/activate
   python -m streamlit run app.py
   ```

4. **Open your browser** to `http://localhost:8501`

### Manual Setup (Alternative)

1. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   streamlit run app.py
   ```

## 📊 Usage

### Data Loading
1. Place your bank CSV files in the `data/` directory
2. Use the "🔄 Load CSV Data" button in the sidebar
3. The system will detect and skip duplicate transactions

### CSV Format
Your CSV files should contain columns for:
- Date (various formats supported)
- Description
- Debit Amount
- Credit Amount  
- Balance

### Features Overview

#### 📊 Dashboard Tab
- Interactive charts with Indian number formatting
- Account filtering with checkboxes
- Weekly summary with transaction counts
- Hover tooltips showing transaction details

#### 🔄 Transfers Tab
- **Transfer Patterns**: Overview of all transfer transactions
- **Inter-Bank Transfers**: Detected transfers between accounts

#### 💼 Accounts Tab
- Account-wise balance summary
- Sweep balance adjustments
- Account performance metrics

#### 📋 Data Quality Tab
- Data validation and integrity checks
- Transaction statistics
- Duplicate detection results

## 🔒 Security & Privacy

### What's Safe to Commit to Git
- ✅ Source code (`src/`, `scripts/`, `tests/`)
- ✅ Documentation (`docs/`, `README.md`)
- ✅ Configuration files (`.gitignore`, `requirements.txt`)
- ✅ Sample/anonymized data (`data/sample/`)

### What's Automatically Ignored
- ❌ Personal financial data (`data/*.csv`)
- ❌ Database files (`*.db`, `*.sqlite`)
- ❌ Virtual environment (`venv/`)
- ❌ Environment files (`.env`)
- ❌ Cache files (`__pycache__/`, `.DS_Store`)

## 🧪 Testing

Run the test suite:
```bash
source venv/bin/activate
python -m pytest tests/ -v
```

Or run individual tests:
```bash
python tests/test_formatting.py
```

## 📈 Indian Number Formatting

The dashboard uses authentic Indian number formatting:
- ₹1,000 (One thousand)
- ₹1,00,000 (One lakh)
- ₹10,00,000 (Ten lakhs)
- ₹1,00,00,000 (One crore)

## 🛠️ Development

### Adding New Features
1. Create feature branches from `main`
2. Add tests for new functionality
3. Update documentation
4. Ensure all tests pass

### Code Structure
- `src/database/db.py`: Database operations and queries
- `src/utils/parser.py`: CSV parsing and data validation
- `src/utils/indian_formatting.py`: Number formatting utilities
- `app.py`: Main Streamlit application and UI

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is for personal use. Ensure you comply with your bank's terms of service when analyzing transaction data.

## 🆘 Troubleshooting

### Common Issues
- **Import errors**: Run `./scripts/setup.sh` to ensure proper environment setup
- **Database errors**: Delete `finance.db` and restart the application
- **CSV parsing errors**: Check your CSV format matches expected columns

### Getting Help
- Check the `docs/` directory for detailed documentation
- Run `python -m streamlit run app.py --help` for Streamlit options
- Ensure your Python version is 3.8 or higher
