# UX Agent Design for Dual-Model Architecture

## Overview

The UX Agent is the user-facing component that provides immediate, natural conversation while orchestrating complex tasks behind the scenes. It leverages the always-loaded small model (qwen2.5:7b) to maintain sub-second response times while seamlessly handing off work to the task model (qwen2.5:14b) for complex operations.

## Core Requirements

### Performance Targets
- **Sub-second responses**: <1s for all user interactions
- **Always available**: UX model never unloaded, instant availability
- **Natural conversation**: Maintains context across interactions
- **Seamless handoff**: Transparent task delegation to gateway
- **Real-time updates**: Progress streaming during task execution

### Dual-Model Integration
- **UX Model (qwen2.5:7b)**: Always-loaded, handles conversation flow
- **Task Model (qwen2.5:14b)**: On-demand for complex work via gateway
- **Memory management**: 4GB UX + 16GB task = 20GB total system load

## Architecture Design

### Component Structure
```
UX Agent Server (HTTP MCP)
├── Conversation Manager
│   ├── Context tracking
│   ├── Intent analysis
│   └── Response generation
├── Task Detection Engine
│   ├── Keyword analysis
│   ├── Confidence scoring
│   └── Handoff triggers
├── Gateway Integration
│   ├── Task submission
│   ├── Status monitoring
│   └── Progress updates
└── Model Pool Client
    ├── UX model access
    ├── Response generation
    └── Context management
```

### Sub-Second Response Protocol

```python
async def handle_user_input(user_input: str) -> AsyncGenerator[str, None]:
    """Sub-second response protocol using always-loaded UX model"""

    # Phase 1: Immediate acknowledgment (target: <200ms)
    ux_model = await model_pool.get_model('conversation')
    acknowledgment = await ux_model.generate_quick_response(user_input)
    yield acknowledgment

    # Phase 2: Intent analysis (target: <300ms)
    intent_analysis = await analyze_intent(user_input, ux_model)

    # Phase 3: Response or handoff (target: <500ms)
    if intent_analysis.requires_task_execution:
        # Hand off to gateway, stream progress
        async for progress_update in handle_task_execution(user_input):
            yield progress_update
    else:
        # Direct conversation response
        response = await ux_model.generate_response(user_input)
        yield response
```

## Task Detection and Handoff Protocol

### Intent Classification
The UX agent classifies user input into categories:

1. **Conversation** (keep with UX model)
   - Casual chat, questions
   - Status inquiries
   - System information

2. **Task Execution** (handoff to gateway)
   - Code generation requests
   - File operations
   - Complex analysis

3. **System Control** (direct handling)
   - Server management
   - Configuration changes
   - Debugging commands

### Detection Algorithm
```python
async def analyze_intent(user_input: str, ux_model) -> IntentAnalysis:
    """Analyze user intent using always-loaded UX model"""

    # Quick keyword analysis (target: <100ms)
    task_keywords = ['write', 'create', 'build', 'generate', 'analyze', 'fix']
    conversation_keywords = ['hello', 'how', 'what', 'why', 'explain']

    # UX model analysis (target: <200ms)
    analysis_prompt = f"""
    Analyze this user input for intent classification:
    Input: "{user_input}"

    Classification options:
    - conversation: General chat, questions, explanations
    - task: Code generation, file operations, complex work
    - system: Server control, configuration, debugging

    Respond with: classification|confidence_score|reason
    """

    result = await ux_model.generate(analysis_prompt, max_tokens=30)
    classification, confidence, reason = result.split('|')

    return IntentAnalysis(
        classification=classification.strip(),
        confidence=float(confidence.strip()),
        reason=reason.strip(),
        requires_task_execution=(classification == 'task' and confidence > 0.7)
    )
```

### Handoff Protocol
When task execution is required:

1. **Quick acknowledgment**: "I'll work on that for you..."
2. **Task submission**: Submit to gateway via HTTP MCP
3. **Progress monitoring**: Stream updates from gateway
4. **Natural updates**: Convert technical progress to user-friendly messages

## Conversation State Management

### Context Tracking
```python
class ConversationState:
    """Manages conversation context across model switches"""

    def __init__(self):
        self.history: List[ConversationTurn] = []
        self.current_tasks: Dict[str, TaskContext] = {}
        self.user_preferences: Dict[str, Any] = {}
        self.session_start = time.time()

    def add_turn(self, user_input: str, response: str, task_id: str = None):
        """Add conversation turn with optional task reference"""
        turn = ConversationTurn(
            timestamp=time.time(),
            user_input=user_input,
            response=response,
            task_id=task_id,
            model_used='ux'
        )
        self.history.append(turn)

        # Maintain rolling context window (last 20 turns)
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def get_context_for_model(self, max_tokens: int = 1000) -> str:
        """Get conversation context formatted for model"""
        context_parts = []
        for turn in self.history[-10:]:  # Last 10 turns
            context_parts.append(f"User: {turn.user_input}")
            context_parts.append(f"Assistant: {turn.response}")

        context = "\n".join(context_parts)
        # Truncate if too long
        if len(context) > max_tokens:
            context = context[-max_tokens:]

        return context
```

### Cross-Model State Preservation
When handing off to task execution:

1. **Context snapshot**: Save current conversation state
2. **Task context**: Include relevant conversation history
3. **Result integration**: Merge task results back into conversation
4. **Seamless continuation**: Resume natural conversation flow

## Progress Update Streaming

### Real-Time Task Monitoring
```python
async def monitor_task_progress(task_id: str) -> AsyncGenerator[str, None]:
    """Stream natural language progress updates"""

    last_update = None
    while True:
        # Poll gateway for task status
        status = await gateway_client.get_task_status(task_id)

        if status != last_update:
            # Generate natural update using UX model
            update_message = await generate_progress_update(status)
            yield update_message
            last_update = status

        if status.get('status') in ['completed', 'failed']:
            break

        await asyncio.sleep(2)  # Poll every 2 seconds
```

### Progress Message Templates
```python
PROGRESS_TEMPLATES = {
    'started': [
        "I'm working on that now...",
        "Let me take care of that for you...",
        "Starting work on your request..."
    ],
    'progress': [
        "Still working on it... {detail}",
        "Making progress... {detail}",
        "Getting there... {detail}"
    ],
    'completed': [
        "Done! {summary}",
        "Finished! {summary}",
        "All set! {summary}"
    ],
    'failed': [
        "I ran into an issue: {error}",
        "Something went wrong: {error}",
        "I couldn't complete that: {error}"
    ]
}

async def generate_progress_update(status: dict) -> str:
    """Generate natural language progress update"""
    template = random.choice(PROGRESS_TEMPLATES[status['status']])

    # Use UX model to personalize the message
    context = {
        'detail': status.get('detail', ''),
        'summary': status.get('result', ''),
        'error': status.get('error', '')
    }

    return template.format(**context)
```

## User Interrupt Handling

### Graceful Interruption
The UX agent must handle user interruptions during long-running tasks:

```python
async def handle_user_interrupt(user_input: str, active_tasks: Dict[str, str]):
    """Handle user input during task execution"""

    # Check if it's a control command
    if user_input.lower() in ['stop', 'pause', 'cancel']:
        for task_id in active_tasks:
            await gateway_client.interrupt_task(task_id, user_input.lower())
        return f"Task {user_input.lower()}d."

    # Check if it's a status request
    if 'status' in user_input.lower() or 'progress' in user_input.lower():
        status_updates = []
        for task_id, description in active_tasks.items():
            status = await gateway_client.get_task_status(task_id)
            status_updates.append(f"{description}: {status['status']}")
        return "\n".join(status_updates)

    # Otherwise, handle as normal conversation
    return await handle_conversation(user_input)
```

### Interrupt Commands
- **"stop"**: Gracefully halt current task
- **"pause"**: Checkpoint and pause for later resume
- **"status"**: Show current progress without interrupting
- **"cancel"**: Abort task and clean up

## Natural Conversation Flow Patterns

### Conversation Patterns
1. **Greeting and Context**: Warm, contextual greetings
2. **Task Acknowledgment**: Confirming understanding
3. **Progress Narration**: Explaining what's happening
4. **Result Presentation**: Clear, actionable results
5. **Follow-up Invitation**: Encouraging continued interaction

### Response Personalization
```python
class PersonalizedResponses:
    """Generate personalized responses based on user history"""

    def __init__(self, conversation_state: ConversationState):
        self.state = conversation_state

    async def generate_greeting(self) -> str:
        """Generate contextual greeting"""
        hour = time.localtime().tm_hour

        if hour < 12:
            time_greeting = "Good morning"
        elif hour < 17:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"

        # Check for recent activity
        if self.state.history:
            last_interaction = self.state.history[-1]
            if time.time() - last_interaction.timestamp < 3600:  # Within 1 hour
                return f"{time_greeting}! Ready to continue where we left off?"

        return f"{time_greeting}! How can I help you today?"

    async def generate_task_acknowledgment(self, task_description: str) -> str:
        """Generate personalized task acknowledgment"""
        templates = [
            "I'll take care of that for you.",
            "Let me work on that right away.",
            "I'm on it!",
            "I'll get started on that now."
        ]

        # Use UX model to select appropriate tone
        return random.choice(templates)
```

## Implementation Architecture

### HTTP MCP Server Structure
```python
class UXAgentServer(HTTPMCPServer):
    """UX Agent HTTP MCP Server with dual-model integration"""

    def __init__(self, model_pool: ModelPool, gateway_client: HTTPMCPClient):
        super().__init__(
            name="ux_agent_server",
            version="1.0.0",
            port=8082
        )

        self.model_pool = model_pool
        self.gateway_client = gateway_client
        self.conversation_state = ConversationState()

        # Register MCP tools
        self.register_tool(self.conversation)
        self.register_tool(self.get_server_info)

    async def conversation(self, user_input: str) -> dict:
        """Main conversation tool with task detection"""

        # Analyze intent using UX model
        intent = await self.analyze_intent(user_input)

        if intent.requires_task_execution:
            # Submit task and stream progress
            task_id = await self.gateway_client.submit_task(user_input)

            # Return task acknowledgment
            return {
                'reply': await self.generate_task_acknowledgment(user_input),
                'task_detected': True,
                'task_id': task_id,
                'confidence': intent.confidence
            }
        else:
            # Direct conversation response
            response = await self.generate_conversation_response(user_input)

            return {
                'reply': response,
                'task_detected': False,
                'confidence': intent.confidence
            }
```

### Integration Points
1. **Model Pool**: Access to always-loaded UX model
2. **Gateway Client**: Task submission and monitoring
3. **Database**: Conversation history and preferences
4. **Configuration**: Response templates and behavior settings

## Success Metrics

### Performance Validation
- **Response latency**: <1s for all user interactions
- **Task detection accuracy**: >80% correct classification
- **Memory usage**: <4GB for UX model operations
- **Conversation continuity**: Context preserved across sessions

### User Experience Validation
- **Natural flow**: Conversations feel seamless and responsive
- **Clear feedback**: Users understand what's happening
- **Interrupt handling**: Graceful response to user commands
- **Progress visibility**: Real-time updates during task execution

## Future Enhancements

### Advanced Features
1. **Voice Integration**: Natural voice input/output
2. **Emotion Detection**: Tone-aware responses
3. **Learning Preferences**: Adaptive response style
4. **Multi-modal Input**: Text, voice, and visual input
5. **Proactive Suggestions**: Anticipate user needs

### Performance Optimizations
1. **Response Caching**: Cache common responses
2. **Predictive Loading**: Anticipate model needs
3. **Streaming Responses**: Character-by-character output
4. **Background Processing**: Prepare responses in advance

This design ensures the UX Agent meets architecture requirements while providing a natural, responsive user experience that seamlessly integrates with the dual-model system.
