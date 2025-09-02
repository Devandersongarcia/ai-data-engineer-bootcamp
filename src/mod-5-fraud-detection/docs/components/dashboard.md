# 🔍 UberEats Fraud Detection Dashboard

A professional Streamlit application for real-time fraud monitoring, AI-powered analytics, and intelligent agent assistance.

## 🌟 Features

### 📊 **Real-time Dashboard**
- Live fraud detection metrics and KPIs
- Interactive trend visualizations 
- Fraud pattern analysis and frequency tracking
- Performance monitoring and agent statistics

### 🚨 **Real-time Alerts**
- High-risk order monitoring
- Intelligent alert filtering and sorting
- Detailed fraud reasoning and risk assessment
- Agent analysis status tracking

### 💬 **AI Chat Assistant**
- Direct integration with MindsDB `agent_fraud_analytics`
- Natural language querying of fraud data
- Quick insight buttons for common questions
- Context-aware fraud analysis and recommendations

### 🔍 **Advanced Search**
- Order ID, User ID, and fraud score range searches
- Detailed order analysis with complete fraud history
- User behavior pattern analysis
- Agent analysis results integration

## 🛠 Installation

### Prerequisites
- Python 3.8+
- PostgreSQL with fraud detection schema
- MindsDB server running locally
- MindsDB agent `agent_fraud_analytics` configured

### Setup Steps

1. **Install Dependencies**
   ```bash
   cd /Users/mateusoliveira/Mateus/owshq/projects/pycharm/uberats-fraud-detection
   pip install -r requirements_streamlit.txt
   ```

2. **Configure Database**
   - Ensure PostgreSQL is running with fraud detection data
   - Verify tables: `fraud_detection_results`, `agent_analysis_results`

3. **Configure MindsDB**
   - Start MindsDB server: `python -m mindsdb`
   - Verify agent exists: Check for `agent_fraud_analytics` in MindsDB console

4. **Launch Application**
   ```bash
   python run_fraud_app.py
   ```
   
   Or manually:
   ```bash
   streamlit run fraud_detection_app.py
   ```

## 📋 Configuration

### Database Connection
- **Host**: localhost (default)
- **Port**: 5432 (default) 
- **Database**: uberats_fraud (default)
- **User**: postgres (default)
- **Password**: postgres (default)

### MindsDB Connection
- **Server URL**: http://127.0.0.1:47334 (default)
- **Agent Name**: agent_fraud_analytics (default)

## 🎯 Usage Guide

### 1. **Connect to Services**
   - Use the sidebar to configure database and MindsDB connections
   - Click "Connect to Agent" and "Connect to Database"
   - Verify green connection status indicators

### 2. **Dashboard Tab**
   - View real-time fraud metrics and trends
   - Analyze fraud patterns and frequencies
   - Monitor system performance

### 3. **Real-time Alerts Tab**
   - Monitor high-risk orders requiring attention
   - Filter by risk level and analysis status
   - View detailed fraud reasoning

### 4. **AI Chat Assistant Tab**
   - Use quick insight buttons for common questions
   - Ask natural language questions about fraud patterns
   - Get AI-powered recommendations and analysis

### 5. **Order Search Tab**
   - Search specific orders by ID
   - Analyze user fraud history
   - Find orders by fraud score range

## 🤖 AI Assistant Capabilities

The MindsDB agent can help with:

- **Real-time Analysis**: Current fraud status and trends
- **Pattern Recognition**: Identifying emerging fraud patterns  
- **Risk Assessment**: Evaluating specific orders or users
- **Prevention Strategies**: Recommending fraud prevention measures
- **Performance Metrics**: Agent effectiveness and accuracy
- **Predictive Insights**: Fraud trend forecasting

### Example Questions:
- "What are the most concerning fraud patterns today?"
- "Analyze the fraud risk for user ID 12345"
- "What prevention strategies do you recommend?"
- "Show me high-risk orders requiring immediate attention"
- "How accurate have the fraud detection agents been?"

## 🔧 Architecture

### Components:
- **Frontend**: Streamlit with custom CSS styling
- **Data Layer**: PostgreSQL with fraud detection schema
- **AI Layer**: MindsDB agent integration
- **Visualization**: Plotly for interactive charts
- **API**: Direct MindsDB REST API integration

### Data Flow:
1. **Real-time Ingestion**: Kafka → Spark → PostgreSQL
2. **AI Analysis**: MindsDB agents analyze high-risk cases
3. **Dashboard**: Streamlit queries PostgreSQL and MindsDB
4. **User Interaction**: Chat interface queries MindsDB agent

## 📊 Database Schema

### Key Tables:
- `fraud_detection_results`: Main fraud detection data from Spark
- `agent_analysis_results`: AI agent analysis results
- Views: `fraud_detection_complete`, `agent_performance_metrics`

### Required Permissions:
```sql
GRANT SELECT ON fraud_detection_results TO dashboard_user;
GRANT SELECT ON agent_analysis_results TO dashboard_user;
GRANT SELECT ON fraud_detection_complete TO dashboard_user;
```

## 🎨 Design Features

- **Professional UI**: Clean, modern interface with fraud-specific color scheme
- **Responsive Layout**: Optimized for different screen sizes
- **Real-time Updates**: Refresh button and automatic data updates
- **Interactive Charts**: Plotly-powered visualizations
- **Status Indicators**: Clear connection and system status
- **Alert System**: Color-coded risk levels and priorities

## 🚀 Performance Optimization

- **Database Indexing**: Optimized queries with proper indexes
- **Connection Pooling**: Efficient database connection management
- **Caching**: MindsDB client session management
- **Pagination**: Limiting large result sets
- **Async Loading**: Non-blocking data loading with spinners

## 🔐 Security Considerations

- **Database**: Secure credential management
- **API**: MindsDB authentication and authorization
- **Input Validation**: SQL injection prevention
- **Session Management**: Secure session handling
- **Error Handling**: Proper error messages without data exposure

## 📱 Responsive Design

The dashboard works on:
- **Desktop**: Full feature set with wide layout
- **Tablet**: Responsive column layouts
- **Mobile**: Simplified interface with essential features

## 🐛 Troubleshooting

### Common Issues:

1. **Database Connection Failed**
   - Check PostgreSQL is running
   - Verify database credentials
   - Ensure fraud tables exist

2. **MindsDB Agent Not Found**
   - Start MindsDB server
   - Verify agent exists: `SHOW AGENTS;` in MindsDB console
   - Check agent name spelling

3. **No Data in Dashboard**
   - Verify fraud detection system is running
   - Check if data exists in PostgreSQL tables
   - Ensure proper table permissions

4. **Import Errors**
   - Install requirements: `pip install -r requirements_streamlit.txt`
   - Check Python path for MindsDB interface modules

## 📈 Monitoring & Alerts

### Health Checks:
- Database connection status
- MindsDB agent availability  
- Real-time data freshness
- System performance metrics

### Performance Metrics:
- Query response times
- Data refresh rates
- Agent analysis success rates
- User interaction tracking

## 🔄 Updates & Maintenance

### Regular Tasks:
- Monitor database disk usage
- Update fraud detection models
- Review agent performance
- Update security configurations

### Version Control:
- Application code in Git
- Database schema versioning
- Configuration management
- Deployment scripts

---

## 🎉 Getting Started

1. **Quick Start**: `python run_fraud_app.py`
2. **Open Browser**: Navigate to http://localhost:8501
3. **Connect Services**: Configure database and MindsDB connections
4. **Start Exploring**: View dashboard, alerts, and chat with AI assistant

**Happy Fraud Hunting! 🔍🚨**