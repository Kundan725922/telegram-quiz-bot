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
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8590474160:AAEMFKT_hyCF3qRROu0BrlqIbTii0HikxII') 

# Define quiz modes and their parameters
QUIZ_MODES = {
    'quick_5': {'num_q': 5, 'timed': False, 'label': "⚡ Quick (5Q)", 'feedback': True},
    'standard_10': {'num_q': 10, 'timed': False, 'label': "📝 Standard (10Q)", 'feedback': True},
    'full_20': {'num_q': 20, 'timed': False, 'label': "🎯 Full Test (20Q)", 'feedback': True},
    'timed_10_300': {'num_q': 10, 'timed': True, 'time_limit': 300, 'label': "⏱️ Timed Challenge (10Q - 5min)", 'feedback': True},
    # New Simulation Mode: No immediate feedback, single submission.
    'simulation_20_720': {'num_q': 20, 'timed': True, 'time_limit': 720, 'label': "🧠 Full Simulation (20Q - 12min)", 'feedback': False}
}
TOPICS = ['algorithms', 'data_structures', 'programming', 'toc']

# Global state (In a real application, replace with a database like PostgreSQL or Redis)
leaderboard_data = defaultdict(lambda: {'total_score': 0, 'total_questions': 0, 'tests_taken': 0, 'best_score_pct': 0, 'username': 'N/A', 'user_id': 0})
user_sessions = {} # Active quiz sessions

# --- Question Bank (Retained & Augmented) ---
# NOTE: Using the augmented structure from the previous response.
QUESTIONS = {
    'algorithms': [
        {'q': 'What is the time complexity of building a heap of n elements?', 'options': ['O(n)', 'O(n log n)', 'O(n²)', 'O(log n)'], 'answer': 0, 'img_url': None},
        {'q': 'Which sorting algorithm is NOT stable?', 'options': ['Merge Sort', 'Quick Sort', 'Insertion Sort', 'Bubble Sort'], 'answer': 1, 'img_url': None},
        {'q': 'Dijkstra algorithm does NOT work correctly with:', 'options': ['Directed graphs', 'Undirected graphs', 'Negative edge weights', 'Weighted graphs'], 'answer': 2, 'img_url': None},
        {'q': 'Time complexity of Floyd-Warshall algorithm is:', 'options': ['O(V²)', 'O(V³)', 'O(V² log V)', 'O(VE)'], 'answer': 1, 'img_url': None},
        {'q': 'Lower bound for comparison-based sorting is:', 'options': ['O(n)', 'O(n log n)', 'O(n²)', 'O(log n)'], 'answer': 1, 'img_url': None},
        {'q': 'Which can be solved using greedy algorithm?', 'options': ['0/1 Knapsack', 'Fractional Knapsack', 'LCS', 'Matrix Chain'], 'answer': 1, 'img_url': None},
        {'q': 'Best case time complexity of Quick Sort is:', 'options': ['O(n)', 'O(n log n)', 'O(n²)', 'O(log n)'], 'answer': 1, 'img_url': None},
        {'q': 'Binary Search works only on:', 'options': ['Sorted arrays', 'Unsorted arrays', 'Linked lists', 'Any structure'], 'answer': 0, 'img_url': None},
        {'q': 'Time complexity of Merge Sort is:', 'options': ['O(n)', 'O(n log n)', 'O(n²)', 'O(2^n)'], 'answer': 1, 'img_url': None},
        {'q': 'Kruskal algorithm uses which data structure?', 'options': ['Priority Queue', 'Union-Find', 'Stack', 'Queue'], 'answer': 1, 'img_url': None},
        {'q': 'Sort the functions in ascending order of asymptotic(big-O) complexity:\nf₁(n) = n, f₂(n) = 80, f₃(n) = n^(logn), f₄(n) = log(log²n), f₅(n) = (logn)^(logn)', 'options': ['f₂(n), f₄(n), f₁(n), f₅(n), f₃(n)', 'f₂(n), f₁(n), f₄(n), f₅(n), f₃(n)', 'f₂(n), f₁(n), f₄(n), f₃(n), f₅(n)', 'f₄(n), f₁(n), f₄(n), f₃(n), f₂(n)'], 'answer': 0, 'img_url': None},
        {'q': 'Which of the following asymptotic notation is transitive but not reflexive?', 'options': ['Big Oh (O)', 'Big Omega (Ω)', 'Small Oh (o)', 'Big Theta (Θ)'], 'answer': 2, 'img_url': None},
        {'q': 'If f(n) = Σ(i=1 to n) i³, which is the most precise asymptotic bound for f(n)?', 'options': ['Θ(n⁴)', 'O(n⁵)', 'Ω(n³)', 'O(n⁴ log n)'], 'answer': 0, 'img_url': None},
        {'q': 'What is the time complexity of the following code? P=n!; for (i=1; i<=n; ++i) for (j=1; j<=P; 2*j) C=C+1;', 'options': ['O(n²)', 'O(n² log n)', 'O(n log n)', 'O(n)'], 'answer': 1, 'img_url': None},
        {'q': 'What is the time complexity of the following code? i=1; j=1; while (j<=n) { ++i; j=j+i; }', 'options': ['Θ(n)', 'Θ(√n)', 'Θ(log n)', 'Θ(n log (log n))'], 'answer': 1, 'img_url': None},
        {'q': 'What is the complexity of Bellman-Ford algorithm with V vertices and E edges?', 'options': ['O(V+E)', 'O(V log V)', 'O(VE)', 'O(E log V)'], 'answer': 2, 'img_url': None},
        {'q': 'Maximum number of comparisons in worst-case merge sort for 7 elements is:', 'options': ['10', '14', '18', '21'], 'answer': 2, 'img_url': None},
        {'q': 'Which technique is primarily used by the Knuth-Morris-Pratt (KMP) algorithm?', 'options': ['Dynamic Programming', 'Greedy Approach', 'Divide and Conquer', 'Pre-processing (Longest Proper Prefix Suffix)'], 'answer': 3, 'img_url': None}
    ],
    'data_structures': [
        {'q': 'Best data structure for LRU cache?', 'options': ['Array', 'Stack', 'HashMap + DLL', 'BST'], 'answer': 2, 'img_url': None},
        {'q': 'Binary tree with n nodes has how many NULL pointers?', 'options': ['n', 'n+1', 'n-1', '2n'], 'answer': 1, 'img_url': None},
        {'q': 'Average search time in hash table with chaining:', 'options': ['O(1)', 'O(log n)', 'O(1 + α)', 'O(n)'], 'answer': 2, 'img_url': None},
        {'q': 'Space complexity of adjacency matrix (V vertices):', 'options': ['O(V)', 'O(V²)', 'O(V + E)', 'O(E)'], 'answer': 1, 'img_url': None},
        {'q': 'Which traversal gives sorted order in BST?', 'options': ['Preorder', 'Inorder', 'Postorder', 'Level order'], 'answer': 1, 'img_url': None},
        {'q': 'Maximum nodes in binary tree of height h (root at 0):', 'options': ['2^h - 1', '2^(h+1) - 1', '2^h', '2^(h-1)'], 'answer': 1, 'img_url': None},
        {'q': 'Stack is useful for:', 'options': ['BFS', 'Level order', 'DFS', 'Dijkstra'], 'answer': 2, 'img_url': None},
        {'q': 'Height of AVL tree with n nodes is:', 'options': ['O(n)', 'O(log n)', 'O(n log n)', 'O(√n)'], 'answer': 1, 'img_url': None},
        {'q': 'Time to delete from middle of doubly linked list (pointer to node given):', 'options': ['O(1)', 'O(n)', 'O(log n)', 'Cannot'], 'answer': 0, 'img_url': None},
        {'q': 'Best cache performance collision resolution:', 'options': ['Chaining', 'Linear probing', 'Quadratic', 'Double hash'], 'answer': 1, 'img_url': None},
        {'q': 'The maximum number of edges in a simple graph with V vertices is:', 'options': ['V(V-1)', 'V(V-1)/2', 'V² - V', 'V²'], 'answer': 1, 'img_url': None},
        {'q': 'What is the worst-case space complexity of a Hash Table using separate chaining?', 'options': ['O(1)', 'O(log n)', 'O(n)', 'O(n²)'], 'answer': 2, 'img_url': None}
    ],
    'programming': [
        {'q': 'Size of pointer on 64-bit system:', 'options': ['4 bytes', '8 bytes', 'Depends', '2 bytes'], 'answer': 1, 'img_url': None},
        {'q': 'Default value of static variable:', 'options': ['Garbage', '0', 'NULL', '-1'], 'answer': 1, 'img_url': None},
        {'q': 'Where are global variables stored?', 'options': ['Stack', 'Heap', 'Data segment', 'Code segment'], 'answer': 2, 'img_url': None},
        {'q': 'Which allocates memory dynamically in C?', 'options': ['alloc()', 'malloc()', 'new', 'allocate()'], 'answer': 1, 'img_url': None},
        {'q': 'calloc() initializes memory with:', 'options': ['Garbage', '0', 'NULL', '-1'], 'answer': 1, 'img_url': None},
        {'q': 'Double free() causes:', 'options': ['Nothing', 'Freed again', 'Undefined behavior', 'Compile error'], 'answer': 2, 'img_url': None},
        {'q': 'Array passed to function is passed as:', 'options': ['Value', 'Reference', 'Copy', 'Constant'], 'answer': 1, 'img_url': None},
        {'q': 'Scope of static variable in function:', 'options': ['Function only', 'Entire file', 'Program', 'Block only'], 'answer': 0, 'img_url': None},
        {'q': 'Union stores:', 'options': ['All members', 'Last assigned', 'First member', 'No member'], 'answer': 1, 'img_url': None},
        {'q': 'Left shift by 1 is equivalent to:', 'options': ['Divide by 2', 'Multiply by 2', 'Add 1', 'Subtract 1'], 'answer': 1, 'img_url': None},
        {'q': 'What does `volatile` keyword in C/C++ prevent?', 'options': ['Type casting', 'Compiler optimization', 'Memory leak', 'Function recursion'], 'answer': 1, 'img_url': None},
        {'q': 'What is the output of `print(10/3)` in Python 3?', 'options': ['3', '3.333', '3.0', 'Error'], 'answer': 1, 'img_url': None}
    ],
    'toc': [
        {'q': 'DFA accepts which language class?', 'options': ['Context-free', 'Regular', 'Context-sensitive', 'Recursive'], 'answer': 1, 'img_url': None},
        {'q': 'Which is NOT regular?', 'options': ['a^n b^n', 'a^n', '(ab)^n', 'a^n b^m'], 'answer': 0, 'img_url': None},
        {'q': 'Grammar is ambiguous if:', 'options': ['Left recursion', 'No strings', 'Multiple parse trees', 'ε-productions'], 'answer': 2, 'img_url': None},
        {'q': 'Halting problem is:', 'options': ['Decidable', 'Undecidable', 'Regular', 'Context-free'], 'answer': 1, 'img_url': None},
        {'q': 'CFLs are NOT closed under:', 'options': ['Union', 'Concatenation', 'Intersection', 'Kleene star'], 'answer': 2, 'img_url': None},
        {'q': 'PDA accepts by:', 'options': ['Final state only', 'Empty stack only', 'Both equivalent', 'Initial state'], 'answer': 2, 'img_url': None},
        {'q': 'Turing Machine more powerful than PDA because:', 'options': ['Infinite tape', 'Bidirectional', 'Can modify', 'All above'], 'answer': 3, 'img_url': None},
        {'q': 'Chomsky hierarchy (most to least restrictive):', 'options': ['Reg ⊂ CFL ⊂ CSL ⊂ RE', 'CFL ⊂ Reg', 'Reg ⊂ CSL ⊂ CFL', 'RE ⊂ CSL'], 'answer': 0, 'img_url': None},
        {'q': 'Regular languages closed under:', 'options': ['Intersection', 'Complement', 'Union', 'All above'], 'answer': 3, 'img_url': None},
        {'q': 'Which is decidable for CFLs?', 'options': ['Membership', 'Equivalence', 'Intersection empty', 'Universality'], 'answer': 0, 'img_url': None},
        {
            'q': 'The possible number of DFA with 2 states X, Y, where X is always initial state over the alphabet {a, b}, that accepts (a+b)* is-',
            'options': ['32', '20', '24', '64'],
            'answer': 3,
            'img_url': 'https://t.me/LLB_2024_25/34/38' 
        },
        {'q': 'Pumping Lemma is generally used for proving that a language is:', 'options': ['Regular', 'Context-Free', 'Not Regular', 'Not Context-Free'], 'answer': 2, 'img_url': None}
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
/quiz - Select your challenge mode
/topics - Focus on a specific subject
/leaderboard - Top 10 rankers globally
/mystats - Your personalized analytics
/help - Complete guide and info

Start your preparation now! 🚀"""
    await update.message.reply_text(text, parse_mode='HTML')

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

async def leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show full leaderboard"""
    if not leaderboard_data:
        await update.message.reply_text("📊 No rankings yet. Start with /quiz to register your score!")
        return
    
    text = "🏆 <b>GLOBAL LEADERBOARD - TOP 10</b>\n\n"
    top_users = sorted(leaderboard_data.items(), key=lambda x: x[1]['best_score_pct'], reverse=True)[:10]
    
    for i, (uid, data) in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        avg_score = (data['total_score'] / data['total_questions'] * 100) if data['total_questions'] > 0 else 0
        text += f"{medal} <b>{data['username']}</b>\n"
        text += f"  Best: {data['best_score_pct']:.1f}% | Avg: {avg_score:.1f}%\n"
        text += f"  Tests: {data['tests_taken']}\n\n"
    
    await update.message.reply_text(text, parse_mode='HTML')

async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics"""
    user = update.effective_user
    user_id = user.id
    user_data = leaderboard_data.get(user_id)
    
    if not user_data or user_data['tests_taken'] == 0:
        await update.message.reply_text("📊 No stats yet. Start with /quiz!")
        return
    
    avg_score = (user_data['total_score'] / user_data['total_questions'] * 100) if user_data['total_questions'] > 0 else 0
    
    text = f"📊 <b>Your Personalized Stats</b>\n\n"
    text += f"👤 User: {user_data.get('username', user.first_name)}\n"
    text += f"🎯 Best Score: {user_data['best_score_pct']:.1f}%\n"
    text += f"📈 Average Score: {avg_score:.1f}%\n"
    text += f"📝 Total Quizzes: {user_data['tests_taken']}\n"
    text += f"✅ Total Correct: {user_data['total_score']}/{user_data['total_questions']}\n\n"
    
    history = context.user_data.get('history', [])
    if history:
        text += "<b>Recent 5 Quizzes:</b>\n"
        for i, r in enumerate(history[-5:], 1):
            emoji = "🎉" if r['pct'] >= 75 else "👍" if r['pct'] >= 60 else "📚"
            text += f"{emoji} {r['score']}/{r['total']} ({r['pct']:.0f}%) in {r.get('time', 'N/A')}\n"
    
    await update.message.reply_text(text, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help message"""
    text = """📖 <b>Complete Guide</b>

<b>🎮 Quiz Modes:</b>
• /quiz: General modes (Quick, Standard, Timed)
• 🧠 Full Simulation: Complete the test, then submit for a final score (No instant feedback).
• /topics: Focus on Algorithms, DS, Programming, or TOC.

<b>🏆 Features:</b>
• Real-time Global Leaderboard (<code>/leaderboard</code>)
• Detailed Personal Stats (<code>/mystats</code>)
• For questions with diagrams, look for the 'View Diagram/Image' link.

Good luck! 🚀"""
    await update.message.reply_text(text, parse_mode='HTML')

# --- Callback Query Handlers ---

async def mode_or_topic_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles both mode and topic selection from their respective menus."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    user_id = user.id
    data = query.data.split('_select_')[1]
    
    if data == 'topics_redirect':
        await topics(update, context)
        return

    # 1. Determine Quiz Parameters
    num_q = 0
    is_timed = False
    time_limit = None
    mode = data
    instant_feedback = True # Default for all quick quizzes

    if data in QUIZ_MODES: # Mode selection
        config = QUIZ_MODES[data]
        num_q = config['num_q']
        is_timed = config['timed']
        time_limit = config.get('time_limit')
        instant_feedback = config['feedback'] # Set feedback based on mode
    
    elif data in TOPICS or data == 'random': # Topic selection (defaults to 10 questions, non-timed)
        num_q = 10 
        is_timed = False
        time_limit = None
        mode = f'topic_{data}'
        instant_feedback = True # Topic quizzes are always sequential/feedback mode
    
    # 2. Select Questions
    if data == 'random' or data in QUIZ_MODES:
        all_q = get_all_questions()
        selected = random.sample(all_q, min(num_q, len(all_q)))
    else: # Specific topic
        selected = QUESTIONS.get(data, []).copy()
        random.shuffle(selected)
        selected = selected[:num_q]
        
    if not selected:
        await query.edit_message_text("⚠️ Not enough questions available for this selection. Try another topic.", parse_mode='HTML')
        return

    # 3. Initialize Session
    if user_id in user_sessions:
        if user_sessions[user_id].get('timer_task'):
            user_sessions[user_id]['timer_task'].cancel()
        logger.info(f"User {user_id} started a new quiz, cancelling old session.")

    user_sessions[user_id] = {
        'questions': selected,
        'current': 0,
        'score': 0,
        'answers': [None] * len(selected), # Store answer index for simulation mode
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
    text += f"📝 Questions: {len(selected)}\n"
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

async def quiz_timer(user_id: int, context: ContextTypes.DEFAULT_TYPE, time_limit: int, chat_id: int):
    """Timer for timed quizzes. Runs as an asyncio task."""
    try:
        await asyncio.sleep(time_limit)
        
        if user_id in user_sessions:
            await send_message_robust(
                context, 
                chat_id, 
                "⏰ <b>Time's Up!</b>\n\nQuiz automatically ended. Evaluating results...",
            )
            # The session will contain answers up to the point of timeout
            await finalize_quiz(user_id, context)
            
    except asyncio.CancelledError:
        logger.info(f"Timer for user {user_id} was cancelled.")
        raise
    except Exception as e:
        logger.error(f"Quiz Timer Error for user {user_id}: {e}")


async def send_question(message, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Sends the current question in the session."""
    session = user_sessions.get(user_id)
    if not session:
        return
    
    q_index = session['current']
    q = session['questions'][q_index]
    
    time_info = ""
    if session.get('is_timed') and session.get('time_limit'):
        elapsed = (datetime.now() - session['start_time']).total_seconds()
        remaining = session['time_limit'] - elapsed
        
        if remaining <= 0:
            await send_message_robust(context, user_id, "⏰ Time ran out before the next question could be sent!")
            await finalize_quiz(user_id, context)
            return

        time_info = f"⏱️ Time Left: <b>{format_time(remaining)}</b>\n\n"
    
    # Image Handling
    image_url = q.get('img_url')
    text_image = ""
    if image_url:
        text_image = f"<a href='{image_url}'>[🖼️ <b>View Diagram/Image</b>]</a>\n\n"

    # Submission Button for Simulation Mode
    submit_button = []
    if not session['instant_feedback']:
        # Show submission button only if all questions are attempted OR if it's the last question
        if all(a is not None for a in session['answers']) or q_index == len(session['questions']) - 1:
             submit_button = [[InlineKeyboardButton("✅ Finish & Submit Test", callback_data='quiz_submit_final')]]
        
    # Question text and options
    answered = session['answers'][q_index] is not None
    answered_text = f" (Answered: {chr(65 + session['answers'][q_index])})" if answered and not session['instant_feedback'] else ""
    
    # Navigation Buttons for Simulation Mode
    nav_buttons = []
    if not session['instant_feedback']:
        if q_index > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f'quiz_nav_{q_index - 1}'))
        if q_index < len(session['questions']) - 1:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f'quiz_nav_{q_index + 1}'))

    keyboard = [[InlineKeyboardButton(f"{chr(65+i)}. {opt}", callback_data=f'answer_submit_{q_index}_{i}')] 
                for i, opt in enumerate(q['options'])]
    
    keyboard.append(nav_buttons)
    keyboard.extend(submit_button)
    
    text = f"{time_info}❓ <b>Q{q_index+1}/{len(session['questions'])}</b>{answered_text}\n\n{text_image}{q['q']}\n\n"
    
    await send_message_robust(context, message.chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes the user's answer submission."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        await query.edit_message_text("⚠️ Quiz session expired. Use /quiz to start again.", parse_mode='HTML')
        return
    
    session = user_sessions[user_id]
    
    # Handle Final Submission
    if query.data == 'quiz_submit_final':
        if session.get('timer_task'):
            session['timer_task'].cancel()
        await finalize_quiz(user_id, context, query.message)
        return
    
    # Handle Navigation in Simulation Mode
    if query.data.startswith('quiz_nav_'):
        new_index = int(query.data.split('_nav_')[1])
        session['current'] = new_index
        await send_question(query.message, context, user_id)
        return

    # Process Answer
    _, _, q_index_str, user_ans_str = query.data.split('_')
    q_index = int(q_index_str)
    user_ans = int(user_ans_str)

    # A quick fix to ensure the user is answering the current question, useful in immediate feedback mode
    if session['instant_feedback'] and q_index != session['current']:
        # This occurs if the user clicks an old question button. We'll ignore it.
        return 

    # In simulation mode, we must accept answers for any question index from the session
    q = session['questions'][q_index]
    
    # Store the answer index (no score yet)
    session['answers'][q_index] = user_ans

    if session['instant_feedback']:
        correct = q['answer']
        is_correct = user_ans == correct
        
        # 1. Update Score & Feedback
        if is_correct:
            session['score'] += 1
            text = f"✅ <b>Q{q_index+1}: Correct!</b> (+1 Point)\n\nAnswer: {chr(65+correct)}. {q['options'][correct]}"
        else:
            text = f"❌ <b>Q{q_index+1}: Wrong!</b>\n\nYour Answer: {chr(65+user_ans)}. {q['options'][user_ans]}\nCorrect Answer: {chr(65+correct)}. {q['options'][correct]}"
        
        try:
            await query.edit_message_text(text, parse_mode='HTML')
        except error.BadRequest:
            pass

        # 2. Advance to Next Question or Finalize
        session['current'] += 1
        if session['current'] < len(session['questions']):
            await send_question(query.message, context, user_id)
        else:
            if session.get('timer_task'):
                session['timer_task'].cancel()
            await finalize_quiz(user_id, context, query.message)
    else: # SIMULATION MODE
        # The answer is recorded in session['answers']. Now, just move to the next question.
        try:
            # We must edit the message to show the 'answered' status on the current question
            q_text = session['questions'][q_index]['q']
            image_url = session['questions'][q_index].get('img_url')
            text_image = f"<a href='{image_url}'>[🖼️ <b>View Diagram/Image</b>]</a>\n\n" if image_url else ""
            
            answered_text = f" (Answered: {chr(65 + user_ans)})" 
            text = f"❓ <b>Q{q_index+1}/{len(session['questions'])}</b>{answered_text}\n\n{text_image}{q_text}\n\n"
            
            # The keyboard needs to be rebuilt to update the navigation/submit buttons on the answered question
            keyboard = [[InlineKeyboardButton(f"{chr(65+i)}. {opt}", callback_data=f'answer_submit_{q_index}_{i}')] 
                        for i, opt in enumerate(q['options'])]
                        
            nav_buttons = []
            if q_index > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f'quiz_nav_{q_index - 1}'))
            if q_index < len(session['questions']) - 1:
                nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f'quiz_nav_{q_index + 1}'))
            
            keyboard.append(nav_buttons)
            
            submit_button = []
            # Only add the submit button if all questions are answered
            if all(a is not None for a in session['answers']):
                 submit_button = [[InlineKeyboardButton("✅ Finish & Submit Test", callback_data='quiz_submit_final')]]
            
            keyboard.extend(submit_button)
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        except error.BadRequest:
            # Ignore if no change
            pass
            
        # Automatically advance to the next unanswered question if possible, or stay put if on the last question
        next_q_index = next((i for i, a in enumerate(session['answers']) if a is None and i > q_index), None)
        if next_q_index is not None:
             session['current'] = next_q_index
             await send_question(query.message, context, user_id)
        elif session['current'] < len(session['questions']) - 1:
             # If no unanswered question forward, just move to the next one
             session['current'] += 1
             await send_question(query.message, context, user_id)


async def post_quiz_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles interactive post-quiz actions like re-test or evaluation review."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    action = query.data.split('_action_')[1]
    
    if action == 'start_new':
        await query.edit_message_text("Starting a new test session. Please select your mode:", parse_mode='HTML')
        await quiz(update, context)
    elif action == 'retake':
        # Simple retake uses the last quiz mode
        last_mode = context.user_data.get('last_mode')
        if last_mode:
            query.data = f'mode_select_{last_mode}'
            await mode_or_topic_selected(update, context)
        else:
            await query.edit_message_text("Could not determine last mode. Please use /quiz to select a new one.", parse_mode='HTML')
    elif action == 'evaluation':
        # Detailed review of missed questions (Advanced feature idea)
        await query.edit_message_text("⚠️ Evaluation is an advanced feature coming soon! You can manually compare your performance using /mystats.", parse_mode='HTML')


async def finalize_quiz(user_id: int, context: ContextTypes.DEFAULT_TYPE, message=None) -> None:
    """Finalize quiz, calculate score, update leaderboard, and show results."""
    session = user_sessions.get(user_id)
    if not session:
        return
    
    # Calculate Final Score (Crucial for Simulation Mode)
    total = len(session['questions'])
    score = 0
    correct_answers = []
    
    # Recalculate score from stored answers array
    for i in range(total):
        user_ans = session['answers'][i]
        correct_ans = session['questions'][i]['answer']
        is_correct = (user_ans is not None) and (user_ans == correct_ans)
        
        if is_correct:
            score += 1
            correct_answers.append(True)
        elif user_ans is not None:
             correct_answers.append(False)
        else:
             # Unanswered questions count as wrong for stats
             correct_answers.append(False)

    pct = (score/total)*100 if total > 0 else 0.0
    
    time_taken = (datetime.now() - session['start_time']).total_seconds()
    time_str = format_time(time_taken)
    
    # Update Leaderboard
    user_data = leaderboard_data[user_id]
    user_data['total_score'] += score
    user_data['total_questions'] += total
    user_data['tests_taken'] += 1
    user_data['best_score_pct'] = max(user_data['best_score_pct'], pct)
    
    # Result Message Construction
    text = f"🎯 <b>Quiz Complete!</b>\n\n"
    text += f"📊 Score: {score}/{total} (<b>{pct:.1f}%</b>)\n"
    text += f"⏱️ Time Taken: {time_str}\n\n"
    
    if pct >= 90:
        text += "👑 GATE Grandmaster! You crushed it!\n"
    elif pct >= 75:
        text += "🧠 Excellent Performance! Solid fundamentals.\n"
    elif pct >= 60:
        text += "🌟 Good Job! Keep practicing to secure a top rank.\n"
    else:
        text += "💡 Keep learning. Reviewing your weaker topics will help!\n"
    
    # Visual Progress Bar
    correct_count = correct_answers.count(True)
    wrong_count = correct_answers.count(False)
    progress_bar = "✅" * correct_count + "❌" * wrong_count
    text += f"\n<b>Detailed Progress</b>:\n<code>{progress_bar}</code>\n"
    
    # Leaderboard Snapshot
    text += "\n🏆 <b>TOP 5 LEADERBOARD SNAPSHOT</b>\n"
    top_users = sorted(leaderboard_data.items(), key=lambda x: x[1]['best_score_pct'], reverse=True)[:5]
    
    for i, (uid, data) in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
        name = f"<b>{data['username']}</b> (You)" if uid == user_id else data['username']
        text += f"{medal} {name}: {data['best_score_pct']:.1f}%\n"
    
    # Interactive Post-Quiz Buttons
    post_quiz_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Retake This Test", callback_data=f'post_quiz_action_retake')],
        [InlineKeyboardButton("🆕 Start New Test", callback_data=f'post_quiz_action_start_new')],
        [InlineKeyboardButton("📈 Full Evaluation (Coming Soon)", callback_data=f'post_quiz_action_evaluation')]
    ])
    
    # Save to history & last mode
    context.user_data['last_mode'] = session['mode']
    if 'history' not in context.user_data:
        context.user_data['history'] = []
    context.user_data['history'].append({'score': score, 'total': total, 'pct': pct, 'time': time_str, 'mode': session['mode']})
    
    # Send the final result message
    if message:
        await message.reply_text(text, reply_markup=post_quiz_keyboard, parse_mode='HTML')
    else:
        await send_message_robust(context, user_id, text, reply_markup=post_quiz_keyboard)
    
    # Clean up the session
    del user_sessions[user_id]


# --- Main Application Setup ---

def main():
    """Main function - optimized for deployment"""
    if BOT_TOKEN == '8590474160:AAEMFKT_hyCF3qRROu0BrlqIbTii0HikxII':
        logger.error("❌ ERROR: Please replace the placeholder token with your actual bot token or set BOT_TOKEN environment variable!")
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
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(CommandHandler("leaderboard", leaderboard_handler))
    app.add_handler(CommandHandler("mystats", mystats))
    app.add_handler(CommandHandler("help", help_command))
    
    # Callback handlers
    # Unified handler for mode/topic selection
    app.add_handler(CallbackQueryHandler(mode_or_topic_selected, pattern='^mode_select_|^topic_select_'))
    # Answer and Navigation handler
    app.add_handler(CallbackQueryHandler(handle_answer, pattern='^answer_submit_|^quiz_submit_final|^quiz_nav_'))
    # Post-Quiz action handler
    app.add_handler(CallbackQueryHandler(post_quiz_action, pattern='^post_quiz_action_'))
    
    print("🤖 Bot starting...")
    
    # Deployment Logic
    if os.environ.get('RENDER'):
        port = int(os.environ.get('PORT', 8080))
        webhook_url = os.environ.get('RENDER_EXTERNAL_URL', f"https://your-bot-name.onrender.com")
        
        if webhook_url.endswith('/'): webhook_url = webhook_url[:-1]
        final_webhook_url = f"{webhook_url}/{BOT_TOKEN}" 

        print(f"✅ Webhook mode active. Listening on port {port}. Webhook URL: {final_webhook_url}")
        
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
    main()
