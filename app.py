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
    # Ensure database is initialized
    init_db()
    
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
    # Ensure database is initialized
    init_db()
    
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
    c.execute('''INSERT INTO goals (title, target_amount, current_amount, deadline, category) 
                 VALUES (?, ?, ?, ?, ?)''',
              (data['title'], data['target_amount'], data.get('current_amount', 0), 
               data['deadline'], data['category']))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/update_goal', methods=['POST'])
def update_goal():
    data = request.get_json()
    
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('UPDATE goals SET current_amount = current_amount + ? WHERE id = ?',
              (data['amount'], data['goal_id']))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/delete_goal', methods=['POST'])
def delete_goal():
    data = request.get_json()
    
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('DELETE FROM goals WHERE id = ?', (data['goal_id'],))
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
    
    # Check if we have any data
    c.execute('SELECT COUNT(*) FROM transactions')
    total_transactions = c.fetchone()[0]
    
    if total_transactions == 0:
        insights.append({
            'type': 'welcome',
            'message': '🌟 Welcome to AI Finance Assistant! Add some transactions to get personalized insights.',
            'confidence': 1.0,
            'category': 'getting_started'
        })
        conn.close()
        return insights
    
    # Spending pattern analysis
    c.execute('''SELECT category, AVG(amount), COUNT(*), SUM(amount) 
                 FROM transactions WHERE type = 'expense' 
                 GROUP BY category ORDER BY SUM(amount) DESC''')
    spending_patterns = c.fetchall()
    
    if spending_patterns:
        top_category = spending_patterns[0]
        insights.append({
            'type': 'pattern',
            'message': f'💰 Your biggest expense category is {top_category[0]} with ${top_category[3]:.2f} total spent (avg ${top_category[1]:.2f} per transaction)',
            'confidence': 0.95,
            'category': top_category[0]
        })
    
    # Weekly spending analysis
    c.execute('''SELECT AVG(daily_total) FROM (
                    SELECT DATE(date) as day, SUM(amount) as daily_total
                    FROM transactions WHERE type = 'expense'
                    GROUP BY DATE(date)
                 )''')
    avg_daily = c.fetchone()[0] or 0
    
    if avg_daily > 0:
        insights.append({
            'type': 'trend',
            'message': f'📊 You spend an average of ${avg_daily:.2f} per day. Monthly projection: ${avg_daily * 30:.2f}',
            'confidence': 0.88,
            'category': 'spending_rate'
        })
    
    # High-risk transactions
    c.execute('''SELECT COUNT(*), AVG(amount) FROM transactions 
                 WHERE type = 'expense' AND amount > 200''')
    high_amount_data = c.fetchone()
    
    if high_amount_data[0] > 0:
        insights.append({
            'type': 'warning',
            'message': f'⚠️ You have {high_amount_data[0]} high-value transactions (>$200). Average: ${high_amount_data[1]:.2f}',
            'confidence': 0.92,
            'category': 'risk_assessment'
        })
    
    # Income vs Expense ratio
    c.execute('SELECT SUM(amount) FROM transactions WHERE type = "income"')
    total_income = c.fetchone()[0] or 0
    c.execute('SELECT SUM(amount) FROM transactions WHERE type = "expense"')
    total_expenses = c.fetchone()[0] or 0
    
    if total_income > 0:
        savings_rate = ((total_income - total_expenses) / total_income) * 100
        if savings_rate > 20:
            insights.append({
                'type': 'positive',
                'message': f'🎉 Excellent! Your savings rate is {savings_rate:.1f}%. You\'re doing great!',
                'confidence': 0.98,
                'category': 'savings'
            })
        elif savings_rate > 0:
            insights.append({
                'type': 'moderate',
                'message': f'👍 Your savings rate is {savings_rate:.1f}%. Try to aim for 20% or higher.',
                'confidence': 0.85,
                'category': 'savings'
            })
        else:
            insights.append({
                'type': 'alert',
                'message': f'🚨 You\'re spending more than you earn! Deficit: ${abs(total_income - total_expenses):.2f}',
                'confidence': 0.99,
                'category': 'budget_alert'
            })
    
    conn.close()
    return insights

def generate_financial_predictions():
    """Generate financial predictions using trend analysis"""
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    predictions = []
    
    # Check if we have enough data
    c.execute('SELECT COUNT(*) FROM transactions WHERE type = "expense"')
    expense_count = c.fetchone()[0]
    
    if expense_count < 5:
        predictions.append({
            'type': 'info',
            'message': '📈 Add more transactions to get accurate spending predictions and forecasts.',
            'predicted_amount': 0
        })
        conn.close()
        return predictions
    
    # Get recent spending trend
    c.execute('''SELECT DATE(date) as day, SUM(amount) as daily_total
                 FROM transactions WHERE type = 'expense'
                 AND date >= date('now', '-30 days')
                 GROUP BY DATE(date) ORDER BY day DESC LIMIT 10''')
    recent_daily = c.fetchall()
    
    if len(recent_daily) >= 5:
        amounts = [float(row[1]) for row in recent_daily]
        avg_recent = sum(amounts) / len(amounts)
        
        # Compare with older data
        c.execute('''SELECT AVG(daily_total) FROM (
                        SELECT DATE(date) as day, SUM(amount) as daily_total
                        FROM transactions WHERE type = 'expense'
                        AND date < date('now', '-30 days')
                        GROUP BY DATE(date)
                     )''')
        avg_older = c.fetchone()[0] or avg_recent
        
        if avg_older > 0:
            trend = ((avg_recent - avg_older) / avg_older) * 100
            
            if trend > 15:
                predictions.append({
                    'type': 'warning',
                    'message': f'📈 Spending increased by {trend:.1f}%! Next month prediction: ${avg_recent * 30:.2f}',
                    'predicted_amount': avg_recent * 30
                })
            elif trend < -15:
                predictions.append({
                    'type': 'positive',
                    'message': f'📉 Great! Spending decreased by {abs(trend):.1f}%. Keep it up! Predicted: ${avg_recent * 30:.2f}',
                    'predicted_amount': avg_recent * 30
                })
            else:
                predictions.append({
                    'type': 'stable',
                    'message': f'📊 Spending is stable. Next month prediction: ${avg_recent * 30:.2f}',
                    'predicted_amount': avg_recent * 30
                })
    
    # Category-based predictions
    c.execute('''SELECT category, AVG(amount) * COUNT(*) as monthly_est
                 FROM transactions WHERE type = 'expense'
                 GROUP BY category ORDER BY monthly_est DESC LIMIT 3''')
    top_categories = c.fetchall()
    
    if top_categories:
        for cat, monthly_est in top_categories:
            predictions.append({
                'type': 'category_forecast',
                'message': f'🏷️ {cat.title()}: Expected monthly spending ${monthly_est:.2f}',
                'predicted_amount': monthly_est
            })
    
    conn.close()
    return predictions

def generate_smart_recommendations():
    """Generate personalized financial recommendations"""
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    recommendations = []
    
    # Check if we have data
    c.execute('SELECT COUNT(*) FROM transactions')
    if c.fetchone()[0] == 0:
        recommendations.append({
            'type': 'getting_started',
            'message': '🚀 Start by adding your income and expenses to get personalized recommendations!',
            'potential_savings': 0
        })
        conn.close()
        return recommendations
    
    # Analyze spending categories for optimization
    c.execute('''SELECT category, SUM(amount) as total, COUNT(*) as count
                 FROM transactions WHERE type = 'expense'
                 GROUP BY category ORDER BY total DESC''')
    categories = c.fetchall()
    
    total_expenses = sum(cat[1] for cat in categories)
    
    for category, amount, count in categories[:3]:  # Top 3 categories
        percentage = (amount / total_expenses) * 100 if total_expenses > 0 else 0
        
        if category.lower() in ['entertainment', 'shopping'] and percentage > 25:
            recommendations.append({
                'type': 'savings_opportunity',
                'message': f'💰 {category.title()} takes {percentage:.1f}% of your budget (${amount:.2f}). Reduce by 15% to save ${amount * 0.15:.2f}',
                'potential_savings': amount * 0.15
            })
        elif category.lower() == 'food' and amount / count > 25:
            recommendations.append({
                'type': 'lifestyle',
                'message': f'🍴 Average food expense: ${amount/count:.2f}. Try meal planning to reduce costs by 20%',
                'potential_savings': amount * 0.20
            })
    
    # Income vs expense analysis
    c.execute('SELECT SUM(amount) FROM transactions WHERE type = "income"')
    total_income = c.fetchone()[0] or 0
    
    if total_income > 0:
        savings_rate = ((total_income - total_expenses) / total_income) * 100
        
        if savings_rate < 10:
            recommendations.append({
                'type': 'emergency',
                'message': f'⚠️ Low savings rate ({savings_rate:.1f}%). Try the 50/30/20 rule: 50% needs, 30% wants, 20% savings',
                'monthly_target': total_income * 0.20
            })
        elif savings_rate < 20:
            recommendations.append({
                'type': 'improvement',
                'message': f'📈 Good savings rate ({savings_rate:.1f}%). Aim for 20% to build wealth faster',
                'monthly_target': total_income * 0.20
            })
    
    # Goal-based recommendations
    c.execute('SELECT * FROM goals WHERE current_amount < target_amount')
    active_goals = c.fetchall()
    
    for goal in active_goals:
        remaining = goal[2] - goal[3]  # target - current
        if remaining > 0:
            recommendations.append({
                'type': 'goal_progress',
                'message': f'🎯 Goal: {goal[1]} - Save ${remaining/12:.2f} monthly to reach ${goal[2]:.2f} target',
                'monthly_target': remaining/12
            })
    
    # Smart budgeting tips
    if len(categories) > 0:
        recommendations.append({
            'type': 'budgeting_tip',
            'message': '💡 Pro tip: Use the envelope method - allocate specific amounts for each category and stick to it!',
            'potential_savings': 0
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