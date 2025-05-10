from flask import Flask, render_template, request, jsonify
from business_analyst_agent import BusinessAnalystAgent
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
agent = BusinessAnalystAgent()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    response = agent._process_input(user_message)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True) 