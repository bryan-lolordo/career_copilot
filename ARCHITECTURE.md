# 🏗️ Career Copilot - Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Component Design](#component-design)
4. [Data Flow](#data-flow)
5. [Plugin System](#plugin-system)
6. [Conversation Memory](#conversation-memory)
7. [Database Design](#database-design)
8. [Security Architecture](#security-architecture)
9. [Development Guide](#development-guide)

---

## System Overview

Career Copilot is built on a **three-layer architecture** that separates concerns between presentation, business logic, and data persistence:
```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                    │
│  (Streamlit Multi-Page App + CLI Interface)             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│                   Business Logic Layer                   │
│  (Semantic Kernel Agent + Plugins + Services)           │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│                    Data Layer                           │
│  (SQLite Database + External APIs)                      │
└─────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Separation of Concerns**: UI, business logic, and data access are cleanly separated
2. **Plugin Architecture**: Extensible functionality through modular plugins
3. **Stateful Conversations**: Conversation memory maintains context across interactions
4. **Autonomous Orchestration**: AI agent selects and chains tools automatically
5. **Safety First**: Read-only queries, input validation, error handling

---

## Architecture Layers

### 1. Presentation Layer

**Components:**
- `streamlit_app.py` - Main web application entry point
- `pages/*.py` - Individual feature pages
- `ui/components.py` - Reusable UI components
- `ui/utils.py` - UI helper functions
- `agents/semantic_kernel_setup.py` - CLI interface

**Responsibilities:**
- Render user interface
- Capture user input
- Display results and feedback
- Handle file uploads
- Manage navigation

**Technology Stack:**
- Streamlit for web UI
- Python asyncio for CLI
- Custom HTML/CSS components

### 2. Business Logic Layer

**Core Components:**

#### Semantic Kernel Agent
```python
# agents/semantic_kernel_setup.py
kernel = sk.Kernel()
kernel.add_service(AzureChatCompletion(...))

# Register plugins
kernel.add_plugin(JobPlugin(), "JobPlugin")
kernel.add_plugin(ResumeMatchingPlugin(), "ResumeMatchingPlugin")
# ... more plugins

# Agent executes with auto function calling
result = await kernel.invoke_prompt(
    user_input,
    settings=PromptExecutionSettings(
        auto_invoke_kernel_functions=True,
        function_choice_behavior=FunctionChoiceBehavior.Auto()
    )
)
```

#### Chatbot Service
```python
# services/chatbot.py
class Chatbot:
    def __init__(self):
        self.kernel = initialize_kernel()
        self.memory = ConversationMemory()
        self.history = ChatHistory()
    
    async def chat(self, user_message: str) -> str:
        # Add user message to history
        self.history.add_user_message(user_message)
        
        # Get AI response with function calling
        response = await self.kernel.invoke_prompt(
            user_message,
            chat_history=self.history
        )
        
        # Update conversation context
        self.memory.update(response)
        
        return response
```

#### Plugin System
Each plugin exposes kernel functions:
```python
class MyPlugin:
    @kernel_function(
        name="function_name",
        description="What this function does (for AI to understand)"
    )
    async def my_function(
        self,
        param: Annotated[str, "Parameter description for AI"]
    ) -> Annotated[str, "Return value description"]:
        # Implementation
        return result
```

**Responsibilities:**
- AI orchestration and decision-making
- Tool selection and invocation
- Conversation state management
- Business logic execution
- Data validation

### 3. Data Layer

**Components:**
- `services/db.py` - SQLite database operations
- `services/database_service.py` - High-level data access
- `services/job_api.py` - External API integration
- `services/resume_parser.py` - Document processing

**Responsibilities:**
- Data persistence
- External API calls
- File parsing
- Query execution

---

## Component Design

### Chatbot Engine

**File:** `services/chatbot.py`
```python
class Chatbot:
    """
    Main orchestration engine that:
    1. Maintains conversation history
    2. Manages conversation context
    3. Invokes Semantic Kernel with plugins
    4. Handles errors gracefully
    """
    
    def __init__(self):
        self.kernel = initialize_kernel()
        self.memory = ConversationMemory()
        self.history = ChatHistory()
    
    async def chat(self, user_message: str) -> str:
        """Process user message and return AI response"""
        pass
    
    def reset(self):
        """Clear conversation history and context"""
        pass
```

**Key Features:**
- Asynchronous message processing
- Function calling enabled
- Error handling with user-friendly messages
- Conversation history management

### Conversation Memory

**File:** `services/conversation_memory.py`
```python
@dataclass
class ConversationContext:
    """Maintains state across conversation turns"""
    
    # Active references
    active_resume_id: Optional[int] = None
    active_job_id: Optional[int] = None
    
    # Recent results (for follow-up questions)
    last_search_results: Optional[List[Dict]] = None
    last_match_results: Optional[List[Dict]] = None
    
    # Multi-step workflow state
    awaiting_resume_selection: bool = False
    awaiting_job_filter_selection: bool = False
    selected_resume_for_matching: Optional[Dict] = None
    
    # User preferences
    preferred_locations: List[str] = field(default_factory=list)
    preferred_job_types: List[str] = field(default_factory=list)

class ConversationMemory:
    """Manages conversation context and state"""
    
    def __init__(self):
        self.context = ConversationContext()
    
    def update_active_resume(self, resume_id: int):
        """Set currently active resume"""
        self.context.active_resume_id = resume_id
    
    def store_search_results(self, results: List[Dict]):
        """Store results for follow-up questions"""
        self.context.last_search_results = results
    
    def is_awaiting_selection(self) -> bool:
        """Check if in multi-step workflow"""
        return (self.context.awaiting_resume_selection or 
                self.context.awaiting_job_filter_selection)
```

**Why This Matters:**
- Enables natural follow-up questions ("tell me more about #2")
- Supports multi-turn workflows ("match my resume" → "the first one")
- Maintains user preferences learned over time

### Database Service

**File:** `services/database_service.py`
```python
class DatabaseService:
    """High-level data access layer for plugins"""
    
    def __init__(self, db_path: str = "career_copilot.db"):
        self.db = Database(db_path)
    
    # Resume operations
    def get_all_resumes(self) -> List[Dict]:
        """Get all resumes with metadata"""
        pass
    
    def get_resume_by_id(self, resume_id: int) -> Optional[Dict]:
        """Get specific resume"""
        pass
    
    # Job operations
    def get_all_jobs(self) -> List[Dict]:
        """Get all saved jobs"""
        pass
    
    def save_job(self, job: Dict) -> int:
        """Save job to database"""
        pass
    
    # Match operations
    def save_match(self, match: Dict) -> int:
        """Save resume-job match"""
        pass
    
    def get_matches_for_resume(self, resume_id: int) -> List[Dict]:
        """Get all matches for a resume"""
        pass
```

**Design Pattern:**
- Repository pattern for data access
- Abstracts SQL details from plugins
- Provides type-safe data operations

---

## Data Flow

### Job Search Flow
```
┌──────────┐
│   User   │ "search for Python jobs in Chicago"
└────┬─────┘
     │
     ▼
┌────────────────┐
│  Streamlit UI  │
└────┬───────────┘
     │
     ▼
┌─────────────────┐
│ Chatbot Service │ Maintains conversation history
└────┬────────────┘
     │
     ▼
┌────────────────────┐
│ Semantic Kernel    │ AI decides to call JobPlugin.search_jobs
└────┬───────────────┘
     │
     ▼
┌────────────────┐
│   JobPlugin    │ Calls SerpAPI
└────┬───────────┘
     │
     ▼
┌────────────────┐
│    SerpAPI     │ Returns job listings
└────┬───────────┘
     │
     ▼
┌────────────────┐
│   JobPlugin    │ Formats results
└────┬───────────┘
     │
     ▼
┌──────────────────────┐
│ Conversation Memory  │ Stores results for follow-up
└────┬─────────────────┘
     │
     ▼
┌────────────────┐
│      User      │ Sees formatted job listings
└────────────────┘
```

### Resume Matching Flow
```
┌──────────┐
│   User   │ "match my resume to jobs"
└────┬─────┘
     │
     ▼
┌───────────────────────┐
│  Semantic Kernel      │ Calls ResumeMatchingPlugin.list_resumes
└────┬──────────────────┘
     │
     ▼
┌───────────────────────┐
│ ResumeMatchingPlugin  │ Returns resume list
└────┬──────────────────┘
     │
     ▼
┌──────────────────────┐
│ Conversation Memory  │ Sets awaiting_resume_selection = True
└────┬─────────────────┘
     │
     ▼
┌──────────┐
│   User   │ "the first one"
└────┬─────┘
     │
     ▼
┌───────────────────────┐
│ Semantic Kernel       │ Calls select_resume(resume_number=1)
└────┬──────────────────┘
     │
     ▼
┌──────────────────────┐
│ Conversation Memory  │ Stores selected_resume_for_matching
│                      │ Sets awaiting_job_filter_selection = True
└────┬─────────────────┘
     │
     ▼
┌──────────┐
│   User   │ "only unmatched jobs"
└────┬─────┘
     │
     ▼
┌───────────────────────┐
│ ResumeMatchingPlugin  │ Executes match_resume_to_jobs()
└────┬──────────────────┘
     │
     ▼
┌────────────────────────┐
│  For each job:         │
│  1. Get job details    │
│  2. Call Azure OpenAI  │
│  3. Parse scores       │
│  4. Save to database   │
└────┬───────────────────┘
     │
     ▼
┌──────────────────────┐
│ Database Service     │ Saves all matches
└────┬─────────────────┘
     │
     ▼
┌──────────────────────┐
│ Conversation Memory  │ Stores match results
│                      │ Clears workflow flags
└────┬─────────────────┘
     │
     ▼
┌──────────┐
│   User   │ Sees ranked match results
└──────────┘
```

### Natural Language SQL Flow
```
┌──────────┐
│   User   │ "show me jobs from Deloitte with salary > $120k"
└────┬─────┘
     │
     ▼
┌────────────────────┐
│ Semantic Kernel    │ Calls QueryDatabasePlugin.query_database
└────┬───────────────┘
     │
     ▼
┌─────────────────────┐
│ QueryDatabasePlugin │ 
│ 1. Get schema       │
│ 2. Call Azure OpenAI│
│    with schema +    │
│    user query       │
└────┬────────────────┘
     │
     ▼
┌────────────────┐
│ Azure OpenAI   │ Generates SQL query
└────┬───────────┘
     │
     ▼
┌─────────────────────┐
│ QueryDatabasePlugin │
│ 3. Validate query   │
│    - SELECT only    │
│    - No injection   │
└────┬────────────────┘
     │
     ▼
┌────────────────┐
│ Database       │ Executes query
└────┬───────────┘
     │
     ▼
┌─────────────────────┐
│ QueryDatabasePlugin │ Formats results
└────┬────────────────┘
     │
     ▼
┌──────────┐
│   User   │ Sees query results
└──────────┘
```

---

## Plugin System

### Plugin Architecture

Each plugin is a Python class that exposes kernel functions. The Semantic Kernel agent reads function descriptions and automatically invokes them based on user intent.

### Creating a Plugin
```python
from semantic_kernel.functions import kernel_function
from typing import Annotated

class MyCustomPlugin:
    """Brief description of what this plugin does"""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
    
    @kernel_function(
        name="my_function",
        description="""
        Detailed description of what this function does.
        Include when the AI should call this function.
        Example: "Call this when user wants to analyze trends"
        """
    )
    async def my_function(
        self,
        param1: Annotated[str, "Description of param1 for the AI"],
        param2: Annotated[int, "Description of param2"] = 10
    ) -> Annotated[str, "Description of return value"]:
        """
        Implementation of the function.
        
        Args:
            param1: First parameter
            param2: Second parameter (optional)
        
        Returns:
            Formatted string response
        """
        # Your logic here
        result = self._process_data(param1, param2)
        
        return f"Processed {param1} with value {param2}: {result}"
    
    def _process_data(self, data: str, value: int):
        """Private helper method (not exposed to kernel)"""
        pass
```

### Registering a Plugin
```python
# In semantic_kernel_setup.py
from plugins.MyCustomPlugin import MyCustomPlugin

def initialize_kernel():
    kernel = sk.Kernel()
    
    # Add services
    kernel.add_service(AzureChatCompletion(...))
    
    # Initialize plugin with dependencies
    db_service = DatabaseService()
    my_plugin = MyCustomPlugin(db_service)
    
    # Register plugin
    kernel.add_plugin(my_plugin, "MyCustomPlugin")
    
    return kernel
```

### Existing Plugins

#### 1. JobPlugin

**Purpose:** Search and manage job listings

**Functions:**
- `search_jobs(query, location, num_results)` - Search via SerpAPI
- `get_job_details(job_number)` - Get specific job from last search
- `save_jobs(job_numbers)` - Save selected jobs to database
- `save_all_jobs()` - Save all jobs from last search
- `delete_jobs_by_company(company_name)` - Bulk delete

**Dependencies:**
- `services/job_api.py` - SerpAPI integration
- `services/database_service.py` - Data persistence

#### 2. ResumeMatchingPlugin

**Purpose:** AI-powered resume-job matching

**Functions:**
- `list_resumes()` - Show available resumes
- `select_resume(resume_number)` - Choose resume for matching
- `select_job_filter(filter_type)` - Filter jobs before matching
- `match_resume_to_jobs()` - Execute matching workflow

**Matching Algorithm:**
```python
async def _match_single_job(self, resume: Dict, job: Dict) -> Dict:
    """
    Match a single resume-job pair using AI
    
    Returns:
        {
            'overall_score': int (0-100),
            'skill_alignment': int (0-100),
            'experience_match': int (0-100),
            'role_fit': int (0-100),
            'reasoning': str (detailed explanation)
        }
    """
    prompt = f"""
    Analyze this resume against the job description.
    
    Resume:
    {resume['content']}
    
    Job:
    {job['description']}
    
    Provide scores (0-100) for:
    1. Skill Alignment
    2. Experience Match
    3. Role Fit
    
    Calculate overall score as: (skill * 0.4) + (experience * 0.3) + (role_fit * 0.3)
    
    Provide detailed reasoning for each score.
    """
    
    response = await self.kernel.invoke_prompt(prompt)
    return self._parse_scores(response)
```

#### 3. QueryDatabasePlugin

**Purpose:** Natural language to SQL query generation

**Functions:**
- `query_database(natural_language_query)` - Execute NL query
- `get_database_schema()` - Show database structure
- `get_database_statistics()` - Show data stats

**Safety Implementation:**
```python
def _validate_sql(self, sql: str) -> bool:
    """
    Validate SQL query for safety
    
    Rules:
    1. Must start with SELECT
    2. No DELETE, UPDATE, DROP, INSERT
    3. No semicolons (prevents multi-statement)
    4. No comments (-- or /* */)
    """
    sql_upper = sql.strip().upper()
    
    if not sql_upper.startswith('SELECT'):
        return False
    
    dangerous_keywords = ['DELETE', 'UPDATE', 'DROP', 'INSERT', 'ALTER']
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            return False
    
    if ';' in sql or '--' in sql or '/*' in sql:
        return False
    
    return True
```

#### 4. SelfImprovingMatchPlugin

**Purpose:** Iterative refinement of match analysis

**Functions:**
- `improve_match(resume_id, job_id, max_iterations)` - Self-critique loop

**Implementation:**
```python
async def improve_match(self, resume_id: int, job_id: int, max_iterations: int = 3):
    """
    Iteratively improve match analysis through AI self-critique
    
    Process:
    1. Initial analysis
    2. AI critic evaluates quality
    3. If insufficient, refine with guidance
    4. Repeat until quality threshold met or max iterations
    """
    resume = self.db.get_resume_by_id(resume_id)
    job = self.db.get_job_by_id(job_id)
    
    guidance = []
    
    for iteration in range(max_iterations):
        # Analyze with accumulated guidance
        analysis = await self._analyze_match(resume, job, guidance)
        
        # AI critic evaluates
        critique = await self._critique_analysis(analysis)
        
        if critique['quality_score'] >= 85:
            # Good enough
            return analysis
        
        # Add critique to guidance for next iteration
        guidance.append(critique['suggestions'])
    
    return analysis  # Return best attempt
```

#### 5. ResumeTailoringPlugin

**Purpose:** Optimize resume for specific jobs

**Functions:**
- `tailor_resume(resume_id, job_id)` - Generate tailored version
- `suggest_improvements(resume_id, job_id)` - Get specific suggestions

#### 6. PreprocessorPlugins

**Purpose:** Clean and normalize text data

**ResumePreprocessorPlugin:**
- `preprocess_resume(resume_id)` - Clean resume text
- `preprocess_all_resumes()` - Batch processing

**JobPreprocessorPlugin:**
- `preprocess_job(job_id)` - Clean job description
- `preprocess_all_jobs()` - Batch processing

---

## Conversation Memory

### Architecture

The conversation memory system consists of two components:

1. **ConversationContext** (Data Class) - Holds current state
2. **ConversationMemory** (Service) - Manages state transitions

### Context Structure
```python
@dataclass
class ConversationContext:
    # === Active References ===
    # Track what the user is currently working with
    active_resume_id: Optional[int] = None
    active_job_id: Optional[int] = None
    
    # === Recent Results ===
    # Store results for follow-up questions
    last_search_results: Optional[List[Dict]] = None
    last_match_results: Optional[List[Dict]] = None
    last_query_results: Optional[List[Dict]] = None
    
    # === Multi-Step Workflows ===
    # Track progress in multi-turn conversations
    awaiting_resume_selection: bool = False
    awaiting_job_filter_selection: bool = False
    selected_resume_for_matching: Optional[Dict] = None
    match_filter_type: Optional[str] = None
    
    # === User Preferences ===
    # Learn preferences over time
    preferred_locations: List[str] = field(default_factory=list)
    preferred_job_types: List[str] = field(default_factory=list)
    preferred_companies: List[str] = field(default_factory=list)
    
    # === Session Metadata ===
    session_start: datetime = field(default_factory=datetime.now)
    total_searches: int = 0
    total_matches: int = 0
```

### Memory Operations
```python
class ConversationMemory:
    def __init__(self):
        self.context = ConversationContext()
    
    # === Reference Management ===
    def update_active_resume(self, resume_id: int):
        """User is now working with this resume"""
        self.context.active_resume_id = resume_id
    
    def update_active_job(self, job_id: int):
        """User is now working with this job"""
        self.context.active_job_id = job_id
    
    # === Result Storage ===
    def store_search_results(self, results: List[Dict]):
        """Store for follow-up: 'tell me more about #2'"""
        self.context.last_search_results = results
        self.context.total_searches += 1
    
    def store_match_results(self, results: List[Dict]):
        """Store for follow-up: 'why did I get 94%?'"""
        self.context.last_match_results = results
        self.context.total_matches += 1
    
    # === Workflow State ===
    def start_resume_selection(self):
        """Begin multi-step matching workflow"""
        self.context.awaiting_resume_selection = True
    
    def complete_resume_selection(self, resume: Dict):
        """User selected a resume"""
        self.context.selected_resume_for_matching = resume
        self.context.awaiting_resume_selection = False
        self.context.awaiting_job_filter_selection = True
    
    def complete_job_filter_selection(self, filter_type: str):
        """User selected filter type"""
        self.context.match_filter_type = filter_type
        self.context.awaiting_job_filter_selection = False
    
    # === Query Interface ===
    def get_result_by_number(self, number: int, result_type: str) -> Optional[Dict]:
        """Get specific result by number (1-indexed)"""
        if result_type == 'search':
            results = self.context.last_search_results
        elif result_type == 'match':
            results = self.context.last_match_results
        else:
            return None
        
        if not results or number < 1 or number > len(results):
            return None
        
        return results[number - 1]
    
    def is_in_workflow(self) -> bool:
        """Check if in multi-step workflow"""
        return (self.context.awaiting_resume_selection or 
                self.context.awaiting_job_filter_selection)
    
    def reset(self):
        """Clear all context"""
        self.context = ConversationContext()
```

### Usage in Plugins

Plugins can access conversation memory to provide contextual responses:
```python
class ResumeMatchingPlugin:
    def __init__(self, db_service, memory):
        self.db = db_service
        self.memory = memory
    
    @kernel_function(name="select_resume")
    async def select_resume(self, resume_number: int):
        """Handle resume selection in multi-step workflow"""
        
        # Get resume from last list operation
        resume = self.memory.get_result_by_number(resume_number, 'search')
        
        if not resume:
            return "Invalid resume number. Please list resumes again."
        
        # Update memory
        self.memory.complete_resume_selection(resume)
        
        return f"Selected {resume['name']}. How would you like to filter jobs?"
```

---

## Database Design

### Schema
```sql
-- Resumes Table
CREATE TABLE resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    file_type TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    preprocessed_content TEXT,
    metadata TEXT  -- JSON for extensibility
);

CREATE INDEX idx_resumes_uploaded_at ON resumes(uploaded_at);

-- Jobs Table
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    description TEXT NOT NULL,
    link TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    preprocessed_description TEXT,
    source TEXT DEFAULT 'SerpAPI',
    metadata TEXT  -- JSON for extensibility
);

CREATE INDEX idx_jobs_company ON jobs(company);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
CREATE INDEX idx_jobs_title ON jobs(title);

-- Resume-Job Matches Table
CREATE TABLE resume_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    overall_score INTEGER NOT NULL,
    skill_alignment INTEGER,
    experience_match INTEGER,
    role_fit INTEGER,
    cultural_fit INTEGER,
    reasoning TEXT,
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    match_version INTEGER DEFAULT 1,  -- For tracking algorithm changes
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    UNIQUE(resume_id, job_id)  -- Prevent duplicate matches
);

CREATE INDEX idx_matches_resume_id ON resume_matches(resume_id);
CREATE INDEX idx_matches_job_id ON resume_matches(job_id);
CREATE INDEX idx_matches_score ON resume_matches(overall_score);
CREATE INDEX idx_matches_matched_at ON resume_matches(matched_at);
```

### Database Operations

**File:** `services/db.py`
```python
class Database:
    def __init__(self, db_path: str = "career_copilot.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS resumes (...)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS jobs (...)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS resume_matches (...)""")
    
    # === Resume Operations ===
    def insert_resume(self, name: str, content: str, file_type: str) -> int:
        """Insert new resume and return ID"""
        pass
    
    def get_resume(self, resume_id: int) -> Optional[Dict]:
        """Get resume by ID"""
        pass
    
    def get_all_resumes(self) -> List[Dict]:
        """Get all resumes"""
        pass
    
    def update_resume(self, resume_id: int, updates: Dict):
        """Update resume fields"""
        pass
    
    def delete_resume(self, resume_id: int):
        """Delete resume and cascade matches"""
        pass
    
    # === Job Operations ===
    def insert_job(self, job: Dict) -> int:
        """Insert new job and return ID"""
        pass
    
    def get_job(self, job_id: int) -> Optional[Dict]:
        """Get job by ID"""
        pass
    
    def get_all_jobs(self) -> List[Dict]:
        """Get all jobs"""
        pass
    
    def bulk_delete_jobs(self, job_ids: List[int]):
        """Delete multiple jobs"""
        pass
    
    # === Match Operations ===
    def insert_match(self, match: Dict) -> int:
        """Insert or update match (UPSERT)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO resume_matches 
                (resume_id, job_id, overall_score, skill_alignment, 
                 experience_match, role_fit, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(resume_id, job_id) DO UPDATE SET
                overall_score = excluded.overall_score,
                skill_alignment = excluded.skill_alignment,
                experience_match = excluded.experience_match,
                role_fit = excluded.role_fit,
                reasoning = excluded.reasoning,
                matched_at = CURRENT_TIMESTAMP
            """, (match['resume_id'], match['job_id'], ...))
    
    def get_matches_for_resume(self, resume_id: int) -> List[Dict]:
        """Get all matches for a resume, ordered by score"""
        pass
    
    # === Query Operations ===
    def execute_query(self, sql: str) -> List[Dict]:
        """Execute arbitrary SELECT query"""
        if not self._is_safe_query(sql):
            raise ValueError("Unsafe query")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
```

### Transaction Management

For operations involving multiple tables:
```python
def save_match_with_metadata(self, match: Dict, job: Dict):
    """Atomic operation to save match and update job"""
    with sqlite3.connect(self.db_path) as conn:
        try:
            # Start transaction
            cursor = conn.cursor()
            
            # Insert match
            cursor.execute("""
                INSERT INTO resume_matches (...)
                VALUES (...)
            """, match_values)
            
            # Update job metadata
            cursor.execute("""
                UPDATE jobs 
                SET metadata = json_set(metadata, '$.last_matched', ?)
                WHERE id = ?
            """, (datetime.now().isoformat(), job['id']))
            
            # Commit transaction
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
```

---

## Security Architecture

### 1. SQL Injection Prevention

**QueryDatabasePlugin** validates all SQL queries:
```python
def _validate_sql(self, sql: str) -> bool:
    """
    Multi-layer validation:
    1. Whitelist: Must start with SELECT
    2. Blacklist: No DML/DDL keywords
    3. Pattern check: No dangerous patterns
    """
    sql_clean = sql.strip().upper()
    
    # Layer 1: Whitelist
    if not sql_clean.startswith('SELECT'):
        return False
    
    # Layer 2: Blacklist dangerous keywords
    blacklist = [
        'DELETE', 'UPDATE', 'DROP', 'INSERT', 'ALTER',
        'CREATE', 'TRUNCATE', 'REPLACE', 'EXEC'
    ]
    for keyword in blacklist:
        if keyword in sql_clean:
            return False
    
    # Layer 3: Pattern checks
    dangerous_patterns = [
        ';',           # Multi-statement
        '--',          # Comments
        '/*',          # Multi-line comments
        'PRAGMA',      # SQLite pragmas
        'ATTACH'       # Database attachment
    ]
    for pattern in dangerous_patterns:
        if pattern in sql:
            return False
    
    return True
```

### 2. API Key Management
```python
# .env file (not committed)
AZURE_OPENAI_KEY=your_key_here
AZURE_OPENAI_BASE_URL=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
SERPAPI_KEY=your_serpapi_key

# Load securely
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("AZURE_OPENAI_KEY")
if not api_key:
    raise ValueError("Missing AZURE_OPENAI_KEY")
```

### 3. Input Sanitization
```python
def sanitize_user_input(text: str) -> str:
    """Clean user input before processing"""
    # Remove potentially dangerous characters
    cleaned = text.replace('\x00', '')  # Null bytes
    
    # Limit length to prevent DoS
    max_length = 10000
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    return cleaned.strip()
```

### 4. Token Limits
```python
def truncate_text(text: str, max_tokens: int = 4000) -> str:
    """Prevent excessive API costs"""
    # Rough estimation: 1 token ≈ 4 characters
    max_chars = max_tokens * 4
    
    if len(text) <= max_chars:
        return text
    
    # Truncate and add indicator
    return text[:max_chars] + "\n\n[Text truncated due to length]"
```

### 5. Error Handling
```python
async def safe_plugin_call(func, *args, **kwargs):
    """Wrapper for plugin functions with error handling"""
    try:
        return await func(*args, **kwargs)
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return "Database error occurred. Please try again."
    except aiohttp.ClientError as e:
        logger.error(f"API error: {e}")
        return "External API error. Please try again later."
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return "An unexpected error occurred. Please contact support."
```

---

## Development Guide

### Setting Up Development Environment
```bash
# Clone repository
git clone <repo-url>
cd career_copilot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run tests
python -m pytest tests/

# Start development server
streamlit run streamlit_app.py --server.runOnSave=true
```

### Adding a New Plugin

1. **Create plugin file** in `agents/plugins/`
```python
# agents/plugins/MyNewPlugin.py
from semantic_kernel.functions import kernel_function
from typing import Annotated

class MyNewPlugin:
    def __init__(self, db_service):
        self.db = db_service
    
    @kernel_function(
        name="my_function",
        description="Description for AI to understand when to call this"
    )
    async def my_function(
        self,
        param: Annotated[str, "Parameter description"]
    ) -> Annotated[str, "Return value description"]:
        # Implementation
        return "Result"
```

2. **Register in kernel setup**
```python
# agents/semantic_kernel_setup.py
from plugins.MyNewPlugin import MyNewPlugin

def initialize_kernel():
    # ... existing code ...
    
    my_plugin = MyNewPlugin(db_service)
    kernel.add_plugin(my_plugin, "MyNewPlugin")
    
    return kernel
```

3. **Test the plugin**
```python
# tests/test_my_plugin.py
import pytest
from plugins.MyNewPlugin import MyNewPlugin

@pytest.mark.asyncio
async def test_my_function():
    plugin = MyNewPlugin(mock_db_service)
    result = await plugin.my_function("test")
    assert result == "Expected result"
```

### Adding a New UI Page

1. **Create page file** in `pages/`
```python
# pages/8_🎯_My_Feature.py
import streamlit as st
from services.database_service import DatabaseService

st.set_page_config(page_title="My Feature", page_icon="🎯")

st.title("🎯 My Feature")

# Your UI code
db = DatabaseService()
data = db.get_some_data()

st.dataframe(data)
```

2. **Add navigation** (automatic in Streamlit multi-page apps)

3. **Add to documentation**

Update README.md with new page description.

### Code Style Guide
```python
# Use type hints
def process_data(input: str, count: int = 10) -> List[Dict]:
    pass

# Use docstrings
def my_function(param: str) -> str:
    """
    Brief description.
    
    Args:
        param: Description of parameter
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When param is invalid
    """
    pass

# Use descriptive variable names
user_resume = get_resume(resume_id)  # Good
r = get_resume(rid)  # Bad

# Use constants for magic values
MAX_SEARCH_RESULTS = 20  # Good
results = results[:20]  # Bad
```

### Testing Strategy
```python
# Unit tests for plugins
@pytest.mark.asyncio
async def test_job_search():
    plugin = JobPlugin(mock_api)
    results = await plugin.search_jobs("Python", "Chicago")
    assert len(results) > 0

# Integration tests for database
def test_save_and_retrieve_job():
    db = Database(":memory:")
    job_id = db.insert_job(test_job)
    retrieved = db.get_job(job_id)
    assert retrieved['title'] == test_job['title']

# End-to-end tests for workflows
@pytest.mark.asyncio
async def test_full_matching_workflow():
    chatbot = Chatbot()
    
    # Step 1: List resumes
    response = await chatbot.chat("match my resume")
    assert "Available resumes" in response
    
    # Step 2: Select resume
    response = await chatbot.chat("the first one")
    assert "filter" in response.lower()
    
    # Step 3: Execute matching
    response = await chatbot.chat("all jobs")
    assert "matched" in response.lower()
```

### Debugging Tips
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Add debug prints in plugins
@kernel_function(name="my_function")
async def my_function(self, param: str):
    print(f"DEBUG: Called with param={param}")
    result = self._process(param)
    print(f"DEBUG: Result={result}")
    return result

# Use Streamlit debugging
import streamlit as st
st.write("Debug info:", st.session_state)

# Test SQL queries directly
db = Database()
results = db.execute_query("SELECT * FROM jobs LIMIT 5")
print(results)
```

### Performance Optimization
```python
# Cache expensive operations
from functools import lru_cache

@lru_cache(maxsize=100)
def get_schema():
    """Cache database schema"""
    return db.get_schema()

# Batch database operations
def save_multiple_jobs(jobs: List[Dict]):
    """Use executemany for bulk inserts"""
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO jobs (...) VALUES (?, ?, ?)",
            [(job['title'], job['company'], job['description']) for job in jobs]
        )

# Limit API token usage
def truncate_for_api(text: str, max_tokens: int = 4000) -> str:
    """Prevent excessive costs"""
    return text[:max_tokens * 4]  # Rough estimation
```

---

## Appendix

### Technology Choices

**Why Semantic Kernel?**
- Native Azure OpenAI integration
- Function calling support
- Plugin architecture
- Microsoft support

**Why Streamlit?**
- Rapid prototyping
- Python-native
- Auto-reloading
- Built-in components

**Why SQLite?**
- Zero configuration
- File-based (portable)
- Sufficient for single-user
- Easy to migrate to PostgreSQL

### Future Architecture Considerations

**Scaling to Multi-User:**
```
Current: SQLite + local files
→ PostgreSQL + cloud storage

Current: Single kernel instance
→ Kernel pool with load balancing

Current: Synchronous UI
→ WebSocket for real-time updates
```

**Adding Vector Search:**
```
1. Add embeddings table
2. Generate embeddings on upload
3. Use cosine similarity for matching
4. Hybrid: keyword + semantic search
```

**Microservices Architecture:**
```
┌───────────────┐
│   API Gateway │
└───────┬───────┘
        │
    ┌───┴────┬──────────┬─────────┐
    │        │          │         │
┌───▼──┐ ┌──▼───┐ ┌────▼──┐ ┌───▼────┐
│ Job  │ │Resume│ │ Match │ │ Query  │
│Service│ │Service│ │Service│ │Service │
└───┬──┘ └──┬───┘ └────┬──┘ └───┬────┘
    │       │          │         │
    └───────┴──────────┴─────────┘
              │
        ┌─────▼──────┐
        │  Database  │
        └────────────┘
```

### Common Patterns

**Pattern: Multi-Step Workflow**
```python
# Step 1: Present options
memory.start_workflow('resume_selection')
return "Available resumes: ..."

# Step 2: Capture selection
if memory.is_in_workflow('resume_selection'):
    resume = parse_selection(user_input)
    memory.complete_workflow('resume_selection', resume)
    memory.start_workflow('filter_selection')
    return "How to filter jobs?"

# Step 3: Execute
if memory.is_in_workflow('filter_selection'):
    filter_type = parse_filter(user_input)
    memory.complete_workflow('filter_selection', filter_type)
    return execute_matching(resume, filter_type)
```

**Pattern: Result Caching**
```python
# Store results for follow-up
results = search_jobs(query)
memory.store_results('search', results)
return format_results(results)

# Later: "tell me more about #2"
if user_asks_about_number(input):
    number = extract_number(input)
    item = memory.get_result('search', number)
    return detailed_view(item)
```

**Pattern: Contextual Responses**
```python
if memory.has_active_resume():
    # User is working with a specific resume
    resume_id = memory.get_active_resume()
    return f"Working with resume {resume_id}. {response}"
else:
    # No context yet
    return "Which resume would you like to use?"
```

---

**End of Architecture Documentation**