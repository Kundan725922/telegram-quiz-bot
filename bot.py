import logging
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, error, WebAppInfo
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
completed_quizzes = {}  # Store completed quiz data for review

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

def has_calculator_emoji(question_text: str) -> bool:
    """Check if question needs calculator (has 🧮 emoji)"""
    return "🧮" in question_text

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
/quite - exit the test

<b>🔥 NEW Features:</b>
✅ Detailed answer review after quiz
✅ Calculator button for numerical questions
✅ MSQ (Multiple Select Questions) support
✅ Comprehensive explanations for every question

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
    
    # Determine question type from question text
    q_type = "MCQ"
    if q_data['q'].startswith('[MSQ]'):
        q_type = "MSQ"
    elif q_data['q'].startswith('[NAT]'):
        q_type = "NAT"
    
    header = f"❓ <b>Question {q_index + 1}/{len(questions)}</b> [{q_type}]\n"
    if session['is_timed']:
        elapsed = (datetime.now() - session['start_time']).total_seconds()
        remaining = session['time_limit'] - elapsed
        time_display = f"⏱️ Time Left: {format_time(max(0, remaining))}\n"
        header = f"{time_display}" + header
        
    question_text = f"{header}\n{q_data['q']}"

    keyboard = []
    
    # Check if MSQ (multiple answers possible)
    is_msq = isinstance(q_data.get('answer'), list)
    user_answers = session['answers'][q_index] if session['answers'][q_index] else []
    if not isinstance(user_answers, list):
        user_answers = [user_answers] if user_answers is not None else []
    
    for i, option in enumerate(q_data['options']):
        prefix = "✅ " if i in user_answers else ""
        button_text = f"{prefix}{chr(65+i)}. {option}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f'answer_submit_{i}')])
    
    # Add Clear Selection button for MSQ
    if is_msq and user_answers:
        keyboard.append([InlineKeyboardButton("🗑️ Clear Selection", callback_data='answer_clear')])
    
    # Navigation buttons
    nav_buttons = []
    if q_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data='quiz_nav_prev'))
    if q_index < len(questions) - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data='quiz_nav_next'))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Add calculator button if question has 🧮 emoji
    if has_calculator_emoji(q_data['q']):
        keyboard.append([InlineKeyboardButton("🧮 Open Calculator", web_app=WebAppInfo(url="https://www.desmos.com/scientific"))])
    
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
    elif data == 'answer_clear':
        session['answers'][q_index] = []
        await send_question(query.message, context, user_id)
        return

    if data.startswith('answer_submit_'):
        try:
            selected_option = int(data.split('_')[-1])
        except ValueError:
            return

        # Check if MSQ
        q_data = questions[q_index]
        is_msq = isinstance(q_data.get('answer'), list)
        
        if is_msq:
            # MSQ: Toggle selection
            current_answers = session['answers'][q_index] if session['answers'][q_index] else []
            if not isinstance(current_answers, list):
                current_answers = []
            
            if selected_option in current_answers:
                current_answers.remove(selected_option)
            else:
                current_answers.append(selected_option)
            
            session['answers'][q_index] = sorted(current_answers)
        else:
            # MCQ/NAT: Single selection
            session['answers'][q_index] = selected_option
        
        if session['instant_feedback'] and not is_msq:
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
    
    # Calculate score handling both MSQ and MCQ
    for q_data, user_ans in zip(session['questions'], session['answers']):
        correct_ans = q_data['answer']
        
        if isinstance(correct_ans, list):  # MSQ
            if isinstance(user_ans, list) and sorted(user_ans) == sorted(correct_ans):
                final_score += 1
        else:  # MCQ/NAT
            if user_ans == correct_ans:
                final_score += 1
            
    score_pct = (final_score / total_q) * 100 if total_q > 0 else 0
    time_taken = (datetime.now() - session['start_time']).total_seconds()
    
    stats = leaderboard_data[user_id]
    stats['total_score'] += final_score
    stats['total_questions'] += total_q
    stats['tests_taken'] += 1
    stats['best_score_pct'] = max(stats['best_score_pct'], score_pct)

    # Store completed quiz for review
    quiz_key = f"{user_id}_{int(datetime.now().timestamp())}"
    completed_quizzes[quiz_key] = {
        'questions': session['questions'],
        'user_answers': session['answers'],
        'score': final_score,
        'total': total_q,
        'score_pct': score_pct
    }

    status_text = "⚠️ <b>TIME UP!</b> Your quiz has automatically submitted." if timed_out else "✅ <b>Quiz Complete!</b>"
    
    result_text = f"🎉 {status_text}\n\n"
    result_text += f"🎯 Mode: <b>{session['mode'].replace('_', ' ').title()}</b>\n"
    result_text += f"✅ Correct Answers: <b>{final_score} / {total_q}</b>\n"
    result_text += f"💯 Score: <b>{score_pct:.1f}%</b>\n"
    result_text += f"⏱️ Time Taken: <b>{format_time(time_taken)}</b>"

    keyboard = [
        [InlineKeyboardButton("👀 Review Answers", callback_data=f'review_start_{quiz_key}')],
        [InlineKeyboardButton("🆕 Start New Quiz", callback_data='post_quiz_action_new')]
    ]
    
    await send_message_robust(context, session['chat_id'], result_text, reply_markup=InlineKeyboardMarkup(keyboard))
    del user_sessions[user_id]

async def review_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display detailed review of quiz answers."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith('review_start_'):
        quiz_key = data.replace('review_start_', '')
        
        if quiz_key not in completed_quizzes:
            await query.edit_message_text("❌ Quiz data not found. It may have been cleared.", parse_mode='HTML')
            return
        
        # Start review from question 1
        await show_review_question(query, quiz_key, 0)
    
    elif data.startswith('review_q_'):
        parts = data.split('_')
        quiz_key = parts[2]
        q_index = int(parts[3])
        
        await show_review_question(query, quiz_key, q_index)

async def show_review_question(query, quiz_key: str, q_index: int) -> None:
    """Show a single question in review mode."""
    if quiz_key not in completed_quizzes:
        await query.edit_message_text("❌ Quiz data not found.", parse_mode='HTML')
        return
    
    quiz_data = completed_quizzes[quiz_key]
    questions = quiz_data['questions']
    user_answers = quiz_data['user_answers']
    
    if q_index >= len(questions):
        # Review complete
        await query.edit_message_text(
            f"✅ <b>Review Complete!</b>\n\n"
            f"Final Score: <b>{quiz_data['score']}/{quiz_data['total']} ({quiz_data['score_pct']:.1f}%)</b>\n\n"
            f"Keep practicing to improve! 💪",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🆕 Start New Quiz", callback_data='post_quiz_action_new')]])
        )
        return
    
    q_data = questions[q_index]
    user_ans = user_answers[q_index]
    correct_ans = q_data['answer']
    
    # Determine question type
    q_type = "MCQ"
    if q_data['q'].startswith('[MSQ]'):
        q_type = "MSQ"
    elif q_data['q'].startswith('[NAT]'):
        q_type = "NAT"
    
    # Check if answer is correct
    if isinstance(correct_ans, list):  # MSQ
        is_correct = isinstance(user_ans, list) and sorted(user_ans) == sorted(correct_ans)
    else:  # MCQ/NAT
        is_correct = user_ans == correct_ans
    
    status_icon = "✅" if is_correct else "❌"
    
    # Build review text
    review_text = f"<b>Review - Question {q_index + 1}/{len(questions)}</b> [{q_type}] {status_icon}\n\n"
    review_text += f"{q_data['q']}\n\n"
    
    # Show options with indicators
    for i, option in enumerate(q_data['options']):
        prefix = ""
        
        if isinstance(correct_ans, list):  # MSQ
            if i in correct_ans:
                prefix = "✅ "
            if isinstance(user_ans, list) and i in user_ans and i not in correct_ans:
                prefix = "❌ "
        else:  # MCQ/NAT
            if i == correct_ans:
                prefix = "✅ "
            elif i == user_ans and i != correct_ans:
                prefix = "❌ "
        
        review_text += f"{prefix}{chr(65+i)}. {option}\n"
    
    # Show user's answer
    review_text += f"\n<b>Your Answer:</b> "
    if user_ans is None or (isinstance(user_ans, list) and len(user_ans) == 0):
        review_text += "Not answered"
    elif isinstance(user_ans, list):
        review_text += ", ".join([chr(65+i) for i in user_ans])
    else:
        review_text += chr(65+user_ans)
    
    # Show correct answer
    review_text += f"\n<b>Correct Answer:</b> "
    if isinstance(correct_ans, list):
        review_text += ", ".join([chr(65+i) for i in correct_ans])
    else:
        review_text += chr(65+correct_ans)
    
    # Add explanation if available
    if 'explanation' in q_data and q_data['explanation']:
        review_text += f"\n\n💡 <b>Explanation:</b>\n{q_data['explanation']}"
    
    # Navigation buttons for review
    keyboard = []
    nav_buttons = []
    
    if q_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f'review_q_{quiz_key}_{q_index-1}'))
    
    if q_index < len(questions) - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f'review_q_{quiz_key}_{q_index+1}'))
    else:
        nav_buttons.append(InlineKeyboardButton("🏁 Finish Review", callback_data=f'review_q_{quiz_key}_{len(questions)}'))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🆕 Start New Quiz", callback_data='post_quiz_action_new')])
    
    try:
        await query.edit_message_text(
            review_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except error.BadRequest as e:
        logger.error(f"Error updating review message: {e}")

# --- Callback Query Router ---

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main router for all callback queries."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Route to appropriate handler
    if data.startswith('mode_select_'):
        await handle_mode_selection(update, context)
    elif data.startswith('topic_select_'):
        await handle_topic_selection(update, context)
    elif data.startswith('quiz_start_'):
        await handle_quiz_start(update, context)
    elif data.startswith('answer_') or data.startswith('quiz_nav_') or data == 'quiz_submit_final':
        await handle_answer(update, context)
    elif data.startswith('review_'):
        await review_quiz(update, context)
    elif data == 'post_quiz_action_new':
        keyboard = [[InlineKeyboardButton(mode_data['label'], callback_data=f'mode_select_{mode_key}')] 
                    for mode_key, mode_data in QUIZ_MODES.items()]
        keyboard.append([InlineKeyboardButton("➡️ Choose Topic Instead", callback_data='topics_redirect')])
        
        await query.edit_message_text(
            "🎮 <b>Select Quiz Mode:</b>\n\nChoose your next challenge:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    elif data == 'topics_redirect':
        await show_topics_inline(query, context)

async def handle_mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle quiz mode selection."""
    query = update.callback_query
    mode_key = query.data.replace('mode_select_', '')
    
    if mode_key not in QUIZ_MODES:
        await query.edit_message_text("❌ Invalid mode selected.", parse_mode='HTML')
        return
    
    # Get available quizzes
    available = get_available_quizzes()
    
    if not available:
        await query.edit_message_text(
            "⚠️ No quizzes available!\n\nPlease add JSON files to the 'questions' folder.",
            parse_mode='HTML'
        )
        return
    
    # Show quiz selection for this mode
    sorted_quizzes = sorted(available.items(), key=lambda item: item[1])
    keyboard = [[InlineKeyboardButton(label, callback_data=f'quiz_start_{quiz_id}_{mode_key}')] 
                for quiz_id, label in sorted_quizzes[:15]]  # Limit to 15 to avoid message size issues
    
    keyboard.append([InlineKeyboardButton("⬅️ Back to Modes", callback_data='back_to_modes')])
    
    mode_info = QUIZ_MODES[mode_key]
    await query.edit_message_text(
        f"📚 <b>Select Quiz for {mode_info['label']}</b>\n\n"
        f"Questions: {mode_info['num_q']}\n"
        f"{'⏱️ Timed: ' + format_time(mode_info.get('time_limit', 0)) if mode_info['timed'] else '⏱️ Untimed'}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle topic selection and start quiz."""
    query = update.callback_query
    topic_id = query.data.replace('topic_select_', '')
    
    if topic_id == 'random':
        # Random mix of questions from all topics
        all_questions = []
        available = get_available_quizzes()
        
        for quiz_id in available.keys():
            if '/' not in quiz_id:  # Only root topics
                questions = load_questions_from_file(quiz_id)
                all_questions.extend(questions)
        
        if len(all_questions) < 10:
            await query.edit_message_text(
                "⚠️ Not enough questions for random mix!\n\nAdd more topics to use this feature.",
                parse_mode='HTML'
            )
            return
        
        selected_questions = random.sample(all_questions, min(10, len(all_questions)))
        quiz_mode = 'standard_10'
    else:
        # Load specific topic
        selected_questions = load_questions_from_file(topic_id)
        
        if not selected_questions:
            await query.edit_message_text(
                f"❌ Could not load questions for topic: {topic_id}",
                parse_mode='HTML'
            )
            return
        
        quiz_mode = 'standard_10'
        selected_questions = random.sample(selected_questions, min(10, len(selected_questions)))
    
    await start_quiz_session(query, context, selected_questions, quiz_mode, topic_id)

async def handle_quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle quiz start from tests menu."""
    query = update.callback_query
    data_parts = query.data.replace('quiz_start_', '').split('_')
    
    # Extract quiz_id and mode_key
    if len(data_parts) > 1 and data_parts[-1] in QUIZ_MODES:
        mode_key = data_parts[-1]
        quiz_id = '_'.join(data_parts[:-1])
    else:
        mode_key = 'standard_10'
        quiz_id = '_'.join(data_parts)
    
    # Load questions
    all_questions = load_questions_from_file(quiz_id)
    
    if not all_questions:
        await query.edit_message_text(
            f"❌ Could not load quiz: {quiz_id}\n\nPlease check if the file exists.",
            parse_mode='HTML'
        )
        return
    
    # Select questions based on mode
    mode_config = QUIZ_MODES[mode_key]
    num_questions = min(mode_config['num_q'], len(all_questions))
    selected_questions = random.sample(all_questions, num_questions)
    
    await start_quiz_session(query, context, selected_questions, mode_key, quiz_id)

async def start_quiz_session(query, context: ContextTypes.DEFAULT_TYPE, questions: list, mode_key: str, quiz_id: str) -> None:
    """Initialize and start a quiz session."""
    user_id = query.from_user.id
    user = query.from_user
    
    # Update leaderboard with username
    if leaderboard_data[user_id]['username'] == 'N/A':
        leaderboard_data[user_id]['username'] = user.username or user.first_name
        leaderboard_data[user_id]['user_id'] = user_id
    
    mode_config = QUIZ_MODES[mode_key]
    
    # Create session
    user_sessions[user_id] = {
        'questions': questions,
        'answers': [None] * len(questions),
        'current': 0,
        'start_time': datetime.now(),
        'is_timed': mode_config['timed'],
        'time_limit': mode_config.get('time_limit', 0),
        'instant_feedback': mode_config['feedback'],
        'mode': mode_key,
        'quiz_id': quiz_id,
        'chat_id': query.message.chat_id,
        'is_finished': False,
        'timer_task': None
    }
    
    # Start timer if timed quiz
    if mode_config['timed']:
        timer_task = asyncio.create_task(
            quiz_timer(user_id, context, mode_config['time_limit'], query.message.chat_id)
        )
        user_sessions[user_id]['timer_task'] = timer_task
    
    await query.edit_message_text(
        f"🚀 <b>Quiz Starting!</b>\n\n"
        f"Mode: {mode_config['label']}\n"
        f"Questions: {len(questions)}\n"
        f"{'Time Limit: ' + format_time(mode_config['time_limit']) if mode_config['timed'] else 'No Time Limit'}\n\n"
        f"Good luck! 🍀",
        parse_mode='HTML'
    )
    
    await asyncio.sleep(1)
    await send_question(query.message, context, user_id)

async def show_topics_inline(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show topics menu inline."""
    available = get_available_quizzes()
    
    if not available:
        await query.edit_message_text(
            "⚠️ No topics found!\n\nAdd JSON files to 'questions' folder.",
            parse_mode='HTML'
        )
        return
    
    topics_dict = {k: v for k, v in available.items() if '/' not in k}
    
    if not topics_dict:
        await query.edit_message_text(
            "⚠️ No topics in root folder!\n\nUse /tests for all quizzes.",
            parse_mode='HTML'
        )
        return
    
    sorted_topics = sorted(topics_dict.items(), key=lambda item: item[1])
    keyboard = [[InlineKeyboardButton(label, callback_data=f'topic_select_{topic_id}')] 
                for topic_id, label in sorted_topics]
    
    keyboard.append([InlineKeyboardButton("🎲 Random Mix (10Q)", callback_data='topic_select_random')])
    
    await query.edit_message_text(
        f'📚 <b>Choose Topic:</b>\n\n✨ {len(topics_dict)} topic(s) available',
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# --- Main Application ---

def main() -> None:
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN not found in environment variables!")
        logger.error("Please set BOT_TOKEN environment variable and restart.")
        return
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CommandHandler("tests", special_tests))
    application.add_handler(CommandHandler("topics", topics))
    application.add_handler(CommandHandler("leaderboard", leaderboard_handler))
    application.add_handler(CommandHandler("mystats", mystats))
    
    # Register callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Log startup
    logger.info("🤖 Bot starting up...")
    logger.info(f"📂 Quiz directory: {os.path.abspath(QUIZ_DATA_DIR)}")
    
    # Discover available quizzes on startup
    available = get_available_quizzes()
    logger.info(f"✅ Found {len(available)} quiz(es) on startup")
    
    # Run the bot
    logger.info("✅ Bot is now running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
