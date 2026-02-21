# START HERE - Next Manus Instance

**User will start you with:** `Resume work on CRAP/DAPY`

---

## Quick Start Guide

### 1. Read These Documents First (In Order)

1. **USER_VISION_CHECKPOINT.md** - User's requirements (their words only)
2. **CURRENT_STATE.md** - What has been built (nothing is DONE yet)
3. **HANDOFF_TO_NEXT_MANUS.md** - Your instructions

### 2. Understand the Context

**Project:** DAPY - Personal knowledge management workflow
**User:** Alex (akarelin)
**Status:** Code exists, NOT tested, NOT deployed, NOT approved
**Your Job:** Test, iterate, debug, deliver working system

### 3. Critical Rules

**NOTHING IS DONE UNTIL USER APPROVES IT**

Even if:
- Code exists
- Tests pass
- Looks good

It's NOT done until user explicitly says: "This is done"

### 4. What User Expects

**Phase 1 (Your responsibility):**
- Deploy DAPY
- Run 10 test cases
- Iterate until all pass
- Show user results
- Get approval

**Phase 2 (After approval):**
- User starts using it
- User encounters issues
- User gives you access
- You debug collaboratively
- Iterate until perfect

### 5. Repository Structure

```
CRAP/DAPY/
├── START_HERE.md                    <- You are here
├── USER_VISION_CHECKPOINT.md        <- Read first
├── CURRENT_STATE.md                 <- Read second
├── HANDOFF_TO_NEXT_MANUS.md        <- Read third
├── dapy/                            <- Core code (27 Python files)
│   ├── cli.py                       <- CLI entry point
│   ├── tools/                       <- 10 LangChain tools
│   ├── workflows/                   <- 3 LangGraph workflows
│   ├── middleware/                  <- Observability stack
│   └── prompts/                     <- System prompts
├── tools/                           <- Log ingestion tools
│   ├── ingest_llm_logs.py          <- Import logs to LangSmith
│   ├── query_llm_logs.py           <- Query and generate tests
│   └── README_LOG_INGESTION.md     <- Documentation
├── deployment/                      <- Deployment configs
│   ├── langchain-cloud/            <- User chose this (but don't start yet)
│   ├── server-five/                <- Alternative
│   └── gcp/                        <- Alternative
└── [Documentation files]           <- Various guides and analysis

Total: 50+ files, ~3,635 lines of Python, ~15,000 lines of docs
```

### 6. Immediate Actions

**When user says "Resume work on CRAP/DAPY":**

1. Acknowledge you've read the context
2. Ask if user has registered for LangChain Cloud
3. Ask if user has API keys ready
4. Ask if user wants you to proceed with deployment
5. WAIT for user's answers before doing anything

**DO NOT:**
- Start deploying without approval
- Make assumptions about API keys
- Proceed without explicit go-ahead
- Assume anything is done

### 7. Key Files to Reference

**User Requirements:**
- `USER_VISION_CHECKPOINT.md` - User's vision in their words

**Technical Context:**
- `CURRENT_STATE.md` - Complete inventory of code
- `HANDOFF_TO_NEXT_MANUS.md` - Your instructions

**Test Cases:**
- `DAPY_TEST_CASES.md` - 10 test cases to run

**Deployment:**
- `LANGCHAIN_CLOUD_DEPLOYMENT.md` - Deployment guide
- `API_KEYS_TEMPLATE.txt` - Keys needed from user

**Log Ingestion:**
- `tools/README_LOG_INGESTION.md` - How to import user's logs
- `GOLDEN_DATASET_PLAN.md` - Golden dataset strategy

### 8. User's Communication Style

- **Direct and technical** - No need to over-explain
- **Iterative** - Expects things won't work first try
- **Collaborative** - Wants to work WITH you
- **Evidence-based** - Show logs, traces, screenshots

### 9. Success Criteria

**Phase 1 Complete When:**
- All 10 test cases pass
- Results documented with evidence
- User approves to proceed

**Then:** User starts using DAPY

### 10. Questions to Ask User

When you start:

1. **API Keys:** Have you registered for LangChain Cloud? Can you provide:
   - LANGCHAIN_API_KEY
   - OPENAI_API_KEY
   - GITHUB_TOKEN
   - ANTHROPIC_API_KEY (optional)

2. **Deployment:** Ready to deploy to LangChain Cloud?

3. **Log Locations:** Where are your:
   - Daily Notes with LLM interactions?
   - ChatGPT export file?
   - Claude export file?

4. **Priority:** What should I focus on first?

### 11. Remember

**User will say:** `Resume work on CRAP/DAPY`

**You should:**
1. Read the three key documents
2. Acknowledge you understand the context
3. Ask the questions above
4. Wait for user's answers
5. Then proceed

**Don't assume, don't proceed without approval, show your work.**

---

## Quick Reference

**User:** akarelin
**Project:** DAPY
**Repo:** akarelin/CRAP/DAPY
**Status:** Code exists, NOT done
**Your job:** Test, iterate, deliver
**User's expectation:** Collaborative debugging

**Read first:**
1. USER_VISION_CHECKPOINT.md
2. CURRENT_STATE.md
3. HANDOFF_TO_NEXT_MANUS.md

**Then ask user for:**
- API keys
- Deployment approval
- Log locations
- Priority

**Good luck!**
