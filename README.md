# Smart Task Analyzer

An intelligent task prioritization system that helps you decide what to work on next. It analyzes your tasks across multiple dimensions—urgency, importance, effort, and dependencies—and provides smart recommendations based on different work styles.

---

## 🚀 Setup Instructions

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. **Navigate to the backend directory**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations and start the server**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```
   
   The API will be available at `http://127.0.0.1:8000`

5. **Open the frontend**
   - Simply open `frontend/index.html` in your browser, or
   - Use a local server: `python -m http.server 8080` from the frontend directory

The frontend will automatically connect to the Django backend.

---

## 🧮 Algorithm Explanation

The core algorithm calculates a priority score for each task by combining four normalized components with configurable weights. Here's how it works:

**1. Urgency Score**  
Tasks are scored based on how soon they're due. Past-due tasks receive a moderate boost (capped at 1.8x) to ensure they appear near the top without completely dominating other factors. Tasks due within the next 30 days get linearly scaled urgency scores, while tasks further out receive minimal urgency. This design prevents overdue tasks from always winning regardless of their actual importance.

**2. Importance Score**  
Users rate tasks from 1-10, which we normalize to a 0-1 scale. Importance receives relatively high weight in the default strategy because research shows that genuinely important tasks often get deprioritized for urgent-but-less-important items. By giving importance a strong voice in the scoring, we help users focus on what truly matters.

**3. Effort Score**  
Short tasks are rewarded using an inverse logarithmic formula: `1 / (1 + log(1 + hours))`. This means a 1-hour task scores higher than an 8-hour task, encouraging "quick wins" that build momentum. The log scaling prevents extreme differences—a 2-hour task isn't penalized too harshly compared to a 1-hour task, but a 20-hour task naturally ranks lower. This feels intuitive to how humans perceive effort.

**4. Dependency Score**  
Tasks that unblock other work are prioritized. We traverse the dependency graph using depth-first search to count all tasks (direct and indirect) that depend on each task. These counts are log-normalized to prevent bottleneck tasks from completely dominating scores. If circular dependencies are detected using cycle detection algorithms, those tasks receive zero dependency scores and a small penalty to avoid infinite loops.

**Strategy Weights**  
Four preset strategies adjust how much each factor matters:
- **Smart Balance** (default): 30% urgency, 35% importance, 20% effort, 15% dependencies
- **Fastest Wins**: Heavy emphasis on effort (60%) for momentum building
- **High Impact**: Importance-focused (70%) for strategic work
- **Deadline Driven**: Urgency-heavy (70%) for time-sensitive periods

The final score is mapped to a 0-100 scale with High/Medium/Low priority labels to make it immediately actionable.

---

## 🎯 Design Decisions

**Stateless API Design**  
I chose to pass tasks in each request rather than storing them in a database. While this means no persistence, it simplified the implementation for this assignment's scope and made testing straightforward. The Django model is included as a foundation for future database integration.

**Logarithmic Normalization**  
Using log scaling for effort and dependencies prevents extreme outliers from skewing results unreasonably. This matches human intuition better—the difference between 1 and 2 hours feels much larger than between 10 and 11 hours. The trade-off is slightly more complex math, but the result is more balanced prioritization.

**Fixed Strategy Presets**  
Rather than letting users configure custom weights, I provided four research-backed preset strategies. This keeps the UX simple while covering most real-world scenarios. Custom weights would be a natural next step, but for this assignment, the presets deliver 80% of the value with 20% of the complexity.

**Cycle Handling**  
When circular dependencies are detected, I apply a 15% penalty rather than rejecting those tasks entirely. This allows prioritization to continue working while warning the user about the issue. In practice, some cycles might be acceptable or intentional, so I wanted to preserve user agency rather than blocking their workflow.

---

## ⏱️ Time Breakdown

| Task | Time Spent |
|------|------------|
| Algorithm design and research | 40 min |
| Backend implementation (scoring logic, API) | 85 min |
| Unit tests | 25 min |
| Frontend structure and logic | 50 min |
| Frontend styling and UX polish | 40 min |
| Eisenhower Matrix bonus feature | 30 min |
| Documentation and README | 35 min |
| **Total** | **~4 hours** |

---

## ✨ Bonus Challenges Attempted

**Eisenhower Matrix View**  
I implemented a toggle that displays tasks in a 2×2 grid based on urgency and importance. The four quadrants (Do First, Schedule, Delegate, Eliminate) help visualize task distribution and identify workflow imbalances. This took about 30 minutes and uses median splitting to categorize tasks.

---

## 🚀 Future Improvements

With more time, I would enhance this system in several ways:

**Persistence and User Management**  
Add database storage, user authentication, and task history tracking. This would enable features like completion analytics and learning user preferences over time.

**Smarter Scheduling**  
Incorporate working hours, weekends, and energy levels into the algorithm. For example, match high-effort tasks to users' peak productivity hours, or adjust urgency calculations to skip weekends.

**Visualization Enhancements**  
Build an interactive dependency graph using D3.js to help users understand task relationships visually. Add a timeline view showing deadlines and a calendar integration for better planning.

**Machine Learning Integration**  
Track which tasks users actually complete first, regardless of the algorithm's suggestions. Over time, learn individual preferences and adjust strategy weights automatically.

**Collaboration Features**  
Extend the system for teams with shared task boards, delegation capabilities, and real-time updates via WebSockets.

**Mobile Experience**  
Build native mobile apps with push notifications for urgent tasks and offline mode with sync capabilities.

---

## 🧪 Testing

Run the unit tests with:
```bash
cd backend
python manage.py test tasks
```

Tests cover priority ordering, past-due task handling, and circular dependency detection.

---

## 📚 Tech Stack

**Backend:** Django 4.0+, Django REST Framework  
**Frontend:** Vanilla JavaScript, CSS3 (Grid/Flexbox)  
**Testing:** Django's built-in test framework

---
