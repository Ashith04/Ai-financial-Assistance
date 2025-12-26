from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import datetime
import json
import random
import math
from collections import defaultdict
import re

app = Flask(__name__)

@app.template_filter('tojsonfilter')
def to_json_filter(obj):
    return json.dumps(obj)

def init_db():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    # Transactions table
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  amount REAL NOT NULL,
                  category TEXT NOT NULL,
                  description TEXT,
                  type TEXT NOT NULL,
                  date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  ai_category TEXT,
                  risk_score REAL DEFAULT 0)''')
    
    # Goals table
    c.execute('''CREATE TABLE IF NOT EXISTS goals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  target_amount REAL NOT NULL,
                  current_amount REAL DEFAULT 0,
                  deadline DATE,
                  category TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # AI insights table
    c.execute('''CREATE TABLE IF NOT EXISTS ai_insights
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  insight_type TEXT NOT NULL,
                  message TEXT NOT NULL,
                  confidence REAL DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

@app.route('/')
def dashboard():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    # Get recent transactions
    c.execute('SELECT * FROM transactions ORDER BY date DESC LIMIT 10')
    recent_transactions = c.fetchall()
    
    # Get financial summary
    c.execute('SELECT SUM(amount) FROM transactions WHERE type = "income"')
    total_income = c.fetchone()[0] or 0
    
    c.execute('SELECT SUM(amount) FROM transactions WHERE type = "expense"')
    total_expenses = c.fetchone()[0] or 0
    
    # Get spending by category
    c.execute('SELECT category, SUM(amount) FROM transactions WHERE type = "expense" GROUP BY category')
    spending_by_category = c.fetchall()
    
    # Get goals
    c.execute('SELECT * FROM goals ORDER BY deadline ASC')
    goals = c.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                         transactions=recent_transactions,
                         total_income=total_income,
                         total_expenses=total_expenses,
                         balance=total_income - total_expenses,
                         spending_by_category=spending_by_category,
                         goals=goals)

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    data = request.get_json()
    amount = float(data['amount'])
    category = data['category']
    description = data['description']
    trans_type = data['type']
    
    # AI categorization
    ai_category = ai_categorize_transaction(description, category)
    risk_score = calculate_risk_score(amount, category, trans_type)
    
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('''INSERT INTO transactions 
                 (amount, category, description, type, ai_category, risk_score) 
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (amount, category, description, trans_type, ai_category, risk_score))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'ai_category': ai_category, 'risk_score': risk_score})

@app.route('/ai_insights')
def ai_insights():
    insights = generate_advanced_ai_insights()
    predictions = generate_financial_predictions()
    recommendations = generate_smart_recommendations()
    
    return render_template('ai_insights.html', 
                         insights=insights,
                         predictions=predictions,
                         recommendations=recommendations)

@app.route('/analytics')
def analytics():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    # Monthly spending trends
    c.execute('''SELECT strftime('%Y-%m', date) as month, 
                        SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expenses,
                        SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income
                 FROM transactions 
                 GROUP BY strftime('%Y-%m', date) 
                 ORDER BY month DESC LIMIT 12''')
    monthly_data = c.fetchall()
    
    # Category analysis
    c.execute('''SELECT category, SUM(amount) as total, COUNT(*) as count
                 FROM transactions WHERE type = 'expense'
                 GROUP BY category ORDER BY total DESC''')
    category_analysis = c.fetchall()
    
    conn.close()
    
    return render_template('analytics.html',
                         monthly_data=monthly_data,
                         category_analysis=category_analysis)

@app.route('/goals')
def goals():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('SELECT * FROM goals ORDER BY deadline ASC')
    goals_data = c.fetchall()
    conn.close()
    
    return render_template('goals.html', goals=goals_data)

@app.route('/add_goal', methods=['POST'])
def add_goal():
    data = request.get_json()
    
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('''INSERT INTO goals (title, target_amount, deadline, category) 
                 VALUES (?, ?, ?, ?)''',
              (data['title'], data['target_amount'], data['deadline'], data['category']))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/api/spending_forecast')
def spending_forecast():
    forecast = generate_spending_forecast()
    return jsonify(forecast)

@app.route('/api/budget_optimization')
def budget_optimization():
    optimization = generate_budget_optimization()
    return jsonify(optimization)

def ai_categorize_transaction(description, category):
    """AI-powered transaction categorization"""
    keywords = {
        'food': ['restaurant', 'food', 'grocery', 'cafe', 'pizza', 'burger'],
        'transport': ['uber', 'taxi', 'gas', 'fuel', 'parking', 'metro'],
        'entertainment': ['movie', 'game', 'netflix', 'spotify', 'concert'],
        'shopping': ['amazon', 'mall', 'store', 'clothes', 'shoes'],
        'bills': ['electricity', 'water', 'internet', 'phone', 'rent'],
        'health': ['doctor', 'pharmacy', 'hospital', 'medicine', 'gym']
    }
    
    description_lower = description.lower()
    for ai_cat, words in keywords.items():
        if any(word in description_lower for word in words):
            return ai_cat
    
    return category.lower()

def calculate_risk_score(amount, category, trans_type):
    """Calculate financial risk score for transaction"""
    if trans_type == 'income':
        return 0
    
    risk_categories = {
        'entertainment': 0.7,
        'shopping': 0.6,
        'food': 0.4,
        'transport': 0.3,
        'bills': 0.1,
        'health': 0.2
    }
    
    base_risk = risk_categories.get(category.lower(), 0.5)
    amount_risk = min(amount / 1000, 1.0)  # Higher amounts = higher risk
    
    return round((base_risk + amount_risk) / 2, 2)

def generate_advanced_ai_insights():
    """Generate advanced AI insights using pattern analysis"""
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    insights = []
    
    # Spending pattern analysis
    c.execute('''SELECT category, AVG(amount), COUNT(*) 
                 FROM transactions WHERE type = 'expense' 
                 GROUP BY category''')
    spending_patterns = c.fetchall()
    
    for category, avg_amount, count in spending_patterns:
        if count > 5 and avg_amount > 100:
            insights.append({
                'type': 'pattern',
                'message': f"🔍 You spend an average of ${avg_amount:.2f} on {category}. Consider setting a monthly limit.",
                'confidence': 0.85,
                'category': category
            })
    
    # Unusual spending detection
    c.execute('''SELECT amount, category, description 
                 FROM transactions WHERE type = 'expense' 
                 ORDER BY amount DESC LIMIT 5''')
    high_expenses = c.fetchall()
    
    if high_expenses:
        highest = high_expenses[0]
        insights.append({
            'type': 'anomaly',
            'message': f"⚠️ Unusual high expense detected: ${highest[0]:.2f} in {highest[1]}. Review if necessary.",
            'confidence': 0.92,
            'amount': highest[0]
        })
    
    conn.close()
    return insights

def generate_financial_predictions():
    """Generate financial predictions using trend analysis"""
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    # Get monthly trends
    c.execute('''SELECT strftime('%Y-%m', date) as month,
                        SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expenses
                 FROM transactions 
                 GROUP BY month ORDER BY month DESC LIMIT 6''')
    monthly_expenses = c.fetchall()
    
    predictions = []
    
    if len(monthly_expenses) >= 3:
        recent_avg = sum(float(row[1]) for row in monthly_expenses[:3]) / 3
        older_avg = sum(float(row[1]) for row in monthly_expenses[3:]) / max(len(monthly_expenses[3:]), 1)
        
        trend = (recent_avg - older_avg) / older_avg * 100 if older_avg > 0 else 0
        
        if trend > 10:
            predictions.append({
                'type': 'warning',
                'message': f"📈 Your spending has increased by {trend:.1f}% recently. Next month prediction: ${recent_avg * 1.1:.2f}",
                'predicted_amount': recent_avg * 1.1
            })
        elif trend < -10:
            predictions.append({
                'type': 'positive',
                'message': f"📉 Great! Your spending decreased by {abs(trend):.1f}%. Keep it up!",
                'predicted_amount': recent_avg * 0.95
            })
        else:
            predictions.append({
                'type': 'stable',
                'message': f"📊 Your spending is stable. Next month prediction: ${recent_avg:.2f}",
                'predicted_amount': recent_avg
            })
    
    conn.close()
    return predictions

def generate_smart_recommendations():
    """Generate personalized financial recommendations"""
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    recommendations = []
    
    # Analyze spending categories
    c.execute('''SELECT category, SUM(amount) as total
                 FROM transactions WHERE type = 'expense'
                 GROUP BY category ORDER BY total DESC LIMIT 3''')
    top_categories = c.fetchall()
    
    for category, amount in top_categories:
        if category.lower() in ['entertainment', 'shopping']:
            recommendations.append({
                'type': 'savings',
                'message': f"💡 You spent ${amount:.2f} on {category}. Try the 50/30/20 rule: reduce by 10% to save ${amount * 0.1:.2f}",
                'potential_savings': amount * 0.1
            })
    
    # Goal-based recommendations
    c.execute('SELECT * FROM goals WHERE current_amount < target_amount')
    active_goals = c.fetchall()
    
    for goal in active_goals:
        remaining = goal[2] - goal[3]  # target - current
        recommendations.append({
            'type': 'goal',
            'message': f"🎯 To reach '{goal[1]}', save ${remaining/12:.2f} monthly for the next year",
            'monthly_target': remaining/12
        })
    
    conn.close()
    return recommendations

def generate_spending_forecast():
    """Generate 6-month spending forecast"""
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    c.execute('''SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
                 FROM transactions WHERE type = 'expense'
                 GROUP BY month ORDER BY month DESC LIMIT 6''')
    historical_data = c.fetchall()
    
    if len(historical_data) < 3:
        return {'error': 'Insufficient data for forecast'}
    
    # Simple linear regression for forecast
    amounts = [float(row[1]) for row in reversed(historical_data)]
    forecast = []
    
    for i in range(6):  # 6 months forecast
        # Simple trend calculation
        if len(amounts) >= 2:
            trend = (amounts[-1] - amounts[0]) / len(amounts)
            predicted = amounts[-1] + trend * (i + 1)
            forecast.append(max(predicted, 0))  # Ensure non-negative
        else:
            forecast.append(amounts[-1] if amounts else 0)
    
    conn.close()
    return {'forecast': forecast, 'months': 6}

def generate_budget_optimization():
    """Generate budget optimization suggestions"""
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    c.execute('''SELECT category, SUM(amount) as total, AVG(amount) as avg
                 FROM transactions WHERE type = 'expense'
                 GROUP BY category''')
    category_data = c.fetchall()
    
    optimizations = []
    for category, total, avg in category_data:
        if total > 500:  # Focus on significant categories
            optimizations.append({
                'category': category,
                'current_spending': total,
                'suggested_budget': total * 0.9,  # 10% reduction
                'potential_savings': total * 0.1
            })
    
    conn.close()
    return optimizations

if __name__ == '__main__':
    init_db()
    app.run(debug=True)