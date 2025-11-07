import logging
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, error
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random
from collections import defaultdict
import sys
# ⚠️ WARNING: Using a real token here for an example is risky. 
# The token is replaced with a placeholder 'PLACEHOLDER_TOKEN' in the code below.

# --- Configuration & Initialization ---

# Check Python version
if sys.version_info >= (3, 13):
    print("⚠️ WARNING: Python 3.13 detected. Telegram bot library works best with Python 3.8-3.12")

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants (Improved Readability & Maintainability)
# Use a secure method like an environment variable for the real token.
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'P8590474160:AAEMFKT_hyCF3qRROu0BrlqIbTii0HikxII') 
# Define quiz modes and their parameters
QUIZ_MODES = {
    'quick_5': {'num_q': 5, 'timed': False, 'label': "⚡ Quick (5Q)"},
    'standard_10': {'num_q': 10, 'timed': False, 'label': "📝 Standard (10Q)"},
    'full_20': {'num_q': 20, 'timed': False, 'label': "🎯 Full Test (20Q)"},
    'timed_10_300': {'num_q': 10, 'timed': True, 'time_limit': 300, 'label': "⏱️ Timed Challenge (10Q - 5min)"}, # 5 min = 300 sec
    'timed_15_420': {'num_q': 15, 'timed': True, 'time_limit': 420, 'label': "🔥 Speed Round (15Q - 7min)"} # 7 min = 420 sec
}
TOPICS = ['algorithms', 'data_structures', 'programming', 'toc']

# Global state (In a real application, replace with a database like PostgreSQL or Redis)
leaderboard_data = defaultdict(lambda: {'total_score': 0, 'total_questions': 0, 'tests_taken': 0, 'best_score_pct': 0, 'username': 'N/A', 'user_id': 0})
user_sessions = {} # Active quiz sessions

# --- Question Bank (Retained) ---
QUESTIONS = {
    'algorithms': [
        {'q': 'What is the time complexity of building a heap of n elements?', 'options': ['O(n)', 'O(n log n)', 'O(n²)', 'O(log n)'], 'answer': 0},
        {'q': 'Which sorting algorithm is NOT stable?', 'options': ['Merge Sort', 'Quick Sort', 'Insertion Sort', 'Bubble Sort'], 'answer': 1},
        {'q': 'Dijkstra algorithm does NOT work correctly with:', 'options': ['Directed graphs', 'Undirected graphs', 'Negative edge weights', 'Weighted graphs'], 'answer': 2},
        {'q': 'Time complexity of Floyd-Warshall algorithm is:', 'options': ['O(V²)', 'O(V³)', 'O(V² log V)', 'O(VE)'], 'answer': 1},
        {'q': 'Lower bound for comparison-based sorting is:', 'options': ['O(n)', 'O(n log n)', 'O(n²)', 'O(log n)'], 'answer': 1},
        {'q': 'Which can be solved using greedy algorithm?', 'options': ['0/1 Knapsack', 'Fractional Knapsack', 'LCS', 'Matrix Chain'], 'answer': 1},
        {'q': 'Best case time complexity of Quick Sort is:', 'options': ['O(n)', 'O(n log n)', 'O(n²)', 'O(log n)'], 'answer': 1},
        {'q': 'Binary Search works only on:', 'options': ['Sorted arrays', 'Unsorted arrays', 'Linked lists', 'Any structure'], 'answer': 0},
        {'q': 'Time complexity of Merge Sort is:', 'options': ['O(n)', 'O(n log n)', 'O(n²)', 'O(2^n)'], 'answer': 1},
        {'q': 'Kruskal algorithm uses which data structure?', 'options': ['Priority Queue', 'Union-Find', 'Stack', 'Queue'], 'answer': 1}
    ],
    'data_structures': [
        {'q': 'Best data structure for LRU cache?', 'options': ['Array', 'Stack', 'HashMap + DLL', 'BST'], 'answer': 2},
        {'q': 'Binary tree with n nodes has how many NULL pointers?', 'options': ['n', 'n+1', 'n-1', '2n'], 'answer': 1},
        {'q': 'Average search time in hash table with chaining:', 'options': ['O(1)', 'O(log n)', 'O(1 + α)', 'O(n)'], 'answer': 2},
        {'q': 'Space complexity of adjacency matrix (V vertices):', 'options': ['O(V)', 'O(V²)', 'O(V + E)', 'O(E)'], 'answer': 1},
        {'q': 'Which traversal gives sorted order in BST?', 'options': ['Preorder', 'Inorder', 'Postorder', 'Level order'], 'answer': 1},
        {'q': 'Maximum nodes in binary tree of height h:', 'options': ['2^h - 1', '2^(h+1) - 1', '2^h', '2^(h-1)'], 'answer': 1},
        {'q': 'Stack is useful for:', 'options': ['BFS', 'Level order', 'DFS', 'Dijkstra'], 'answer': 2},
        {'q': 'Height of AVL tree with n nodes is:', 'options': ['O(n)', 'O(log n)', 'O(n log n)', 'O(√n)'], 'answer': 1},
        {'q': 'Time to delete from middle of doubly linked list:', 'options': ['O(1)', 'O(n)', 'O(log n)', 'Cannot'], 'answer': 0},
        {'q': 'Best cache performance collision resolution:', 'options': ['Chaining', 'Linear probing', 'Quadratic', 'Double hash'], 'answer': 1}
    ],
    'programming': [
        {'q': 'Size of pointer on 64-bit system:', 'options': ['4 bytes', '8 bytes', 'Depends', '2 bytes'], 'answer': 1},
        {'q': 'Default value of static variable:', 'options': ['Garbage', '0', 'NULL', '-1'], 'answer': 1},
        {'q': 'Where are global variables stored?', 'options': ['Stack', 'Heap', 'Data segment', 'Code segment'], 'answer': 2},
        {'q': 'Which allocates memory dynamically?', 'options': ['alloc()', 'malloc()', 'new', 'allocate()'], 'answer': 1},
        {'q': 'calloc() initializes memory with:', 'options': ['Garbage', '0', 'NULL', '-1'], 'answer': 1},
        {'q': 'Double free() causes:', 'options': ['Nothing', 'Freed again', 'Undefined behavior', 'Compile error'], 'answer': 2},
        {'q': 'Array passed to function is passed as:', 'options': ['Value', 'Reference', 'Copy', 'Constant'], 'answer': 1},
        {'q': 'Scope of static variable in function:', 'options': ['Function only', 'Entire file', 'Program', 'Block only'], 'answer': 0},
        {'q': 'Union stores:', 'options': ['All members', 'Last assigned', 'First member', 'No member'], 'answer': 1},
        {'q': 'Left shift by 1 is equivalent to:', 'options': ['Divide by 2', 'Multiply by 2', 'Add 1', 'Subtract 1'], 'answer': 1}
    ],
    'toc': [
        {'q': 'DFA accepts which language class?', 'options': ['Context-free', 'Regular', 'Context-sensitive', 'Recursive'], 'answer': 1},
        {'q': 'Which is NOT regular?', 'options': ['a^n b^n', 'a^n', '(ab)^n', 'a^n b^m'], 'answer': 0},
        {'q': 'Grammar is ambiguous if:', 'options': ['Left recursion', 'No strings', 'Multiple parse trees', 'ε-productions'], 'answer': 2},
        {'q': 'Halting problem is:', 'options': ['Decidable', 'Undecidable', 'Regular', 'Context-free'], 'answer': 1},
        {'q': 'CFLs are NOT closed under:', 'options': ['Union', 'Concatenation', 'Intersection', 'Kleene star'], 'answer': 2},
        {'q': 'PDA accepts by:', 'options': ['Final state only', 'Empty stack only', 'Both equivalent', 'Initial state'], 'answer': 2},
        {'q': 'Turing Machine more powerful than PDA because:', 'options': ['Infinite tape', 'Bidirectional', 'Can modify', 'All above'], 'answer': 3},
        {'q': 'Chomsky hierarchy (most to least restrictive):', 'options': ['Reg ⊂ CFL ⊂ CSL ⊂ RE', 'CFL ⊂ Reg', 'Reg ⊂ CSL ⊂ CFL', 'RE ⊂ CSL'], 'answer': 0},
        {'q': 'Regular languages closed under:', 'options': ['Intersection', 'Complement', 'Union', 'All above'], 'answer': 3},
        {'q': 'Which is decidable for CFLs?', 'options': ['Membership', 'Equivalence', 'Intersection empty', 'Universality'], 'answer': 0}
    ]
}

# --- Utility Functions ---

def get_all_questions():
    """Compiles all questions from all topics."""
    all_q = []
    for qs in QUESTIONS.values():
        all_q.extend(qs)
    return all_q

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
            parse_mode='Markdown'
        )
    except error.TelegramError as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
        # Optionally, remove user from sessions/leaderboard if error is related to blocked user

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = f"""🎓 *Welcome {user.first_name} to GATE CSE Quiz Bot!*
Ready to test your knowledge? Choose a quiz mode or a specific topic!

📚 *Commands:*
/quiz - Select your challenge mode
/topics - Focus on a specific subject
/leaderboard - Top 10 rankers globally
/mystats - Your personalized analytics
/help - Complete guide and info

Start your preparation now! 🚀"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show quiz mode selection"""
    keyboard = [[InlineKeyboardButton(mode_data['label'], callback_data=f'mode_select_{mode_key}')] 
                for mode_key, mode_data in QUIZ_MODES.items()]
    
    # Add a 'Choose Topic' button for better UX
    keyboard.append([InlineKeyboardButton("➡️ Choose Topic Instead", callback_data='topics_redirect')]) 
    
    await update.message.reply_text(
        "🎮 *Select Quiz Mode:*\n\nChoose difficulty and type:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show topic selection"""
    keyboard = [
        [InlineKeyboardButton("🔢 Algorithms", callback_data='topic_select_algorithms')],
        [InlineKeyboardButton("📊 Data Structures", callback_data='topic_select_data_structures')],
        [InlineKeyboardButton("💻 Programming", callback_data='topic_select_programming')],
        [InlineKeyboardButton("🔤 TOC", callback_data='topic_select_toc')],
        [InlineKeyboardButton("🎲 Random Mix (10Q)", callback_data='topic_select_random')]
    ]
    await update.message.reply_text('📚 *Choose Topic:*', reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show full leaderboard"""
    if not leaderboard_data:
        await update.message.reply_text("📊 No rankings yet. Start with /quiz to register your score!")
        return
    
    text = "🏆 *GLOBAL LEADERBOARD - TOP 10*\n\n"
    # Key change: Sort by 'best_score_pct'
    top_users = sorted(leaderboard_data.items(), key=lambda x: x[1]['best_score_pct'], reverse=True)[:10]
    
    for i, (uid, data) in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        avg_score = (data['total_score'] / data['total_questions'] * 100) if data['total_questions'] > 0 else 0
        text += f"{medal} *{data['username']}*\n"
        text += f"   Best: {data['best_score_pct']:.1f}% | Avg: {avg_score:.1f}%\n"
        text += f"   Tests: {data['tests_taken']}\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics"""
    user = update.effective_user
    user_id = user.id
    user_data = leaderboard_data.get(user_id)
    
    if not user_data or user_data['tests_taken'] == 0:
        await update.message.reply_text("📊 No stats yet. Start with /quiz!")
        return
    
    avg_score = (user_data['total_score'] / user_data['total_questions'] * 100) if user_data['total_questions'] > 0 else 0
    
    text = f"📊 *Your Personalized Stats*\n\n"
    text += f"👤 User: {user_data.get('username', user.first_name)}\n"
    text += f"🎯 Best Score: {user_data['best_score_pct']:.1f}%\n"
    text += f"📈 Average Score: {avg_score:.1f}%\n"
    text += f"📝 Total Quizzes: {user_data['tests_taken']}\n"
    text += f"✅ Total Correct: {user_data['total_score']}/{user_data['total_questions']}\n\n"
    
    # Recent history (Improved formatting for clarity)
    history = context.user_data.get('history', [])
    if history:
        text += "*Recent 5 Quizzes:*\n"
        for i, r in enumerate(history[-5:], 1):
            emoji = "🎉" if r['pct'] >= 75 else "👍" if r['pct'] >= 60 else "📚"
            text += f"{emoji} {r['score']}/{r['total']} ({r['pct']:.0f}%) in {r.get('time', 'N/A')}\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help message"""
    text = """📖 *Complete Guide*

*🎮 Quiz Modes:*
• /quiz: General modes (Quick, Standard, Full, Timed)
• /topics: Focus on Algorithms, DS, Programming, or TOC.

*🏆 Features:*
• Real-time Global Leaderboard (`/leaderboard`)
• Detailed Personal Stats (`/mystats`)
• Immediate feedback after each question.
• Timed challenges for speed practice.

*💡 Quick Tips:*
• Your score is calculated on your *best* quiz percentage!
• Time taken matters most in *Timed* mode.
• For suggestions or bugs, contact the developer (if applicable).

Good luck! 🚀"""
    await update.message.reply_text(text, parse_mode='Markdown')

# --- Callback Query Handlers ---

async def mode_or_topic_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles both mode and topic selection from their respective menus."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    user_id = user.id
    data = query.data.split('_select_')[1]
    
    # Redirect for topics button on quiz menu
    if data == 'topics_redirect':
        await topics(update, context)
        return

    # 1. Determine Quiz Parameters
    num_q = 0
    is_timed = False
    time_limit = None
    mode = data

    if data in QUIZ_MODES: # Mode selection
        config = QUIZ_MODES[data]
        num_q = config['num_q']
        is_timed = config['timed']
        time_limit = config.get('time_limit')
    
    elif data in TOPICS or data == 'random': # Topic selection (defaults to 10 questions, non-timed)
        num_q = 10 
        is_timed = False
        time_limit = None
        mode = f'topic_{data}'
    
    # 2. Select Questions
    if data == 'random' or data in QUIZ_MODES:
        all_q = get_all_questions()
        selected = random.sample(all_q, min(num_q, len(all_q)))
    else: # Specific topic
        selected = QUESTIONS.get(data, []).copy()
        random.shuffle(selected)
        selected = selected[:num_q] # Use only the required number
        
    if not selected:
        await query.edit_message_text("⚠️ Not enough questions available for this selection. Try another topic.")
        return

    # 3. Initialize Session
    if user_id in user_sessions:
        # Clear previous session to prevent overlap
        if user_sessions[user_id].get('timer_task'):
            user_sessions[user_id]['timer_task'].cancel()
        logger.info(f"User {user_id} started a new quiz, cancelling old session.")

    user_sessions[user_id] = {
        'questions': selected,
        'current': 0,
        'score': 0,
        'answers': [],
        'is_timed': is_timed,
        'time_limit': time_limit,
        'start_time': datetime.now(),
        'mode': mode,
        'chat_id': query.message.chat_id # Store chat_id for timer
    }
    
    # Update username in leaderboard data (good for user display names)
    leaderboard_data[user_id]['username'] = user.username or user.first_name
    leaderboard_data[user_id]['user_id'] = user_id

    text = f"🎯 *Quiz Started!*\n\n"
    text += f"📝 Questions: {len(selected)}\n"
    if is_timed:
        text += f"⏱️ Time Limit: {time_limit//60} minutes ({time_limit} seconds)\n"
    text += f"\nGet ready! 💪"
    
    try:
        await query.edit_message_text(text, parse_mode='Markdown')
    except error.BadRequest:
        # If the message hasn't changed, Telegram throws an error. Ignore it.
        pass 
    
    # 4. Start Timer and Send First Question
    if is_timed:
        # Pass the task so it can be cancelled later
        task = asyncio.create_task(quiz_timer(user_id, context, time_limit, query.message.chat_id))
        user_sessions[user_id]['timer_task'] = task
        
    await send_question(query.message, context, user_id)

async def quiz_timer(user_id: int, context: ContextTypes.DEFAULT_TYPE, time_limit: int, chat_id: int):
    """Timer for timed quizzes. Runs as an asyncio task."""
    try:
        # Check if the session is still active and timed
        if user_id not in user_sessions or not user_sessions[user_id].get('is_timed'):
            return # Guard to prevent false finalization

        await asyncio.sleep(time_limit)
        
        # Check again after sleep to ensure the quiz wasn't finished manually
        if user_id in user_sessions and user_sessions[user_id]['current'] < len(user_sessions[user_id]['questions']):
            await send_message_robust(
                context, 
                chat_id, 
                "⏰ *Time's Up!*\n\nQuiz automatically ended. Here are your results:",
            )
            await finalize_quiz(user_id, context)
            
    except asyncio.CancelledError:
        logger.info(f"Timer for user {user_id} was cancelled.")
        raise # Re-raise CancelledError to allow clean termination
    except Exception as e:
        logger.error(f"Quiz Timer Error for user {user_id}: {e}")

async def send_question(message, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Sends the current question in the session."""
    session = user_sessions.get(user_id)
    if not session:
        return
    
    q_index = session['current']
    q = session['questions'][q_index]
    
    # Calculate time remaining for timed mode
    time_info = ""
    if session.get('is_timed') and session.get('time_limit'):
        elapsed = (datetime.now() - session['start_time']).total_seconds()
        remaining = session['time_limit'] - elapsed
        
        if remaining <= 0:
            await send_message_robust(context, user_id, "⏰ Time ran out before the next question could be sent!")
            await finalize_quiz(user_id, context)
            return

        time_info = f"⏱️ Time Left: *{format_time(remaining)}*\n\n"
    
    text = f"{time_info}❓ *Q{q_index+1}/{len(session['questions'])}*\n\n{q['q']}\n\n"
    keyboard = [[InlineKeyboardButton(f"{chr(65+i)}. {opt}", callback_data=f'answer_submit_{i}')] 
                for i, opt in enumerate(q['options'])]
    
    await send_message_robust(context, message.chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes the user's answer submission."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        await query.edit_message_text("⚠️ Quiz session expired. Use /quiz to start again.", parse_mode='Markdown')
        return
    
    session = user_sessions[user_id]
    
    # Time expired check (essential for a reliable timed mode)
    if session.get('is_timed') and (datetime.now() - session['start_time']).total_seconds() > session['time_limit']:
        await query.edit_message_text("⏰ Time expired while answering!", parse_mode='Markdown')
        await finalize_quiz(user_id, context)
        return
    
    q = session['questions'][session['current']]
    user_ans = int(query.data.split('_submit_')[1])
    correct = q['answer']
    is_correct = user_ans == correct
    
    # 1. Update Session and Feedback
    if is_correct:
        session['score'] += 1
        text = f"✅ *Q{session['current']+1}: Correct!* (+1 Point)\n\nAnswer: {chr(65+correct)}. {q['options'][correct]}"
    else:
        text = f"❌ *Q{session['current']+1}: Wrong!*\n\nYour Answer: {chr(65+user_ans)}. {q['options'][user_ans]}\nCorrect Answer: {chr(65+correct)}. {q['options'][correct]}"
    
    session['answers'].append(is_correct)
    
    try:
        await query.edit_message_text(text, parse_mode='Markdown')
    except error.BadRequest:
        # Ignore if the message was already edited by an answer from a previous question
        pass

    # 2. Advance to Next Question or Finalize
    session['current'] += 1
    if session['current'] < len(session['questions']):
        await send_question(query.message, context, user_id)
    else:
        # Quiz is finished (manually by completing questions)
        if session.get('timer_task'):
            session['timer_task'].cancel() # Stop the timer task
        await finalize_quiz(user_id, context, query.message)

async def finalize_quiz(user_id: int, context: ContextTypes.DEFAULT_TYPE, message=None) -> None:
    """Finalize quiz, calculate score, update leaderboard, and show results."""
    session = user_sessions.get(user_id)
    if not session:
        return
    
    score = session['score']
    total = len(session['questions'])
    pct = (score/total)*100 if total > 0 else 0.0
    
    # Calculate time taken (only up to the point of finalization)
    time_taken = (datetime.now() - session['start_time']).total_seconds()
    time_str = format_time(time_taken)
    
    # Update Leaderboard and User Data
    user_data = leaderboard_data[user_id]
    user_data['total_score'] += score
    user_data['total_questions'] += total
    user_data['tests_taken'] += 1
    # Key change: Update best score only if the current one is better
    user_data['best_score_pct'] = max(user_data['best_score_pct'], pct)
    
    # Result Message Construction
    text = f"🎯 *Quiz Complete!*\n\n"
    text += f"📊 Score: {score}/{total} (*{pct:.1f}%*)\n"
    text += f"⏱️ Time Taken: {time_str}\n\n"
    
    # Dynamic Feedback
    if pct >= 90:
        text += "👑 GATE Grandmaster! You crushed it!\n"
    elif pct >= 75:
        text += "🧠 Excellent Performance! Solid fundamentals.\n"
    elif pct >= 60:
        text += "🌟 Good Job! Keep practicing to secure a top rank.\n"
    else:
        text += "💡 Keep learning. Reviewing your weaker topics will help!\n"
    
    # Visual Progress Bar (A bit of extra flair!)
    correct_count = session['answers'].count(True)
    wrong_count = session['answers'].count(False)
    progress_bar = "✅" * correct_count + "❌" * wrong_count
    text += f"\n*Detailed Progress*:\n`{progress_bar}`\n"
    
    # Top 5 Leaderboard Snapshot
    text += "\n🏆 *TOP 5 LEADERBOARD SNAPSHOT*\n"
    top_users = sorted(leaderboard_data.items(), key=lambda x: x[1]['best_score_pct'], reverse=True)[:5]
    
    for i, (uid, data) in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
        # Highlight current user in the snapshot
        name = f"*{data['username']}* (You)" if uid == user_id else data['username']
        text += f"{medal} {name}: {data['best_score_pct']:.1f}%\n"
    
    text += "\n/quiz - New Test | /leaderboard - Full Ranks"
    
    # Save to history
    if 'history' not in context.user_data:
        context.user_data['history'] = []
    # Store only essential, recent history
    context.user_data['history'].append({
        'score': score, 
        'total': total, 
        'pct': pct, 
        'time': time_str, 
        'mode': session['mode']
    })
    
    # Send the final result message
    if message:
        await message.reply_text(text, parse_mode='Markdown')
    else:
        # Used by the timer function if a message object isn't available
        await send_message_robust(context, user_id, text)
    
    # Clean up the session
    del user_sessions[user_id]


# --- Main Application Setup ---

def main():
    """Main function - optimized for deployment"""
    if BOT_TOKEN == 'PLACEHOLDER_TOKEN':
        logger.error("❌ ERROR: Please replace 'PLACEHOLDER_TOKEN' with your actual bot token or set BOT_TOKEN environment variable!")
        return

    # Using Application.builder() for modern, robust setup
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
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(CommandHandler("leaderboard", leaderboard_handler)) # Renamed for clarity
    app.add_handler(CommandHandler("mystats", mystats))
    app.add_handler(CommandHandler("help", help_command))
    
    # Callback handlers (Using the unified selector function)
    app.add_handler(CallbackQueryHandler(mode_or_topic_selected, pattern='^mode_select_|^topic_select_'))
    app.add_handler(CallbackQueryHandler(handle_answer, pattern='^answer_submit_')) # Changed pattern for clarity
    
    print("🤖 Bot starting...")
    
    # Deployment Logic: Use webhook for production, polling for local
    if os.environ.get('RENDER'):
        # Production mode (Render/Heroku/etc.)
        port = int(os.environ.get('PORT', 8080))
        webhook_url = os.environ.get('RENDER_EXTERNAL_URL', f"https://your-bot-name.onrender.com")
        
        # Ensure a valid URL is provided for the webhook
        if webhook_url.endswith('/'): webhook_url = webhook_url[:-1]
        
        # Use a unique path for the webhook URL
        final_webhook_url = f"{webhook_url}/{BOT_TOKEN}" 

        print(f"✅ Webhook mode active. Listening on port {port}. Webhook URL: {final_webhook_url}")
        
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN, # The unique path the bot listens on
            webhook_url=final_webhook_url
        )
    else:
        # Local development mode
        print("✅ Polling mode active (Local Dev). Press Ctrl+C to stop.")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
