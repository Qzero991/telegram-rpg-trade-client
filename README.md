# 🤖 Telegram RPG-game Trade Client

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)

**Automated trade market analyzer for a Telegram-based RPG game that detects arbitrage opportunities (buy low, sell high).**


---

## 📌 Table of Contents

* [About the Project](#-about-the-project)
* [Features](#-features)
* [How It Works](#-how-it-works)
* [Telegram Bot Control](#-telegram-bot-control)
* [Database](#-database)
* [Requirements](#-requirements)
* [Credentials & API Keys](#-required-credentials--api-keys)
* [Environment Variables](#-environment-variables)
* [Running the Project](#-running-the-project)
    * [Docker (Recommended)](#-running-with-docker-recommended)
    * [Local Setup](#-local-setup-advanced)
* [Technologies Used](#-technologies-used)
* [License](#-license)

---

## 📝 About the Project

**Telegram RPG-game Trade Client** is an automated system for analyzing player-driven trade markets in Telegram-based RPG games.

The project was originally developed for the game **EpsilionWar**, but its architecture is generic and can be reused as a **template for other Telegram trade analysis or monitoring tasks**.

The client connects to Telegram, listens to new messages in a trading chat, extracts buy/sell offers from unstructured text, compares them with existing market data, and automatically detects **arbitrage opportunities**. When a profitable opportunity is found, the user is notified via a Telegram bot.


> This project focuses on real-world conditions where trade messages:
> * Have no strict format
> * Contain typos, emojis, and abbreviations
> * Mix multiple offers in a single message
>
> Because of this, a **Large Language Model (LLM)** is used instead of rigid parsing rules.

---

## ✨ Features


**🧠 LLM-powered trade parsing**<br>
-- Extracts structured trade offers from completely unstructured Telegram messages.

**🌐 OpenAI-compatible model support**<br>
-- Works with any OpenAI-compatible API (e.g. DeepSeek, OpenAI, or local models).

**📈 Arbitrage detection engine**<br>
-- Automatically matches buy/sell offers in real-time and calculates potential profitability.

**🤖 Integrated Telegram bot**<br>
-- Clean notifications with interactive controls to manage, edit, or delete detected entries.

**🛠 Two application modes**<br>
-- `collector` for initializing the database <br>
-- `worker` for active market monitoring.

**🐳 Docker & Docker Compose support**<br>
-- One-command startup with a fully isolated environment and database.

**🗄 PostgreSQL-backed persistence**<br>
-- Reliable storage for items, trade history, and detected arbitrage opportunities.

**🧱 Modular architecture**<br>
-- Designed as a template — easily adapt the client for other games or data sources.---


___

## ⚙️ How It Works

The system operates in two distinct modes. Both modes share a foundation of database initialization and Telegram connectivity.

---

### 📥 Collector Mode: Database Initialization
This mode is used to build a reference library of all game items. 

> ⚠️You need to use this mode first, to initialize database, then you can use Worker mode

**The Workflow:**
1.  **DB Sync:** Connects to PostgreSQL and initializes the schema.
2.  **Authentication:** Establishes a Telegram connection via **MTProto**.
3.  **Bot Listener:** Starts a dedicated listener to capture responses from the official game bot.
4.  **Command Sequence:** Triggers a function that sends predefined inquiry commands to the game bot.
5.  **Data Extraction:** The listener intercepts bot replies, parses item specifications, and populates the `items` table in the database.

---

### 🛠 Worker Mode: Market Analysis & Arbitrage
The core engine for real-time trade monitoring and profit detection.

**The Workflow:**
* **Initialization:** Connects to DB, establishes MTProto session, and starts both the **Trade Chat Listener** and the **Notification Bot**.
* **Message Processing:**
    * The **Handler** waits for incoming messages from the trade chat.
    * New messages are dispatched to the **LLM** for structured data extraction.
* **Item Mapping:**
    * For every extracted offer, the engine performs a search in the DB to find the **Top 5 matches** based on name and parameters.
    * The ID of the best match is assigned as the `item_id` (foreign key) in the `offer` table.
* **Arbitrage Detection:**
    *  The offer is saved to the database.
    *  An **Arbitrage Engine** instantly scans for price discrepancies between the new offer and existing market data.
    *  If a profitable gap is found, the entry is recorded in the DB.
    *  The **Notification Bot** sends an interactive alert to the user for immediate action.

---

## 🤖 Telegram Bot Control

The Telegram bot runs **in parallel** with the main application and provides:
* **Real-time notifications** about arbitrage opportunities.
* **Detailed information** about each offer.
* **Interactive controls** to delete invalid offers, edit incorrect values, or manage detected entries.

<br>

<p align="center">
  <img src="assets/bot_notification.png" alt="Bot Alert Example" width="400">
</p>

---
## 🗄 Database

The project uses **PostgreSQL** as the primary data store.

The database is responsible for:
- Storing a reference catalog of all in-game items
- Persisting parsed trade offers
- Tracking detected arbitrage opportunities
- Linking offers to canonical item definitions

The schema is automatically initialized on application startup.

> ⚠️ The database must be initialized using **Collector mode** before running the Worker.

### 📊 Database Schema

Below is a simplified overview of the database structure.

<p align="center">
  <img src="assets/database_schema.png" alt="Database Schema" >
</p>


___
## 📦 Requirements

Before running the project, make sure the following software is installed:

### Required Software
- **Docker** (recommended)  
  👉 https://docs.docker.com/get-docker/

- **Docker Compose**  
  👉 Included with Docker Desktop

### Optional (for local / non-Docker usage)
- **Python 3.11+**  
  👉 https://www.python.org/downloads/

- **PostgreSQL 16+**  
  👉 https://www.postgresql.org/download/

---

## 🔐 Required Credentials & API Keys

To run the project, you need to generate several credentials manually.

### 🧠 LLM (OpenAI-compatible) API
You need:
- API Key
- Base URL
- Model name

Examples:
- DeepSeek
- OpenAI
- Local OpenAI-compatible servers

---

### 📱 Telegram MTProto Credentials
Used for connecting as a Telegram client.

You need:
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`

📖 Official guide:  
https://my.telegram.org/apps

---

### 🤖 Telegram Bot Token
Used for notifications and interactive controls.

You need:
- `TELEGRAM_BOT_TOKEN`

📖 Official guide:  
https://core.telegram.org/bots#how-do-i-create-a-bot

---

## ⚙️ Environment Variables

Create a `.env` file (or copy from `.env-example`) and configure the following variables:

| Variable | Description                                                                             |
|--------|-----------------------------------------------------------------------------------------|
| `ENGINE_URL` | Async SQLAlchemy connection string for PostgreSQL                                       |
| `LLM_API_KEY` | API key for the LLM provider                                                            |
| `LLM_BASE_URL` | Base URL of the OpenAI-compatible API                                                   |
| `LLM_MODEL` | Model name used for parsing messages                                                    |
| `TELEGRAM_API_ID` | Telegram application API ID                                                             |
| `TELEGRAM_API_HASH` | Telegram application API hash                                                           |
| `TELEGRAM_SESSION_NAME` | Local session name for MTProto authorization                                            |
| `TELEGRAM_BOT_TOKEN` | Token of the Telegram notification bot                                                  |
| `TRADE_GROUP_ID` | Telegram ID of the trade chat (set as default on EpsilionWar in .env-example)           |
| `ITEMS_INFO_GROUP_ID` | Username or ID of the official game bot (set as default on EpsilionWar in .env-example) |
| `EQUIPMENT_LAST_ID` | Last known equipment item ID (id of items for bot commands printer)                     |
| `RESOURCE_LAST_ID` | Last known resource item ID (id of items for bot commands printer)                                                            |
| `APP_MODE` | Application mode: `collector` or `worker`                                               |

___


## 🚀 Running the Project

The system is designed to run in two stages: first, the **Collector** (to build the item database), and then the **Worker** (to monitor the market).

---

## 🐳 Running with Docker (Recommended)

Docker is the preferred method as it automatically handles PostgreSQL, dependencies, and environment isolation.

### 🔹 Phase 1: Initial Database Setup
This step is **mandatory** and must be performed once to populate the database with game items.

1.  **Prepare Environment:** Create a `.env` file from the template.
2.  **Launch Collector:**
    ```bash
    docker-compose up --build collector
    ```

> **🔍 What's happening?**
> * Starts the **PostgreSQL** container and initializes tables.
> * Connects to Telegram via **MTProto** to query the Game Bot.
> * Scrapes, parses, and saves all items to the `items` table.
> * **Action required:** Once the logs show the process is finished, stop the container (**Ctrl+C**).

### 🔹 Phase 2: Live Market Monitoring
After the items are saved, you can start the continuous monitoring service.

1.  **Launch Worker:**
    ```bash
    docker-compose up -d worker
    ```

**In this mode:** The system listens to trade chats, uses LLM to analyze messages, and sends real-time arbitrage alerts to your Telegram bot.

### 🔄 Maintenance
* **Stop Services:** `docker-compose down`
* **Hard Reset:** `docker-compose down -v` (Warning: This deletes all database data).

---

## 🖥 Local Setup (Advanced)

Use this method if you prefer to manage your own Python environment and a local PostgreSQL instance.

### Prerequisites
* **Python:** 3.11+
* **PostgreSQL:** 16+
* **Database:** A manually created database and user.

### 1. Installation & Environment
1.  **Configure Database Connection:**
    Set `ENGINE_URL` in your `.env` to point to your local Postgres:
    ```env
    ENGINE_URL=postgresql+asyncpg://user:password@localhost:5432/db_name
    ```
2.  **Setup Virtual Environment:**
    ```bash
    python -m venv .venv
    
    # Windows:
    .venv\Scripts\activate
    # Linux/macOS:
    source .venv/bin/activate

    pip install -r requirements.txt
    ```

### 2. Execution Steps

#### 📥 Step A: Run Collector (One-time setup)
Used to initialize the database items.
1.  Set `APP_MODE=collector` in your `.env`.
2.  Execute:
    ```bash
    python main.py
    ```

#### ⚙️ Step B: Run Worker (Live monitoring)
Switch to market monitoring once the database is ready.
1.  Set `APP_MODE=worker` in your `.env`.
2.  Execute:
    ```bash
    python main.py
    ```

---

## 🛠 Technologies Used

| Category | Technology |
| :--- | :--- |
| **Language** | Python 3.11+ |
| **Telegram API** | Telethon (MTProto) |
| **Database** | PostgreSQL + Async SQLAlchemy |
| **AI Integration** | OpenAI-compatible LLM APIs (DeepSeek, etc.) |
| **Data Validation** | Pydantic |
| **Infrastructure** | Docker & Docker Compose |

---

## 📄 License

This project is licensed under the **MIT License**.