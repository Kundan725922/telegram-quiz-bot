import logging
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, error
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random
from collections import defaultdict
import sys
import json # <-- NEW IMPORT

# Check Python version
if sys.version_info >= (3, 13):
    print("⚠️ WARNING: Python 3.13 detected. Telegram bot library works best with Python 3.8-3.12")

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration & Initialization ---
BOT_TOKEN = os.environ.get('BOT_TOKEN') 
QUIZ_DATA_DIR = 'questions' # <-- NEW: Directory for dynamic quiz files

# Define quiz modes and their parameters
QUIZ_MODES = {
    'quick_5': {'num_q': 5, 'timed': False, 'label': "⚡ Quick (5Q)", 'feedback': True},
    'standard_10': {'num_q': 10, 'timed': False, 'label': "📝 Standard (10Q)", 'feedback': True},
    'full_20': {'num_q': 20, 'timed': False, 'label': "🎯 Full Test (20Q)", 'feedback': True},
    'timed_10_300': {'num_q': 10, 'timed': True, 'time_limit': 300, 'label': "⏱️ Timed Challenge (10Q - 5min)", 'feedback': True},
    # Simulation Mode: No immediate feedback, single submission.
    'simulation_20_720': {'num_q': 20, 'timed': True, 'time_limit': 720, 'label': "🧠 Full Simulation (20Q - 12min)", 'feedback': False}
}
TOPICS = ['algorithms', 'data_structures', 'programming', 'toc']

# Global state (In a real application, replace with a database like PostgreSQL or Redis)
leaderboard_data = defaultdict(lambda: {'total_score': 0, 'total_questions': 0, 'tests_taken': 0, 'best_score_pct': 0, 'username': 'N/A', 'user_id': 0})
user_sessions = {} # Active quiz sessions

# --- Question Bank (Retained for functionality) ---
# NOTE: The QUESTIONS dictionary is kept for the /topics command functionality.
QUESTIONS = {
    'algorithms': [
        {'q': 'What is the time complexity of building a heap of n elements?', 'options': ['O(n)', 'O(n log n)', 'O(n²)', 'O(log n)'], 'answer': 0, 'img_url': None},
        {'q': 'Which sorting algorithm is NOT stable?', 'options': ['Merge Sort', 'Quick Sort', 'Insertion Sort', 'Bubble Sort'], 'answer': 1, 'img_url': None},
        {'q': 'Dijkstra algorithm does NOT work correctly with:', 'options': ['Directed graphs', 'Undirected graphs', 'Negative edge weights', 'Weighted graphs'], 'answer': 2, 'img_url': None},
        # ... (rest of algorithms questions)
        {'q': 'Which technique is primarily used by the Knuth-Morris-Pratt (KMP) algorithm?', 'options': ['Dynamic Programming', 'Greedy Approach', 'Divide and Conquer', 'Pre-processing (Longest Proper Prefix Suffix)'], 'answer': 3, 'img_url': None}
    ],
    'data_structures': [
        {'q': 'Best data structure for LRU cache?', 'options': ['Array', 'Stack', 'HashMap + DLL', 'BST'], 'answer': 2, 'img_url': None},
        # ... (rest of data_structures questions)
        {'q': 'What is the worst-case space complexity of a Hash Table using separate chaining?', 'options': ['O(1)', 'O(log n)', 'O(n)', 'O(n²)'], 'answer': 2, 'img_url': None}
    ],
    'programming': [
        {'q': 'Size of pointer on 64-bit system:', 'options': ['4 bytes', '8 bytes', 'Depends', '2 bytes'], 'answer': 1, 'img_url': None},
        # ... (rest of programming questions)
        {'q': 'What is the output of `print(10/3)` in Python 3?', 'options': ['3', '3.333', '3.0', 'Error'], 'answer': 1, 'img_url': None}
    ],
    'toc': [
        {'q': 'DFA accepts which language class?', 'options': ['Context-free', 'Regular', 'Context-sensitive', 'Recursive'], 'answer': 1, 'img_url': None},
        # ... (rest of toc questions)
        {'q': 'Pumping Lemma is generally used for proving that a language is:', 'options': ['Regular', 'Context-Free', 'Not Regular', 'Not Context-Free'], 'answer': 2, 'img_url': None}
    ]
}

# --- Utility Functions ---

def get_all_questions():
    """Compiles all questions from all topics from the hardcoded bank."""
    all_q = []
    for qs in QUESTIONS.values():
        all_q.extend(qs)
    return all_q

# <-- NEW FUNCTIONS FOR DYNAMIC QUIZ LOADING -->

def load_questions_from_file(quiz_id: str) -> list:
    """Loads questions from a JSON file based on the quiz ID."""
    try:
        file_path = os.path.join(QUIZ_DATA_DIR, f'{quiz_id}.json')
        if not os.path.exists(file_path):
            logger.error(f"Quiz file not found: {file_path}")
            # Fallback for demonstration if file system is not available
            return QUESTIONS.get('algorithms', [])[:5] 
            
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading questions for {quiz_id}: {e}")
        return []

def get_available_quizzes() -> dict:
    """Scans the QUIZ_DATA_DIR and returns a dict of available quizzes {quiz_id: label}."""
    available = {}
    try:
        # 1. Ensure the directory exists
        if not os.path.exists(QUIZ_DATA_DIR):
            os.makedirs(QUIZ_DATA_DIR, exist_ok=True)
            
        # 2. Scan the directory
        for filename in os.listdir(QUIZ_DATA_DIR):
            if filename.endswith('.json'):
                quiz_id = filename.replace('.json', '')
                
                # Simple label creation logic:
                label_parts = quiz_id.split('_')
                if label_parts[0] == 'daily':
                    label = f"📅 Daily Quiz ({label_parts[-1]})"
                elif label_parts[0] == 'weekly':
                    label = f"🗓️ Weekly Test {label_parts[-1]}"
                elif label_parts[0] == 'mock':
                    label = f"🧠 Mock Test {label_parts[-1]}"
                else:
                    label = quiz_id.replace('_', ' ').title()
                    
                available[quiz_id] = label
    except Exception as e:
        logger.error(f"Error listing quizzes in {QUIZ_DATA_DIR}: {e}")
        
    # Mock data for initial testing if no files are present
    if not available:
         available = {
            f'daily_{datetime.now().strftime("%Y%m%d")}': "📅 Today's Daily Quiz",
            'mock_test_01': "🧠 Full Mock Test 1",
            'weekly_01': "🗓️ Weekly Test 1",
        }
        
    return available

# <-- END NEW FUNCTIONS -->


def format_time(seconds: float) -> str:
    # ... (rest of format_time remains the same)
    """Formats seconds into MM:SS string."""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

async def send_message_robust(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, reply_markup=None):
    # ... (rest of send_message_robust remains the same)
    """Sends a message, handling common Telegram API errors."""
    try:
        return await context.bot.send_message(
            chat_id=chat_id, 
            text=text, 
            reply_markup=reply_markup, 
            parse_mode='HTML' # Using HTML for links and bold/italic
        )
    except error.TelegramError as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = f"""🎓 <b>Welcome {user.first_name} to GATE CSE Quiz Bot!</b>
Ready to test your knowledge? Choose a quiz mode or a specific topic!

📚 <b>Commands:</b>
/quiz - Select your challenge mode (Quick, Timed, Simulation)
/tests - Select a specific daily, weekly, or mock test <--- NEW COMMAND
/topics - Focus on a specific subject
/leaderboard - Top 10 rankers globally
/mystats - Your personalized analytics
/help - Complete guide and info

Start your preparation now! 🚀"""
    await update.message.reply_text(text, parse_mode='HTML')

# <-- NEW COMMAND HANDLER -->
async def special_tests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of available date-wise, mock, or weekly quizzes."""
    available = get_available_quizzes()
    
    if not available:
        await update.message.reply_text("⚠️ No special quizzes found. Try /quiz for a standard test.", parse_mode='HTML')
        return

    keyboard = [[InlineKeyboardButton(label, callback_data=f'quiz_start_{quiz_id}')] 
                for quiz_id, label in available.items()]
    
    await update.message.reply_text(
        "📅 <b>Select a Special Test:</b>\n\nChoose from daily, mock, or other date-based tests:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
# <-- END NEW COMMAND HANDLER -->

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (rest of quiz command handler remains the same)
    """Show quiz mode selection"""
    keyboard = [[InlineKeyboardButton(mode_data['label'], callback_data=f'mode_select_{mode_key}')] 
                for mode_key, mode_data in QUIZ_MODES.items()]
    
    keyboard.append([InlineKeyboardButton("➡️ Choose Topic Instead", callback_data='topics_redirect')]) 
    
    await update.message.reply_text(
        "🎮 <b>Select Quiz Mode:</b>\n\nChoose difficulty and type:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (rest of topics command handler remains the same)
    """Show topic selection"""
    keyboard = [
        [InlineKeyboardButton("🔢 Algorithms (10Q)", callback_data='topic_select_algorithms')],
        [InlineKeyboardButton("📊 Data Structures (10Q)", callback_data='topic_select_data_structures')],
        [InlineKeyboardButton("💻 Programming (10Q)", callback_data='topic_select_programming')],
        [InlineKeyboardButton("🔤 TOC (10Q)", callback_data='topic_select_toc')],
        [InlineKeyboardButton("🎲 Random Mix (10Q)", callback_data='topic_select_random')]
    ]
    await update.message.reply_text('📚 <b>Choose Topic:</b>', reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
# ... (leaderboard_handler, mystats, help_command remain the same)


# --- Callback Query Handlers ---

async def mode_or_topic_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles mode, topic, AND special quiz selection from their respective menus."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    user_id = user.id
    data = query.data
    selected_questions_list = [] # Initialize question list

    if data == 'topics_redirect':
        await topics(update, context)
        return

    # --- NEW LOGIC: Special Quiz Selection (/tests command) ---
    if data.startswith('quiz_start_'):
        quiz_id = data.split('_start_')[1]
        selected_questions_list = load_questions_from_file(quiz_id) # Use the dynamic loader
        
        # Determine quiz parameters for the special test
        num_q = len(selected_questions_list)
        # Apply standard settings for mock tests (e.g., simulation_20_720) 
        # but adjust based on question count
        config = QUIZ_MODES.get('simulation_20_720', QUIZ_MODES['full_20']) 
        is_timed = config['timed']
        time_limit = config.get('time_limit')
        mode = quiz_id # Use the quiz_id as the mode identifier
        instant_feedback = config['feedback']
        
    # --- EXISTING LOGIC: Mode/Topic Selection (/quiz or /topics command) ---
    elif data.startswith('mode_select_') or data.startswith('topic_select_'):
        data = data.split('_select_')[1]
        
        # 1. Determine Quiz Parameters (Restored logic)
        num_q = 0
        is_timed = False
        time_limit = None
        mode = data
        instant_feedback = True 

        if data in QUIZ_MODES: # Mode selection
            config = QUIZ_MODES[data]
            num_q = config['num_q']
            is_timed = config['timed']
            time_limit = config.get('time_limit')
            instant_feedback = config['feedback']
        
        elif data in TOPICS or data == 'random': # Topic selection (defaults to 10 questions, non-timed)
            num_q = 10 
            is_timed = False
            time_limit = None
            mode = f'topic_{data}'
            instant_feedback = True
        
        # 2. Select Questions from hardcoded bank (Restored logic)
        if data == 'random' or data in QUIZ_MODES:
            all_q = get_all_questions()
            selected_questions_list = random.sample(all_q, min(num_q, len(all_q)))
        else: # Specific topic
            selected_questions_list = QUESTIONS.get(data, []).copy()
            random.shuffle(selected_questions_list)
            selected_questions_list = selected_questions_list[:num_q]
    
    # --- Final Check & Session Initialization ---
    if not selected_questions_list:
        await query.edit_message_text("⚠️ Not enough questions available for this selection. Try another quiz or topic.", parse_mode='HTML')
        return

    # 3. Initialize Session
    if user_id in user_sessions:
        if user_sessions[user_id].get('timer_task'):
            user_sessions[user_id]['timer_task'].cancel()
        logger.info(f"User {user_id} started a new quiz, cancelling old session.")

    user_sessions[user_id] = {
        'questions': selected_questions_list,
        'current': 0,
        'score': 0,
        'answers': [None] * len(selected_questions_list), 
        'is_timed': is_timed,
        'time_limit': time_limit,
        'start_time': datetime.now(),
        'mode': mode,
        'chat_id': query.message.chat_id,
        'instant_feedback': instant_feedback
    }
    
    # ... (rest of session setup, including leaderboard_data, text construction, and starting timer/question sending)

    leaderboard_data[user_id]['username'] = user.username or user.first_name
    leaderboard_data[user_id]['user_id'] = user_id

    text = f"🎯 <b>Quiz Started!</b>\n\n"
    text += f"📝 Questions: {len(selected_questions_list)}\n"
    if is_timed:
        text += f"⏱️ Time Limit: {time_limit//60} minutes ({time_limit} seconds)\n"
    if not instant_feedback:
        text += "⚠️ <b>Simulation Mode:</b> No immediate feedback. You will submit all answers at the end.\n"
    text += f"\nGet ready! 💪"
    
    try:
        await query.edit_message_text(text, parse_mode='HTML')
    except error.BadRequest:
        pass 
    
    # 4. Start Timer and Send First Question
    if is_timed:
        task = asyncio.create_task(quiz_timer(user_id, context, time_limit, query.message.chat_id))
        user_sessions[user_id]['timer_task'] = task
        
    await send_question(query.message, context, user_id)

# ... (quiz_timer, send_question, handle_answer, post_quiz_action, finalize_quiz remain the same)


# --- Main Application Setup ---

def main():
    """Main function - optimized for deployment"""
    # Check if the required BOT_TOKEN environment variable is present
    if not BOT_TOKEN:
        logger.error("❌ ERROR: The BOT_TOKEN environment variable is not set. The application cannot start.")
        return

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .build()
    )
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("tests", special_tests)) # <-- NEW COMMAND REGISTERED
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(CommandHandler("leaderboard", leaderboard_handler))
    app.add_handler(CommandHandler("mystats", mystats))
    app.add_handler(CommandHandler("help", help_command))
    
    # Callback handlers
    # Unified handler for all quiz selection logic (mode_select_, topic_select_, quiz_start_)
    app.add_handler(CallbackQueryHandler(mode_or_topic_selected, pattern='^mode_select_|^topic_select_|^quiz_start_')) # <-- UPDATED PATTERN
    # Answer and Navigation handler
    app.add_handler(CallbackQueryHandler(handle_answer, pattern='^answer_submit_|^quiz_submit_final|^quiz_nav_'))
    # Post-Quiz action handler
    app.add_handler(CallbackQueryHandler(post_quiz_action, pattern='^post_quiz_action_'))
    
    print("🤖 Bot starting...")
    
    # Deployment Logic
    if os.environ.get('RENDER'):
        port = int(os.environ.get('PORT', 8080))
        webhook_url = os.environ.get('RENDER_EXTERNAL_URL')
        
        if not webhook_url:
            logger.error("❌ ERROR: RENDER_EXTERNAL_URL environment variable is missing for webhook setup.")
            return

        if webhook_url.endswith('/'): webhook_url = webhook_url[:-1]
        final_webhook_url = f"{webhook_url}/{BOT_TOKEN}" 

        print(f"✅ Webhook mode active. Listening on port {port}.")
        
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN,
            webhook_url=final_webhook_url
        )
    else:
        print("✅ Polling mode active (Local Dev). Press Ctrl+C to stop.")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    # Ensure the directory for new quizzes exists before starting the bot
    os.makedirs(QUIZ_DATA_DIR, exist_ok=True)
    main()
