import logging
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, error
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random
from collections import defaultdict
import sys
import json

# Check Python version
if sys.version_info >= (3, 13):
    print("⚠️ WARNING: Python 3.13 detected. Telegram bot library works best with Python 3.8-3.12")

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration & Initialization ---
BOT_TOKEN = os.environ.get('BOT_TOKEN') 
# QUIZ_DATA_DIR must be the top-level folder where all quizzes and subfolders are kept
QUIZ_DATA_DIR = 'questions' 

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

# --- Question Bank (Retained for functionality of /topics command) ---
QUESTIONS = {
    'algorithms': [
        {'q': 'What is the time complexity of building a heap of n elements?', 'options': ['O(n)', 'O(n log n)', 'O(n²)', 'O(log n)'], 'answer': 0, 'img_url': None},
        {'q': 'Which sorting algorithm is NOT stable?', 'options': ['Merge Sort', 'Quick Sort', 'Insertion Sort', 'Bubble Sort'], 'answer': 1, 'img_url': None},
        {'q': 'Dijkstra algorithm does NOT work correctly with:', 'options': ['Directed graphs', 'Undirected graphs', 'Negative edge weights', 'Weighted graphs'], 'answer': 2, 'img_url': None},
        {'q': 'The complexity of n^(log n) is asymptotically greater than which of the following: n, 80, (log(log n))^2, (log n)^(log n)?', 'options': ['All of them', 'Only n', 'Only 80 and n', 'Only (log n)^(log n)'], 'answer': 0, 'img_url': None}
    ],
    'data_structures': [
        {'q': 'Best data structure for LRU cache?', 'options': ['Array', 'Stack', 'HashMap + DLL', 'BST'], 'answer': 2, 'img_url': None},
        {'q': 'What is the worst-case space complexity of a Hash Table using separate chaining?', 'options': ['O(1)', 'O(log n)', 'O(n)', 'O(n²)'], 'answer': 2, 'img_url': None}
    ],
    'programming': [
        {'q': 'Size of pointer on 64-bit system:', 'options': ['4 bytes', '8 bytes', 'Depends', '2 bytes'], 'answer': 1, 'img_url': None},
        {'q': 'What is the output of print(10/3) in Python 3?', 'options': ['3', '3.333', '3.0', 'Error'], 'answer': 1, 'img_url': None}
    ],
    'toc': [
        {'q': 'DFA accepts which language class?', 'options': ['Context-free', 'Regular', 'Context-sensitive', 'Recursive'], 'answer': 1, 'img_url': None},
        {'q': 'Pumping Lemma is generally used for proving that a language is:', 'options': ['Regular', 'Context-Free', 'Not Regular', 'Not Context-Free'], 'answer': 2, 'img_url': None}
    ]
}

# --- Utility Functions (Updated for recursive folder scan) ---

def get_all_questions():
    """Compiles all questions from all topics from the hardcoded bank."""
    all_q = []
    for qs in QUESTIONS.values():
        all_q.extend(qs)
    return all_q

def load_questions_from_file(quiz_id: str) -> list:
    """
    Loads questions from a JSON file using the full relative path stored in quiz_id.
    quiz_id is now the path, e.g., 'subject_wise/algorithm/algorithms_dpp_01_discussion'.
    """
    try:
        # NOTE: quiz_id is the path relative to QUIZ_DATA_DIR, file_path now resolves subfolders
        file_path = os.path.join(QUIZ_DATA_DIR, f'{quiz_id}.json')
        
        if not os.path.exists(file_path):
            logger.error(f"Quiz file not found: {file_path}")
            # Fallback for demonstration
            return QUESTIONS.get('algorithms', [])[:5] 
            
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading questions for {quiz_id}: {e}")
        return []

def get_available_quizzes() -> dict:
    """
    Scans the QUIZ_DATA_DIR and all subdirectories recursively using os.walk.
    Returns a dict of available quizzes {relative_path_id: label}.
    """
    available = {}
    try:
        if not os.path.exists(QUIZ_DATA_DIR):
            os.makedirs(QUIZ_DATA_DIR, exist_ok=True)
            
        # 2. Recursive Scan
        for root, dirs, files in os.walk(QUIZ_DATA_DIR):
            for filename in files:
                if filename.endswith('.json'):
                    full_path = os.path.join(root, filename)
                    
                    # Create the relative path ID (e.g., 'subject wise/algorithm/quiz_name')
                    # We strip QUIZ_DATA_DIR/ and the .json extension
                    relative_path = os.path.relpath(full_path, QUIZ_DATA_DIR)
                    quiz_id = relative_path[:-5] # Remove '.json'
                    
                    # 3. Create a User-Friendly Label
                    # Use os.path.sep to ensure cross-platform compatibility
                    parts = quiz_id.replace(os.path.sep, ' - ').split(' - ')
                    
                    # Use up to the last three parts for a concise label
                    display_parts = parts[-3:]
                    
                    # Capitalize and make it readable
                    label = " | ".join([p.replace('_', ' ').title() for p in display_parts])
                    
                    # Prepend an icon based on the top-level folder
                    top_folder = parts[0].lower()
                    if 'mock' in top_folder:
                         label = "🧠 " + label
                    elif 'pyqs' in top_folder:
                         label = "📖 " + label
                    elif 'subject' in top_folder:
                         label = "📚 " + label # Using '📚' for subject wise
                    else:
                         label = "📝 " + label
                        
                    available[quiz_id] = label

    except Exception as e:
        logger.error(f"Error listing quizzes in {QUIZ_DATA_DIR}: {e}")
        
    # Mock data for initial testing if no files are present
    if not available:
         available = {
             f'daily_{datetime.now().strftime("%Y%m%d")}': "📅 Today's Daily Quiz (Mock)",
         }
        
    return available

def format_time(seconds: float) -> str:
    """Formats seconds into MM:SS string."""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

async def send_message_robust(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, reply_markup=None):
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
        return None


# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = f"""🎓 <b>Welcome {user.first_name} to GATE CSE Quiz Bot!</b>
Ready to test your knowledge? Choose a quiz mode or a specific topic!

📚 <b>Commands:</b>
/quiz - Select your challenge mode (Quick, Timed, Simulation)
/tests - Select a specific daily, weekly, or mock test (Includes subfolders!)
/topics - Focus on a specific subject
/leaderboard - Top 10 rankers globally
/mystats - Your personalized analytics
/help - Complete guide and info

Start your preparation now! 🚀"""
    await update.message.reply_text(text, parse_mode='HTML')

async def special_tests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of available date-wise, mock, or weekly quizzes found in subfolders."""
    available = get_available_quizzes()
    
    if not available:
        await update.message.reply_text("⚠️ No special quizzes found in the 'questions' folder or its subfolders. Try /quiz for a standard test.", parse_mode='HTML')
        return

    # Sort available quizzes alphabetically by label for a cleaner UI
    sorted_quizzes = sorted(available.items(), key=lambda item: item[1])
    
    keyboard = [[InlineKeyboardButton(label, callback_data=f'quiz_start_{quiz_id}')] 
                for quiz_id, label in sorted_quizzes]
    
    await update.message.reply_text(
        "📅 <b>Select a Special Test:</b>\n\nQuizzes found in subfolders (Mock, PYQs, Subject Wise):",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    """Show topic selection"""
    keyboard = [
        [InlineKeyboardButton("🔢 Algorithms (10Q)", callback_data='topic_select_algorithms')],
        [InlineKeyboardButton("📊 Data Structures (10Q)", callback_data='topic_select_data_structures')],
        [InlineKeyboardButton("💻 Programming (10Q)", callback_data='topic_select_programming')],
        [InlineKeyboardButton("🔤 TOC (10Q)", callback_data='topic_select_toc')],
        [InlineKeyboardButton("🎲 Random Mix (10Q)", callback_data='topic_select_random')]
    ]
    await update.message.reply_text('📚 <b>Choose Topic:</b>', reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    

# --- Command Handler Definitions ---

async def leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the leaderboard."""
    sorted_board = sorted(leaderboard_data.items(), key=lambda x: x[1]['best_score_pct'], reverse=True)[:10]
    
    if not sorted_board:
        text = "🏆 **Global Leaderboard**\n\nNo scores recorded yet! Start a quiz with /quiz."
    else:
        text = "🏆 <b>Top 10 Global Rankers:</b>\n\n"
        for i, (user_id, data) in enumerate(sorted_board):
            text += f"{i+1}. <b>{data['username']}</b>: {data['best_score_pct']:.1f}% ({data['tests_taken']} tests)\n"

    await update.message.reply_text(text, parse_mode='HTML')


async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's personal statistics."""
    user_id = update.effective_user.id
    stats = leaderboard_data[user_id]
    
    if stats['tests_taken'] == 0:
        text = "📊 <b>Your Statistics</b>\n\nNo tests taken yet! Start your first quiz with /quiz."
    else:
        avg_score = stats['total_score'] / stats['total_questions'] * 100 if stats['total_questions'] > 0 else 0
        text = f"👤 <b>{stats['username']}'s Performance Report</b>\n\n"
        text += f"Total Quizzes Taken: <b>{stats['tests_taken']}</b>\n"
        text += f"Total Questions Attempted: <b>{stats['total_questions']}</b>\n"
        text += f"Total Correct Answers: <b>{stats['total_score']}</b>\n"
        text += f"Overall Average Score: <b>{avg_score:.1f}%</b>\n"
        text += f"Best Score Percentage: <b>{stats['best_score_pct']:.1f}%</b>\n"

    await update.message.reply_text(text, parse_mode='HTML')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help message."""
    await start(update, context) # Re-use start message as a simple help response

# --- Internal Quiz Logic ---

async def quiz_timer(user_id: int, context: ContextTypes.DEFAULT_TYPE, time_limit: int, chat_id: int) -> None:
    """The timer function for timed quizzes."""
    session = user_sessions.get(user_id)
    if not session: return

    end_time = session['start_time'] + timedelta(seconds=time_limit)
    
    # Send a one-minute warning
    await asyncio.sleep(time_limit - 60)
    if not session.get('is_finished') and session.get('timer_task'):
        await send_message_robust(context, chat_id, "⏰ **ONE MINUTE REMAINING!** Submit your answers soon.")
        
    # Wait for the remaining time
    await asyncio.sleep(60)
    
    # Time's up!
    if not session.get('is_finished') and session.get('timer_task'):
        logger.info(f"User {user_id} quiz timed out.")
        await finalize_quiz(user_id, context, timed_out=True)


async def send_question(message, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Sends the current question to the user."""
    session = user_sessions.get(user_id)
    if not session or session.get('is_finished'):
        return

    q_index = session['current']
    questions = session['questions']
    
    if q_index >= len(questions):
        await finalize_quiz(user_id, context)
        return

    q_data = questions[q_index]
    
    # 1. Build the question text
    header = f"❓ **Question {q_index + 1}/{len(questions)}**\n"
    if session['is_timed']:
        elapsed = (datetime.now() - session['start_time']).total_seconds()
        remaining = session['time_limit'] - elapsed
        time_display = f"⏱️ Time Left: {format_time(max(0, remaining))}\n"
        header = f"**{time_display}**" + header
        
    question_text = f"{header}\n{q_data['q']}"

    # 2. Build the keyboard
    keyboard = []
    for i, option in enumerate(q_data['options']):
        # Mark selected answer if exists
        prefix = "✅ " if session['answers'][q_index] == i else ""
        keyboard.append([InlineKeyboardButton(f"{prefix}{chr(65+i)}. {option}", callback_data=f'answer_submit_{i}')])
        
    # Navigation buttons
    nav_buttons = []
    if q_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data='quiz_nav_prev'))
    if q_index < len(questions) - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data='quiz_nav_next'))
    keyboard.append(nav_buttons)
    
    # Final Submission Button
    keyboard.append([InlineKeyboardButton("🏁 **SUBMIT FINAL ANSWERS** 🏁", callback_data='quiz_submit_final')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # 3. Send/Edit Message
    try:
        await message.edit_text(question_text, reply_markup=reply_markup, parse_mode='HTML')
    except error.BadRequest:
        logger.info(f"Attempted to edit message with identical content for user {user_id}.")


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles user's answer submission and navigation via inline keyboard."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    session = user_sessions.get(user_id)
    
    if not session or session.get('is_finished'):
        await query.edit_message_text("❌ Quiz is finished or invalid session. Start a new one with /quiz.", parse_mode='HTML')
        return

    data = query.data
    q_index = session['current']
    questions = session['questions']
    
    # Handle Navigation
    if data == 'quiz_nav_prev':
        session['current'] = max(0, q_index - 1)
        await send_question(query.message, context, user_id)
        return
    elif data == 'quiz_nav_next':
        session['current'] = min(len(questions) - 1, q_index + 1)
        await send_question(query.message, context, user_id)
        return
    elif data == 'quiz_submit_final':
        await finalize_quiz(user_id, context)
        return

    # Handle Answer Submission
    if data.startswith('answer_submit_'):
        try:
            selected_option = int(data.split('_')[-1])
        except ValueError:
            return

        session['answers'][q_index] = selected_option
        
        # Immediate Feedback Logic (Only if not in Simulation Mode)
        if session['instant_feedback']:
            correct_answer = questions[q_index]['answer']
            if selected_option == correct_answer:
                feedback = "✅ **Correct Answer!** Moving to the next question."
            else:
                feedback = f"❌ **Incorrect!** The correct answer was option {chr(65+correct_answer)}."
            
            await send_message_robust(context, user_id, feedback)
            
            # Automatically advance to the next question
            session['current'] = min(len(questions), q_index + 1)
        
        # Re-render the question (or the next one)
        await send_question(query.message, context, user_id)


async def finalize_quiz(user_id: int, context: ContextTypes.DEFAULT_TYPE, timed_out=False) -> None:
    """Calculates final score and updates the leaderboard."""
    session = user_sessions.get(user_id)
    if not session: return

    # 1. Mark as finished and cancel timer
    session['is_finished'] = True
    if session.get('timer_task'):
        session['timer_task'].cancel()
        session['timer_task'] = None

    # 2. Calculate Score
    final_score = 0
    total_q = len(session['questions'])
    for q_data, user_ans in zip(session['questions'], session['answers']):
        if user_ans == q_data['answer']:
            final_score += 1
            
    score_pct = (final_score / total_q) * 100 if total_q > 0 else 0
    time_taken = (datetime.now() - session['start_time']).total_seconds()
    
    # 3. Update Global Stats (leaderboard_data)
    stats = leaderboard_data[user_id]
    stats['total_score'] += final_score
    stats['total_questions'] += total_q
    stats['tests_taken'] += 1
    stats['best_score_pct'] = max(stats['best_score_pct'], score_pct)

    # 4. Final Message
    status_text = "⚠️ **TIME UP!** Your quiz has automatically submitted." if timed_out else "✅ **Quiz Complete!**"
    
    result_text = f"🎉 **{status_text}**\n\n"
    result_text += f"🎯 Mode: **{session['mode'].replace('_', ' ').title()}**\n"
    result_text += f"✅ Correct Answers: **{final_score} / {total_q}**\n"
    result_text += f"💯 Score: **{score_pct:.1f}%**\n"
    result_text += f"⏱️ Time Taken: **{format_time(time_taken)}**"

    keyboard = [
        [InlineKeyboardButton("👀 Review Answers", callback_data='post_quiz_action_review')],
        [InlineKeyboardButton("🆕 Start New Quiz", callback_data='post_quiz_action_new')]
    ]
    
    # 5. Send results and clean up
    await send_message_robust(context, session['chat_id'], result_text, reply_markup=InlineKeyboardMarkup(keyboard))
    del user_sessions[user_id] # Clean up session


async def post_quiz_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles actions after a quiz is finished (e.g., review, new quiz)."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'post_quiz_action_new':
        await quiz(update, context)
        try:
            await query.delete_message()
        except error.BadRequest:
             pass # Can't delete, ignore
    elif data == 'post_quiz_action_review':
        await query.edit_message_text("👀 **Review Feature**\n\nThis feature is under construction! Please check back later or start a new quiz with /quiz.")


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

    # --- 1. Special Quiz Selection (/tests command) ---
    if data.startswith('quiz_start_'):
        quiz_id = data.split('_start_')[1]
        selected_questions_list = load_questions_from_file(quiz_id) # Use the dynamic loader
        
        # Determine quiz parameters for the special test
        num_q = len(selected_questions_list)
        # Apply standard settings for mock tests 
        config = QUIZ_MODES.get('simulation_20_720', QUIZ_MODES['full_20']) 
        is_timed = config['timed']
        time_limit = config.get('time_limit', 720) # Default to 12 mins if not specified
        mode = quiz_id # Use the relative path ID as the mode identifier
        instant_feedback = config['feedback']
        
    # --- 2. Mode/Topic Selection (/quiz or /topics command) ---
    elif data.startswith('mode_select_') or data.startswith('topic_select_'):
        data = data.split('_select_')[1]
        
        # Determine Quiz Parameters
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
        
        # Select Questions from hardcoded bank
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


# --- Main Application Setup ---

def main():
    """Main function - optimized for deployment"""
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
    app.add_handler(CommandHandler("tests", special_tests)) # Uses the new recursive scan
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(CommandHandler("leaderboard", leaderboard_handler)) 
    app.add_handler(CommandHandler("mystats", mystats)) 
    app.add_handler(CommandHandler("help", help_command)) 
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(mode_or_topic_selected, pattern='^mode_select_|^topic_select_|^quiz_start_')) 
    app.add_handler(CallbackQueryHandler(handle_answer, pattern='^answer_submit_|^quiz_submit_final|^quiz_nav_'))
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
