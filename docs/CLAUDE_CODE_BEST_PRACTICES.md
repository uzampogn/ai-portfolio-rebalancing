# Claude Code Best Practices - MVP Implementation Guide

This guide outlines the optimal workflow for implementing the Portfolio Rebalancing MVP with Claude Code for rapid, autonomous development with minimal debugging.

---

## Implementation Strategy: Phase-by-Phase with Immediate Testing

### Why Phase-by-Phase?

✅ **Sequential Dependencies**: Each phase builds on the previous
✅ **Immediate Validation**: Catch issues early when context is fresh
✅ **Reduced Debugging**: Isolate problems to specific phase
✅ **Clear Progress**: Visual milestones as you complete phases

### Recommended Flow

```
Phase 1: Setup & Polygon Integration
    ↓ [Test: verify Polygon returns prices]

Phase 2: MCP Server
    ↓ [Test: MCP server starts, tools work]

Phase 3: Three Agents
    ↓ [Test: agents run, delegation works]

Phase 4: Gradio UI
    ↓ [Test: UI loads, button triggers agents]

Phase 5: Final Integration
    ↓ [Test: end-to-end rebalancing]
```

---

## When to Use Subagents

### ❌ DON'T Use Subagents For This Project

Reasons:
- Phases are sequential (not parallelizable)
- Each phase is manageable (~3-5 files)
- Coordination overhead outweighs benefits
- Harder to maintain context across subagents

### ✅ DO Use Subagents When

- Building multiple independent features in parallel
- Large refactoring across many files
- Research + implementation simultaneously
- Working on unrelated parts of codebase

---

## Workflow Within Each Phase

```
1. You: Request phase implementation
   → "Implement Phase 2"

2. Claude: Uses TodoWrite to create phase tasks
   → Shows clear checklist of what will be done

3. Claude: Implements all files for the phase
   → Creates/edits files systematically

4. Claude: Reports completion
   → "Phase 2 complete, ready for testing"

5. You: Test immediately
   → Run provided test commands

6. Together: Debug if issues arise
   → Paste errors, Claude fixes

7. You: Approve phase
   → "Phase 2 approved, proceed to Phase 3"
```

---

## Best Practice 1: TodoWrite for Transparent Progress

Claude will use TodoWrite to:
- Break down each phase into tasks
- Mark tasks as in_progress/completed
- Keep you informed of progress
- Track blockers

**Example TodoWrite Output**:
```
Phase 2: MCP Server Implementation
☐ pending: Create portfolio_mcp.py
☑ completed: Implement get_portfolio_state tool
☑ completed: Implement simulate_trade tool
⟳ in_progress: Test MCP server starts
☐ pending: Verify all tools working
```

**Benefits**:
- Visual progress tracking
- Clear status at any point
- Easy to see what's blocked
- Transparent workflow

---

## Best Practice 2: Immediate Testing Strategy

After each phase, Claude provides:

### Test Commands
```bash
# Phase 2 Example
uv run portfolio_mcp.py
```

### Expected Output
```
✓ MCP server running on stdio
✓ Registered 5 tools
```

### What to Check
- No error messages
- Expected output appears
- Process runs without crashing

### If It Fails
- Paste the full error message to Claude
- Claude debugs and fixes
- Re-test before moving on

**Golden Rule**: Never proceed to next phase with failing tests.

---

## Best Practice 3: Incremental File Creation

Claude creates files in logical order:

### Phase 1: Foundation
1. Data/Config (mock_data.py, .env)
2. Test utilities (test_polygon.py)

### Phase 2: Core Logic
1. MCP server (portfolio_mcp.py)

### Phase 3: Agents
1. Helper agents first (researcher.py, financial_analyst.py)
2. Orchestrator last (trader.py)

### Phase 4: UI
1. UI components (app.py)

**Why This Order?**
- Minimizes dependency issues
- Each file can be tested independently
- Clear build-up from foundation to complete system

---

## Best Practice 4: Self-Contained Testing

Every module includes test code:

```python
if __name__ == "__main__":
    # Quick test/demo code
    print("Testing module...")
    # Run basic functionality
```

**Benefits**:
- Run `uv run filename.py` to verify it works
- No need for separate test files in MVP
- Quick smoke tests during development

---

## Best Practice 5: Clear Commit Points

After each working phase:

```bash
git add .
git commit -m "Phase 2: MCP server with Polygon integration working"
```

**Why Commit Per Phase?**
- Creates rollback points if needed
- Documents progress
- Safe experimentation (can always revert)
- Clear project history

---

## Testing Tiers

### Tier 1: Smoke Tests (Required)
**Run after each phase**

```bash
# Does it run without crashing?
uv run <file>.py
```

**Goal**: Verify basics work

### Tier 2: Functional Tests (Recommended)
**Quick manual checks**

```bash
# Does Polygon return real prices?
uv run test_polygon.py

# Do agents complete rebalancing?
uv run agents/trader.py
```

**Goal**: Verify core functionality

### Tier 3: Integration Tests (Phase 5)
**Full end-to-end**

```bash
# Does UI work?
uv run app.py
# → Click button, verify trades appear
```

**Goal**: Verify complete workflow

### Skip for MVP
- ❌ Unit tests with pytest (defer to V2)
- ❌ Mocking/fixtures (use real APIs)
- ❌ Coverage reports
- ❌ CI/CD pipelines

---

## Debugging Strategy

### When Something Breaks

**Your Action**: Paste the complete error message

**Claude Will**:
1. Read and analyze the error
2. Identify root cause
3. Fix the specific issue
4. Explain what was wrong
5. Ask you to re-test

### Example Debugging Flow

```
You: "Error: POLYGON_API_KEY not found"

Claude: "The .env file isn't being loaded properly.
         Let me add the load_dotenv() call..."

Claude: [Fixes mock_data.py]

Claude: "Fixed! The issue was missing python-dotenv import.
         Try again: uv run test_polygon.py"

You: [Re-tests] "Working now!"
```

### Common Issues Claude Watches For

1. **Import errors** → Missing dependencies in requirements
2. **API errors** → Wrong API key format or missing .env
3. **Agent timeout** → Increase max_turns parameter
4. **MCP connection** → Port conflicts or server not starting
5. **Price fetching** → Polygon rate limits or wrong ticker format

---

## Communication Protocol

### ✅ Good Communication

**Clear and Actionable**:
- "Phase 2 complete and tested, proceed to Phase 3"
- "Error: ModuleNotFoundError: No module named 'polygon'"
- "Agents running but not delegating to researcher"
- "Trades executed successfully, 5 trades total"

### ❌ Unhelpful Communication

**Too Vague**:
- "It doesn't work"
- "Something is wrong"
- "Try again"
- "There's an error"

### What Claude Needs When Debugging

1. **Complete error message** (not just the last line)
2. **What command you ran** (exact command)
3. **Context** (which phase, what was working before)
4. **Console output** (if relevant)

### What Claude Will Ask If Stuck

- "What error message do you see?"
- "Can you paste the console output?"
- "Did test_polygon.py work in Phase 1?"
- "Which phase are you on?"

---

## Phase-Specific Workflows

### Phase 1: Setup & Polygon Integration (35 min)

**You Say**: "Implement Phase 1"

**Claude Will**:
1. Create TodoWrite checklist
2. Create files:
   - `mock_data.py` (with Polygon integration)
   - `.env.example` (API key template)
   - `test_polygon.py` (verification script)
3. Report completion

**You Do**:
```bash
# Set up environment
cd trader_app
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install polygon-api-client python-dotenv

# Configure API keys
cp .env.example .env
# Edit .env with your actual API keys

# Test Polygon integration
uv run test_polygon.py
```

**Expected Output**:
```
Testing Polygon API integration...
==================================================
VTI          $    225.30
AGG          $    102.15
BTC-USD      $ 48,234.50
VNQ          $     90.75
==================================================
✓ Polygon API integration working!
```

**If Success**: "Phase 1 approved, proceed to Phase 2"

---

### Phase 2: MCP Server (45 min)

**You Say**: "Implement Phase 2"

**Claude Will**:
1. Update TodoWrite for Phase 2
2. Create `portfolio_mcp.py` (with all tools)
3. Test it starts without errors
4. Report completion

**You Do**:
```bash
uv pip install fastmcp
uv run portfolio_mcp.py
# Should show MCP server starting on stdio
# Press Ctrl+C to stop
```

**Expected Output**:
```
Starting MCP server on stdio...
✓ Registered tool: get_portfolio_state
✓ Registered tool: get_asset_price
✓ Registered tool: simulate_trade
✓ Registered tool: get_trade_history
✓ Registered tool: calculate_performance
✓ Registered resource: portfolio://current
```

**If Success**: "Phase 2 approved, proceed to Phase 3"

---

### Phase 3: Three Agents (75 min)

**You Say**: "Implement Phase 3"

**Claude Will**:
1. Update TodoWrite for Phase 3
2. Create `agents/` folder structure
3. Implement:
   - `researcher.py`
   - `financial_analyst.py`
   - `trader.py`
   - `__init__.py`
4. Test agent coordination
5. Report completion

**You Do**:
```bash
uv pip install agents
uv run agents/trader.py
```

**Expected Output**:
```
🚀 Starting 3-Agent Portfolio Rebalancing System
======================================================================
Agents:
  1. Researcher - Market research specialist
  2. Financial Analyst - Portfolio analysis expert
  3. Trader - Orchestrator and executor

💰 Using REAL-TIME prices from Polygon API
======================================================================

📡 Connecting to MCP servers...
  ✓ Portfolio MCP connected (with Polygon API)
  ✓ Brave Search MCP connected
  ✓ Fetch MCP connected

🤖 Creating specialist agents...
  ✓ Researcher agent created
  ✓ Financial Analyst agent created
  ✓ Trader (orchestrator) agent created

======================================================================
🎯 Starting rebalancing process...
======================================================================

[Agent activity logs...]

✅ Trade executed: SELL 0.1 BTC-USD @ $48234.50
✅ Trade executed: BUY 15 VTI @ $225.30
[More trades...]

======================================================================
✅ Rebalancing process completed!
======================================================================
```

**Critical Test**: If agents run and execute trades, you're 80% done!

**If Success**: "Phase 3 approved, proceed to Phase 4"

---

### Phase 4: Gradio UI (45 min)

**You Say**: "Implement Phase 4"

**Claude Will**:
1. Update TodoWrite for Phase 4
2. Create `app.py` (Gradio interface)
3. Test UI launches
4. Report completion

**You Do**:
```bash
uv pip install gradio plotly pandas
uv run app.py
```

**Expected Output**:
```
Running on local URL:  http://127.0.0.1:7860

To create a public link, set `share=True` in `launch()`.
```

**Manual Test**:
1. Open http://localhost:7860 in browser
2. Verify initial portfolio displays with real prices
3. Click "Run 3-Agent Rebalancing" button
4. Watch console for agent activity
5. Verify trades appear in UI table

**If Success**: "Phase 4 approved, proceed to Phase 5"

---

### Phase 5: Final Integration & Testing (45 min)

**You Say**: "Implement Phase 5"

**Claude Will**:
1. Update TodoWrite for Phase 5
2. Run full end-to-end tests
3. Create README.md
4. Document any known issues
5. Report final status

**You Do**:
```bash
# Full integration test
uv run app.py

# In UI:
# 1. Verify initial state loads
# 2. Click rebalancing button
# 3. Wait for completion
# 4. Verify all components updated
```

**Success Criteria**:
- ✅ UI loads without errors
- ✅ Real-time prices displayed
- ✅ Agents execute successfully
- ✅ Trades appear in table
- ✅ Charts update correctly
- ✅ Performance metrics calculated

**If Success**: "MVP complete! Ready for deployment."

---

## Estimated Timeline with This Approach

| Activity | Time |
|----------|------|
| Phase 1: Claude implements + you test | 45 min |
| Phase 2: Claude implements + you test | 60 min |
| Phase 3: Claude implements + you test | 90 min |
| Phase 4: Claude implements + you test | 60 min |
| Phase 5: Claude implements + you test | 60 min |
| Debugging buffer | 45 min |
| **Total** | **6 hours** |

### Time Breakdown
- **Claude writing code**: ~3 hours
- **You testing**: ~1.5 hours
- **Debugging together**: ~45 min
- **Setup/config**: ~45 min

---

## Common Pitfalls to Avoid

### ❌ Don't Skip Testing
- Testing after all phases = hard to debug
- Test immediately = easy to isolate issues

### ❌ Don't Batch Approvals
- Approving multiple phases without testing each one
- Creates compounding errors

### ❌ Don't Ignore Warnings
- "It works but shows warnings" → Will break later
- Address warnings immediately

### ❌ Don't Rush API Setup
- Missing API keys = everything fails
- Take time in Phase 1 to configure correctly

### ❌ Don't Skip Environment Setup
- Virtual environment issues = import errors
- Follow setup commands exactly

---

## Quick Reference Commands

### Environment Setup
```bash
cd trader_app
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### Install Dependencies (Phase by Phase)
```bash
# Phase 1
uv pip install polygon-api-client python-dotenv

# Phase 2
uv pip install fastmcp

# Phase 3
uv pip install agents

# Phase 4
uv pip install gradio plotly pandas
```

### Test Commands
```bash
# Phase 1: Test Polygon
uv run test_polygon.py

# Phase 2: Test MCP Server
uv run portfolio_mcp.py

# Phase 3: Test Agents
uv run agents/trader.py

# Phase 4: Test UI
uv run app.py

# Phase 5: Full Integration
uv run app.py
```

### Git Workflow
```bash
# After each working phase
git add .
git commit -m "Phase X: [description] working"

# If you need to rollback
git log  # Find commit hash
git reset --hard <commit-hash>
```

---

## Troubleshooting Guide

### Issue: "Module not found"
**Cause**: Missing dependency
**Fix**: `uv pip install <package>`

### Issue: "POLYGON_API_KEY not found"
**Cause**: .env not loaded or missing
**Fix**:
1. Verify .env exists
2. Check .env has POLYGON_API_KEY=your_key
3. Restart terminal/reload environment

### Issue: "MCP server won't start"
**Cause**: Port conflict or missing fastmcp
**Fix**:
1. Kill existing processes: `pkill -f portfolio_mcp`
2. Reinstall: `uv pip install --force-reinstall fastmcp`

### Issue: "Agents timeout"
**Cause**: max_turns too low
**Fix**: Increase max_turns in trader.py

### Issue: "Polygon rate limit"
**Cause**: Too many API calls
**Fix**:
1. Wait 1 minute (free tier resets)
2. Caching should prevent this
3. Check cache is working

### Issue: "Gradio won't launch"
**Cause**: Port 7860 in use
**Fix**: `app.launch(server_port=7861)`

---

## Success Indicators

### Phase 1 Success
✅ test_polygon.py shows real prices
✅ No import errors
✅ All 4 assets return prices

### Phase 2 Success
✅ MCP server starts on stdio
✅ All 5 tools registered
✅ No errors on startup

### Phase 3 Success
✅ All 3 agents created
✅ Agents delegate to each other
✅ Trades executed
✅ Console shows agent coordination

### Phase 4 Success
✅ UI loads in browser
✅ Real prices displayed
✅ Button triggers agents
✅ Trades appear in table

### Phase 5 Success
✅ Full end-to-end rebalancing works
✅ Charts update correctly
✅ Performance metrics calculated
✅ No errors in console

---

## Final Checklist Before Starting

Before saying "Implement Phase 1", ensure:

- [ ] You have Polygon API key ready
- [ ] You have OpenAI API key ready
- [ ] You have Brave API key ready
- [ ] uv is installed (`uv --version`)
- [ ] Node.js is installed (`node --version`) for MCP servers
- [ ] Git is initialized in trader_app/ (optional but recommended)
- [ ] You understand the testing workflow
- [ ] You're ready to test after each phase

---

## How to Start

**Say**: "Let's start with Phase 1. Implement the setup and Polygon integration. Use TodoWrite to track tasks."

**Claude Will**:
1. Create TodoWrite checklist for Phase 1
2. Create all Phase 1 files
3. Provide exact test commands
4. Wait for your approval before Phase 2

**This ensures**:
- ✅ No wasted work (test before building on top)
- ✅ Clear progress visibility (TodoWrite)
- ✅ Rapid debugging (fresh context)
- ✅ High confidence MVP (tested at each step)

---

## Summary

**Key Principles**:
1. **Phase-by-Phase**: Sequential implementation with gates
2. **Immediate Testing**: Test after each phase, not at the end
3. **TodoWrite**: Transparent progress tracking
4. **Clear Communication**: Specific errors, not vague descriptions
5. **Incremental Commits**: Save working states
6. **No Subagents**: Direct collaboration is faster here

**Golden Rules**:
- Never skip a phase test
- Never approve a failing phase
- Always paste complete error messages
- Commit after each working phase

**Expected Timeline**: 6 hours to working MVP

---

End of Best Practices Guide
