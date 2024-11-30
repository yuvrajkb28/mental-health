import streamlit as st
from mentalbot import chat_with_bot
from datetime import datetime

# CSS specific to the Chat page
chat_css = """
<style>
/* Fixed header */
.header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: white;
    padding: 0.1rem;
    z-index: 100;
    border-bottom: 1px solid #eee;
    text-align: center;
    font-weight: bold;
    font-size: 1.2rem;
}

/* Messages container */
.messages-container {
    max-height: 350px;
    margin-top: 70px;  /* Space for header */
    margin-bottom: 60px;  /* Space for input */
    overflow-y: auto;
    padding: 1rem;
}

/* Message styling */
.chat-message {
    padding: 0.8rem;
    border-radius: 0.5rem;
    margin-bottom: 0.5rem;
    max-width: 70%;
    display: flex;
    flex-direction: column;
}

.user-message {
    background-color: #e6f3ff;
    border-left: 3px solid #2b6cb0;
    margin-left: auto;
}

.bot-message {
    background-color: #f0f0f0;
    border-left: 3px solid #718096;
    margin-right: auto;
}

.message-timestamp {
    font-size: 0.7rem;
    color: #666;
    margin-top: 0.3rem;
    text-align: right;
}

/* Fixed input container */
.input-container {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 0.5rem;
    background: white;
    border-top: 1px solid #eee;
    z-index: 100;
}

.typing-indicator {
    color: #666;
    font-size: 0.9rem;
    padding: 0.5rem;
    font-style: italic;
}

/* Hide Streamlit elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Additional spacing fixes */
.stTextInput {
    margin: 0 !important;
    padding: 0 !important;
}

.stButton {
    margin: 0 !important;
    padding: 0 !important;
}
</style>
"""

# Navigation options
pages = ["Home", "Chat"]
selected_page = st.sidebar.radio("Navigate", pages)

# Home Page
if selected_page == "Home":
    st.header("Welcome to the Mental Health AI Chat Assistant!")
    st.write(
        """
        This assistant is here to help you with mental health resources and provide a supportive conversational AI.
        Navigate to the **Chat** section to start a conversation.
        """
    )

# Chat Page
elif selected_page == "Chat":
    st.markdown(chat_css, unsafe_allow_html=True)
    
    # Fixed header
    st.markdown('<div class="header">Mental Health AI Assistant</div>', unsafe_allow_html=True)
    
    # Initialize session states
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'session_id' not in st.session_state:
        st.session_state.session_id = None
    if 'is_typing' not in st.session_state:
        st.session_state.is_typing = False
    if 'needs_rerun' not in st.session_state:
        st.session_state.needs_rerun = False

    # Initialize the container first
    messages_container = st.container()
    
    # Function to update messages
    def update_messages():
        with messages_container:
            st.markdown('<div class="messages-container">', unsafe_allow_html=True)
            for message in st.session_state.chat_history:
                message_time = message.get('timestamp', datetime.now().strftime("%H:%M"))
                
                if message['role'] == 'user':
                    st.markdown(f"""
                        <div class="chat-message user-message">
                            <div>{message['content']}</div>
                            <div class="message-timestamp">{message_time}</div>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div class="chat-message bot-message">
                            <div>{message['content']}</div>
                            <div class="message-timestamp">{message_time}</div>
                        </div>
                    """, unsafe_allow_html=True)
            
            # Show typing indicator only when needed
            if st.session_state.is_typing:
                st.markdown("""
                    <div class="chat-message bot-message typing-indicator">
                        Assistant is typing...
                    </div>
                """, unsafe_allow_html=True)
                
            st.markdown('</div>', unsafe_allow_html=True)

    # Check if rerun is needed at the top level
    if st.session_state.needs_rerun:
        st.session_state.needs_rerun = False
        st.rerun()
    
    # Call update_messages to show the chat history
    update_messages()
    
    # Message processing function
    def process_message():
        if st.session_state.user_input.strip():
            user_message = st.session_state.user_input.strip()
            
            # Add user message
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_message,
                'timestamp': datetime.now().strftime("%H:%M")
            })
            st.session_state.user_input = ""
            
            try:
                # Get bot response
                response = chat_with_bot(user_message)
                
                # Update session ID if present
                if 'session_id' in response:
                    st.session_state.session_id = response['session_id']
                
                # Safely extract the bot's response
                bot_response = response.get('response', "I apologize, but I couldn't process that properly.")
                
                # Add bot response to chat history
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': bot_response,
                    'timestamp': datetime.now().strftime("%H:%M")
                })
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                # Add error message to chat history
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': "I'm sorry, but I encountered an error. Please try again.",
                    'timestamp': datetime.now().strftime("%H:%M")
                })
            finally:
                # Set flag for rerun instead of calling rerun directly
                st.session_state.needs_rerun = True

    # Input container
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    col1, col2 = st.columns([6,1])
    
    with col1:
        st.text_input("",
                     placeholder="Type your message here... (Press Enter to send)",
                     key="user_input",
                     on_change=process_message)
    
    with col2:
        if st.button("Send"):
            process_message()
    
    st.markdown('</div>', unsafe_allow_html=True)
