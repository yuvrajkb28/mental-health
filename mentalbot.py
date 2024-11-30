import requests
from datetime import datetime, timedelta
import uuid
import base64
from functools import lru_cache

class MentalBot:
    def __init__(self, assistant_api_key, assistant_url, watsonx_api_key, project_id):
        # Watson Assistant setup
        self.assistant_api_key = assistant_api_key
        self.assistant_id = "f0a129de-9ce7-4270-962c-a858accbf8e9"
        self.assistant_url = assistant_url
        self.version = "2023-05-29"
        self.assistant_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {self._get_base64_auth()}'
        }
        
        # WatsonX setup
        self.watsonx_api_key = watsonx_api_key
        self.project_id = project_id
        self.watsonx_token = self._get_iam_token()
        
        # Custom session management
        self.sessions = {}
        self.session_timeout = timedelta(minutes=30)

    def _get_base64_auth(self):
        """Get base64 encoded auth for Assistant"""
        auth_string = f"apikey:{self.assistant_api_key}"
        return base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

    def _get_iam_token(self):
        """Get IAM token for WatsonX"""
        iam_url = "https://iam.cloud.ibm.com/identity/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": self.watsonx_api_key
        }
        
        response = requests.post(iam_url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            raise Exception(f"Failed to get IAM token: {response.text}")

    def _create_session(self):
        """Create a new session with context"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'created_at': datetime.now(),
            'last_accessed': datetime.now(),
            'context': {},
            'conversation_history': []
        }
        return session_id

    def _get_or_create_session(self, session_id=None):
        """Get existing session or create new one"""
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            if datetime.now() - session['last_accessed'] < self.session_timeout:
                session['last_accessed'] = datetime.now()
                return session_id
        return self._create_session()

    def get_assistant_intent(self, user_input):
        """Get intent from Watson Assistant"""
        message_url = f"{self.assistant_url}/v2/assistants/{self.assistant_id}/message?version={self.version}"
        message_data = {
            "input": {
                "text": user_input
            }
        }
        
        try:
            response = requests.post(message_url, headers=self.assistant_headers, json=message_data)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Assistant error: {str(e)}")
            return None

    def get_model_response(self, user_input, conversation_history):
        """Get response from WatsonX model with enhanced mental health prompting"""
        
        # Enhanced mental health focused prompt
        prompt = f"""\"Offer personalized, empathetic, and achievable solutions for users facing mental health challenges, ensuring responses are compassionate and provide actionable advice.\"

Input: \"I've been feeling really overwhelmed and can't focus on my tasks.\"  
Output: \"It's okay to feel overwhelmed. Start by taking a few moments to step away and breathe deeply. Breaking your tasks into smaller, manageable steps might help you regain focus. I can guide you through a simple prioritization exercise if you'd like.\"  

Input: \"I keep doubting my abilities and feel like I'm not good enough.\"  
Output: \"Self-doubt can be hard to face, but it doesn't define you. Reflect on moments where you overcame challenges—that's evidence of your capabilities. If you'd like, I can suggest ways to build your confidence gradually.\"  

Input: \"I feel disconnected from everyone and don't know how to fix it.\"  
Output: \"Feeling disconnected can be isolating, but small steps can help rebuild connections. Reaching out to a trusted friend for a short conversation or engaging in a group activity can make a difference. Let me know if you'd like suggestions for activities or conversation starters.\"  

Input: \"I think I need a break, but I don't know how to justify it to my team.\"  
Output: \"Taking a break is essential for your well-being. You could frame it to your team as a way to recharge and bring your best self to work. I can help you draft a supportive message to explain this to them if you'd like.\"  

Previous Context: {' '.join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-2:]])}

Input: \"{user_input}\"
Output:\"
"""

        url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"
        body = {
            "input": prompt,
            "parameters": {
                "decoding_method": "greedy",
                "max_new_tokens": 200,
                "stop_sequences": ["\n\n", "Input:", "Output:", "\""],
                "repetition_penalty": 1.2
            },
            "model_id": "meta-llama/llama-3-1-8b-instruct",
            "project_id": self.project_id,
            "moderations": {
                "hap": {
                    "input": {
                        "enabled": True,
                        "threshold": 0.5,
                        "mask": {
                            "remove_entity_value": True
                        }
                    },
                    "output": {
                        "enabled": True,
                        "threshold": 0.5,
                        "mask": {
                            "remove_entity_value": True
                        }
                    }
                },
                "pii": {
                    "input": {
                        "enabled": True,
                        "threshold": 0.5,
                        "mask": {
                            "remove_entity_value": True
                        }
                    },
                    "output": {
                        "enabled": True,
                        "threshold": 0.5,
                        "mask": {
                            "remove_entity_value": True
                        }
                    }
                }
            }
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.watsonx_token}"
        }

        try:
            response = requests.post(url, headers=headers, json=body)
            
            if response.status_code == 200:
                return response.json()['results'][0]['generated_text'].strip()
            elif response.status_code == 401:
                # Refresh token and retry
                self.watsonx_token = self._get_iam_token()
                headers["Authorization"] = f"Bearer {self.watsonx_token}"
                response = requests.post(url, headers=headers, json=body)
                if response.status_code == 200:
                    return response.json()['results'][0]['generated_text'].strip()
            return None
        except Exception as e:
            print(f"Model error: {str(e)}")
            return None

    def chat(self, user_input, session_id=None):
        """Main chat function combining Assistant and Model"""
        # Get or create session
        session_id = self._get_or_create_session(session_id)
        session = self.sessions[session_id]
        
        # Update conversation history with user input
        session['conversation_history'].append({"role": "user", "content": user_input})
        
        # Get intent from Assistant
        assistant_response = self.get_assistant_intent(user_input)
        
        # Check if we need model response based on intent
        needs_model_response = False
        if assistant_response:
            # Check for specific intents that need model response
            if "action_3200_intent_45093-2" in str(assistant_response):
                needs_model_response = True
        else:
            # Fallback to model if Assistant fails
            needs_model_response = True
        
        if needs_model_response:
            # Get model response
            model_response = self.get_model_response(user_input, session['conversation_history'])
            if model_response:
                # Update conversation history with model's response
                session['conversation_history'].append({"role": "assistant", "content": model_response})
                return {
                    'response': model_response,
                    'session_id': session_id,
                    'source': 'model'
                }
        elif assistant_response and 'output' in assistant_response:
            # Use Assistant response
            assistant_text = assistant_response['output']['generic'][0]['text']
            session['conversation_history'].append({"role": "assistant", "content": assistant_text})
            return {
                'response': assistant_text,
                'session_id': session_id,
                'source': 'assistant'
            }
        
        # Fallback response
        fallback = "I apologize, but I'm having trouble generating a response."
        session['conversation_history'].append({"role": "assistant", "content": fallback})
        return {
            'response': fallback,
            'session_id': session_id,
            'source': 'fallback'
        }

@lru_cache(maxsize=1)
def get_bot_instance():
    """Creates or returns a cached instance of MentalBot"""
    return MentalBot(
        assistant_api_key="5nyZwrMVF9SoZEgd8gB06N9OwxFDM4e1MuiwM_ZKYHe5",
        assistant_url="https://api.jp-tok.assistant.watson.cloud.ibm.com/instances/07a350a3-5dd5-4ca6-94fd-5858ef362bd7",
        watsonx_api_key="n3CRX50da1UclUgJEWreZE2-Zyko9lcssh-NNGwD5VXG",
        project_id="caed8c8a-e950-41bd-8fd3-e0b4f6572936"
    )

def chat_with_bot(message):
    """Handle chat interactions with the bot"""
    bot = get_bot_instance()
    return bot.chat(message) 