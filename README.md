# 🤖 COMP7940 Telegram Chatbot Project

A cloud-native, GPT-powered Telegram bot that helps users register interests, receive personalized activity recommendations, and chat with an AI assistant — all built on modern cloud tools with containerization and Firebase integration.

![Heroku + Telegram + GPT + Firebase](https://img.shields.io/badge/deploy-Heroku-blueviolet) ![License](https://img.shields.io/badge/license-CC%20BY--NC%204.0-lightgrey) ![Built With](https://img.shields.io/badge/built%20with-Python%203.11-blue)

---

## ✨ Features

- ✅ Telegram-based chatbot with natural language support  
- ✅ User registration with interest + description  
- ✅ Event recommendation based on interests  
- ✅ Chat with GPT for open Q&A  
- ✅ Rate-limiting and request logging for fairness  
- ✅ Interactive inline menu for quick command access  
- ✅ Cloud-hosted using Heroku + Docker + Firebase Firestore

---

## 🧠 Project Architecture

```plaintext
User ↔ Telegram Bot ↔ Heroku Container
                         ↘
               ChatGPT API & Firebase
```

- **Telegram Bot**: Main user interface
- **Heroku**: Cloud hosting platform using a Docker container
- **Firebase (Firestore)**: Cloud database for storing user data & logs
- **OpenAI GPT API**: Used to answer open-ended queries and simulate recommendations

---

## ⚙️ Technologies Used

| Component        | Tech Stack              |
|------------------|-------------------------|
| Programming      | Python 3.11             |
| Bot Framework    | `python-telegram-bot`   |
| LLM Integration  | OpenAI Chat API         |
| Database         | Firebase Firestore      |
| Hosting          | Heroku (Docker based)   |
| Containerization | Dockerfile + GitHub CI  |
| Monitoring       | Heroku Logs             |

---

## 🚀 Deployment Guide

> ✅ You can deploy the project to Heroku by following these steps.

### 1. Clone the repo

```bash
git clone https://github.com/your-org/your-bot.git
cd your-bot
```

### 2. Prepare secrets

Create an `.env` file locally or set the following environment variables on Heroku:

```env
TELEGRAM_TOKEN=your-telegram-token
OPENAI_API_KEY=your-openai-key
GOOGLE_CREDENTIALS={...firebase serviceAccountKey JSON...}
APP_URL=https://yourapp.herokuapp.com
```

### 3. Deploy to Heroku

```bash
heroku create your-bot-name
heroku stack:set container
heroku config:set $(cat .env | xargs)
git push heroku main
```

---

## 💬 Telegram Command List

- `/start` - Welcome message with menu
- `/register <interests> [description]` - Save your interests
- `/events` - Get event recommendations
- `/add <keyword>` - Log a topic
- `/openai <message>` - Ask ChatGPT anything
- `/help` - Show all commands

---

## 📦 Folder Structure

```
src/
└── pybot/
    ├── chatbot.py         # Entry point
    ├── handlers.py        # Telegram command & message handlers
    ├── repository.py      # Firebase database layer
    ├── event.py, user.py  # Domain services
    └── chatgpt.py         # GPT interface logic
```

---

## 📄 License

This project is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).

You are free to share and adapt the source code **non-commercially**, with proper credit.

---

## 🎓 Course Info

- **Course**: COMP7940 Cloud Computing  
- **Instructor**: HKBU Spring 2024/25
- **Project Context**: Recommending online activities & matching users via ChatGPT

