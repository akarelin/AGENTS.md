# DAPY Vision - User Checkpoint

**Date:** 2025-11-26
**Purpose:** Preserve user's vision using only their words, organized by topic, with history of changes

---

## Project Overview

### Core Goal

> Rebuilding my personal knowledge management workflow

### Current State

> Currently: cascading .md with instructions + Claude core. See all my git repos. Pull only md files.

### What We're Building

> Building: DAPY, reimplement tools That Claude provided and my subagents and tools (all in md) as tools. Reimplement advanced sub-prompts like archive or process mistakes using native tools of langchain and lang graph. I want to be able to observe my interaction with DAPY, breakpoints, snapshots, human in the loop, all the best practices.

### Technology Stack

> Stick to python + prompts. Rebuild using best practices langchain/graph 1.0

---

## Deployment Strategy

### Three Deployment Targets

> Plan for 3 deployments: cloud vm on GCP, docker-compose on local server and lang chains cloud.

### Deployment Decision

~~Prepare to deploy to langchain cloud.~~

> ~~All right, so please review that my main workflow is working. And that, so my main workflow will be as following. I will start using DAPY the same way as I normally use Cloud Code.~~

**Latest Decision:**

> B, but don't start it yet.

*(Context: Chose LangChain Cloud deployment option B, but instructed not to start deployment yet)*

---

## Testing & Iteration Workflow

### My Testing Approach

> And I expect that at the beginning, it will not behave as expected. And what I'd like to do, I'd like to be able to like, to immediately look at what happened and make corrections. So my workflow will be, so I will get through like several basic operations. Let's say set map ID for a new project, you know, like stuff that I usually do. And I want to stop whenever I get a dissatisfactory response or I see a link invalid.

> Or I see invalid tool use, so I want to stop and then what's most importantly is I want to provide to you, Manus, all of the access or all of the data that you will need to troubleshoot 1.1 from.

### Collaborative Debugging

> So let's say I deploy it to a private cloud, to a Docker container, I can expose that IP to your container and can you interact in a way where I will give you all the access you need. I will start using zpage and CLI and if something goes wrong, I invoke your session and you can go and look and collect everything and suggest some answers.

### Manus Ownership

> I expect that you will deploy, run, manage and interact with dapy. I wont try it until you can deliver good results on 10 simple test use cases.

---

## Data Access & Sync

### Repository Access

> Add sync/access mechanism between agents's filesystem and my data. Code and prompts should be in GitHub, but the rest can be locally stored or pushed to Google Drive. I also can provide rsync or scp + data location.

### Clarification on Data Access

> No that's to provide data to agents without having to use MCPs or tools.

> Agents can already read my git. It's code. Agents need all kinds of data to perform tasks.

---

## Test Data & Examples

### Source of Examples

> Select good example tasks from my LLM logs found in underscore repo. Most tasks required integration:tools. I will provide data as text files in folders instead of API access. This will be staging/sandbox environment for our sandbox.

### Golden Dataset

> Establish "golden dataset" in langchain. Place to keep perfect examples of task execution. Allow me to annotate past LLM conversation as golden.

### Using Native LangChain Features

> Extract any examples for repos. Use native thing of langchain t that does golden dataset. Same for prompt canvas feature of langchain

### Better Idea: Log Ingestion

> So I just had a better idea. What if we create a mechanism to ingest my LLM logs from MD files or from JSON files into a Lankchain backend and then you will run queries against it. I'll be able to annotate it first of all and you'll be able to run queries to generate your test use case.

---

## LLM Chat Logs

### Chat Log Exports

> Chat log exports. Do they include cli interactions (codex, claudecode)? If not, how to procure. Propose other ways to capture LLM logs for analysis.

### Unified LLM Interface (Future)

> What if I want to run all of my LLM interactions through unified interface.

> Can I keep using native iOS apps, can I use one 3rd party unified app, what would it take to build and iOS app that just passes everything into API.

### Capturing Historical Data

> add and research another items to the roadmap. I can, if let's say I pay for LangSmith, LangChain platform, can I take my whole bunch, let's say, chat, GPT, and entropic interactions, import them into LangChain, whatever tools they have, and run some like machine, run some like process that will help me improve that main agentic loop of DAPY. It should be like having a full history of my interactions with LAMs that I can annotate, should be a great data point to tweak the best workflow for what we're building.

---

## LangChain Platform

### Registration & Setup

> Prepare to deploy to langchain cloud. I will register for an account, you will suggest the plan to pay for, API keys I need to add or generate so you can operate langchain cloud. From there I expect that you will handle deployment and testing. You should have enough examples of past interactions in .md files in my repos. If you need more test tasks - let me know.

### Platform Features Research

> Just curious, does Lankchain have a model router for me to put in all of my other LLMs into? And if they do, is there a front-end for Lankchain that I can use instead of desktop version of JGPT or Entropic? Or is there anything I can use on iOS that would be great?

### Separate Roadmap Item

> This is capturing chat GPT and entropic is a separate item on the roadmap. I just wanted for you to record it and plan for it, but right now we're just implementing DAPY with full durability.

---

## Feedback System

### User Feedback Mechanism

> Make sure to include some easy way to capture my feedback from CLI, where I can invoke something and give a free-form text field what went wrong, and that should be submitted via standard mechanism that LendChain provides, and you will have an agent that's looking at the new records and the user feedback table, whatever it stores by LendChain, and you will be creating tickets to resolve them, and you'll build a dashboard showing me what has been submitted, what has been done, just so I can keep track of you, resolving, reacting to the feedback.

---

## Deployment Environment

### Server Five

> So let's say I'll deploy it to Docker Compose. So your access should be part of that deployment. So like, let's do first deployment to Docker Compose. Let's say it will go on a server called five. You will find some of the other things deployed there. See around repositories for services. So prepare it for deployment same way as you afford it. And also provide yourself keys. I will take care of the firewall.

---

## Decision Points & Changes

### LangSmith UI vs Custom Dashboard

> So, at the decision point, before building our own UI for traceability, if instead of using Docker Compose as an initial platform, what if I get a paid subscription to the Lank Chain platform, will I get all of the UI tools that I need directly from the Lank Chain? That would be better for me to use their native tools, as long as they have an API for you to connect.

**Decision:** Use LangSmith's native UI instead of building custom dashboard

---

## Checkpoint Instructions

> Okay, now it's time to do a checkpoint. So as a part of checkpoint, create a document that outlines my vision, only use my words, and on topics where I change my mind, only keep the history, but strike out the old versions and keep the latest version. So effectively, no text that I have produced should be lost. It should be organized and should not be polluted with the LLM created contents. More to come. Second, don't do anything.

---

## Status

**Awaiting:** More instructions from user before proceeding

**Current Phase:** Checkpoint - preserving user vision

**Next Steps:** TBD by user
