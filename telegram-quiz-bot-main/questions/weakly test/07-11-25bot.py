import logging
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, error
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random
from collections import defaultdict
import sys

# Check Python version
if sys.version_info >= (3, 13):
    print("⚠️ WARNING: Python 3.13 detected. Telegram bot library works best with Python 3.8-3.12")

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration & Initialization ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Define quiz modes and their parameters
QUIZ_MODES = {
    'quick_5': {'num_q': 5, 'timed': False, 'label': "⚡ Quick (5Q)", 'feedback': True},
    'standard_10': {'num_q': 10, 'timed': False, 'label': "📝 Standard (10Q)", 'feedback': True},
    'standard_15': {'num_q': 15, 'timed': False, 'label': "📚 Extended (15Q)", 'feedback': True},
    'full_25': {'num_q': 25, 'timed': False, 'label': "🎯 Full Test (25Q)", 'feedback': True},
    'timed_15_450': {'num_q': 15, 'timed': True, 'time_limit': 450, 'label': "⏱️ Timed Challenge (15Q - 7.5min)", 'feedback': True},
    'simulation_25_900': {'num_q': 25, 'timed': True, 'time_limit': 900, 'label': "🧠 Full Simulation (25Q - 15min)", 'feedback': False}
}

TOPICS = ['algorithms', 'data_structures', 'operating_systems', 'databases', 'networks', 
          'toc', 'digital_logic', 'coa', 'discrete_math', 'compiler_design']

# Global state
leaderboard_data = defaultdict(lambda: {'total_score': 0, 'total_questions': 0, 'tests_taken': 0, 
                                       'best_score_pct': 0, 'username': 'N/A', 'user_id': 0, 
                                       'topic_stats': defaultdict(lambda: {'correct': 0, 'total': 0})})
user_sessions = {}

# --- EXPANDED QUESTION BANK ---
QUESTIONS = {
    'algorithms': [
        {'q': 'What is the time complexity of building a max-heap from an unsorted array of n elements using the bottom-up approach?', 
         'options': ['O(n log n)', 'O(n²)', 'O(n)', 'O(log n)'], 'answer': 2, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'Consider the following recurrence relation: T(n) = 2T(n/2) + n log n. What is the time complexity using Master\'s theorem?', 
         'options': ['O(n log n)', 'O(n log² n)', 'O(n²)', 'Master\'s theorem is not applicable'], 'answer': 1, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'Which sorting algorithm is NOT stable?', 
         'options': ['Merge Sort', 'Quick Sort', 'Insertion Sort', 'Bubble Sort'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Dijkstra algorithm does NOT work correctly with:', 
         'options': ['Directed graphs', 'Undirected graphs', 'Negative edge weights', 'Weighted graphs'], 'answer': 2, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Time complexity of Floyd-Warshall algorithm is:', 
         'options': ['O(V²)', 'O(V³)', 'O(V² log V)', 'O(VE)'], 'answer': 1, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'Lower bound for comparison-based sorting is:', 
         'options': ['O(n)', 'O(n log n)', 'O(n²)', 'O(log n)'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Best case time complexity of Quick Sort is:', 
         'options': ['O(n)', 'O(n log n)', 'O(n²)', 'O(log n)'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Binary Search works only on:', 
         'options': ['Sorted arrays', 'Unsorted arrays', 'Linked lists', 'Any structure'], 'answer': 0, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'What is the complexity of Bellman-Ford algorithm with V vertices and E edges?', 
         'options': ['O(V+E)', 'O(V log V)', 'O(VE)', 'O(E log V)'], 'answer': 2, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'Which technique is primarily used by the Knuth-Morris-Pratt (KMP) algorithm?', 
         'options': ['Dynamic Programming', 'Greedy Approach', 'Divide and Conquer', 'Pre-processing (Longest Proper Prefix Suffix)'], 
         'answer': 3, 'type': 'MCQ', 'marks': 2, 'img_url': None},
    ],
    
    'data_structures': [
        {'q': 'Which of the following statements is/are TRUE about AVL trees? (Select all that apply)', 
         'options': ['The height of an AVL tree with n nodes is O(log n)', 'Every AVL tree is a binary search tree', 
                    'Insertion in an AVL tree always requires at most one rotation', 'The balance factor of every node is -1, 0, or 1'], 
         'answer': [0, 1, 3], 'type': 'MSQ', 'marks': 2, 'img_url': None},
        
        {'q': 'A queue is implemented using two stacks S1 and S2. Enqueue operation is done by pushing to S1. What is the amortized time complexity of the dequeue operation?', 
         'options': ['O(1)', 'O(n)', 'O(log n)', 'O(n²)'], 'answer': 0, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Best data structure for LRU cache implementation?', 
         'options': ['Array', 'Stack', 'HashMap + Doubly Linked List', 'BST'], 'answer': 2, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'Binary tree with n nodes has how many NULL pointers?', 
         'options': ['n', 'n+1', 'n-1', '2n'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Average search time in hash table with chaining (load factor α):', 
         'options': ['O(1)', 'O(log n)', 'O(1 + α)', 'O(n)'], 'answer': 2, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'Which traversal gives sorted order in BST?', 
         'options': ['Preorder', 'Inorder', 'Postorder', 'Level order'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Maximum nodes in binary tree of height h (root at level 0):', 
         'options': ['2^h - 1', '2^(h+1) - 1', '2^h', '2^(h-1)'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Height of AVL tree with n nodes is:', 
         'options': ['O(n)', 'O(log n)', 'O(n log n)', 'O(√n)'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'The maximum number of edges in a simple graph with V vertices is:', 
         'options': ['V(V-1)', 'V(V-1)/2', 'V² - V', 'V²'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
    ],
    
    'operating_systems': [
        {'q': 'Which of the following scheduling algorithms can cause starvation? (Select all that apply)', 
         'options': ['First Come First Serve (FCFS)', 'Shortest Job First (SJF)', 'Round Robin (RR)', 'Priority Scheduling (without aging)'], 
         'answer': [1, 3], 'type': 'MSQ', 'marks': 2, 'img_url': None},
        
        {'q': 'In a paging system with page size 4KB and page table entry size 4 bytes, what is the maximum size of logical address space if single-level paging is used and page table must fit in one page?', 
         'options': ['4 MB', '4 GB', '16 MB', '1 MB'], 'answer': 0, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'A CPU has a cache with access time 2 ns and main memory with access time 100 ns. If the cache hit ratio is 80%, what is the average memory access time?', 
         'options': ['21.6 ns', '22 ns', '20 ns', '82 ns'], 'answer': 1, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'In a 5-stage pipeline (IF, ID, EX, MEM, WB), what is the maximum speedup achievable compared to non-pipelined execution (ignoring pipeline hazards)?', 
         'options': ['2×', '5×', '10×', '4×'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Thrashing occurs when:', 
         'options': ['CPU is too fast', 'Too many page faults', 'Memory is full', 'Disk is slow'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Banker\'s algorithm is used for:', 
         'options': ['Deadlock prevention', 'Deadlock avoidance', 'Deadlock detection', 'Deadlock recovery'], 'answer': 1, 'type': 'MCQ', 'marks': 2, 'img_url': None},
    ],
    
    'databases': [
        {'q': 'Consider a relation R(A,B,C,D,E) with functional dependencies: A → B, BC → E, ED → A. Which of the following is/are candidate keys? (Select all that apply)', 
         'options': ['ACD', 'BCD', 'ECD', 'ABCDE'], 'answer': [0, 2], 'type': 'MSQ', 'marks': 2, 'img_url': None},
        
        {'q': 'What is the minimum number of tables required to represent a many-to-many relationship between two entities in a relational database?', 
         'options': ['1', '2', '3', '4'], 'answer': 2, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Which normal form eliminates transitive dependencies?', 
         'options': ['1NF', '2NF', '3NF', 'BCNF'], 'answer': 2, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'ACID properties stand for:', 
         'options': ['Atomicity, Consistency, Isolation, Durability', 'Access, Control, Integrity, Data', 
                    'Atomicity, Control, Integrity, Durability', 'Access, Consistency, Isolation, Data'], 
         'answer': 0, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Which isolation level prevents dirty reads but allows phantom reads?', 
         'options': ['Read Uncommitted', 'Read Committed', 'Repeatable Read', 'Serializable'], 'answer': 1, 'type': 'MCQ', 'marks': 2, 'img_url': None},
    ],
    
    'networks': [
        {'q': 'Which of the following protocols operate at the Transport Layer of the OSI model? (Select all that apply)', 
         'options': ['TCP', 'UDP', 'ICMP', 'SCTP'], 'answer': [0, 1, 3], 'type': 'MSQ', 'marks': 2, 'img_url': None},
        
        {'q': 'A network has a bandwidth of 10 Mbps and propagation delay of 20 ms. What is the bandwidth-delay product?', 
         'options': ['200 kb', '25 KB', '200 Kb', '2 Mb'], 'answer': 1, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'In IPv4, what is the maximum number of hops a packet can take before being discarded?', 
         'options': ['128', '255', '256', 'Unlimited'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Stop-and-Wait protocol efficiency formula is:', 
         'options': ['1/(1+2a)', '1/(1+a)', '2/(1+2a)', 'a/(1+a)'], 'answer': 0, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'Which layer is responsible for routing in OSI model?', 
         'options': ['Data Link', 'Network', 'Transport', 'Session'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
    ],
    
    'toc': [
        {'q': 'Which of the following languages is/are regular? (Select all that apply)', 
         'options': ['{aⁿbⁿ | n ≥ 0}', '{aⁿ | n is a prime number}', '{w | w has equal 0s and 1s}', '{aⁿbᵐ | n ≥ 0, m ≥ 0}'], 
         'answer': [3], 'type': 'MSQ', 'marks': 2, 'img_url': None},
        
        {'q': 'A Turing machine that halts on all inputs is called:', 
         'options': ['Universal Turing Machine', 'Decider', 'Recognizer', 'Non-deterministic Turing Machine'], 
         'answer': 1, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'Which of the following problems is undecidable?', 
         'options': ['Whether a CFG is ambiguous', 'Whether a DFA accepts any string', 
                    'Whether two DFAs accept same language', 'Whether a regex matches a string'], 
         'answer': 0, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'DFA accepts which language class?', 
         'options': ['Context-free', 'Regular', 'Context-sensitive', 'Recursive'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'CFLs are NOT closed under:', 
         'options': ['Union', 'Concatenation', 'Intersection', 'Kleene star'], 'answer': 2, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Pumping Lemma is generally used for proving that a language is:', 
         'options': ['Regular', 'Context-Free', 'Not Regular', 'Not Context-Free'], 'answer': 2, 'type': 'MCQ', 'marks': 1, 'img_url': None},
    ],
    
    'digital_logic': [
        {'q': 'Which of the following flip-flops can be used to build a counter? (Select all that apply)', 
         'options': ['SR flip-flop', 'JK flip-flop', 'D flip-flop', 'T flip-flop'], 
         'answer': [1, 2, 3], 'type': 'MSQ', 'marks': 2, 'img_url': None},
        
        {'q': 'Number of minterms for a 3-variable boolean function:', 
         'options': ['6', '8', '9', '16'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'A 4-to-1 multiplexer requires how many select lines?', 
         'options': ['1', '2', '3', '4'], 'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
    ],
    
    'coa': [
        {'q': 'In a 5-stage pipeline, data hazards can be resolved using:', 
         'options': ['Forwarding only', 'Stalling only', 'Both forwarding and stalling', 'Neither'], 
         'answer': 2, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'RISC architecture is characterized by:', 
         'options': ['Complex instructions', 'Simple instructions', 'Variable length instructions', 'Microprogramming'], 
         'answer': 1, 'type': 'MCQ', 'marks': 1, 'img_url': None},
    ],
    
    'discrete_math': [
        {'q': 'Let G be a simple connected graph with 10 vertices and 21 edges. Which of the following is/are TRUE? (Select all that apply)', 
         'options': ['G must contain at least one cycle', 'G can be a tree', 'G must be planar', 'The chromatic number of G is at most 5'], 
         'answer': [0, 3], 'type': 'MSQ', 'marks': 2, 'img_url': None},
        
        {'q': 'How many different binary search trees can be constructed using the keys 1, 2, 3, 4?', 
         'options': ['12', '14', '16', '24'], 'answer': 1, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'What is the coefficient of x⁷ in the expansion of (1 + x)¹⁰?', 
         'options': ['120', '210', '252', '720'], 'answer': 0, 'type': 'MCQ', 'marks': 1, 'img_url': None},
        
        {'q': 'Number of permutations of n distinct objects is:', 
         'options': ['n!', '2^n', 'n²', 'n^n'], 'answer': 0, 'type': 'MCQ', 'marks': 1, 'img_url': None},
    ],
    
    'compiler_design': [
        {'q': 'Which of the following can be performed during lexical analysis? (Select all that apply)', 
         'options': ['Removing comments', 'Checking type compatibility', 'Removing white spaces', 'Detecting undeclared variables'], 
         'answer': [0, 2], 'type': 'MSQ', 'marks': 2, 'img_url': None},
        
        {'q': 'Consider the grammar: S → aSb | ab. Which statement is TRUE?', 
         'options': ['The grammar is LL(1)', 'The grammar is ambiguous', 'The grammar generates {aⁿbⁿ | n ≥ 1}', 'The grammar is left-recursive'], 
         'answer': 2, 'type': 'MCQ', 'marks': 2, 'img_url': None},
        
        {'q': 'Which phase generates intermediate code?', 
         'options': ['Lexical Analysis', 'Syntax Analysis', 'Semantic Analysis', 'Intermediate Code Generation'], 
         'answer': 3, 'type': 'MCQ', 'marks': 1, 'img_url': None},
    ],
}

# --- Utility Functions ---

def get_all_questions():
    """Compiles all questions from all topics."""
    all_q = []
    for topic, qs in QUESTIONS.items():
        for q in qs:
            q_copy = q.copy()
            q_copy['topic'] = topic
            all_q.append(q_copy)
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
            parse_mode='HTML'
        )
    except error.TelegramError as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")

def get_topic_name(topic_key):
    """Convert topic key to display name"""
    topic_names = {
        'algorithms': 'Algorithms',
        'data_structures': 'Data Structures',
        'operating_systems': 'Operating Systems',
        'databases': 'Databases',
        'networks': 'Computer Networks',
        'toc': 'Theory of Computation',
        'digital_logic': 'Digital Logic',
        'coa': 'Computer Organization',
        'discrete_math': 'Discrete Mathematics',
        'compiler_design': 'Compiler Design'
    }
    return topic_names.get(topic_key, topic_key.title())

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = f"""🎓 <b>Welcome {user.first_name} to GATE CSE Master Quiz Bot!</b>

Ready to ace GATE 2026? This bot offers:
✅ MCQ & MSQ questions (just like real GATE!)
✅ 10+ topics covering complete GATE CSE syllabus
✅ Multiple quiz modes (Quick, Timed, Simulation)
✅ Global leaderboard & detailed analytics
✅ Topic-wise performance tracking

📚 <b>Quick Start Commands:</b>
/quiz - Start practice with different modes
/topics - Practice specific subjects
/leaderboard - See top 10 rankers
/mystats - Your performance analytics
/topicstats - Your topic-wise breakdown
/help - Detailed guide

🚀 Start your GATE preparation journey now!"""
    await update.message.reply_text(text, parse_mode='HTML')

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show quiz mode selection"""
    keyboard = [[InlineKeyboardButton(mode_data['label'], callback_data=f'mode_select_{mode_key}')] 
                for mode_key, mode_data in QUIZ_MODES.items()]
    
    keyboard.append([InlineKeyboardButton("➡️ Choose Topic Instead", callback_data='topics_redirect')]) 
    
    await update.message.reply_text(
        "🎮 <b>Select Quiz Mode:</b>\n\nChoose your challenge level:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show topic selection"""
    keyboard = [
        [InlineKeyboardButton("🔢 Algorithms", callback_data='topic_select_algorithms')],
        [InlineKeyboardButton("📊 Data Structures", callback_data='topic_select_data_structures')],
        [InlineKeyboardButton("💾 Operating Systems", callback_data='topic_select_operating_systems')],
        [InlineKeyboardButton("🗄️ Databases (DBMS)", callback_data='topic_select_databases')],
        [InlineKeyboardButton("🌐 Computer Networks", callback_data='topic_select_networks')],
        [InlineKeyboardButton("🔤 Theory of Computation", callback_data='topic_select_toc')],
        [InlineKeyboardButton("⚡ Digital Logic", callback_data='topic_select_digital_logic')],
        [InlineKeyboardButton("🖥️ Computer Organization", callback_data='topic_select_coa')],
        [InlineKeyboardButton("➗ Discrete Mathematics", callback_data='topic_select_discrete_math')],
        [InlineKeyboardButton("🔧 Compiler Design", callback_data='topic_select_compiler_design')],
        [InlineKeyboardButton("🎲 Random Mix (All Topics)", callback_data='topic_select_random')]
    ]
    await update.message.reply_text('📚 <b>Choose Subject:</b>', reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

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
        text += f"   Best: {data['best_score_pct']:.1f}% | Avg: {avg_score:.1f}%\n"
        text += f"   Tests: {data['tests_taken']}\n\n"
    
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
    
    text = f"📊 <b>Your Performance Dashboard</b>\n\n"
    text += f"👤 User: {user_data.get('username', user.first_name)}\n"
    text += f"🎯 Best Score: {user_data['best_score_pct']:.1f}%\n"
    text += f"📈 Average Score: {avg_score:.1f}%\n"
    text += f"📝 Total Quizzes: {user_data['tests_taken']}\n"
    text += f"✅ Accuracy: {user_data['total_score']}/{user_data['total_questions']} questions\n\n"
    
    history = context.user_data.get('history', [])
    if history:
        text += "<b>📋 Recent 5 Quizzes:</b>\n"
        for i, r in enumerate(history[-5:], 1):
            emoji = "🎉" if r['pct'] >= 75 else "👍" if r['pct'] >= 60 else "📚"
            text += f"{emoji} {r['score']}/{r['total']} ({r['pct']:.0f}%) - {r.get('time', 'N/A')}\n"
    
    text += "\n💡 Use /topicstats to see subject-wise performance"
    await update.message.reply_text(text, parse_mode='HTML')

async def topicstats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show topic-wise statistics"""
    user = update.effective_user
    user_id = user.id
    user_data = leaderboard_data.get(user_id)
    
    if not user_data or user_data['tests_taken'] == 0:
        await update.message.reply_text("📊 No topic stats yet. Complete some topic-based quizzes!")
        return
    
    text = f"📚
