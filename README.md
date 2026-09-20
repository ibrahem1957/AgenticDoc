# AI Multi-Agent RAG System

A production-style **Multi-Agent AI system** built from scratch to help students, researchers, and professionals understand large documents faster using **AI Agents** and **Retrieval-Augmented Generation (RAG)**.

## Overview

With the growing number of books, research papers, educational materials, and articles being published and continuously updated, reading every document in full and extracting the most important information can be time-consuming.

This project was built to address that problem.

The system allows users to upload documents and interact with their content through multiple AI-powered capabilities. It can automatically summarize long documents, generate review questions, and provide a conversational chatbot that answers questions based on the uploaded content.

The goal is to make large amounts of information easier to explore, understand, and review without requiring users to manually read hundreds of pages.

## Key Features

### Multi-Agent System

The system uses specialized AI agents, where each agent is responsible for a specific task:

- **Summarizer Agent** — generates structured summaries of long documents.
- **Question Generator Agent** — creates review questions directly from the document content.

### Retrieval-Augmented Generation (RAG)

A complete RAG pipeline is implemented to provide grounded answers based on the uploaded documents.

The pipeline includes:

- Document processing and text extraction
- Text chunking
- Embedding generation using OpenRouter
- Vector similarity search
- Context retrieval using Cosine Similarity
- Context-grounded answer generation

When a user asks a question, the system retrieves the most relevant chunks from the document and uses them as context for generating the answer.

### Interactive Chatbot

The chatbot allows users to interact directly with their documents.

Users can:

- Ask questions about the uploaded content
- Retrieve relevant information from large documents
- Receive answers grounded in the original document
- View the retrieved context used to support the answer

### Custom Agent Engine

One of the main technical aspects of this project is that the agent architecture was built **from scratch**, without relying on agent frameworks such as LangChain or LangGraph.

The project includes a custom:

- **Multi-Agent Architecture**
- **ReAct Agent Engine**
- **Tool Registry System**
- **Agent execution loop**
- **Tool execution mechanism**
- **Agent state and control flow**

This provides greater visibility into how agents reason, select tools, execute actions, and process observations.

### Tool System

The system includes a custom tool infrastructure that allows agents to interact with external functionality.

Currently supported tool:

- `read_file` — enables agents to read and process document content.

The architecture is designed so additional tools can be integrated later.

### Observability

An observability layer was implemented to make agent execution easier to inspect and debug.

It tracks:

- Agent execution steps
- Tool calls
- Tool outputs
- Execution time
- Agent actions and observations

This makes it possible to understand how the system reaches its results instead of treating the agent as a black box.

### Reliability

The agent engine also includes reliability mechanisms to reduce unstable execution behavior, including:

- Loop detection
- Repetition prevention
- Agent execution safeguards

These mechanisms help prevent agents from repeatedly executing the same action or becoming stuck in unnecessary reasoning loops.

## Architecture

At a high level, the system combines:

**Document → Processing → Chunking → Embeddings → Vector Retrieval → Relevant Context → AI Agent / Chatbot → Answer**

The Multi-Agent layer operates alongside the RAG pipeline to perform specialized tasks such as summarization and question generation.

## Built From Scratch

The project intentionally avoids high-level agent frameworks such as **LangChain** and **LangGraph**.

Instead, the core components were implemented directly in Python to better understand and control the internal behavior of agentic AI systems.

This includes:

- Agent orchestration
- ReAct reasoning loop
- Tool registration and execution
- RAG pipeline
- Vector retrieval with Cosine Similarity
- Execution tracing and observability
- Loop and repetition detection

## Use Cases

The system can be useful for:

- Students reviewing textbooks and lecture materials
- Researchers exploring papers and technical documents
- Professionals working with long reports
- Generating study questions automatically
- Summarizing large amounts of information
- Asking document-specific questions through a conversational interface

## Tech Stack

- **Python**
- **OpenRouter**
- **Large Language Models (LLMs)**
- **Embeddings**
- **Retrieval-Augmented Generation (RAG)**
- **Cosine Similarity**
- **ReAct Agent Architecture**
- **Custom Multi-Agent System**

## Project Goal

The goal of this project is not only to build a document assistant, but also to explore the internal architecture behind modern **Agentic AI and RAG systems** by implementing the core components from scratch.

Rather than hiding agent behavior behind existing frameworks, the project provides direct control over the agent loop, tools, retrieval pipeline, observability, and reliability mechanisms.
