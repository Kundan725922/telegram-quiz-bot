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
QUIZ_DATA_DIR = 'questions' 

# Define quiz modes and their parameters
QUIZ_MODES = {
    'quick_5': {'num_q': 5, 'timed': False, 'label': "⚡ Quick (5Q)", 'feedback': True},
    'standard_10': {'num_q': 10, 'timed': False, 'label': "📝 Standard (10Q)", 'feedback': True},
    'full_20': {'num_q': 20, 'timed': False, 'label': "🎯 Full Test (20Q)", 'feedback': True},
    'timed_10_300': {'num_q': 10, 'timed': True, 'time_limit': 300, 'label': "⏱️ Timed Challenge (10Q - 5min)", 'feedback': True},
    'simulation_20_720': {'num_q': 20, 'timed': True, 'time_limit': 720, 'label': "🧠 Full Simulation (20Q - 12min)", 'feedback': False}
}

# Global state
leaderboard_data = defaultdict(lambda: {'total_score': 0, 'total_questions': 0, 'tests_taken': 0, 'best_score_pct': 0, 'username': 'N/A', 'user_id': 0})
user_sessions = {}

# --- DYNAMIC TOPIC LOADING (NO HARDCODING NEEDED!) ---
def get_all_topic_files() -> dict:
    """
    🔥 AUTO-DISCOVERS all topics from JSON files in 'questions' folder
    Returns: {topic_name: file_path}
    NO NEED TO UPDATE CODE when adding new topics!
    """
    topics = {}
    try:
        if not os.path.exists(QUIZ_DATA_DIR):
            os.makedirs(QUIZ_DATA_DIR, exist_ok=True)
            return topics
            
        # Scan for individual topic files in the root questions folder
        for filename in os.listdir(QUIZ_DATA_DIR):
            if filename.endswith('.json') and not filename.startswith('_'):
                topic_name = filename[:-5]  # Remove .json
                topics[topic_name] = os.path.join(QUIZ_DATA_DIR, filename)
                logger.info(f"📚 Discovered topic: {topic_name}")
                
    except Exception as e:
        logger.error(f"Error discovering topics: {e}")
        
    return topics

# --- Utility Functions ---

def load_questions_from_file(quiz_id: str) -> list:
    """
    Loads questions from a JSON file using the full relative path stored in quiz_id.
    FIXED: Now handles spaces in folder names correctly.
    """
    try:
        # Handle both forward slashes and backslashes
        quiz_id_normalized = quiz_id.replace('\\', '/')
        file_path = os.path.join(QUIZ_DATA_DIR, f'{quiz_id_normalized}.json')
        
        logger.info(f"🔍 Attempting to load: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"❌ Quiz file not found: {file_path}")
            logger.info(f"📁 Current directory: {os.getcwd()}")
            logger.info(f"📂 Looking for file at: {os.path.abspath(file_path)}")
            return []
            
        with open(file_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
            logger.info(f"✅ Successfully loaded {len(questions)} questions from {quiz_id}")
            return questions
    except Exception as e:
        logger.error(f"❌ Error loading questions for {quiz_id}: {e}")
        return []

def get_available_quizzes() -> dict:
    """
    🔥 FULLY AUTOMATIC - NO HARDCODING REQUIRED!
    Scans the QUIZ_DATA_DIR recursively and handles spaces in folder names.
    Returns a dict of available quizzes {relative_path_id: label}.
    """
    available = {}
    try:
        if not os.path.exists(QUIZ_DATA_DIR):
            os.makedirs(QUIZ_DATA_DIR, exist_ok=True)
            logger.warning(f"Created questions directory: {QUIZ_DATA_DIR}")
            
        logger.info(f"📂 Scanning directory: {os.path.abspath(QUIZ_DATA_DIR)}")
        
        # Recursive scan with better logging
        for root, dirs, files in os.walk(QUIZ_DATA_DIR):
            logger.info(f"📁 Checking folder: {root}")
            
            for filename in files:
                if filename.endswith('.json') and not filename.startswith('_'):
                    full_path = os.path.join(root, filename)
                    
                    # Create the relative path ID
                    relative_path = os.path.relpath(full_path, QUIZ_DATA_DIR)
                    quiz_id = relative_path[:-5]  # Remove '.json'
                    
                    # Normalize path separators for consistency (use forward slash)
                    quiz_id = quiz_id.replace(os.path.sep, '/')
                    
                    logger.info(f"✅ Found quiz: {quiz_id}")
                    
                    # Create a user-friendly label
                    parts = quiz_id.split('/')
                    
                    # Use last 3 parts for label or all if less than 3
                    display_parts = parts[-3:] if len(parts) >= 3 else parts
                    
                    # Capitalize and make it readable
                    label = " | ".join([p.replace('_', ' ').title() for p in display_parts])
                    
                    # Prepend an icon based on the top-level folder or filename
                    top_folder = parts[0].lower() if len(parts) > 1 else filename.lower()
                    
                    if 'gate' in top_folder and 'pyq' in top_folder:
                        label = "📖 " + label
                    elif 'mock' in top_folder:
                        label = "🧠 " + label
                    elif 'pyq' in top_folder:
                        label = "📖 " + label
                    elif 'subject' in top_folder or 'subject_wise' in top_folder:
                        label = "📚 " + label
                    elif 'weekly' in top_folder or 'daily' in top_folder:
                        label = "📅 " + label
                    else:
                        label = "📋 " + label
                        
                    available[quiz_id] = label
                    logger.info(f"   Label: {label}")

        logger.info(f"📊 Total quizzes found: {len(available)}")
        
    except Exception as e:
        logger.error(f"❌ Error listing quizzes in {QUIZ_DATA_DIR}: {e}")
        
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
            parse_mode='HTML'
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
/tests - Browse all available quizzes (Auto-discovered!)
/topics - Focus on specific subjects (Auto-discovered!)
/leaderboard - Top 10 rankers globally
/mystats - Your personalized analytics
/help - Complete guide and info

<b>🔥 NEW:</b> ALL PYQS AVALIBLE SHORTLY year vise
Start your preparation now! 🚀"""
    await update.message.reply_text(text, parse_mode='HTML')

async def special_tests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    🔥 FULLY AUTOMATIC - Shows ALL available quizzes from subfolders.
    NO CODE CHANGES needed when adding new quizzes!
    """
    available = get_available_quizzes()
    
    if not available:
        await update.message.reply_text(
            "⚠️ No quizzes found!\n\n"
            f"📂 Searched in: {os.path.abspath(QUIZ_DATA_DIR)}\n\n"
            "💡 <b>How to add quizzes:</b>\n"
            "1. Create a JSON file with questions\n"
            "2. Place it in the 'questions' folder or any subfolder\n"
            "3. Restart the bot - it will appear automatically!\n\n"
            "Try /quiz for mode-based quizzes.", 
            parse_mode='HTML'
        )
        return

    # Sort available quizzes alphabetically by label
    sorted_quizzes = sorted(available.items(), key=lambda item: item[1])
    
    keyboard = [[InlineKeyboardButton(label, callback_data=f'quiz_start_{quiz_id}')] 
                for quiz_id, label in sorted_quizzes]
    
    await update.message.reply_text(
        f"📅 <b>Select a Test:</b>\n\n✨ Found {len(available)} quiz(es) - automatically discovered!\n\n"
        "🔥 <i>Just add new JSON files to 'questions' folder and they'll appear here!</i>",
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
    """
    🔥 FULLY AUTOMATIC - Shows ALL available topics.
    NO CODE CHANGES needed when adding new topics!
    """
    # Get all available quizzes and filter by single-level topics
    available = get_available_quizzes()
    
    if not available:
        await update.message.reply_text(
            "⚠️ No topics found!\n\n"
            "💡 Add JSON files directly to 'questions' folder to create topics.\n"
            "Try /tests to see all quizzes or /quiz for mode-based quizzes.",
            parse_mode='HTML'
        )
        return
    
    # Separate topics (single level) from nested quizzes
    topics_dict = {}
    for quiz_id, label in available.items():
        # Topics are files directly in questions folder (no subfolders)
        if '/' not in quiz_id:
            topics_dict[quiz_id] = label
    
    if not topics_dict:
        await update.message.reply_text(
            "⚠️ No topics found in root folder!\n\n"
            "Topics should be JSON files directly in 'questions' folder.\n"
            "Use /tests to see all available quizzes.",
            parse_mode='HTML'
        )
        return
    
    # Sort topics alphabetically
    sorted_topics = sorted(topics_dict.items(), key=lambda item: item[1])
    
    keyboard = [[InlineKeyboardButton(label, callback_data=f'topic_select_{topic_id}')] 
                for topic_id, label in sorted_topics]
    
    # Add a random mix option
    keyboard.append([InlineKeyboardButton("🎲 Random Mix (10Q)", callback_data='topic_select_random')])
    
    await update.message.reply_text(
        f'📚 <b>Choose Topic:</b>\n\n✨ Found {len(topics_dict)} topic(s) - automatically discovered!\n\n'
        '🔥 <i>Add more JSON files to see them here!</i>',
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the leaderboard."""
    sorted_board = sorted(leaderboard_data.items(), key=lambda x: x[1]['best_score_pct'], reverse=True)[:10]
    
    if not sorted_board:
        text = "🏆 <b>Global Leaderboard</b>\n\nNo scores recorded yet! Start a quiz with /quiz."
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
    await start(update, context)

# --- Internal Quiz Logic ---

async def quiz_timer(user_id: int, context: ContextTypes.DEFAULT_TYPE, time_limit: int, chat_id: int) -> None:
    """The timer function for timed quizzes."""
    session = user_sessions.get(user_id)
    if not session: return

    end_time = session['start_time'] + timedelta(seconds=time_limit)
    
    await asyncio.sleep(time_limit - 60)
    if not session.get('is_finished') and session.get('timer_task'):
        await send_message_robust(context, chat_id, "⏰ <b>ONE MINUTE REMAINING!</b> Submit your answers soon.")
        
    await asyncio.sleep(60)
    
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
    
    header = f"❓ <b>Question {q_index + 1}/{len(questions)}</b>\n"
    if session['is_timed']:
        elapsed = (datetime.now() - session['start_time']).total_seconds()
        remaining = session['time_limit'] - elapsed
        time_display = f"⏱️ Time Left: {format_time(max(0, remaining))}\n"
        header = f"{time_display}" + header
        
    question_text = f"{header}\n{q_data['q']}"

    keyboard = []
    for i, option in enumerate(q_data['options']):
        prefix = "✅ " if session['answers'][q_index] == i else ""
        keyboard.append([InlineKeyboardButton(f"{prefix}{chr(65+i)}. {option}", callback_data=f'answer_submit_{i}')])
        
    nav_buttons = []
    if q_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data='quiz_nav_prev'))
    if q_index < len(questions) - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data='quiz_nav_next'))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🏁 SUBMIT FINAL ANSWERS 🏁", callback_data='quiz_submit_final')])

    reply_markup = InlineKeyboardMarkup(keyboard)

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

    if data.startswith('answer_submit_'):
        try:
            selected_option = int(data.split('_')[-1])
        except ValueError:
            return

        session['answers'][q_index] = selected_option
        
        if session['instant_feedback']:
            correct_answer = questions[q_index]['answer']
            if selected_option == correct_answer:
                feedback = "✅ <b>Correct Answer!</b> Moving to the next question."
            else:
                feedback = f"❌ <b>Incorrect!</b> The correct answer was option {chr(65+correct_answer)}."
            
            await send_message_robust(context, user_id, feedback)
            
            session['current'] = min(len(questions), q_index + 1)
        
        await send_question(query.message, context, user_id)

async def finalize_quiz(user_id: int, context: ContextTypes.DEFAULT_TYPE, timed_out=False) -> None:
    """Calculates final score and updates the leaderboard."""
    session = user_sessions.get(user_id)
    if not session: return

    session['is_finished'] = True
    if session.get('timer_task'):
        session['timer_task'].cancel()
        session['timer_task'] = None

    final_score = 0
    total_q = len(session['questions'])
    for q_data, user_ans in zip(session['questions'], session['answers']):
        if user_ans == q_data['answer']:
            final_score += 1
            
    score_pct = (final_score / total_q) * 100 if total_q > 0 else 0
    time_taken = (datetime.now() - session['start_time']).total_seconds()
    
    stats = leaderboard_data[user_id]
    stats['total_score'] += final_score
    stats['total_questions'] += total_q
    stats['tests_taken'] += 1
    stats['best_score_pct'] = max(stats['best_score_pct'], score_pct)

    status_text = "⚠️ <b>TIME UP!</b> Your quiz has automatically submitted." if timed_out else "✅ <b>Quiz Complete!</b>"
    
    result_text = f"🎉 {status_text}\n\n"
    result_text += f"🎯 Mode: <b>{session['mode'].replace('_', ' ').title()}</b>\n"
    result_text += f"✅ Correct Answers: <b>{final_score} / {total_q}</b>\n"
    result_text += f"💯 Score: <b>{score_pct:.1f}%</b>\n"
    result_text += f"⏱️ Time Taken: <b>{format_time(time_taken)}</b>"

    keyboard = [
        [InlineKeyboardButton("👀 Review Answers", callback_data='post_quiz_action_review')],
        [InlineKeyboardButton("🆕 Start New Quiz", callback_data='post_quiz_action_new')]
    ]
    
    await send_message_robust(context, session['chat_id'], result_text, reply_markup=InlineKeyboardMarkup(keyboard))
    del user_sessions[user_id]

async def post_quiz_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles actions after a quiz is finished."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'post_quiz_action_new':
        await quiz(update, context)
        try:
            await query.delete_message()
        except error.BadRequest:
             pass
    elif data == 'post_quiz_action_review':
        await query.edit_message_text("👀 <b>Review Feature</b>\n\nThis feature is under construction! Please check back later or start a new quiz with /quiz.", parse_mode='HTML')

# --- Callback Query Handlers ---

async def mode_or_topic_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    🔥 FULLY AUTOMATIC - Handles mode, topic, AND special quiz selection.
    NO CODE CHANGES needed when adding new quizzes!
    """
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    user_id = user.id
    data = query.data
    selected_questions_list = []

    if data == 'topics_redirect':
        await topics(update, context)
        return

    # --- 1. Special Quiz Selection (/tests command) ---
    if data.startswith('quiz_start_'):
        quiz_id = data.split('quiz_start_', 1)[1]
        selected_questions_list = load_questions_from_file(quiz_id)
        
        if not selected_questions_list:
            await query.edit_message_text(
                "⚠️ Could not load quiz questions!\n\n"
                f"Quiz ID: {quiz_id}\n\n"
                "Please check the file exists and is valid JSON.",
                parse_mode='HTML'
            )
            return
        
        num_q = len(selected_questions_list)
        config = QUIZ_MODES.get('simulation_20_720', QUIZ_MODES['full_20']) 
        is_timed = config['timed']
        time_limit = config.get('time_limit', 720)
        mode = quiz_id
        instant_feedback = config['feedback']
        
    # --- 2. Topic Selection (/topics command) ---
    elif data.startswith('topic_select_'):
        topic = data.split('topic_select_', 1)[1]
        
        if topic == 'random':
            # Load all available quizzes and mix them
            all_quizzes = get_available_quizzes()
            all_questions = []
            for quiz_id in all_quizzes.keys():
                questions = load_questions_from_file(quiz_id)
                all_questions.extend(questions)
            
            if all_questions:
                selected_questions_list = random.sample(all_questions, min(10, len(all_questions)))
            mode = 'random_mix'
        else:
            # Load specific topic
            selected_questions_list = load_questions_from_file(topic)
            mode = f'topic_{topic}'
        
        num_q = len(selected_questions_list)
        is_timed = False
        time_limit = None
        instant_feedback = True
        
    # --- 3. Mode Selection (/quiz command) ---
    elif data.startswith('mode_select_'):
        mode_key = data.split('mode_select_', 1)[1]
        
        if mode_key not in QUIZ_MODES:
            await query.edit_message_text("❌ Invalid mode selected.", parse_mode='HTML')
            return
            
        config = QUIZ_MODES[mode_key]
        num_q = config['num_q']
        is_timed = config['timed']
        time_limit = config.get('time_limit')
        instant_feedback = config['feedback']
        mode = mode_key
        
        # Load random questions from all available quizzes
        all_quizzes = get_available_quizzes()
        all_questions = []
        for quiz_id in all_quizzes.keys():
            questions = load_questions_from_file(quiz_id)
            all_questions.extend(questions)
        
        if all_questions:
            selected_questions_list = random.sample(all_questions, min(num_q, len(all_questions)))
    
    # --- Final Check & Session Initialization ---
    if not selected_questions_list:
        await query.edit_message_text(
            "⚠️ Not enough questions available!\n\n"
            "💡 Add more JSON files to the 'questions' folder.\n"
            "Try /tests to see available quizzes.",
            parse_mode='HTML'
        )
        return

    # Limit questions if needed
    if len(selected_questions_list) > num_q:
        selected_questions_list = random.sample(selected_questions_list, num_q)

    # Initialize Session
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
        text += "⚠️ <b>Simulation Mode:</b> No immediate feedback. Submit all answers at the end.\n"
    text += f"\nGet ready! 💪"
    
    try:
        await query.edit_message_text(text, parse_mode='HTML')
    except error.BadRequest:
        pass 
    
    # Start Timer and Send First Question
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
    app.add_handler(CommandHandler("tests", special_tests))
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(CommandHandler("leaderboard", leaderboard_handler)) 
    app.add_handler(CommandHandler("mystats", mystats)) 
    app.add_handler(CommandHandler("help", help_command)) 
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(mode_or_topic_selected, pattern='^mode_select_|^topic_select_|^quiz_start_|^topics_redirect')) 
    app.add_handler(CallbackQueryHandler(handle_answer, pattern='^answer_submit_|^quiz_submit_final|^quiz_nav_'))
    app.add_handler(CallbackQueryHandler(post_quiz_action, pattern='^post_quiz_action_'))
    
    print("🤖 Bot starting...")
    print("🔥 AUTO-DISCOVERY ENABLED: Add JSON files to 'questions' folder - they appear automatically!")
    
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
        print("✅ Running! Press Ctrl+C to stop")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    # Ensure the directory for new quizzes exists before starting the bot
    os.makedirs(QUIZ_DATA_DIR, exist_ok=True)
    main()

