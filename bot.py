"""
GATE CSE Quiz Telegram Bot - Working Version
pip install python-telegram-bot --upgrade
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# IMPORTANT: Replace with your token from @BotFather
BOT_TOKEN = '8590474160:AAEMFKT_hyCF3qRROu0BrlqIbTii0HikxII'

# Question Bank
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
    text = """🎓 *Welcome to GATE CSE Quiz Bot!*

📚 *Commands:*
/quiz - Quick 5-question quiz
/topics - Choose topic
/score - View performance
/help - Get help

Ready to ace GATE 2026? 🚀"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔢 Algorithms", callback_data='topic_algorithms')],
        [InlineKeyboardButton("📊 Data Structures", callback_data='topic_data_structures')],
        [InlineKeyboardButton("💻 Programming", callback_data='topic_programming')],
        [InlineKeyboardButton("🔤 TOC", callback_data='topic_toc')],
        [InlineKeyboardButton("🎲 Random Mix", callback_data='topic_random')]
    ]
    await update.message.reply_text('Choose topic:', reply_markup=InlineKeyboardMarkup(keyboard))

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_q = []
    for qs in QUESTIONS.values():
        all_q.extend(qs)
    selected = random.sample(all_q, 5)
    user_sessions[user_id] = {'questions': selected, 'current': 0, 'score': 0, 'answers': []}
    await update.message.reply_text("🎯 Starting quiz! 5 questions\n\nGood luck! 💪")
    await send_question(update.message, context, user_id)

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
        selected = selected[:5]
    
    user_sessions[user_id] = {'questions': selected, 'current': 0, 'score': 0, 'answers': []}
    await query.edit_message_text(f"✅ Starting quiz! {len(selected)} questions")
    await send_question(query.message, context, user_id)

async def send_question(message, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    session = user_sessions.get(user_id)
    if not session:
        return
    q = session['questions'][session['current']]
    text = f"❓ *Q{session['current']+1}/{len(session['questions'])}*\n\n{q['q']}\n\n"
    keyboard = [[InlineKeyboardButton(f"{chr(65+i)}. {opt}", callback_data=f'answer_{i}')] for i, opt in enumerate(q['options'])]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        await query.edit_message_text("Session expired. Use /quiz")
        return
    
    session = user_sessions[user_id]
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
        await show_results(query.message, context, user_id)

async def show_results(message, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    session = user_sessions.get(user_id)
    if not session:
        return
    
    score = session['score']
    total = len(session['questions'])
    pct = (score/total)*100
    
    text = f"🎯 *Quiz Complete!*\n\n📊 Score: {score}/{total} ({pct:.0f}%)\n\n"
    if pct >= 80:
        text += "🌟 Excellent!"
    elif pct >= 60:
        text += "👍 Good job!"
    else:
        text += "📚 Keep practicing!"
    
    text += "\n\n"
    for i, ans in enumerate(session['answers']):
        text += "✅" if ans else "❌"
        text += " "
    
    text += "\n\n/quiz to try again"
    
    if 'history' not in context.user_data:
        context.user_data['history'] = []
    context.user_data['history'].append({'score': score, 'total': total, 'pct': pct})
    
    await message.reply_text(text, parse_mode='Markdown')
    del user_sessions[user_id]

async def score_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    history = context.user_data.get('history', [])
    if not history:
        await update.message.reply_text("📊 No history. Start with /quiz")
        return
    
    text = "📈 *Performance History*\n\n"
    for i, r in enumerate(history[-10:], 1):
        text += f"{i}. {r['score']}/{r['total']} ({r['pct']:.0f}%)\n"
    
    avg = sum(r['pct'] for r in history) / len(history)
    text += f"\n*Average: {avg:.0f}%*"
    await update.message.reply_text(text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """📖 *Help*

/start - Welcome
/quiz - Quick 5Q quiz
/topics - Choose topic
/score - View history
/help - This message

*How to use:*
1. Start quiz
2. Tap answer
3. Get instant feedback
4. See final score

Good luck! 🎓"""
    await update.message.reply_text(text, parse_mode='Markdown')

def main():
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ ERROR: Set your bot token!")
        print("Edit bot.py and replace YOUR_BOT_TOKEN_HERE")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(CommandHandler("score", score_history))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(topic_selected, pattern='^topic_'))
    app.add_handler(CallbackQueryHandler(handle_answer, pattern='^answer_'))
    
    print("🤖 Bot starting...")
    print("✅ Running! Press Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()