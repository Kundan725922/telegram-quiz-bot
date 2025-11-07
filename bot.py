"""
Enhanced GATE CSE Quiz Telegram Bot with Leaderboard & Advanced Features
Compatible with Python 3.8+ including 3.13
Deploy on Render.com for 24/7 operation
"""

import logging
import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random
from collections import defaultdict
import sys

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Check Python version
if sys.version_info >= (3, 13):
    logger.warning("Python 3.13 detected. Telegram bot library works best with Python 3.8-3.12")

# Get token from environment variable (for deployment) or use default
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8590474160:AAEMFKT_hyCF3qRROu0BrlqIbTii0HikxII')

# Global leaderboard storage (in production, use database)
leaderboard_data = defaultdict(lambda: {'total_score': 0, 'total_questions': 0, 'tests_taken': 0, 'best_score': 0, 'username': ''})

# Question Bank (Your existing questions)
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

user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = f"""🎓 *Welcome {user.first_name} to GATE CSE Quiz Bot!*

🆕 *NEW FEATURES:*
🏆 Leaderboard Rankings
⏱️ Timed Quiz Mode
📊 Custom Quiz Length
🎯 Performance Analytics

📚 *Commands:*
/quiz - Start quiz with options
/leaderboard - Top 10 rankers
/mystats - Your statistics
/topics - Choose specific topic
/help - Complete guide

Ready to compete? 🚀"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show quiz mode selection"""
    keyboard = [
        [InlineKeyboardButton("⚡ Quick (5Q)", callback_data='mode_quick_5')],
        [InlineKeyboardButton("📝 Standard (10Q)", callback_data='mode_standard_10')],
        [InlineKeyboardButton("🎯 Full Test (20Q)", callback_data='mode_full_20')],
        [InlineKeyboardButton("⏱️ Timed Challenge (10Q - 5min)", callback_data='mode_timed_10')],
        [InlineKeyboardButton("🔥 Speed Round (15Q - 7min)", callback_data='mode_timed_15')]
    ]
    await update.message.reply_text(
        "🎮 *Select Quiz Mode:*\n\nChoose difficulty and type:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔢 Algorithms", callback_data='topic_algorithms')],
        [InlineKeyboardButton("📊 Data Structures", callback_data='topic_data_structures')],
        [InlineKeyboardButton("💻 Programming", callback_data='topic_programming')],
        [InlineKeyboardButton("🔤 TOC", callback_data='topic_toc')],
        [InlineKeyboardButton("🎲 Random Mix", callback_data='topic_random')]
    ]
    await update.message.reply_text('📚 *Choose Topic:*', reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def mode_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quiz mode selection"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    mode = query.data.replace('mode_', '')
    
    # Parse mode
    if 'timed' in mode:
        is_timed = True
        num_q = int(mode.split('_')[1])
        time_limit = 300 if num_q == 10 else 420  # 5 or 7 minutes
    else:
        is_timed = False
        num_q = int(mode.split('_')[1])
        time_limit = None
    
    # Select questions
    all_q = []
    for qs in QUESTIONS.values():
        all_q.extend(qs)
    selected = random.sample(all_q, min(num_q, len(all_q)))
    
    user_sessions[user_id] = {
        'questions': selected,
        'current': 0,
        'score': 0,
        'answers': [],
        'is_timed': is_timed,
        'time_limit': time_limit,
        'start_time': datetime.now(),
        'mode': mode
    }
    
    text = f"🎯 *Quiz Started!*\n\n"
    text += f"📝 Questions: {num_q}\n"
    if is_timed:
        text += f"⏱️ Time Limit: {time_limit//60} minutes\n"
    text += f"\nGood luck! 💪"
    
    await query.edit_message_text(text, parse_mode='Markdown')
    
    # Start timer for timed mode
    if is_timed:
        asyncio.create_task(quiz_timer(user_id, context, time_limit))
    
    await send_question(query.message, context, user_id)

async def quiz_timer(user_id: int, context: ContextTypes.DEFAULT_TYPE, time_limit: int):
    """Timer for timed quizzes"""
    await asyncio.sleep(time_limit)
    
    if user_id in user_sessions:
        session = user_sessions[user_id]
        if session['is_timed'] and session['current'] < len(session['questions']):
            # Time's up!
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="⏰ *Time's Up!*\n\nQuiz ended. Here are your results:",
                    parse_mode='Markdown'
                )
                await finalize_quiz(user_id, context)
            except Exception as e:
                logger.error(f"Timer error: {e}")

async def topic_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    topic = query.data.replace('topic_', '')
    
    if topic == 'random':
        all_q = []
        for qs in QUESTIONS.values():
            all_q.extend(qs)
        selected = random.sample(all_q, 10)
    else:
        selected = QUESTIONS.get(topic, []).copy()
        random.shuffle(selected)
        selected = selected[:10]
    
    user_sessions[user_id] = {
        'questions': selected,
        'current': 0,
        'score': 0,
        'answers': [],
        'is_timed': False,
        'start_time': datetime.now(),
        'mode': f'topic_{topic}'
    }
    
    await query.edit_message_text(f"✅ Starting {topic.replace('_', ' ').title()} quiz! {len(selected)} questions")
    await send_question(query.message, context, user_id)

async def send_question(message, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    session = user_sessions.get(user_id)
    if not session:
        return
    
    q = session['questions'][session['current']]
    
    # Calculate time remaining for timed mode
    time_info = ""
    if session.get('is_timed'):
        elapsed = (datetime.now() - session['start_time']).total_seconds()
        remaining = session['time_limit'] - elapsed
        if remaining > 0:
            time_info = f"⏱️ Time: {int(remaining//60)}:{int(remaining%60):02d}\n\n"
    
    text = f"{time_info}❓ *Q{session['current']+1}/{len(session['questions'])}*\n\n{q['q']}\n\n"
    keyboard = [[InlineKeyboardButton(f"{chr(65+i)}. {opt}", callback_data=f'answer_{i}')] for i, opt in enumerate(q['options'])]
    
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        await query.edit_message_text("⚠️ Session expired. Use /quiz to start again")
        return
    
    session = user_sessions[user_id]
    
    # Check if time expired
    if session.get('is_timed'):
        elapsed = (datetime.now() - session['start_time']).total_seconds()
        if elapsed > session['time_limit']:
            await query.edit_message_text("⏰ Time expired!")
            await finalize_quiz(user_id, context)
            return
    
    q = session['questions'][session['current']]
    user_ans = int(query.data.replace('answer_', ''))
    correct = q['answer']
    is_correct = user_ans == correct
    
    if is_correct:
        session['score'] += 1
        text = f"✅ *Correct!*\n\nAnswer: {chr(65+correct)}. {q['options'][correct]}"
    else:
        text = f"❌ *Wrong!*\n\nYour answer: {chr(65+user_ans)}. {q['options'][user_ans]}\nCorrect: {chr(65+correct)}. {q['options'][correct]}"
    
    session['answers'].append(is_correct)
    await query.edit_message_text(text, parse_mode='Markdown')
    
    session['current'] += 1
    if session['current'] < len(session['questions']):
        await send_question(query.message, context, user_id)
    else:
        await finalize_quiz(user_id, context, query.message)

async def finalize_quiz(user_id: int, context: ContextTypes.DEFAULT_TYPE, message=None):
    """Finalize quiz and show results with leaderboard"""
    session = user_sessions.get(user_id)
    if not session:
        return
    
    score = session['score']
    total = len(session['questions'])
    pct = (score/total)*100 if total > 0 else 0
    
    # Calculate time taken
    time_taken = (datetime.now() - session['start_time']).total_seconds()
    time_str = f"{int(time_taken//60)}:{int(time_taken%60):02d}"
    
    # Update leaderboard
    user = await context.bot.get_chat(user_id)
    username = user.username or user.first_name
    
    leaderboard_data[user_id]['username'] = username
    leaderboard_data[user_id]['total_score'] += score
    leaderboard_data[user_id]['total_questions'] += total
    leaderboard_data[user_id]['tests_taken'] += 1
    leaderboard_data[user_id]['best_score'] = max(leaderboard_data[user_id]['best_score'], pct)
    
    text = f"🎯 *Quiz Complete!*\n\n"
    text += f"📊 Score: {score}/{total} ({pct:.1f}%)\n"
    text += f"⏱️ Time: {time_str}\n\n"
    
    if pct >= 90:
        text += "🌟 Outstanding! You're a GATE expert!\n"
    elif pct >= 75:
        text += "🎉 Excellent work! Keep it up!\n"
    elif pct >= 60:
        text += "👍 Good job! Practice more!\n"
    else:
        text += "📚 Keep learning! You'll improve!\n"
    
    text += "\n"
    for i, ans in enumerate(session['answers']):
        text += "✅" if ans else "❌"
        if (i+1) % 5 == 0:
            text += "\n"
    
    # Show top 5 leaderboard
    text += "\n\n🏆 *TOP 5 LEADERBOARD*\n\n"
    top_users = sorted(leaderboard_data.items(), key=lambda x: x[1]['best_score'], reverse=True)[:5]
    
    for i, (uid, data) in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
        text += f"{medal} {data['username']}: {data['best_score']:.1f}% (Tests: {data['tests_taken']})\n"
    
    text += "\n/quiz - Try again\n/leaderboard - Full rankings"
    
    # Save to history
    if 'history' not in context.user_data:
        context.user_data['history'] = []
    context.user_data['history'].append({'score': score, 'total': total, 'pct': pct, 'time': time_str})
    
    if message:
        await message.reply_text(text, parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode='Markdown')
    
    del user_sessions[user_id]

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show full leaderboard"""
    if not leaderboard_data:
        await update.message.reply_text("📊 No rankings yet. Start with /quiz!")
        return
    
    text = "🏆 *GLOBAL LEADERBOARD - TOP 10*\n\n"
    top_users = sorted(leaderboard_data.items(), key=lambda x: x[1]['best_score'], reverse=True)[:10]
    
    for i, (uid, data) in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        avg_score = (data['total_score'] / data['total_questions'] * 100) if data['total_questions'] > 0 else 0
        text += f"{medal} *{data['username']}*\n"
        text += f"   Best: {data['best_score']:.1f}% | Avg: {avg_score:.1f}%\n"
        text += f"   Tests: {data['tests_taken']}\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    user_id = update.effective_user.id
    user_data = leaderboard_data.get(user_id)
    
    if not user_data or user_data['tests_taken'] == 0:
        await update.message.reply_text("📊 No stats yet. Start with /quiz!")
        return
    
    avg_score = (user_data['total_score'] / user_data['total_questions'] * 100) if user_data['total_questions'] > 0 else 0
    
    text = f"📊 *Your Statistics*\n\n"
    text += f"👤 User: {user_data['username']}\n"
    text += f"🎯 Best Score: {user_data['best_score']:.1f}%\n"
    text += f"📈 Average Score: {avg_score:.1f}%\n"
    text += f"📝 Tests Taken: {user_data['tests_taken']}\n"
    text += f"✅ Total Correct: {user_data['total_score']}/{user_data['total_questions']}\n\n"
    
    # Recent history
    history = context.user_data.get('history', [])
    if history:
        text += "*Recent Performance:*\n"
        for i, r in enumerate(history[-5:], 1):
            text += f"{i}. {r['score']}/{r['total']} ({r['pct']:.0f}%) - {r.get('time', 'N/A')}\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """📖 *Complete Guide*

*🎮 Quiz Modes:*
⚡ Quick - 5 questions, no timer
📝 Standard - 10 questions
🎯 Full Test - 20 questions  
⏱️ Timed - Race against clock

*🏆 Features:*
• Real-time leaderboard
• Performance tracking
• Instant feedback
• Speed challenges
• Topic selection

*📊 Commands:*
/quiz - Start quiz
/leaderboard - Top 10 rankers
/mystats - Your statistics
/topics - Choose specific topic
/help - This guide

*💡 Tips:*
• Aim for 80%+ for excellence
• Try timed mode for challenge
• Check leaderboard often
• Practice regularly

Good luck! 🚀"""
    await update.message.reply_text(text, parse_mode='Markdown')

def main():
    """Main function - optimized for deployment"""
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ ERROR: Set BOT_TOKEN environment variable!")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("mystats", mystats))
    app.add_handler(CommandHandler("help", help_command))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(mode_selected, pattern='^mode_'))
    app.add_handler(CallbackQueryHandler(topic_selected, pattern='^topic_'))
    app.add_handler(CallbackQueryHandler(handle_answer, pattern='^answer_'))
    
    print("🤖 Bot starting...")
    print("✅ Running! Press Ctrl+C to stop")
    
    # Use webhook for production, polling for local
    if os.environ.get('RENDER'):
        # Production mode (Render)
        port = int(os.environ.get('PORT', 8080))
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=f"{os.environ.get('RENDER_EXTERNAL_URL')}/{BOT_TOKEN}"
        )
    else:
        # Local development mode
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()